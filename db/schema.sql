-- =============================================================================
-- STARK-VIX · Schema PostgreSQL 16 + pgvector
-- Reto DataHack 2026 #3
-- =============================================================================

BEGIN;

-- Extensiones requeridas
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- para gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- índice GIN de título

-- =============================================================================
-- Trigger helper: mantener updated_at al día
-- =============================================================================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 1. models — catálogo de LLMs y embeddings (local + frontier mock)
-- =============================================================================
CREATE TABLE models (
    id                          TEXT PRIMARY KEY,
    provider                    TEXT NOT NULL CHECK (provider IN ('local','openai','anthropic','google','voyage')),
    kind                        TEXT NOT NULL CHECK (kind IN ('embedding','llm','rerank')),
    execution_mode              TEXT NOT NULL CHECK (execution_mode IN ('local','frontier_mock')),
    input_cost_per_1m_tokens    NUMERIC(10,4),
    output_cost_per_1m_tokens   NUMERIC(10,4),
    embedding_dimension         INT,
    context_window              INT,
    default_tokens_per_second   NUMERIC(10,2),  -- para mocks cuando no hay tok/s real
    is_active                   BOOLEAN NOT NULL DEFAULT TRUE,
    notes                       TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT models_mock_requires_cost CHECK (
        execution_mode = 'local' OR (input_cost_per_1m_tokens IS NOT NULL)
    ),
    CONSTRAINT models_embedding_requires_dim CHECK (
        kind <> 'embedding' OR embedding_dimension IS NOT NULL
    )
);

CREATE INDEX idx_models_provider ON models(provider) WHERE is_active;
CREATE INDEX idx_models_kind     ON models(kind)     WHERE is_active;

