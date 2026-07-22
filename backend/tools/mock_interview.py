"""
面试模拟 Agent - AI 面试官，支持问答+评分+反馈
"""

import json
import logging
from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

GENERATE_QUESTION_PROMPT = """你是一个资深的技术面试官。请根据以下信息生成一个面试问题。

目标岗位：{position}
技术栈：{skills}
已问过的问题：{asked_questions}
难度要求：{difficulty}

请生成一个面试问题，严格返回JSON格式：
{{
  "question": "问题内容",
  "category": "问题分类（技术/项目/场景）",
  "difficulty": "easy/medium/hard",
  "key_points": ["考察要点1", "考察要点2"],
  "reference_answer": "参考答案要点"
}}

要求：
- 不要与已问过的问题重复
- 问题要贴近实际面试场景
- 参考答案列出3-5个关键要点
- 严格返回JSON，不要有其他文字"""

EVALUATE_ANSWER_PROMPT = """你是一个资深的技术面试官。请对候选人的回答进行评价。

岗位：{position}
问题：{question}
考察要点：{key_points}
参考答案：{reference_answer}
候选人回答：{user_answer}

请评价候选人的回答，严格返回JSON格式：
{{
  "score": 80,
  "level": "良好",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["不足1", "不足2"],
  "feedback": "总体评价和改进建议",
  "improved_answer": "更好的回答示例（简要）"
}}

评分标准：
- 90-100：优秀，回答全面准确
- 75-89：良好，回答基本正确但有遗漏
- 60-74：及格，回答部分正确
- 0-59：不及格，回答有明显错误或遗漏
- 严格返回JSON，不要有其他文字"""


class MockInterviewAgent:
    """面试模拟Agent"""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    def generate_question(
        self,
        position: str = "AI Agent开发",
        skills: Optional[List[str]] = None,
        asked_questions: Optional[List[str]] = None,
        difficulty: str = "medium",
    ) -> Dict[str, Any]:
        prompt = ChatPromptTemplate.from_template(GENERATE_QUESTION_PROMPT)
        chain = prompt | self.llm | StrOutputParser()
        raw = chain.invoke({
            "position": position,
            "skills": ", ".join(skills or []),
            "asked_questions": "; ".join(asked_questions or []) or "无",
            "difficulty": difficulty,
        })
        return self._parse_json(raw)

    def evaluate_answer(
        self,
        position: str,
        question: str,
        key_points: List[str],
        reference_answer: str,
        user_answer: str,
    ) -> Dict[str, Any]:
        prompt = ChatPromptTemplate.from_template(EVALUATE_ANSWER_PROMPT)
        chain = prompt | self.llm | StrOutputParser()
        raw = chain.invoke({
            "position": position,
            "question": question,
            "key_points": "; ".join(key_points),
            "reference_answer": reference_answer,
            "user_answer": user_answer,
        })
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
            logger.error(f"面试模拟返回非JSON: {text[:200]}")
            return {"question": "", "score": 0, "feedback": "解析失败"}
