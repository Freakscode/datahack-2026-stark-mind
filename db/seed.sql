-- =============================================================================
-- STARK-VIX · seed data
-- Prerequisitos: schema.sql ya aplicado.
-- =============================================================================

BEGIN;

-- =============================================================================
-- Catálogo de modelos
-- =============================================================================

-- --- OpenAI frontier mocks -------------------------------------------------
INSERT INTO models (id, provider, kind, execution_mode, input_cost_per_1m_tokens, output_cost_per_1m_tokens, embedding_dimension, context_window, default_tokens_per_second, notes) VALUES
('gpt-4o',                   'openai', 'llm',       'frontier_mock',  2.50, 10.00,  NULL,  128000, 120.0, 'LLM premium OpenAI'),
('gpt-4o-mini',              'openai', 'llm',       'frontier_mock',  0.15,  0.60,  NULL,  128000, 150.0, 'Balance precio/calidad OpenAI'),
('gpt-4.1',                  'openai', 'llm',       'frontier_mock',  2.00,  8.00,  NULL,  128000, 110.0, 'Mid-tier OpenAI'),
('gpt-4.1-mini',             'openai', 'llm',       'frontier_mock',  0.40,  1.60,  NULL,  128000, 140.0, 'Econo OpenAI 4.1'),
('o3-mini',                  'openai', 'llm',       'frontier_mock',  1.10,  4.40,  NULL,  200000,  80.0, 'Razonamiento extenso OpenAI'),
('text-embedding-3-small',   'openai', 'embedding', 'frontier_mock',  0.02,  NULL,  1536,     NULL,  NULL, 'Embedding barato OpenAI'),
('text-embedding-3-large',   'openai', 'embedding', 'frontier_mock',  0.13,  NULL,  3072,     NULL,  NULL, 'Embedding premium OpenAI');

-- --- Anthropic frontier mocks ----------------------------------------------
INSERT INTO models (id, provider, kind, execution_mode, input_cost_per_1m_tokens, output_cost_per_1m_tokens, embedding_dimension, context_window, default_tokens_per_second, notes) VALUES
('claude-opus-4-7',          'anthropic', 'llm',       'frontier_mock', 15.00, 75.00,  NULL, 200000,  60.0, 'Claude flagship'),
('claude-sonnet-4-6',        'anthropic', 'llm',       'frontier_mock',  3.00, 15.00,  NULL, 200000,  80.0, 'Default síntesis propuesto'),
('claude-haiku-4-5',         'anthropic', 'llm',       'frontier_mock',  1.00,  5.00,  NULL, 200000, 180.0, 'Agentes rápidos'),
('voyage-3',                 'voyage',    'embedding', 'frontier_mock',  0.06,  NULL,  1024,   NULL,  NULL, 'Drop-in swap con bge-large-en-v1.5');

-- --- Google frontier mocks -------------------------------------------------
INSERT INTO models (id, provider, kind, execution_mode, input_cost_per_1m_tokens, output_cost_per_1m_tokens, embedding_dimension, context_window, default_tokens_per_second, notes) VALUES
('gemini-2.5-pro',           'google', 'llm', 'frontier_mock', 1.25, 5.00,  NULL, 1000000, 110.0, 'Alternativa premium Gemini'),
('gemini-2.5-flash',         'google', 'llm', 'frontier_mock', 0.075, 0.30, NULL, 1000000, 200.0, 'Más barato del mercado');

-- --- Local (Track 1 · ejecución real) --------------------------------------
INSERT INTO models (id, provider, kind, execution_mode, input_cost_per_1m_tokens, output_cost_per_1m_tokens, embedding_dimension, context_window, default_tokens_per_second, notes) VALUES
('bge-large-en-v1.5',        'local', 'embedding', 'local', NULL, NULL, 1024,   NULL,  NULL, 'Default embedding local, drop-in con voyage-3'),
('nomic-embed-text-v1',      'local', 'embedding', 'local', NULL, NULL,  768,   NULL,  NULL, 'Alternativa más ligera'),
('llama3.1:8b-instruct',     'local', 'llm',       'local', NULL, NULL, NULL, 128000,  NULL, 'Agentes simples (Ollama)'),
('qwen2.5:7b-instruct',      'local', 'llm',       'local', NULL, NULL, NULL, 128000,  NULL, 'Default síntesis local (Ollama, buen JSON)'),
('mistral:7b-instruct',      'local', 'llm',       'local', NULL, NULL, NULL,  32000,  NULL, 'Fallback local (Ollama)');


