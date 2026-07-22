"""
求职分析API
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from ..models.career import CareerAnalyzeRequest, CareerAnalyzeResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/career", tags=["求职分析"])

# 全局实例（由 init_career_router 初始化）
_agent = None


def init_career_router(agent):
    """初始化求职分析路由"""
    global _agent
    _agent = agent


@router.post("/analyze", response_model=CareerAnalyzeResponse)
async def analyze_career(request: CareerAnalyzeRequest):
    """
    求职分析接口

    上传JD和简历文本，系统自动完成：
    1. JD解析
    2. 简历解析
    3. 技能匹配
    4. 知识库检索学习资料
    5. 面试问题生成
    6. 输出求职分析报告
    """
    if not _agent:
        raise HTTPException(status_code=503, detail="Agent服务未初始化")

    try:
        result = await _agent.career_analyze(
            jd_text=request.jd_text,
            resume_text=request.resume_text,
            conversation_id=request.conversation_id,
        )
        return CareerAnalyzeResponse(**result)
    except Exception as e:
        logger.error(f"求职分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")
