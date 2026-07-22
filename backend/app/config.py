"""
企业知识库助手 - 配置文件
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

# 加载环境变量（指定路径）
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
KNOWLEDGE_BASE_DIR = DATA_DIR / "knowledge_base"
VECTOR_STORE_DIR = DATA_DIR / "vector_store"
UPLOAD_DIR = DATA_DIR / "uploads"


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: str = os.getenv("LLM_PROVIDER", "moonshot")
    model: str = os.getenv("LLM_MODEL", "moonshot-v1-8k")
    api_key: str = os.getenv("MOONSHOT_API_KEY", "")
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))


@dataclass
class EmbeddingConfig:
    """Embedding配置"""
    model_name: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
    device: str = os.getenv("EMBEDDING_DEVICE", "cpu")
    normalize: bool = True


@dataclass
class VectorStoreConfig:
    """向量存储配置"""
    type: str = os.getenv("VECTOR_STORE_TYPE", "faiss")
    persist_dir: str = str(VECTOR_STORE_DIR)
    collection_name: str = "knowledge_base"


@dataclass
class DatabaseConfig:
    """数据库配置"""
    url: str = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/app.db")


@dataclass
class RAGConfig:
    """RAG配置"""
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    top_k: int = int(os.getenv("TOP_K", "5"))
    similarity_threshold: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.3"))


@dataclass
class AppConfig:
    """应用配置"""
    app_name: str = "企业智能知识库助手"
    version: str = "1.0.0"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))

    # 子配置
    llm: Optional[LLMConfig] = field(default_factory=LLMConfig)
    embedding: Optional[EmbeddingConfig] = field(default_factory=EmbeddingConfig)
    vector_store: Optional[VectorStoreConfig] = field(default_factory=VectorStoreConfig)
    database: Optional[DatabaseConfig] = field(default_factory=DatabaseConfig)
    rag: Optional[RAGConfig] = field(default_factory=RAGConfig)


# 全局配置实例
config = AppConfig()


# 确保目录存在
def ensure_dirs():
    """确保必要的目录存在"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
