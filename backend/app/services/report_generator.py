"""
统一 Markdown 报告生成器
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ReportGenerator:
    """生成求职分析的 Markdown 报告"""

    @staticmethod
    def generate(
        jd_data: Dict[str, Any],
        resume_data: Dict[str, Any],
        match_result: Dict[str, Any],
        learning_plan: List[Dict[str, Any]],
        interview_questions: Dict[str, Any],
        resume_optimization: Dict[str, Any] = None,
        job_recommendations: Dict[str, Any] = None,
    ) -> str:
        lines: List[str] = []
        position = jd_data.get("position", "目标岗位")
        name = resume_data.get("name", "候选人")

        # 标题
        lines.append(f"# 求职分析报告")
        lines.append("")
        lines.append(f"- 目标岗位: {position}")
        lines.append(f"- 候选人: {name}")
        lines.append("")

        # 一、岗位分析
        lines.append("## 一、岗位分析")
        lines.append("")
        if jd_data.get("company"):
            lines.append(f"- 公司: {jd_data['company']}")
        if jd_data.get("skills"):
            lines.append(f"- 核心技术要求: {', '.join(jd_data['skills'])}")
        if jd_data.get("responsibilities"):
            lines.append("- 主要职责:")
            for resp in jd_data["responsibilities"][:5]:
                lines.append(f"  - {resp}")
        if jd_data.get("requirements"):
            lines.append("- 任职要求:")
            for req in jd_data["requirements"][:5]:
                lines.append(f"  - {req}")
        lines.append("")

        # 二、简历匹配
        lines.append("## 二、简历匹配")
        lines.append("")
        score = match_result.get("score", 0)
        skill_score = match_result.get("skill_score", score)
        project_score = match_result.get("project_score", 0)
        experience_score = match_result.get("experience_score", 0)

        if score >= 80:
            level = "高度匹配"
        elif score >= 60:
            level = "较好匹配"
        elif score >= 40:
            level = "部分匹配"
        else:
            level = "匹配度较低"

        lines.append(f"- 综合评分: **{score}分** ({level})")
        lines.append(f"- 技能匹配: {skill_score}分")
        lines.append(f"- 项目匹配: {project_score}分")
        lines.append(f"- 经验匹配: {experience_score}分")
        lines.append("")

        # 三、优势
        lines.append("## 三、优势")
        lines.append("")
        matched = match_result.get("skill_match", match_result).get("matched_skills", [])
        if matched:
            for skill in matched[:8]:
                lines.append(f"- {skill}")
        else:
            lines.append("- 暂无明确匹配的优势技能")
        lines.append("")

        # 四、技能缺口
        lines.append("## 四、技能缺口")
        lines.append("")
        missing = match_result.get("missing_skills", [])
        if missing:
            for skill in missing:
                lines.append(f"- {skill}")
        else:
            lines.append("- 无明显技能缺口")
        lines.append("")

        # 五、学习路线
        lines.append("## 五、学习路线")
        lines.append("")
        if learning_plan:
            for item in learning_plan[:5]:
                skill = item.get("skill", "")
                lines.append(f"- **{skill}**: 优先学习")
                for r in item.get("resources", [])[:1]:
                    lines.append(f"  - 参考: {r.get('metadata', {}).get('document_name', '知识库资料')}")
        else:
            lines.append("- 暂无学习建议")
        lines.append("")

        # 六、简历优化建议
        lines.append("## 六、简历优化建议")
        lines.append("")
        if resume_optimization and resume_optimization.get("optimizations"):
            for opt in resume_optimization["optimizations"][:3]:
                lines.append(f"- **{opt.get('project_name', '项目')}**")
                lines.append(f"  - 原始: {opt.get('original', '')[:100]}")
                lines.append(f"  - 优化: {opt.get('optimized', '')[:150]}")
                lines.append(f"  - 原因: {opt.get('reason', '')}")
                lines.append("")
            suggestions = resume_optimization.get("overall_suggestions", [])
            if suggestions:
                lines.append("- 整体建议:")
                for s in suggestions:
                    lines.append(f"  - {s}")
        else:
            lines.append("- 暂无优化建议")
        lines.append("")

        # 七、预测面试题
        lines.append("## 七、预测面试题")
        lines.append("")
        tech_qs = interview_questions.get("technical_questions", [])
        proj_qs = interview_questions.get("project_questions", [])
        if tech_qs:
            lines.append("### 技术题")
            for i, q in enumerate(tech_qs[:5], 1):
                lines.append(f"{i}. {q.get('question', '')}")
                lines.append(f"   - 难度: {q.get('difficulty', 'medium')}")
                lines.append(f"   - 要点: {q.get('reference_answer', '')[:100]}")
                lines.append("")
        if proj_qs:
            lines.append("### 项目追问")
            for i, q in enumerate(proj_qs[:3], 1):
                lines.append(f"{i}. {q.get('question', '')}")
                lines.append(f"   - 针对: {q.get('target_project', '')}")
                lines.append("")

        # 岗位推荐
        if job_recommendations and job_recommendations.get("recommendations"):
            lines.append("## 八、推荐岗位")
            lines.append("")
            for rec in job_recommendations["recommendations"][:3]:
                lines.append(f"- **{rec.get('position', '')}** (匹配度: {rec.get('score', 0)}%)")
                lines.append(f"  - {rec.get('reason', '')}")
                lines.append("")

        return "\n".join(lines)
