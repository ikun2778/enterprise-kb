"""
CareerCopilot - FastAPI主入口
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import config, ensure_dirs, KNOWLEDGE_BASE_DIR
from .core.rag_engine import RAGEngine
from .core.agent import Agent
from .core.memory import ConversationMemory
from .api import chat, knowledge, document
from .api import analyze
from .api import mock_interview

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局实例
rag_engine = None
agent = None
memory = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global rag_engine, agent, memory

    logger.info("=" * 50)
    logger.info("  Loading CareerCopilot")
    logger.info("=" * 50)

    # 确保目录存在
    ensure_dirs()

    # 初始化RAG引擎
    logger.info(f"  Embedding Model: {config.embedding.model_name}")
    rag_engine = RAGEngine(config)

    # 初始化知识库（支持加载已有FAISS索引）
    data_path = str(KNOWLEDGE_BASE_DIR)
    rag_engine.initialize(data_path)
    stats = rag_engine.get_stats()
    logger.info(f"  Knowledge Documents: {stats.get('document_count', 0)}")
    logger.info(f"  Vector Store: {'loaded' if rag_engine.vector_store else 'not ready'}")

    # 初始化记忆管理器
    memory = ConversationMemory(max_history=20)

    # 初始化Agent
    agent = Agent(config, rag_engine, memory)
    tool_count = sum(1 for t in [
        agent.jd_parser, agent.resume_parser, agent.skill_matcher,
        agent.knowledge_search, agent.interview_generator,
        agent.resume_optimizer, agent.mock_interview, agent.job_recommender,
    ] if t is not None)
    logger.info(f"  Agent Tools: {tool_count}")

    # 初始化API路由
    chat.init_chat_router(agent, memory)
    knowledge.init_knowledge_router(rag_engine)
    document.init_document_router(rag_engine)
    analyze.init_career_router(agent)
    mock_interview.init_mock_interview_router(agent)

    logger.info(f"  LLM Model: {config.llm.model}")
    logger.info("-" * 50)
    logger.info("  Service Ready")
    logger.info("=" * 50)
    yield

    logger.info("应用关闭")


# 创建FastAPI应用
app = FastAPI(
    title=config.app_name,
    version=config.version,
    description="CareerCopilot - 基于RAG+Agent的智能求职分析系统",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")
app.include_router(document.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")
app.include_router(mock_interview.router, prefix="/api")


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": config.app_name,
        "version": config.version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "rag_engine_ready": rag_engine is not None,
        "agent_ready": agent is not None
    }


@app.get("/api/info")
async def app_info():
    """应用信息"""
    stats = rag_engine.get_stats() if rag_engine else {}
    return {
        "name": config.app_name,
        "version": config.version,
        "stats": stats,
        "llm_model": config.llm.model,
        "embedding_model": config.embedding.model_name
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug
    )
