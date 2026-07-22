"""
Agent核心 - 查询路由、查询重写、多种回答模式、流式输出
完整实现C8的所有核心功能
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Generator

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI

from .rag_engine import RAGEngine
from .memory import ConversationMemory

logger = logging.getLogger(__name__)


class Agent:
    """Agent核心类"""

    # Moonshot API 基础URL
    MOONSHOT_BASE_URL = "https://api.moonshot.cn/v1"

    def __init__(self, config, rag_engine: RAGEngine, memory: ConversationMemory):
        """
        初始化Agent

        Args:
            config: 应用配置
            rag_engine: RAG引擎实例
            memory: 记忆管理器实例
        """
        self.config = config
        self.rag_engine = rag_engine
        self.memory = memory
        self.llm = None

        self._init_llm()

    def _init_llm(self):
        """初始化LLM"""
        logger.info(f"初始化LLM: {self.config.llm.model}")

        if not self.config.llm.api_key:
            logger.warning("未设置API密钥，LLM功能将不可用")
            return

        self.llm = ChatOpenAI(
            model=self.config.llm.model,
            temperature=self.config.llm.temperature,
            max_tokens=self.config.llm.max_tokens,
            openai_api_key=self.config.llm.api_key,
            openai_api_base=self.MOONSHOT_BASE_URL,
        )
        logger.info("LLM初始化完成")

    # ==================== 查询路由 ====================

    def query_router(self, query: str) -> str:
        """
        查询路由 - 根据查询类型选择不同的处理方式
        使用关键词匹配，避免LLM调用，提高响应速度

        Args:
            query: 用户查询

        Returns:
            路由类型 ('list', 'detail', 'general')
        """
        query_lower = query.lower()

        # 列表查询关键词
        list_keywords = ['推荐', '有哪些', '列出', '几个', '一些', '哪些', '排行', '汇总']
        if any(keyword in query_lower for keyword in list_keywords):
            return 'list'

        # 详细查询关键词（包含"怎么"、"如何"、"为什么"、"原理"等）
        detail_keywords = ['怎么', '如何', '为什么', '原理', '步骤', '方法', '教程', '详细', '介绍']
        if any(keyword in query_lower for keyword in detail_keywords):
            return 'detail'

        # 默认为一般查询
        return 'general'

    # ==================== 查询重写 ====================

    def query_rewrite(self, query: str) -> str:
        """
        智能查询重写 - 简化版本，避免LLM调用
        直接返回原查询，提高响应速度

        Args:
            query: 原始查询

        Returns:
            原始查询（不做修改）
        """
        # 优化：直接返回原查询，避免额外的LLM调用
        return query

    # ==================== 上下文构建 ====================

    def _build_context(self, docs: List[Document], max_length: int = 2000) -> str:
        """
        构建上下文字符串（带元数据信息）

        Args:
            docs: 文档列表
            max_length: 最大长度

        Returns:
            格式化的上下文字符串
        """
        if not docs:
            return "暂无相关信息。"

        context_parts = []
        current_length = 0

        for i, doc in enumerate(docs, 1):
            # 添加元数据信息
            metadata_info = f"【文档 {i}】"
            if 'document_name' in doc.metadata:
                metadata_info += f" {doc.metadata['document_name']}"
            if 'category' in doc.metadata:
                metadata_info += f" | 分类: {doc.metadata['category']}"
            if 'title' in doc.metadata:
                metadata_info += f" | 标题: {doc.metadata['title']}"

            # 构建文档文本
            doc_text = f"{metadata_info}\n{doc.page_content}\n"

            # 检查长度限制
            if current_length + len(doc_text) > max_length:
                break

            context_parts.append(doc_text)
            current_length += len(doc_text)

        divider = "\n" + "=" * 50 + "\n"
        return divider + divider.join(context_parts)

    # ==================== 回答生成 ====================

    def generate_basic_answer(self, query: str, context_docs: List[Document], conversation_id: str) -> str:
        """
        生成基础回答

        Args:
            query: 用户查询
            context_docs: 上下文文档列表
            conversation_id: 会话ID

        Returns:
            生成的回答
        """
        if not self.llm:
            return "抱歉，LLM服务未配置，请检查API密钥设置。"

        context = self._build_context(context_docs)
        history = self.memory.get_langchain_messages(conversation_id)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的知识库助手。请根据以下知识库信息回答用户的问题。

要求：
1. 基于提供的信息回答，如果信息不足请诚实说明
2. 回答要准确、详细、有条理
3. 如果是技术问题，尽量提供具体的示例或步骤
4. 使用中文回答"""),
            MessagesPlaceholder(variable_name="history"),
            ("human", """
相关知识库信息:
{context}

用户问题: {question}

请回答:""")
        ])

        chain = prompt | self.llm | StrOutputParser()
        response = chain.invoke({
            "history": history,
            "context": context,
            "question": query
        })

        return response

    def generate_step_by_step_answer(self, query: str, context_docs: List[Document], conversation_id: str) -> str:
        """
        生成分步骤回答（详细模式）

        Args:
            query: 用户查询
            context_docs: 上下文文档列表
            conversation_id: 会话ID

        Returns:
            分步骤的详细回答
        """
        if not self.llm:
            return "抱歉，LLM服务未配置，请检查API密钥设置。"

        context = self._build_context(context_docs)
        history = self.memory.get_langchain_messages(conversation_id)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的技术导师。请根据知识库信息，为用户提供详细的分步骤解释。