-- =============================================================================
-- Proyectos demo
-- =============================================================================
INSERT INTO projects (id, topic, description, status, metadata) VALUES
('11111111-1111-1111-1111-111111111111',
 'Agentic RAG con citas trazables',
 'Estado del arte 2025-2026 en arquitecturas multiagente para investigación con citation traceability.',
 'in_progress',
 '{"seed": true, "priority": "demo"}'::jsonb),
('22222222-2222-2222-2222-222222222222',
 'Evaluación de LLMs para tareas de razonamiento',
 'Benchmarks recientes y métricas de faithfulness en LLM agents.',
 'pending',
 '{"seed": true}'::jsonb),
('33333333-3333-3333-3333-333333333333',
 'Arquitecturas de vector DB para multimodal',
 'Comparar pgvector, Pinecone y Weaviate para retrieval con texto + figuras.',
 'completed',
 '{"seed": true}'::jsonb);

-- =============================================================================
-- Papers demo (abstracts cortos para no inflar el seed)
-- =============================================================================
INSERT INTO papers (id, source, title, abstract, authors, venue, published_at, doi, url, pdf_url, citations_count, raw_metadata) VALUES
('2405.12345',
 'arxiv',
 'ReAct++: Iterative Tool Use in Agentic Pipelines',
 'We propose ReAct++, an extension to ReAct that introduces iterative self-correction for tool-augmented reasoning in research literature review.',
 ARRAY['Ada Lovelace','Charles Babbage'],
 'arXiv preprint',
 '2025-05-10',
 '10.48550/arXiv.2405.12345',
 'https://arxiv.org/abs/2405.12345',
 'https://arxiv.org/pdf/2405.12345.pdf',
 42,
 '{"seed": true}'::jsonb),
('2510.09876',
 'arxiv',
 'Citation-Guard: A Lightweight Hallucination Detector for RAG',
 'Citation-Guard post-processes RAG outputs and rejects claims that do not entail their cited evidence, improving groundedness by 18 points.',
 ARRAY['Grace Hopper','Alan Turing'],
 'arXiv preprint',
 '2025-10-03',
 '10.48550/arXiv.2510.09876',
 'https://arxiv.org/abs/2510.09876',
 'https://arxiv.org/pdf/2510.09876.pdf',
 7,
 '{"seed": true}'::jsonb),
('2512.00001',
 'arxiv',
 'Multi-Agent RAG Platforms: A Survey',
 'A systematic survey of 40 multi-agent RAG systems, with taxonomy of orchestration patterns and evaluation harnesses.',
 ARRAY['Donald Knuth','Barbara Liskov'],
 'arXiv preprint',
 '2025-12-18',
 '10.48550/arXiv.2512.00001',
 'https://arxiv.org/abs/2512.00001',
 'https://arxiv.org/pdf/2512.00001.pdf',
 12,
 '{"seed": true}'::jsonb),
('10.1145/3636765',
 'scholar',
 'Evaluation Harness Design for Agentic LLM Systems',
 'A principled taxonomy of metrics for evaluating agentic LLM pipelines, with emphasis on groundedness and faithfulness.',
 ARRAY['Judea Pearl','Yoshua Bengio'],
 'ACM CHI 2026',
 '2026-01-20',
 '10.1145/3636765',
 'https://dl.acm.org/doi/10.1145/3636765',
 NULL,
 3,
 '{"seed": true}'::jsonb),
('2604.00042',
 'arxiv',
 'Voyage-3 vs BGE-Large: A Drop-in Embedding Benchmark',
 'We show that BGE-Large (1024d) matches Voyage-3 within 1.2 MRR points on SciDocs, enabling cost-free local swaps.',
 ARRAY['Edsger Dijkstra'],
 'arXiv preprint',
 '2026-02-14',
 '10.48550/arXiv.2604.00042',
 'https://arxiv.org/abs/2604.00042',
 'https://arxiv.org/pdf/2604.00042.pdf',
 2,
 '{"seed": true}'::jsonb);

-- =============================================================================
-- Relaciones project_papers (demo)
-- =============================================================================
INSERT INTO project_papers (project_id, paper_id, relevance_score, added_by) VALUES
('11111111-1111-1111-1111-111111111111', '2405.12345',      0.92, 'discovery_agent'),
('11111111-1111-1111-1111-111111111111', '2510.09876',      0.95, 'discovery_agent'),
('11111111-1111-1111-1111-111111111111', '2512.00001',      0.87, 'discovery_agent'),
('22222222-2222-2222-2222-222222222222', '10.1145/3636765', 0.89, 'discovery_agent'),
('33333333-3333-3333-3333-333333333333', '2604.00042',      0.94, 'user');

