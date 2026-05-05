"""项目全局配置：从 .env 文件读取 LLM 和 Embedding 配置。"""

from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv
import os

# 加载项目根目录下的 .env 文件
_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env")


class LLMSettings(BaseModel):
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    model_flash: str = "deepseek/deepseek-v4-flash"
    model_pro: str = "deepseek/deepseek-v4-pro"


class EmbeddingSettings(BaseModel):
    api_key: str = ""
    base_url: str = "https://api.siliconflow.cn/v1"
    model: str = "Qwen/Qwen3-Embedding-4B"
    dimensions: int = 1024
    reranker_model: str = "Qwen/Qwen3-Reranker-4B"


class AppSettings(BaseModel):
    llm: LLMSettings
    embedding: EmbeddingSettings
    project_root: Path = _project_root
    data_dir: Path = _project_root / "data"
    reports_dir: Path = _project_root / "reports"
    llm_logs_dir: Path = _project_root / "reports" / "llm_logs"


def load_settings() -> AppSettings:
    return AppSettings(
        llm=LLMSettings(
            api_key=os.getenv("LLM_API_KEY", ""),
            base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
            model=os.getenv("LLM_MODEL", "deepseek-chat"),
            model_flash=os.getenv("LLM_MODEL_FLASH", "deepseek/deepseek-v4-flash"),
            model_pro=os.getenv("LLM_MODEL_PRO", "deepseek/deepseek-v4-pro"),
        ),
        embedding=EmbeddingSettings(
            api_key=os.getenv("EMBEDDING_API_KEY", ""),
            base_url=os.getenv("EMBEDDING_BASE_URL", "https://api.siliconflow.cn/v1"),
            model=os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-4B"),
            dimensions=int(os.getenv("EMBEDDING_DIMENSIONS", "1024")),
            reranker_model=os.getenv("RERANKER_MODEL", "Qwen/Qwen3-Reranker-4B"),
        ),
    )


settings = load_settings()
