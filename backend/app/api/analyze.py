"""
求职分析API
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..models.career import CareerAnalyzeRequest, CareerAnalyzeResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/career", tags=["求职分析"])

_agent = None


def init_career_router(agent):
    global _agent
    _agent = agent


@router.post("/analyze", response_model=CareerAnalyzeResponse)
async def analyze_career(request: CareerAnalyzeRequest):
    """求职分析接口（完整响应）"""
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


@router.post("/analyze-stream")
async def analyze_career_stream(request: CareerAnalyzeRequest):
    """求职分析接口（SSE流式 — 逐步推送进度）"""
    if not _agent:
        raise HTTPException(status_code=503, detail="Agent服务未初始化")

    async def event_generator():
        try:
            async for event in _agent.career_analyze_stream(
                jd_text=request.jd_text,
                resume_text=request.resume_text,
                conversation_id=request.conversation_id,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"流式分析失败: {e}", exc_info=True)
            yield f"data: {json.dumps({'step': -1, 'status': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
