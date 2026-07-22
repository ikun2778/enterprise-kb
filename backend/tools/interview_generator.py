"""
面试问题生成器 - 根据 JD、简历和 RAG 知识生成面试问题
"""

import json
import logging
from typing import Any, Dict, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

INTERVIEW_PROMPT = """你是一个资深的技术面试官。根据以下信息生成面试问题和参考答案。

目标岗位JD摘要：
{jd_summary}

候选人简历摘要：
{resume_summary}

相关技术知识：
{knowledge_context}

请生成面试问题，严格返回JSON格式：
{{
  "technical_questions": [
    {{
      "question": "技术问题",
      "category": "问题分类（如：RAG/Python/系统设计等）",
      "difficulty": "难度（easy/medium/hard）",
      "reference_answer": "参考答案要点"
    }}
  ],
  "project_questions": [
    {{
      "question": "项目追问",
      "target_project": "针对的项目",
      "reference_answer": "参考答案要点"
    }}
  ],
  "scenario_questions": [
    {{
      "question": "场景题",
      "category": "场景分类",
      "reference_answer": "参考答案要点"
    }}
  ]
}}

要求：
- 技术问题 5-8 个，覆盖 JD 中的核心技术栈
- 项目追问 3-5 个，针对简历中的项目经历
- 场景题 2-3 个，考察实际问题解决能力
- 参考答案要简洁，列出关键要点即可
- 严格返回JSON，不要有其他文字"""


class InterviewGenerator:
    """面试问题生成器"""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    def generate(
        self,
        jd_data: Dict[str, Any],
        resume_data: Dict[str, Any],
        knowledge_context: str = "",
    ) -> Dict[str, Any]:
        jd_summary = self._build_jd_summary(jd_data)
        resume_summary = self._build_resume_summary(resume_data)

        prompt = ChatPromptTemplate.from_template(INTERVIEW_PROMPT)
        chain = prompt | self.llm | StrOutputParser()
        raw = chain.invoke(
            {
                "jd_summary": jd_summary,
                "resume_summary": resume_summary,
                "knowledge_context": knowledge_context or "暂无相关知识库内容",
            }
        )
        return self._parse_json(raw)

    def generate_from_skill_gap(
        self,
        missing_skills: List[str],
        jd_data: Dict[str, Any],
        resume_data: Dict[str, Any],
        rag_results: str = "",
    ) -> Dict[str, Any]:
        jd_data_copy = dict(jd_data)
        jd_data_copy["skills"] = list(
            set(jd_data.get("skills", []) + missing_skills)
        )
        return self.generate(jd_data_copy, resume_data, rag_results)

    @staticmethod
    def _build_jd_summary(jd_data: Dict[str, Any]) -> str:
        parts: List[str] = []
        if jd_data.get("position"):
            parts.append(f"岗位: {jd_data['position']}")
        if jd_data.get("company"):
            parts.append(f"公司: {jd_data['company']}")
        if jd_data.get("skills"):
            parts.append(f"技术要求: {', '.join(jd_data['skills'])}")
        if jd_data.get("responsibilities"):
            parts.append(
                f"工作职责: {'; '.join(jd_data['responsibilities'][:5])}"
            )
        if jd_data.get("requirements"):
            parts.append(
                f"任职要求: {'; '.join(jd_data['requirements'][:5])}"
            )
        return "\n".join(parts) if parts else "暂无JD信息"

    @staticmethod
    def _build_resume_summary(resume_data: Dict[str, Any]) -> str:
        parts: List[str] = []
        if resume_data.get("name"):
            parts.append(f"姓名: {resume_data['name']}")
        if resume_data.get("skills"):
            parts.append(f"技能: {', '.join(resume_data['skills'])}")
        if resume_data.get("projects"):
            proj_summaries = []
            for proj in resume_data["projects"][:3]:
                name = proj.get("name", "")
                desc = proj.get("description", "")
                tech = ", ".join(proj.get("tech_stack", []))
                proj_summaries.append(f"{name}({tech}): {desc[:100]}")
            parts.append(f"项目经历: {'; '.join(proj_summaries)}")
        if resume_data.get("experience"):
            exp_summaries = []
            for exp in resume_data["experience"][:3]:
                company = exp.get("company", "")
                position = exp.get("position", "")
                exp_summaries.append(f"{company} - {position}")
            parts.append(f"工作经历: {'; '.join(exp_summaries)}")
        return "\n".join(parts) if parts else "暂无简历信息"

    @staticmethod
    def _parse_json(raw: str) -> Dict[str, Any]:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
            logger.error(f"面试问题生成返回非JSON: {text[:200]}")
            return {
                "technical_questions": [],
                "project_questions": [],
                "scenario_questions": [],
            }
