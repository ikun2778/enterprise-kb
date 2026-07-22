"""
面试模拟 API
"""

import logging
from fastapi import APIRouter, HTTPException

from ..models.career import (
    MockInterviewStartRequest,
    MockInterviewAnswerRequest,
    MockInterviewStartResponse,
    MockInterviewAnswerResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mock-interview", tags=["面试模拟"])

_agent = None


def init_mock_interview_router(agent):
    global _agent
    _agent = agent


@router.post("/start", response_model=MockInterviewStartResponse)
async def start_interview(request: MockInterviewStartRequest):
    """开始一轮面试模拟，返回第一个问题"""
    if not _agent:
        raise HTTPException(status_code=503, detail="Agent服务未初始化")
    try:
        result = await _agent.mock_interview_start(
            position=request.position,
            skills=request.skills,
            difficulty=request.difficulty,
        )
        return MockInterviewStartResponse(**result)
    except Exception as e:
        logger.error(f"面试模拟失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/answer", response_model=MockInterviewAnswerResponse)
async def answer_question(request: MockInterviewAnswerRequest):
    """提交面试回答，获取评分和反馈"""
    if not _agent:
        raise HTTPException(status_code=503, detail="Agent服务未初始化")
    try:
        result = await _agent.mock_interview_answer(
            position=request.position,
            question=request.question,
            key_points=request.key_points,
            reference_answer=request.reference_answer,
            user_answer=request.user_answer,
        )
        return MockInterviewAnswerResponse(**result)
    except Exception as e:
        logger.error(f"面试评价失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
