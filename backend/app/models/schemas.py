"""
数据模型定义
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


# ==================== 枚举类型 ====================

class DocumentStatus(str, Enum):
    """文档状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MessageRole(str, Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# ==================== 聊天相关模型 ====================

class ChatMessage(BaseModel):
    """聊天消息"""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., min_length=1, max_length=2000, description="用户消息")
    conversation_id: Optional[str] = Field(None, description="会话ID，为空则创建新会话")
    stream: bool = Field(False, description="是否流式输出")
    knowledge_base_id: Optional[str] = Field(None, description="知识库ID")


class SourceDocument(BaseModel):
    """来源文档"""
    content: str = Field(..., description="文档内容片段")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="文档元数据")
    score: float = Field(0.0, description="相关性分数")


class ChatResponse(BaseModel):
    """聊天响应"""
    answer: str = Field(..., description="回答内容")
    conversation_id: str = Field(..., description="会话ID")
    sources: List[SourceDocument] = Field(default_factory=list, description="来源文档")
    tools_used: List[str] = Field(default_factory=list, description="使用的工具")


class ConversationInfo(BaseModel):
    """会话信息"""
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int


# ==================== 知识库相关模型 ====================

class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求"""
    name: str = Field(..., min_length=1, max_length=100, description="知识库名称")
    description: Optional[str] = Field(None, max_length=500, description="知识库描述")


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class KnowledgeBaseInfo(BaseModel):
    """知识库信息"""
    id: str
    name: str
    description: Optional[str]
    document_count: int
    created_at: datetime
    updated_at: datetime


# ==================== 文档相关模型 ====================

class DocumentUpload(BaseModel):
    """文档上传响应"""
    filename: str
    status: DocumentStatus
    message: Optional[str] = None


class DocumentInfo(BaseModel):
    """文档信息"""
    id: str
    filename: str
    knowledge_base_id: str
    status: DocumentStatus
    chunk_count: int
    file_size: int
    created_at: datetime
    updated_at: datetime


class DocumentChunk(BaseModel):
    """文档分块"""
    id: str
    document_id: str
    content: str
    metadata: Dict[str, Any]


# ==================== 通用响应模型 ====================

class ApiResponse(BaseModel):
    """通用API响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("success", description="消息")
    data: Optional[Any] = Field(None, description="数据")


class PaginatedResponse(BaseModel):
    """分页响应"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==================== 工具相关模型 ====================

class ToolInfo(BaseModel):
    """工具信息"""
    name: str
    description: str
    parameters: Dict[str, Any]


class ToolCallResult(BaseModel):
    """工具调用结果"""
    tool_name: str
    arguments: Dict[str, Any]
    result: Any
    success: bool
    error: Optional[str] = None
