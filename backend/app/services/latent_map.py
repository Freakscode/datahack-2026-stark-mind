"""Pipeline latent map: embeddings 768d → UMAP 2D → TF-IDF labels → gap detection.

Entrada: lista de puntos (id, title, abstract, domain, synthetic, base_paper_id?).
Salida: JSON con coords 2D, cluster id, keywords por cluster, y lista de gap
cells con score alto.

Diseño: deterministico (random_state fijo) para que la demo sea reproducible
entre refreshes. Embeddings se cachean por texto en .cache/embeddings.json
para no gastar cuota de Gemini cada refresh.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from umap import UMAP

from app.services.gemini import embed_batch

logger = logging.getLogger(__name__)


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _cached_embed(texts: list[str], cache_path: Path) -> list[list[float]]:
    """Embebe textos usando caché en disk keyed por sha256(text)."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache: dict[str, list[float]] = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            cache = {}

    missing_idx: list[int] = []
    missing_texts: list[str] = []
    out: list[list[float] | None] = [None] * len(texts)

    for i, t in enumerate(texts):
        h = _text_hash(t)
        if h in cache:
            out[i] = cache[h]
        else:
            missing_idx.append(i)
            missing_texts.append(t)

    if missing_texts:
        logger.info("embed %d nuevos (hit cache: %d)", len(missing_texts), len(texts) - len(missing_texts))
        new_embs = embed_batch(missing_texts)
        for idx, emb in zip(missing_idx, new_embs, strict=True):
            out[idx] = emb
            cache[_text_hash(texts[idx])] = emb
        cache_path.write_text(json.dumps(cache), encoding="utf-8")

    return [e if e is not None else [0.0] * 768 for e in out]


_STOPWORDS_ES = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "y", "o", "de", "del",
    "al", "a", "en", "con", "por", "para", "que", "qué", "se", "su", "sus", "lo",
    "es", "son", "ser", "este", "esta", "estos", "estas", "eso", "esa", "esos",
    "ese", "como", "cómo", "cuando", "cuando", "donde", "donde", "si", "sí", "no",
    "más", "mas", "pero", "sino", "también", "ya", "muy", "porque", "porqué",
    "sobre", "entre", "hasta", "desde", "sin", "contra", "mediante", "durante",
    "ante", "tras", "bajo", "hacia", "nuestro", "nuestra", "nuestros", "nuestras",
    "fue", "han", "ha", "he", "hay", "había", "habían", "sean", "puede", "pueden",
    "tiene", "tienen", "permite", "permiten", "además",
}


def _humanize_clusters(keywords_by_cluster: dict[int, list[str]], titles_by_cluster: dict[int, list[str]]) -> dict[int, str]:
    """Llama a Gemini para convertir keywords TF-IDF en labels humanos cortos.

    Ej: ["quantum","generative","learning"] → "Quantum generative ML"
    Si Gemini falla, devuelve fallback con join de top-2 keywords.
    """
    from app.services.gemini import generate_json

    fallback = {
        c: (", ".join(kw[:2]) if kw else f"cluster {c}")
        for c, kw in keywords_by_cluster.items()
    }
    if not keywords_by_cluster:
        return fallback

    # Construye prompt
    cluster_block = []
    for c, kw in keywords_by_cluster.items():
        titles = titles_by_cluster.get(c, [])[:3]
        cluster_block.append(
            f"cluster_{c}: keywords={kw[:6]}, title_samples={[t[:80] for t in titles]}"
        )
    prompt = (
        "Tengo clusters de papers científicos. Para cada cluster, dame un LABEL corto en español "
        "(3-5 palabras, en minúsculas salvo siglas) que describa la temática común. Evita palabras "
        "genéricas como 'investigación', 'análisis', 'método'. Sé específico y técnico.\n\n"
        + "\n".join(cluster_block)
        + "\n\nDevuelve JSON con la forma: {\"labels\": {\"0\": \"...\", \"1\": \"...\", ...}}"
    )
    try:
        result = generate_json(prompt)
        labels_map = result.get("labels", {}) if isinstance(result, dict) else {}
        out: dict[int, str] = {}
        for c in keywords_by_cluster:
            lbl = labels_map.get(str(c)) or labels_map.get(c)
            out[c] = lbl.strip() if isinstance(lbl, str) and lbl.strip() else fallback[c]
        return out
    except Exception as e:  # noqa: BLE001
        logger.warning("humanize_clusters fallback: %s", e)
        return fallback


def _cluster_keywords(texts: list[str], labels: np.ndarray, *, k: int, top_n: int = 5) -> dict[int, list[str]]:
    """TF-IDF por cluster → top_n keywords. Stopwords EN + ES."""
    import sklearn.feature_extraction.text as sk_text

    stop_combined = list(sk_text.ENGLISH_STOP_WORDS.union(_STOPWORDS_ES))
    vec = TfidfVectorizer(
        max_features=2000,
        stop_words=stop_combined,
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.8,
    )
    try:
        X = vec.fit_transform(texts)
    except ValueError:
        return {i: [] for i in range(k)}
    feats = vec.get_feature_names_out()
    out: dict[int, list[str]] = {}
    for c in range(k):
        mask = labels == c
        if mask.sum() == 0:
            out[c] = []
            continue
        scores = np.asarray(X[mask].mean(axis=0)).ravel()
        top_idx = scores.argsort()[::-1][:top_n]
        out[c] = [feats[i] for i in top_idx if scores[i] > 0]
    return out


