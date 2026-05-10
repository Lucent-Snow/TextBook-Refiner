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
