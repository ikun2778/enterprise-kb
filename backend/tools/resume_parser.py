"""
简历解析器 - 使用 LLM 提取结构化信息
"""

import json
import logging
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from tools.file_parser import FileParser

logger = logging.getLogger(__name__)

RESUME_PARSE_PROMPT = """你是一个专业的简历解析助手。请从以下简历内容中提取结构化信息。

要求严格返回JSON格式，不要添加任何其他文字。

简历内容：
{resume_text}

请按以下JSON格式返回：
{{
  "name": "姓名",
  "phone": "手机号（如有）",
  "email": "邮箱（如有）",
  "education": [
    {{
      "school": "学校名称",
      "degree": "学历",
      "major": "专业",
      "start_date": "开始时间",
      "end_date": "结束时间"
    }}
  ],
  "skills": ["技能1", "技能2", ...],
  "experience": [
    {{
      "company": "公司名称",
      "position": "职位",
      "start_date": "开始时间",
      "end_date": "结束时间",
      "description": "工作描述"
    }}
  ],
  "projects": [
    {{
      "name": "项目名称",
      "role": "担任角色",
      "description": "项目描述",
      "tech_stack": ["技术1", "技术2", ...],
      "achievements": ["成果1", "成果2", ...]
    }}
  ],
  "certifications": ["证书1", "证书2", ...],
  "self_description": "自我评价摘要"
}}

注意：
- skills 填写技术技能（编程语言、框架、工具等）
- 如果某项信息未提及，返回空字符串或空数组
- 严格返回JSON，不要有其他文字"""


class ResumeParser:
    """简历解析器"""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        doc = FileParser.parse(file_path)
        return self._extract(doc.page_content)

    def parse_text(self, text: str) -> Dict[str, Any]:
        return self._extract(text)

    def _extract(self, resume_text: str) -> Dict[str, Any]:
        prompt = ChatPromptTemplate.from_template(RESUME_PARSE_PROMPT)
        chain = prompt | self.llm | StrOutputParser()
        raw = chain.invoke({"resume_text": resume_text})
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
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            logger.error(f"简历解析返回非JSON内容: {text[:200]}")
            return {
                "name": "",
                "skills": [],
                "experience": [],
                "projects": [],
                "education": [],
            }
