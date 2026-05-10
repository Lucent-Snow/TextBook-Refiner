"""Application settings loaded from environment variables."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # DeepSeek chat
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-pro"
    deepseek_fallback_model: str = "deepseek-v4-flash"
    deepseek_reasoning_effort: str = "high"
    deepseek_thinking_type: str = "enabled"

    # ModelScope embeddings
    modelscope_api_key: str = ""
    modelscope_base_url: str = "https://api-inference.modelscope.cn/v1"
    modelscope_embedding_model: str = "Qwen/Qwen3-Embedding-8B"

    # PDF parsing
    pdf_parse_provider: str = "pymupdf"  # auto, pymupdf, mineru
    pdf_min_cjk_ratio: float = 0.2
    pdf_max_replacement_ratio: float = 0.01

    # MinerU document parsing
    mineru_api_key: str = ""
    mineru_script_dir: str = ""
    mineru_python: str = ""
    mineru_output_dir: str = ""
    mineru_model: str = "vlm"
    mineru_max_pages: int = 180
    mineru_max_file_mb: int = 190
    mineru_timeout_seconds: int = 1800

    # Knowledge graph construction
    kg_extract_concurrency: int = 4
    kg_min_section_chars: int = 120
    kg_max_section_input_chars: int = 6000
    kg_max_concepts_per_section: int = 8
    kg_max_edges_per_section: int = 12
    kg_extraction_max_tokens: int = 2048

    # Time-critical RAG-only mode
    rag_only_mode: bool = False
    rag_only_project_id: str = "proj_rag_fast"
    lexical_rag_top_k: int = 8

    # ChromaDB
    chroma_host: Optional[str] = None
    chroma_port: int = 8000

    # Data paths
    data_root: str = str(Path.cwd() / "data")
    textbooks_dir: Optional[str] = None

    # App
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    @property
    def deepseek_extra_body(self) -> dict:
        return {"thinking": {"type": self.deepseek_thinking_type}}


settings = Settings()