请灵活组织回答，建议包含以下部分（可根据实际内容调整）：

## 概念介绍
[简要介绍相关概念和背景]

## 核心原理
[详细解释核心原理和机制]

## 实现步骤
[详细的分步骤说明，每步包含具体操作]

## 注意事项
[仅在有实用建议时包含。优先使用原文中的建议，如果原文内容与主题无关或为空，可以基于内容总结关键要点，或者完全省略此部分]

注意：
- 根据实际内容灵活调整结构
- 不要强行填充无关内容
- 重点突出实用性和可操作性
- 如果没有额外的建议要分享，可以省略注意事项部分
- 使用中文回答"""),
            MessagesPlaceholder(variable_name="history"),
            ("human", """
相关知识库信息:
{context}

用户问题: {question}

请回答:""")
        ])

        chain = prompt | self.llm | StrOutputParser()
        response = chain.invoke({
            "history": history,
            "context": context,
            "question": query
        })

        return response

    def generate_list_answer(self, query: str, context_docs: List[Document]) -> str:
        """
        生成列表式回答（不调用LLM，高效）

        Args:
            query: 用户查询
            context_docs: 上下文文档列表

        Returns:
            列表式回答
        """
        if not context_docs:
            return "抱歉，没有找到相关的信息。"

        # 获取父文档
        parent_docs = self.rag_engine.get_parent_documents(context_docs)

        # 提取文档名称
        doc_names = []
        for doc in parent_docs:
            doc_name = doc.metadata.get('document_name', doc.metadata.get('title', '未知文档'))
            if doc_name not in doc_names:
                doc_names.append(doc_name)

        # 构建简洁的列表回答
        if len(doc_names) == 1:
            return f"为您找到：{doc_names[0]}"
        elif len(doc_names) <= 3:
            return f"为您找到以下相关文档：\n" + "\n".join([f"{i+1}. {name}" for i, name in enumerate(doc_names)])
        else:
            return f"为您找到以下相关文档：\n" + "\n".join([f"{i+1}. {name}" for i, name in enumerate(doc_names[:3])]) + f"\n\n还有其他 {len(doc_names)-3} 个文档可供参考。"

    # ==================== 流式输出 ====================

    def generate_basic_answer_stream(self, query: str, context_docs: List[Document], conversation_id: str) -> Generator[str, None, None]:
        """
        生成基础回答 - 流式输出

        Args:
            query: 用户查询
            context_docs: 上下文文档列表
            conversation_id: 会话ID

        Yields:
            回答片段
        """
        if not self.llm:
            yield "抱歉，LLM服务未配置，请检查API密钥设置。"
            return

        context = self._build_context(context_docs)
        history = self.memory.get_langchain_messages(conversation_id)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的知识库助手。请根据以下知识库信息回答用户的问题。

要求：
1. 基于提供的信息回答，如果信息不足请诚实说明
2. 回答要准确、详细、有条理
3. 如果是技术问题，尽量提供具体的示例或步骤
4. 使用中文回答"""),
            MessagesPlaceholder(variable_name="history"),
            ("human", """
相关知识库信息:
{context}

用户问题: {question}

请回答:""")
        ])

        chain = prompt | self.llm | StrOutputParser()

        for chunk in chain.stream({
            "history": history,
            "context": context,
            "question": query
        }):
            yield chunk

    def generate_step_by_step_answer_stream(self, query: str, context_docs: List[Document], conversation_id: str) -> Generator[str, None, None]:
        """
        生成详细步骤回答 - 流式输出

        Args:
            query: 用户查询
            context_docs: 上下文文档列表
            conversation_id: 会话ID

        Yields:
            回答片段
        """
        if not self.llm:
            yield "抱歉，LLM服务未配置，请检查API密钥设置。"
            return

        context = self._build_context(context_docs)
        history = self.memory.get_langchain_messages(conversation_id)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的技术导师。请根据知识库信息，为用户提供详细的分步骤解释。

请灵活组织回答，建议包含以下部分（可根据实际内容调整）：

## 概念介绍
[简要介绍相关概念和背景]

## 核心原理
[详细解释核心原理和机制]