def _detect_gaps(
    coords: np.ndarray,
    *,
    grid: int = 14,
    density_threshold: int = 1,
    neighbor_threshold: int = 3,
) -> list[dict]:
    """Divide el plano en grid×grid celdas. Una celda es gap si:
    - Tiene 0 papers
    - Está rodeada por >=neighbor_threshold celdas con density_threshold+ papers
    Retorna coord 2D del centro de la celda + gap_score (cuántos vecinos densos).
    """
    if len(coords) < 5:
        return []
    xs, ys = coords[:, 0], coords[:, 1]
    x_min, x_max = xs.min(), xs.max()
    y_min, y_max = ys.min(), ys.max()
    x_pad = (x_max - x_min) * 0.05 or 0.1
    y_pad = (y_max - y_min) * 0.05 or 0.1
    x_min, x_max = x_min - x_pad, x_max + x_pad
    y_min, y_max = y_min - y_pad, y_max + y_pad

    hist, x_edges, y_edges = np.histogram2d(xs, ys, bins=grid, range=[[x_min, x_max], [y_min, y_max]])
    gaps: list[dict] = []
    for i in range(grid):
        for j in range(grid):
            if hist[i, j] > 0:
                continue
            # Contar vecinos densos en ventana 3x3
            dense_neighbors = 0
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    if di == 0 and dj == 0:
                        continue
                    ni, nj = i + di, j + dj
                    if 0 <= ni < grid and 0 <= nj < grid:
                        if hist[ni, nj] >= density_threshold:
                            dense_neighbors += 1
            if dense_neighbors >= neighbor_threshold:
                cx = (x_edges[i] + x_edges[i + 1]) / 2
                cy = (y_edges[j] + y_edges[j + 1]) / 2
                gaps.append({
                    "x": float(cx),
                    "y": float(cy),
                    "score": int(dense_neighbors),
                })
    gaps.sort(key=lambda g: -g["score"])
    return gaps[:8]


def build_latent_map(
    points: list[dict],
    cache_path: Path,
    *,
    n_clusters: int = 4,
    min_cluster_size: int = 3,
) -> dict:
    """Entrada: lista de dicts con {id, title, abstract, domain, synthetic, ...}.

    Salida:
    {
      "points": [{id, x, y, cluster, title, domain, synthetic}, ...],
      "clusters": [{id, keywords, count}, ...],
      "gaps": [{x, y, score}, ...],
      "stats": {total, real, synthetic, dim_input, dim_output}
    }
    """
    if not points:
        return {"points": [], "clusters": [], "gaps": [], "stats": {"total": 0}}

    texts = [f"{p.get('title', '')}. {p.get('abstract', '')}" for p in points]
    embeddings = _cached_embed(texts, cache_path)
    emb_array = np.array(embeddings, dtype=np.float32)

    # UMAP 2D
    n = len(points)
    n_neighbors = min(15, max(2, n - 1))
    reducer = UMAP(
        n_components=2,
        n_neighbors=n_neighbors,
        min_dist=0.1,
        metric="cosine",
        random_state=42,
    )
    coords = reducer.fit_transform(emb_array)

    # KMeans clustering
    k = max(2, min(n_clusters, n // min_cluster_size))
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(emb_array)

    # Keywords por cluster
    keywords = _cluster_keywords(texts, labels, k=k)

    # Titles sample por cluster — sirven para el humanize prompt
    titles_by_cluster: dict[int, list[str]] = {c: [] for c in range(k)}
    for i, p in enumerate(points):
        c = int(labels[i])
        if len(titles_by_cluster[c]) < 3:
            titles_by_cluster[c].append(p.get("title", ""))

    # Labels humanos via Gemini
    human_labels = _humanize_clusters(keywords, titles_by_cluster)

    # Gap detection sobre coords 2D
    gaps = _detect_gaps(coords)

    # Asigna label del cluster más cercano a cada gap
    for g in gaps:
        min_d = float("inf")
        nearest = 0
        for i, p in enumerate(points):
            d = (coords[i, 0] - g["x"]) ** 2 + (coords[i, 1] - g["y"]) ** 2
            if d < min_d:
                min_d = d
                nearest = int(labels[i])
        g["near_cluster"] = nearest
        g["near_label"] = human_labels.get(nearest, "")

    out_points: list[dict] = []
    for i, p in enumerate(points):
        out_points.append({
            "id": p.get("id"),
            "x": float(coords[i, 0]),
            "y": float(coords[i, 1]),
            "cluster": int(labels[i]),
            "title": p.get("title", ""),
            "domain": p.get("domain", ""),
            "synthetic": bool(p.get("synthetic", False)),
            "base_paper_id": p.get("base_paper_id"),
            "year": p.get("year"),
        })

    clusters_out: list[dict] = []
    for c in range(k):
        mask = labels == c
        clusters_out.append({
            "id": int(c),
            "label": human_labels.get(c, ""),
            "keywords": keywords.get(c, []),
            "count": int(mask.sum()),
        })

    real_n = sum(1 for p in points if not p.get("synthetic", False))
    return {
        "points": out_points,
        "clusters": clusters_out,
        "gaps": gaps,
        "stats": {
            "total": n,
            "real": real_n,
            "synthetic": n - real_n,
            "dim_input": 768,
            "dim_output": 2,
            "n_clusters": k,
        },
    }
