"""
会话记忆管理
"""

import uuid
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from collections import defaultdict

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

logger = logging.getLogger(__name__)


class ConversationMemory:
    """会话记忆管理器"""

    def __init__(self, max_history: int = 20):
        """
        初始化记忆管理器

        Args:
            max_history: 每个会话保留的最大历史消息数
        """
        self.max_history = max_history
        # 会话存储: {conversation_id: {"messages": [...], "metadata": {...}}}
        self.conversations: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"messages": [], "metadata": {}, "created_at": datetime.now()}
        )

    def create_conversation(self, title: Optional[str] = None) -> str:
        """
        创建新会话

        Args:
            title: 会话标题

        Returns:
            会话ID
        """
        conversation_id = str(uuid.uuid4())
        self.conversations[conversation_id] = {
            "messages": [],
            "metadata": {"title": title or "新对话"},
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        logger.info(f"创建新会话: {conversation_id}")
        return conversation_id

    def add_message(self, conversation_id: str, role: str, content: str, metadata: Optional[Dict] = None) -> str:
        """
        添加消息到会话

        Args:
            conversation_id: 会话ID
            role: 消息角色 (user/assistant/system)
            content: 消息内容
            metadata: 额外元数据

        Returns:
            实际使用的会话ID
        """
        if conversation_id not in self.conversations:
            conversation_id = self.create_conversation()

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        self.conversations[conversation_id]["messages"].append(message)
        self.conversations[conversation_id]["updated_at"] = datetime.now()

        # 裁剪历史
        if len(self.conversations[conversation_id]["messages"]) > self.max_history:
            self.conversations[conversation_id]["messages"] = \
                self.conversations[conversation_id]["messages"][-self.max_history:]

        return conversation_id

    def get_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """获取会话历史"""
        if conversation_id not in self.conversations:
            return []
        return self.conversations[conversation_id]["messages"]

    def get_langchain_messages(self, conversation_id: str) -> List:
        """获取LangChain格式的消息列表"""
        history = self.get_history(conversation_id)
        messages = []

        for msg in history:
            role = msg["role"]
            content = msg["content"]

            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
            elif role == "system":
                messages.append(SystemMessage(content=content))

        return messages

    def get_conversation_info(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        if conversation_id not in self.conversations:
            return None

        conv = self.conversations[conversation_id]
        return {
            "id": conversation_id,
            "title": conv["metadata"].get("title", "新对话"),
            "message_count": len(conv["messages"]),
            "created_at": conv["created_at"],
            "updated_at": conv["updated_at"]
        }

    def list_conversations(self) -> List[Dict[str, Any]]:
        """列出所有会话"""
        conversations = []
        for conv_id, conv_data in self.conversations.items():
            conversations.append({
                "id": conv_id,
                "title": conv_data["metadata"].get("title", "新对话"),
                "message_count": len(conv_data["messages"]),
                "created_at": conv_data["created_at"],
                "updated_at": conv_data["updated_at"]
            })

        # 按更新时间排序
        conversations.sort(key=lambda x: x["updated_at"], reverse=True)
        return conversations

    def delete_conversation(self, conversation_id: str) -> bool:
        """删除会话"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            logger.info(f"删除会话: {conversation_id}")
            return True
        return False

    def clear_all(self):
        """清空所有会话"""
        self.conversations.clear()
        logger.info("清空所有会话")

    def update_title(self, conversation_id: str, title: str):
        """更新会话标题"""
        if conversation_id in self.conversations:
            self.conversations[conversation_id]["metadata"]["title"] = title