-- =============================================================================
-- Chunks demo (sin embeddings — los llena E3.4 con el pipeline real)
-- =============================================================================
INSERT INTO chunks (paper_id, chunk_index, section, page, text, token_count, embedded_by) VALUES
('2510.09876', 0, 'Abstract', 1,
 'Citation-Guard post-processes RAG outputs and rejects claims that do not entail their cited evidence, improving groundedness by 18 points on the LitGround benchmark.',
 38, 'bge-large-en-v1.5'),
('2510.09876', 1, 'Method',   3,
 'We use a lightweight entailment classifier built on top of DeBERTa-v3 fine-tuned on 50k human-labeled claim-evidence pairs.',
 30, 'bge-large-en-v1.5'),
('2405.12345', 0, 'Abstract', 1,
 'ReAct++ introduces iterative self-correction for tool-augmented reasoning in research literature review, achieving 12% higher recall on arXiv retrieval.',
 32, 'bge-large-en-v1.5');

-- =============================================================================
-- Query + Report + Citations demo (para que el frontend pueda renderizar algo real)
-- =============================================================================
INSERT INTO queries (id, project_id, query_text, query_type, intent, status, execution_mode, created_at, completed_at) VALUES
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
 '11111111-1111-1111-1111-111111111111',
 '¿Cuáles son los patrones de citation-guard más efectivos reportados en 2025?',
 'qa',
 'qa_with_citations',
 'completed',
 'local',
 now() - interval '2 hours',
 now() - interval '1 hour 55 minutes');

INSERT INTO agent_events (query_id, agent, action, status, payload, model_id, input_tokens, output_tokens, tokens_per_second, latency_ms, cost_estimated_usd) VALUES
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'orchestrator', 'route_intent',     'completed',
 '{"intent": "qa"}'::jsonb, 'qwen2.5:7b-instruct', 60, 30, 165.4, 240, 0.000000),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'discovery',    'search_arxiv',      'completed',
 '{"results": 3, "query": "citation guard RAG"}'::jsonb, NULL, NULL, NULL, NULL, 320, NULL),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'reader',       'retrieve_chunks',   'completed',
 '{"chunks_retrieved": 5, "top_k": 5}'::jsonb, 'bge-large-en-v1.5', NULL, NULL, NULL, 180, NULL),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'synthesizer',  'draft_report',      'completed',
 '{"claims": 2}'::jsonb, 'qwen2.5:7b-instruct', 1200, 420, 142.8, 3400, 0.000000),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'citation_guard','validate_citations','completed',
 '{"verified": 2, "rejected": 0}'::jsonb, 'claude-haiku-4-5', 1800, 120, 180.0, 950, 0.002400);

INSERT INTO reports (id, query_id, title, summary, body_markdown, structured_output, groundedness_score, citation_accuracy_score, faithfulness_score) VALUES
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
 'Patrones de citation-guard en 2025',
 'Dos enfoques destacan: entailment classifier ligero y auto-corrección iterativa.',
 E'Los patrones más efectivos reportados en 2025 son:\n\n1. **Entailment classifier ligero** basado en DeBERTa-v3 que filtra claims sin soporte [1].\n2. **Self-correction iterativa** estilo ReAct++ que mejora recall en retrieval [2].\n\nEl primer enfoque mejoró groundedness en 18 puntos sobre el benchmark LitGround.',
 '{"timeline": [{"year": 2025, "paper_id": "2510.09876", "technique": "entailment classifier"}, {"year": 2025, "paper_id": "2405.12345", "technique": "self-correction"}]}'::jsonb,
 0.940,
 0.980,
 0.910);

INSERT INTO citations (report_id, citation_key, paper_id, chunk_id, quote, page, verified, verified_at) VALUES
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '1', '2510.09876', 1,
 'improving groundedness by 18 points', 1, TRUE, now() - interval '1 hour 55 minutes'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '2', '2405.12345', 3,
 'iterative self-correction for tool-augmented reasoning', 1, TRUE, now() - interval '1 hour 55 minutes');

-- =============================================================================
-- Notas demo
-- =============================================================================
INSERT INTO notes (project_id, body) VALUES
('11111111-1111-1111-1111-111111111111',
 'Priorizar arXiv sobre Scholar para este tema — Scholar duplica mucho.'),
('11111111-1111-1111-1111-111111111111',
 'Revisar si Citation-Guard vale la pena integrarlo como post-processor propio.');

-- =============================================================================
-- Eval run demo
-- =============================================================================
INSERT INTO eval_runs (query_id, dataset_version, groundedness, faithfulness, citation_accuracy, judge_model_id, notes) VALUES
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'v0.1', 0.940, 0.910, 0.980, 'claude-haiku-4-5',
 'Seed eval run para tests del runner. Judge mockeado.');

COMMIT;
