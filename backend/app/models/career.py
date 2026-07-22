"""
求职分析相关数据模型
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CareerAnalyzeRequest(BaseModel):
    """求职分析请求"""
    jd_text: str = Field(..., min_length=10, max_length=10000, description="岗位JD文本")
    resume_text: str = Field(..., min_length=10, max_length=10000, description="简历文本")
    conversation_id: Optional[str] = Field(None, description="会话ID")


class CareerAnalyzeResponse(BaseModel):
    """求职分析响应"""
    conversation_id: str = Field(..., description="会话ID")
    score: int = Field(..., description="匹配度评分（0-100）")
    job_analysis: Dict[str, Any] = Field(default_factory=dict, description="JD解析结果")
    resume_analysis: Dict[str, Any] = Field(default_factory=dict, description="简历解析结果")
    skill_match: Dict[str, Any] = Field(default_factory=dict, description="技能匹配详情")
    missing_skills: List[str] = Field(default_factory=list, description="缺失技能列表")
    learning_plan: List[Dict[str, Any]] = Field(default_factory=list, description="学习计划")
    interview_questions: Dict[str, Any] = Field(default_factory=dict, description="面试问题")
    resume_optimization: Dict[str, Any] = Field(default_factory=dict, description="简历优化建议")
    job_recommendations: Dict[str, Any] = Field(default_factory=dict, description="岗位推荐")
    report: Dict[str, Any] = Field(default_factory=dict, description="综合报告")
    tools_used: List[str] = Field(default_factory=list, description="使用的工具列表")


# ==================== 面试模拟 ====================

class MockInterviewStartRequest(BaseModel):
    """开始面试模拟请求"""
    position: str = Field("AI Agent开发", description="目标岗位")
    skills: Optional[List[str]] = Field(None, description="技术栈")
    difficulty: str = Field("medium", description="难度: easy/medium/hard")


class MockInterviewAnswerRequest(BaseModel):
    """面试回答请求"""
    position: str = Field(..., description="目标岗位")
    question: str = Field(..., description="面试问题")
    key_points: List[str] = Field(default_factory=list, description="考察要点")
    reference_answer: str = Field("", description="参考答案")
    user_answer: str = Field(..., min_length=1, description="用户回答")


class MockInterviewStartResponse(BaseModel):
    """开始面试模拟响应"""
    position: str
    question_data: Dict[str, Any]


class MockInterviewAnswerResponse(BaseModel):
    """面试回答评价响应"""
    question: str
    user_answer: str
    evaluation: Dict[str, Any]
