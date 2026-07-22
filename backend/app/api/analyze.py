"""
求职分析API
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse

from ..models.career import CareerAnalyzeRequest, CareerAnalyzeResponse
from tools.file_parser import FileParser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/career", tags=["求职分析"])

_agent = None


def init_career_router(agent):
    global _agent
    _agent = agent


@router.post("/analyze", response_model=CareerAnalyzeResponse)
async def analyze_career(request: CareerAnalyzeRequest):
    """求职分析接口（纯文本）"""
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
    """求职分析接口（SSE流式 — 纯文本输入）"""
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


@router.post("/analyze-upload")
async def analyze_with_upload(
    jd_file: Optional[UploadFile] = File(None),
    resume_file: Optional[UploadFile] = File(None),
    jd_text: str = Form(""),
    resume_text: str = Form(""),
):
    """
    求职分析接口（支持文件上传 + SSE流式）

    支持方式：
    - 上传 JD 文件（PDF/MD/TXT）+ 上传简历文件（PDF/MD/TXT）
    - 上传 JD 文件 + 粘贴简历文本
    - 粘贴 JD 文本 + 上传简历文件
    - 粘贴 JD 文本 + 粘贴简历文本
    """
    if not _agent:
        raise HTTPException(status_code=503, detail="Agent服务未初始化")

    # 解析 JD
    if jd_file:
        try:
            content = await jd_file.read()
            doc = FileParser.parse_bytes(content, jd_file.filename or "jd.txt")
            jd_text = doc.page_content
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"JD文件解析失败: {str(e)}")

    # 解析简历
    if resume_file:
        try:
            content = await resume_file.read()
            doc = FileParser.parse_bytes(content, resume_file.filename or "resume.txt")
            resume_text = doc.page_content
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"简历文件解析失败: {str(e)}")

    if not jd_text or not resume_text:
        raise HTTPException(status_code=400, detail="请提供JD和简历（文件或文本）")

    async def event_generator():
        try:
            async for event in _agent.career_analyze_stream(
                jd_text=jd_text,
                resume_text=resume_text,
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
