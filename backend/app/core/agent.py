"""
Agent核心 - 查询路由、查询重写、多种回答模式、流式输出、求职分析
"""

import re
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional, Generator

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI

from .rag_engine import RAGEngine
from .memory import ConversationMemory

from tools.jd_parser import JDParser
from tools.resume_parser import ResumeParser
from tools.skill_matcher import SkillMatcher
from tools.knowledge_search import KnowledgeSearchTool
from tools.interview_generator import InterviewGenerator
from tools.resume_optimizer import ResumeOptimizer
from tools.mock_interview import MockInterviewAgent
from tools.job_recommend import JobRecommender
from app.services.report_generator import ReportGenerator

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

    # MiMo API (OpenAI兼容协议)
    MIMO_BASE_URL = "https://token-plan-cn.xiaomimimo.com/v1"

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

        # 求职分析工具（延迟初始化，在 LLM 初始化之后）
        self.jd_parser: Optional[JDParser] = None
        self.resume_parser: Optional[ResumeParser] = None
        self.skill_matcher: Optional[SkillMatcher] = None
        self.knowledge_search: Optional[KnowledgeSearchTool] = None
        self.interview_generator: Optional[InterviewGenerator] = None
        self.resume_optimizer: Optional[ResumeOptimizer] = None
        self.mock_interview: Optional[MockInterviewAgent] = None
        self.job_recommender: Optional[JobRecommender] = None
        self.report_generator = ReportGenerator()

        if self.llm:
            self.jd_parser = JDParser(self.llm)
            self.resume_parser = ResumeParser(self.llm)
            self.skill_matcher = SkillMatcher(
                embeddings=self.rag_engine.embeddings,
            )
            self.knowledge_search = KnowledgeSearchTool(self.rag_engine)
            self.interview_generator = InterviewGenerator(self.llm)
            self.resume_optimizer = ResumeOptimizer(self.llm)
            self.mock_interview = MockInterviewAgent(self.llm)
            self.job_recommender = JobRecommender(self.rag_engine)
            logger.info("求职分析工具初始化完成")

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
            openai_api_base=self.MIMO_BASE_URL,
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

    # ==================== 求职分析（CareerCopilot 核心能力） ====================

    async def career_analyze(
        self,
        jd_text: str,
        resume_text: str,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        求职分析主流程（升级版）：
        JD解析 → 简历解析 → 多维评分 → 知识检索 → 面试生成 → 简历优化 → 岗位推荐 → 输出报告
        """
        tools_used: List[str] = []

        if not conversation_id:
            conversation_id = self.memory.create_conversation("求职分析")

        # Step 1: JD 解析
        logger.info("Step 1: 解析岗位JD...")
        jd_data = await asyncio.to_thread(self.jd_parser.parse_text, jd_text)
        tools_used.append("jd_parser")

        # Step 2: 简历解析
        logger.info("Step 2: 解析简历...")
        resume_data = await asyncio.to_thread(self.resume_parser.parse_text, resume_text)
        tools_used.append("resume_parser")

        # Step 3: 多维评分（技能50% + 项目30% + 经验20%）
        logger.info("Step 3: 多维评分分析...")
        match_result = await asyncio.to_thread(
            self.skill_matcher.multi_dimension_match, jd_data, resume_data
        )
        tools_used.append("skill_matcher")

        # Step 4: 知识库检索（针对缺失技能）
        logger.info("Step 4: 知识库检索学习资料...")
        learning_plan: List[Dict[str, Any]] = []
        rag_context = ""
        missing_skills = match_result.get("skill_match", match_result).get("missing_skills", [])
        if missing_skills:
            search_result = await asyncio.to_thread(
                self.knowledge_search.search_skill_gap, missing_skills
            )
            learning_plan = await asyncio.to_thread(
                self.knowledge_search.get_learning_plan, missing_skills
            )
            tools_used.append("knowledge_search")
            for skill_result in search_result.get("skill_results", []):
                for r in skill_result.get("results", []):
                    rag_context += r.get("content", "") + "\n"

        # Step 5: 面试问题生成
        logger.info("Step 5: 生成面试问题...")
        interview_questions = await asyncio.to_thread(
            self.interview_generator.generate_from_skill_gap,
            missing_skills,
            jd_data,
            resume_data,
            rag_context[:3000] if rag_context else "",
        )
        tools_used.append("interview_generator")

        # Step 6: 简历优化
        logger.info("Step 6: 简历优化建议...")
        resume_optimization: Dict[str, Any] = {}
        if self.resume_optimizer:
            # 构建参考案例
            ref_cases = ""
            for skill_result in (search_result if missing_skills else {}).get("skill_results", []):
                for r in skill_result.get("results", []):
                    ref_cases += r.get("content", "")[:200] + "\n"
            resume_optimization = await asyncio.to_thread(
                self.resume_optimizer.optimize, jd_data, resume_data, ref_cases[:2000]
            )
            tools_used.append("resume_optimizer")

        # Step 7: 岗位推荐
        logger.info("Step 7: 岗位推荐...")
        job_recommendations: Dict[str, Any] = {}
        if self.job_recommender:
            job_recommendations = await asyncio.to_thread(
                self.job_recommender.recommend_from_resume, resume_data
            )
            tools_used.append("job_recommender")

        # Step 8: 生成 Markdown 报告
        logger.info("Step 8: 生成求职分析报告...")
        md_report = self.report_generator.generate(
            jd_data=jd_data,
            resume_data=resume_data,
            match_result=match_result,
            learning_plan=learning_plan,
            interview_questions=interview_questions,
            resume_optimization=resume_optimization,
            job_recommendations=job_recommendations,
        )

        report = {
            "summary": md_report,
            "level": self._get_level(match_result.get("score", 0)),
        }
        tools_used.append("report_generator")

        # 记录对话
        self.memory.add_message(
            conversation_id, "user", f"[求职分析] JD: {jd_text[:100]}..."
        )
        self.memory.add_message(
            conversation_id, "assistant", report["summary"][:500]
        )

        return {
            "conversation_id": conversation_id,
            "score": match_result.get("score", 0),
            "job_analysis": jd_data,
            "resume_analysis": resume_data,
            "skill_match": match_result,
            "missing_skills": missing_skills,
            "learning_plan": learning_plan,
            "interview_questions": interview_questions,
            "resume_optimization": resume_optimization,
            "job_recommendations": job_recommendations,
            "report": report,
            "tools_used": tools_used,
        }

    @staticmethod
    def _get_level(score: int) -> str:
        if score >= 80:
            return "高度匹配"
        elif score >= 60:
            return "较好匹配"
        elif score >= 40:
            return "部分匹配"
        return "匹配度较低"

    # ==================== 面试模拟 ====================

    async def mock_interview_start(
        self,
        position: str = "AI Agent开发",
        skills: Optional[List[str]] = None,
        difficulty: str = "medium",
    ) -> Dict[str, Any]:
        """开始一轮面试模拟，生成第一个问题"""
        if not self.mock_interview:
            return {"error": "面试模拟工具未初始化"}
        question_data = await asyncio.to_thread(
            self.mock_interview.generate_question,
            position=position,
            skills=skills,
            difficulty=difficulty,
        )
        return {
            "position": position,
            "question_data": question_data,
        }

    async def mock_interview_answer(
        self,
        position: str,
        question: str,
        key_points: List[str],
        reference_answer: str,
        user_answer: str,
    ) -> Dict[str, Any]:
        """评价用户的面试回答"""
        if not self.mock_interview:
            return {"error": "面试模拟工具未初始化"}
        evaluation = await asyncio.to_thread(
            self.mock_interview.evaluate_answer,
            position=position,
            question=question,
            key_points=key_points,
            reference_answer=reference_answer,
            user_answer=user_answer,
        )
        return {
            "question": question,
            "user_answer": user_answer,
            "evaluation": evaluation,
        }
