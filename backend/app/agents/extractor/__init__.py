"""Extractor agent: PDF → PaperExtraction estructurado.

Arquitectura:
  - prompts.py : templates por nodo, pensados para Gemma 2 pero compatibles
                  con cualquier provider del factory.
  - nodes.py   : funciones async que invocan el LLM y parsean JSON.
  - graph.py   : ensambla LangGraph StateGraph con extracciones paralelas.

Uso programático:
    from app.agents.extractor.graph import build_extractor_graph
    graph = build_extractor_graph()
    result = await graph.ainvoke({"pdf_path": "...", "llm_config": cfg})
"""
from app.agents.extractor.graph import ExtractorState, build_extractor_graph

__all__ = ["ExtractorState", "build_extractor_graph"]
