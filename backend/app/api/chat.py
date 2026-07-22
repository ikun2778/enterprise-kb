"""
聊天API接口
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from ..models.schemas import (
    ChatRequest,
    ChatResponse,
    ApiResponse
)
from ..core.agent import Agent
from ..core.memory import ConversationMemory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["聊天"])

# 全局实例（在main.py中初始化）
agent: Optional[Agent] = None
memory: Optional[ConversationMemory] = None


def init_chat_router(agent_instance: Agent, memory_instance: ConversationMemory):
    """初始化聊天路由"""
    global agent, memory
    agent = agent_instance
    memory = memory_instance


@router.post("/send", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """
    发送消息

    Args:
        request: 聊天请求

    Returns:
        聊天响应
    """
    if not agent:
        raise HTTPException(status_code=500, detail="Agent未初始化")

    try:
        result = await agent.chat(
            query=request.message,
            conversation_id=request.conversation_id,
            stream=False  # API模式暂不支持流式
        )

        return ChatResponse(
            answer=result["answer"],
            conversation_id=result["conversation_id"],
            sources=result["sources"],
            tools_used=result.get("tools_used", [])
        )

    except Exception as e:
        logger.error(f"聊天出错: {e}")
        raise HTTPException(status_code=500, detail=f"处理消息失败: {str(e)}")


@router.get("/conversations")
async def list_conversations():
    """获取会话列表"""
    if not memory:
        raise HTTPException(status_code=500, detail="记忆管理器未初始化")

    conversations = memory.list_conversations()
    return ApiResponse(data=conversations)


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """获取会话详情"""
    if not memory:
        raise HTTPException(status_code=500, detail="记忆管理器未初始化")

    info = memory.get_conversation_info(conversation_id)
    if not info:
        raise HTTPException(status_code=404, detail="会话不存在")

    history = memory.get_history(conversation_id)
    return ApiResponse(data={
        "info": info,
        "messages": history
    })


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """删除会话"""
    if not memory:
        raise HTTPException(status_code=500, detail="记忆管理器未初始化")

    success = memory.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")

    return ApiResponse(message="会话已删除")
