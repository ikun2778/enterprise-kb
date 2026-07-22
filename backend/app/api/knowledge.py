"""
知识库管理API接口
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..models.schemas import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["知识库"])

# 全局实例
rag_engine = None


def init_knowledge_router(rag_engine_instance):
    """初始化知识库路由"""
    global rag_engine
    rag_engine = rag_engine_instance


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., min_length=1, description="搜索查询")
    top_k: int = Field(5, ge=1, le=20, description="返回结果数量")


@router.get("/stats")
async def get_stats():
    """获取知识库统计信息"""
    if not rag_engine:
        raise HTTPException(status_code=500, detail="RAG引擎未初始化")

    stats = rag_engine.get_stats()
    return ApiResponse(data=stats)


@router.post("/rebuild")
async def rebuild_index():
    """重建知识库索引"""
    if not rag_engine:
        raise HTTPException(status_code=500, detail="RAG引擎未初始化")

    try:
        from ..config import KNOWLEDGE_BASE_DIR
        rag_engine.initialize(str(KNOWLEDGE_BASE_DIR), force_rebuild=True)
        stats = rag_engine.get_stats()
        return ApiResponse(message="索引重建成功", data=stats)
    except Exception as e:
        logger.error(f"重建索引失败: {e}")
        raise HTTPException(status_code=500, detail=f"重建索引失败: {str(e)}")


@router.post("/search")
async def search_knowledge(request: SearchRequest):
    """搜索知识库"""
    if not rag_engine:
        raise HTTPException(status_code=500, detail="RAG引擎未初始化")

    try:
        docs = rag_engine.hybrid_search(request.query, top_k=request.top_k)
        results = []
        for doc in docs:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": doc.metadata.get("rrf_score", 0)
            })
        return ApiResponse(data=results)
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")
