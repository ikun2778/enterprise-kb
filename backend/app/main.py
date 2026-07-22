"""
企业智能知识库助手 - FastAPI主入口
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

    logger.info("正在初始化应用...")

    # 确保目录存在
    ensure_dirs()

    # 初始化RAG引擎
    rag_engine = RAGEngine(config)
    logger.info("RAG引擎初始化完成")

    # 初始化知识库
    data_path = str(KNOWLEDGE_BASE_DIR)
    logger.info(f"加载知识库: {data_path}")
    rag_engine.initialize(data_path)

    # 初始化记忆管理器
    memory = ConversationMemory(max_history=20)
    logger.info("记忆管理器初始化完成")

    # 初始化Agent
    agent = Agent(config, rag_engine, memory)
    logger.info("Agent初始化完成")

    # 初始化API路由
    chat.init_chat_router(agent, memory)
    knowledge.init_knowledge_router(rag_engine)
    document.init_document_router(rag_engine)
    logger.info("API路由初始化完成")

    # 打印统计信息
    stats = rag_engine.get_stats()
    logger.info(f"知识库统计: {stats}")

    logger.info("应用初始化完成！")
    yield

    logger.info("应用关闭")


# 创建FastAPI应用
app = FastAPI(
    title=config.app_name,
    version=config.version,
    description="基于RAG+Agent的企业智能知识库问答系统",
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
