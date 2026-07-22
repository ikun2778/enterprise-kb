"""
简历优化 Agent - 根据 JD + 简历 + 项目案例库生成优化建议
"""

import json
import logging
from typing import Any, Dict, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

RESUME_OPTIMIZE_PROMPT = """你是一个资深的简历优化顾问。根据目标岗位JD的要求，对候选人简历中的项目描述进行优化。

目标岗位JD摘要：
{jd_summary}

候选人当前简历项目描述：
{resume_projects}

参考优秀项目案例（如有）：
{reference_cases}

请对每个项目描述进行优化，严格返回JSON格式：
{{
  "optimizations": [
    {{
      "project_name": "项目名称",
      "original": "原描述",
      "optimized": "优化后的描述",
      "reason": "优化原因（如：补充技术栈、量化成果、突出与JD相关的技术点等）"
    }}
  ],
  "overall_suggestions": [
    "整体建议1",
    "整体建议2"
  ]
}}

优化原则：
1. 使用STAR法则（情境-任务-行动-结果）组织描述
2. 量化成果（如：性能提升30%、处理10万+数据）
3. 突出与目标岗位相关的技术栈
4. 使用专业术语，避免口语化
5. 每个项目描述控制在2-3句话
6. 严格返回JSON，不要有其他文字"""


class ResumeOptimizer:
    """简历优化Agent"""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    def optimize(
        self,
        jd_data: Dict[str, Any],
        resume_data: Dict[str, Any],
        reference_cases: str = "",
    ) -> Dict[str, Any]:
        jd_summary = self._build_jd_summary(jd_data)
        resume_projects = self._build_projects_text(resume_data)

        prompt = ChatPromptTemplate.from_template(RESUME_OPTIMIZE_PROMPT)
        chain = prompt | self.llm | StrOutputParser()
        raw = chain.invoke({
            "jd_summary": jd_summary,
            "resume_projects": resume_projects,
            "reference_cases": reference_cases or "暂无参考案例",
        })
        return self._parse_json(raw)

    @staticmethod
    def _build_jd_summary(jd_data: Dict[str, Any]) -> str:
        parts: List[str] = []
        if jd_data.get("position"):
            parts.append(f"岗位: {jd_data['position']}")
        if jd_data.get("skills"):
            parts.append(f"核心技术要求: {', '.join(jd_data['skills'])}")
        if jd_data.get("responsibilities"):
            parts.append(f"职责: {'; '.join(jd_data['responsibilities'][:5])}")
        return "\n".join(parts) if parts else "暂无JD信息"

    @staticmethod
    def _build_projects_text(resume_data: Dict[str, Any]) -> str:
        projects = resume_data.get("projects", [])
        if not projects:
            return "暂无项目经历"
        parts: List[str] = []
        for i, proj in enumerate(projects, 1):
            name = proj.get("name", f"项目{i}")
            desc = proj.get("description", "")
            tech = ", ".join(proj.get("tech_stack", []))
            achievements = "; ".join(proj.get("achievements", []))
            parts.append(f"项目{i}: {name}")
            parts.append(f"  技术栈: {tech}")
            parts.append(f"  描述: {desc}")
            if achievements:
                parts.append(f"  成果: {achievements}")
            parts.append("")
        return "\n".join(parts)

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
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            logger.error(f"简历优化返回非JSON: {text[:200]}")
            return {"optimizations": [], "overall_suggestions": []}