-- =============================================================================
-- 2. projects — una investigación completa del usuario
-- =============================================================================
CREATE TABLE projects (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic       TEXT NOT NULL,
    description TEXT,
    status      TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','in_progress','completed','archived')),
    metadata    JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_created_at ON projects(created_at DESC);

CREATE TRIGGER trg_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =============================================================================
-- 3. papers — catálogo global (dedupe por DOI / arxiv_id)
-- =============================================================================
CREATE TABLE papers (
    id               TEXT PRIMARY KEY,  -- arxiv_id o DOI
    source           TEXT NOT NULL CHECK (source IN ('arxiv','scholar','manual')),
    title            TEXT NOT NULL,
    abstract         TEXT,
    authors          TEXT[] NOT NULL DEFAULT '{}',
    venue            TEXT,
    published_at     DATE,
    doi              TEXT UNIQUE,
    url              TEXT,
    pdf_url          TEXT,
    citations_count  INT,
    raw_metadata     JSONB NOT NULL DEFAULT '{}'::jsonb,
    ingested_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_papers_source       ON papers(source);
CREATE INDEX idx_papers_published    ON papers(published_at DESC);
CREATE INDEX idx_papers_doi          ON papers(doi) WHERE doi IS NOT NULL;
CREATE INDEX idx_papers_title_trgm   ON papers USING gin (title gin_trgm_ops);

-- =============================================================================
-- 4. chunks — fragmentos con embedding pgvector (1024d)
-- =============================================================================
CREATE TABLE chunks (
    id            BIGSERIAL PRIMARY KEY,
    paper_id      TEXT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    chunk_index   INT  NOT NULL,
    section       TEXT,
    page          INT,
    figure_ref    TEXT,
    text          TEXT NOT NULL,
    token_count   INT,
    embedding     VECTOR(1024),
    embedded_by   TEXT REFERENCES models(id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (paper_id, chunk_index)
);

CREATE INDEX idx_chunks_paper ON chunks(paper_id);
-- Índice vectorial: ivfflat con cosine (recomendado para corpus 5k-50k chunks)
CREATE INDEX idx_chunks_embedding_cosine
    ON chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- =============================================================================
-- 5. project_papers — N:M entre projects y papers
-- =============================================================================
CREATE TABLE project_papers (
    project_id       UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    paper_id         TEXT NOT NULL REFERENCES papers(id)   ON DELETE CASCADE,
    relevance_score  NUMERIC(6,4),
    added_by         TEXT NOT NULL CHECK (added_by IN ('discovery_agent','user')),
    added_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (project_id, paper_id)
);

CREATE INDEX idx_project_papers_project ON project_papers(project_id);
CREATE INDEX idx_project_papers_paper   ON project_papers(paper_id);

-- =============================================================================
-- 6. queries — pregunta/búsqueda del usuario en un proyecto
-- =============================================================================
CREATE TABLE queries (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id    UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    query_text    TEXT NOT NULL,
    query_type    TEXT CHECK (query_type IN ('search','deep_read','compare','trend','qa')),
    intent        TEXT,  -- clasificado por el router del orchestrator
    status        TEXT NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending','running','completed','failed')),
    error         TEXT,
    execution_mode TEXT NOT NULL DEFAULT 'local'
                  CHECK (execution_mode IN ('local','frontier_mock','hybrid')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at  TIMESTAMPTZ
);

CREATE INDEX idx_queries_project ON queries(project_id, created_at DESC);
CREATE INDEX idx_queries_status  ON queries(status);

-- =============================================================================
-- 7. agent_events — stream de pensamiento persistido + telemetría
-- =============================================================================
CREATE TABLE agent_events (
    id                    BIGSERIAL PRIMARY KEY,
    query_id              UUID NOT NULL REFERENCES queries(id) ON DELETE CASCADE,
    agent                 TEXT NOT NULL CHECK (agent IN (
                              'orchestrator','discovery','reader',
                              'comparator','synthesizer','citation_guard'
                          )),
    action                TEXT NOT NULL,
    status                TEXT NOT NULL CHECK (status IN ('started','in_progress','completed','failed')),
    payload               JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- Telemetría
    model_id              TEXT REFERENCES models(id),
    input_tokens          INT,
    output_tokens         INT,
    tokens_per_second     NUMERIC(10,2),
    latency_ms            INT,
    cost_estimated_usd    NUMERIC(10,6),
    emitted_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_events_query  ON agent_events(query_id, emitted_at);
CREATE INDEX idx_events_agent  ON agent_events(agent);
CREATE INDEX idx_events_model  ON agent_events(model_id);

-- =============================================================================
-- 8. reports — respuesta sintetizada markdown + structured_output JSONB
-- =============================================================================
CREATE TABLE reports (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_id                  UUID NOT NULL UNIQUE REFERENCES queries(id) ON DELETE CASCADE,
    title                     TEXT,
    summary                   TEXT,
    body_markdown             TEXT NOT NULL,
    structured_output         JSONB NOT NULL DEFAULT '{}'::jsonb,  -- comparisons, timelines, etc.
    groundedness_score        NUMERIC(4,3),
    citation_accuracy_score   NUMERIC(4,3),
    faithfulness_score        NUMERIC(4,3),
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_reports_query ON reports(query_id);

CREATE TRIGGER trg_reports_updated_at
    BEFORE UPDATE ON reports
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =============================================================================
-- 9. citations — anchor trazable (paper + chunk + pag/figura)
-- =============================================================================
CREATE TABLE citations (
    id              BIGSERIAL PRIMARY KEY,
    report_id       UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    citation_key    TEXT NOT NULL,  -- '1', '2', ... para mapear [1] en markdown
    paper_id        TEXT NOT NULL REFERENCES papers(id),
    chunk_id        BIGINT REFERENCES chunks(id),
    quote           TEXT,
    page            INT,
    figure_ref      TEXT,
    verified        BOOLEAN NOT NULL DEFAULT FALSE,
    verified_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (report_id, citation_key)
);

CREATE INDEX idx_citations_report   ON citations(report_id);
CREATE INDEX idx_citations_paper    ON citations(paper_id);
CREATE INDEX idx_citations_verified ON citations(verified);

-- =============================================================================
-- 10. notes — notas libres del usuario por proyecto
-- =============================================================================
CREATE TABLE notes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    body        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_notes_project ON notes(project_id, created_at DESC);

CREATE TRIGGER trg_notes_updated_at
    BEFORE UPDATE ON notes
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =============================================================================
-- 11. eval_runs — scores de eval por query (opcional, alimenta el runner)
-- =============================================================================
CREATE TABLE eval_runs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_id            UUID REFERENCES queries(id) ON DELETE CASCADE,
    dataset_version     TEXT,  -- ej: 'v1.0'
    groundedness        NUMERIC(4,3),
    faithfulness        NUMERIC(4,3),
    citation_accuracy   NUMERIC(4,3),
    judge_model_id      TEXT REFERENCES models(id),
    notes               TEXT,
    ran_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_eval_runs_query ON eval_runs(query_id);

-- =============================================================================
-- Vistas útiles para el dashboard
-- =============================================================================

-- Coste total por proyecto
CREATE VIEW v_project_cost AS
SELECT
    p.id AS project_id,
    p.topic,
    COUNT(DISTINCT q.id)                                  AS total_queries,
    COUNT(DISTINCT ae.id)                                 AS total_events,
    COALESCE(SUM(ae.cost_estimated_usd), 0)               AS total_cost_usd,
    COALESCE(SUM(ae.input_tokens), 0)                     AS total_input_tokens,
    COALESCE(SUM(ae.output_tokens), 0)                    AS total_output_tokens
FROM projects p
LEFT JOIN queries q       ON q.project_id = p.id
LEFT JOIN agent_events ae ON ae.query_id = q.id
GROUP BY p.id, p.topic;

-- Agent load: queries corriendo ahora
CREATE VIEW v_agent_load AS
SELECT
    ae.agent,
    COUNT(DISTINCT q.id) AS active_queries
FROM queries q
JOIN agent_events ae ON ae.query_id = q.id
WHERE q.status = 'running'
  AND ae.status IN ('started','in_progress')
GROUP BY ae.agent;

COMMIT;

-- =============================================================================
-- Fin del schema
-- =============================================================================
