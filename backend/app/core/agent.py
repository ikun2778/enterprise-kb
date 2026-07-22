"""
Agent核心 - 查询路由、查询重写、多种回答模式、流式输出
完整实现C8的所有核心功能
"""

import re
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


def markdown_to_text(md_text: str) -> str:
    """
    将Markdown格式转换为纯文本（终端友好）

    Args:
        md_text: Markdown格式文本

    Returns:
        纯文本
    """
    if not md_text:
        return ""

    text = md_text

    # 移除标题标记，保留内容
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # 移除粗体标记
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)

    # 移除斜体标记
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)

    # 移除删除线
    text = re.sub(r'~~(.*?)~~', r'\1', text)

    # 移除代码块
    text = re.sub(r'```[\s\S]*?```', '', text)

    # 移除行内代码
    text = re.sub(r'`(.*?)`', r'\1', text)

    # 移除链接，保留文本
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)

    # 移除图片
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)

    # 处理表格 - 转换为简单格式
    lines = text.split('\n')
    processed_lines = []
    for line in lines:
        # 跳过表格分隔行
        if re.match(r'^\|[\s\-:]+\|$', line.strip()):
            continue
        # 处理表格行
        if line.strip().startswith('|') and line.strip().endswith('|'):
            cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
            line = '  '.join(cells)
        processed_lines.append(line)
    text = '\n'.join(processed_lines)

    # 移除引用标记
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)

    # 移除水平线
    text = re.sub(r'^[\-\*_]{3,}\s*$', '', text, flags=re.MULTILINE)

    # 清理多余的空行
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


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

    def _extract_filters_from_query(self, query: str) -> dict:
        """
        从用户问题中提取元数据过滤条件

        Args:
            query: 用户查询

        Returns:
            过滤条件字典
        """
        filters = {}

        # 分类关键词
        category_keywords = RAGEngine.get_supported_categories()
        for cat in category_keywords:
            if cat in query:
                filters['category'] = cat
                break

        return filters

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
            生成的回答（纯文本格式）
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
3. 使用纯文本格式输出，不要使用Markdown格式（不要用#、**、|等符号）
4. 使用中文回答
5. 重要：直接输出纯文本，不要添加任何格式标记"""),
            MessagesPlaceholder(variable_name="history"),
            ("human", """
相关知识库信息:
{context}

用户问题: {question}

请用纯文本格式回答（不要使用Markdown）:""")
        ])

        chain = prompt | self.llm | StrOutputParser()
        response = chain.invoke({
            "history": history,
            "context": context,
            "question": query
        })

        # 转换为纯文本（防止LLM仍然输出Markdown）
        return markdown_to_text(response)

    def generate_step_by_step_answer(self, query: str, context_docs: List[Document], conversation_id: str) -> str:
        """
        生成分步骤回答（详细模式）

        Args:
            query: 用户查询
            context_docs: 上下文文档列表
            conversation_id: 会话ID

        Returns:
            分步骤的详细回答（纯文本格式）
        """
        if not self.llm:
            return "抱歉，LLM服务未配置，请检查API密钥设置。"

        context = self._build_context(context_docs)
        history = self.memory.get_langchain_messages(conversation_id)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的知识库助手。请根据知识库信息，为用户提供详细的解释。

请用纯文本格式组织回答，建议包含以下部分（可根据实际内容调整）：

概念介绍：
[简要介绍相关概念和背景]

核心内容：
[详细解释核心原理和机制]

具体步骤：
[详细的分步骤说明，每步包含具体操作]

注意事项：
[仅在有实用建议时包含]

注意：
- 使用纯文本格式，不要使用Markdown格式（不要用#、**、|等符号）
- 根据实际内容灵活调整结构
- 不要强行填充无关内容
- 重点突出实用性和可操作性
- 使用中文回答"""),
            MessagesPlaceholder(variable_name="history"),
            ("human", """
相关知识库信息:
{context}

用户问题: {question}

请用纯文本格式回答（不要使用Markdown）:""")
        ])

        chain = prompt | self.llm | StrOutputParser()
        response = chain.invoke({
            "history": history,
            "context": context,
            "question": query
        })

        # 转换为纯文本（防止LLM仍然输出Markdown）
        return markdown_to_text(response)

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
            回答片段（纯文本格式）
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
3. 使用纯文本格式输出，不要使用Markdown格式（不要用#、**、|等符号）
4. 使用中文回答
5. 重要：直接输出纯文本，不要添加任何格式标记"""),
            MessagesPlaceholder(variable_name="history"),
            ("human", """
相关知识库信息:
{context}

用户问题: {question}

请用纯文本格式回答（不要使用Markdown）:""")
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
            回答片段（纯文本格式）
        """
        if not self.llm:
            yield "抱歉，LLM服务未配置，请检查API密钥设置。"
            return

        context = self._build_context(context_docs)
        history = self.memory.get_langchain_messages(conversation_id)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的知识库助手。请根据知识库信息，为用户提供详细的解释。

请用纯文本格式组织回答，建议包含以下部分（可根据实际内容调整）：

概念介绍：
[简要介绍相关概念和背景]

核心内容：
[详细解释核心原理和机制]

具体步骤：
[详细的分步骤说明，每步包含具体操作]

注意事项：
[仅在有实用建议时包含]

注意：
- 使用纯文本格式，不要使用Markdown格式（不要用#、**、|等符号）
- 根据实际内容灵活调整结构
- 不要强行填充无关内容
- 重点突出实用性和可操作性
- 使用中文回答"""),
            MessagesPlaceholder(variable_name="history"),
            ("human", """
相关知识库信息:
{context}

用户问题: {question}

请用纯文本格式回答（不要使用Markdown）:""")
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

        # 3. 检索相关子块（自动应用元数据过滤）
        filters = self._extract_filters_from_query(query)
        if filters:
            logger.info(f"应用过滤条件: {filters}")
            relevant_chunks = await asyncio.to_thread(
                self.rag_engine.metadata_filtered_search, rewritten_query, filters
            )
        else:
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
