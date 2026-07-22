"""
JD（岗位描述）解析器 - 使用 LLM 提取结构化信息
"""

import json
import logging
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from tools.file_parser import FileParser

logger = logging.getLogger(__name__)

JD_PARSE_PROMPT = """你是一个专业的岗位JD解析助手。请从以下岗位描述中提取结构化信息。

要求严格返回JSON格式，不要添加任何其他文字。

岗位描述内容：
{jd_text}

请按以下JSON格式返回：
{{
  "position": "岗位名称",
  "company": "公司名称（如有）",
  "department": "部门（如有）",
  "location": "工作地点（如有）",
  "salary_range": "薪资范围（如有）",
  "skills": ["技术技能1", "技术技能2", ...],
  "soft_skills": ["软技能1", "软技能2", ...],
  "responsibilities": ["职责1", "职责2", ...],
  "requirements": ["要求1", "要求2", ...],
  "education": "学历要求",
  "experience": "经验要求",
  "nice_to_haves": ["加分项1", "加分项2", ...]
}}

注意：
- skills 只填技术技能（编程语言、框架、工具等）
- soft_skills 填软技能（沟通、团队协作等）
- 如果某项信息未提及，返回空字符串或空数组
- 严格返回JSON，不要有其他文字"""


class JDParser:
    """岗位JD解析器"""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        doc = FileParser.parse(file_path)
        return self._extract(doc.page_content)

    def parse_text(self, text: str) -> Dict[str, Any]:
        return self._extract(text)

    def _extract(self, jd_text: str) -> Dict[str, Any]:
        prompt = ChatPromptTemplate.from_template(JD_PARSE_PROMPT)
        chain = prompt | self.llm | StrOutputParser()
        raw = chain.invoke({"jd_text": jd_text})
        return self._parse_json(raw)

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
            logger.error(f"JD解析返回非JSON内容: {text[:200]}")
            return {
                "position": "",
                "company": "",
                "skills": [],
                "responsibilities": [],
                "requirements": [],
            }