## 实现步骤
[详细的分步骤说明，每步包含具体操作]

## 注意事项
[仅在有实用建议时包含]

注意：
- 根据实际内容灵活调整结构
- 不要强行填充无关内容
- 重点突出实用性和可操作性
- 使用中文回答"""),
            MessagesPlaceholder(variable_name="history"),
            ("human", """
相关知识库信息:
{context}

用户问题: {question}

请回答:""")
        ])

        chain = prompt | self.llm | StrOutputParser()

        for chunk in chain.stream({
            "history": history,
            "context": context,
            "question": query
        }):
            yield chunk

    # ==================== 格式化来源 ====================

    def _format_sources(self, docs: List[Document]) -> List[Dict[str, Any]]:
        """格式化来源文档"""
        sources = []
        for doc in docs[:3]:  # 只返回前3个来源
            sources.append({
                "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                "metadata": {
                    "source": doc.metadata.get("relative_path", "未知"),
                    "category": doc.metadata.get("category", "未分类"),
                    "document_name": doc.metadata.get("document_name", "未知")
                },
                "score": doc.metadata.get("rrf_score", 0)
            })
        return sources

    # ==================== 主聊天方法 ====================

    async def chat(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        处理用户聊天请求

        Args:
            query: 用户问题
            conversation_id: 会话ID
            stream: 是否使用流式输出

        Returns:
            响应结果
        """
        # 确保会话存在
        if not conversation_id:
            conversation_id = self.memory.create_conversation()

        # 记录用户消息（捕获返回的会话ID）
        conversation_id = self.memory.add_message(conversation_id, "user", query)

        # 1. 查询路由
        route_type = await asyncio.to_thread(self.query_router, query)
        logger.info(f"查询类型: {route_type}")

        # 2. 智能查询重写（根据路由类型）
        if route_type == 'list':
            # 列表查询保持原查询
            rewritten_query = query
        else:
            # 详细查询和一般查询使用智能重写
            rewritten_query = await asyncio.to_thread(self.query_rewrite, query)

        # 3. 检索相关子块
        relevant_chunks = await asyncio.to_thread(
            self.rag_engine.hybrid_search, rewritten_query
        )

        # 4. 检查是否找到相关内容
        if not relevant_chunks:
            answer = "抱歉，没有找到相关的信息。请尝试其他关键词。"
            self.memory.add_message(conversation_id, "assistant", answer)
            return {
                "answer": answer,
                "conversation_id": conversation_id,
                "sources": [],
                "tools_used": [],
                "route_type": route_type
            }

        # 5. 获取父文档（小块检索 -> 大块上下文）
        relevant_docs = self.rag_engine.get_parent_documents(relevant_chunks)
        logger.info(f"从 {len(relevant_chunks)} 个子块中找到 {len(relevant_docs)} 个父文档")

        # 6. 格式化来源
        sources = self._format_sources(relevant_chunks)

        # 7. 根据路由类型选择回答方式
        if route_type == 'list':
            # 列表查询：直接返回文档名称列表（不调用LLM）
            answer = self.generate_list_answer(query, relevant_chunks)
            self.memory.add_message(conversation_id, "assistant", answer, {
                "route_type": route_type
            })
            return {
                "answer": answer,
                "conversation_id": conversation_id,
                "sources": sources,
                "tools_used": [],
                "route_type": route_type
            }

        elif route_type == 'detail':
            # 详细查询：使用分步指导模式（使用父文档作为上下文）
            if stream:
                # 流式输出
                answer_generator = self.generate_step_by_step_answer_stream(
                    query, relevant_docs, conversation_id
                )
                return {
                    "answer_generator": answer_generator,
                    "conversation_id": conversation_id,
                    "sources": sources,
                    "tools_used": [],
                    "route_type": route_type,
                    "stream": True
                }
            else:
                answer = await asyncio.to_thread(
                    self.generate_step_by_step_answer,
                    query, relevant_docs, conversation_id
                )

        else:
            # 一般查询：使用基础回答模式（使用父文档作为上下文）
            if stream:
                # 流式输出
                answer_generator = self.generate_basic_answer_stream(
                    query, relevant_docs, conversation_id
                )
                return {
                    "answer_generator": answer_generator,
                    "conversation_id": conversation_id,
                    "sources": sources,
                    "tools_used": [],
                    "route_type": route_type,
                    "stream": True
                }
            else:
                answer = await asyncio.to_thread(
                    self.generate_basic_answer,
                    query, relevant_docs, conversation_id
                )

        # 记录助手回复
        self.memory.add_message(conversation_id, "assistant", answer, {
            "route_type": route_type
        })

        return {
            "answer": answer,
            "conversation_id": conversation_id,
            "sources": sources,
            "tools_used": [],
            "route_type": route_type,
            "stream": False
        }
