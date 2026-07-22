"""
技能匹配模块 - 多维评分 + 语义匹配
评分模型：技能匹配度*50% + 项目经验匹配*30% + 经验背景匹配*20%
"""

import logging
import numpy as np
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SkillMatcher:
    """技能匹配器：支持关键词匹配 + Embedding语义匹配 + 多维评分"""

    # 技能同义词映射（用于语义匹配的补充）
    SKILL_ALIASES = {
        "llm": ["大模型", "大语言模型", "large language model", "chatgpt", "gpt"],
        "rag": ["检索增强生成", "retrieval augmented generation", "知识库问答"],
        "agent": ["智能代理", "ai agent", "智能体"],
        "langchain": ["lang chain"],
        "fastapi": ["fast api"],
        "docker": ["容器", "容器化"],
        "faiss": ["facebook ai similarity search"],
        "milvus": ["向量数据库"],
        "embedding": ["向量化", "文本嵌入", "向量表示"],
        "prompt engineering": ["提示工程", "提示词工程", "prompt设计"],
        "python": ["py"],
        "transformer": ["注意力机制", "attention", "self-attention"],
    }

    def __init__(
        self,
        similarity_threshold: float = 0.6,
        semantic_threshold: float = 0.7,
        embeddings=None,
    ):
        self.similarity_threshold = similarity_threshold
        self.semantic_threshold = semantic_threshold
        self.embeddings = embeddings  # HuggingFaceEmbeddings 实例（可选）

    # ==================== 语义匹配 ====================

    def _compute_cosine_similarity(self, text1: str, text2: str) -> float:
        """使用Embedding计算两个文本的余弦相似度"""
        if not self.embeddings:
            return 0.0
        try:
            vec1 = self.embeddings.embed_query(text1)
            vec2 = self.embeddings.embed_query(text2)
            a = np.array(vec1)
            b = np.array(vec2)
            dot = np.dot(a, b)
            norm = np.linalg.norm(a) * np.linalg.norm(b)
            if norm == 0:
                return 0.0
            return float(dot / norm)
        except Exception as e:
            logger.warning(f"Embedding计算失败: {e}")
            return 0.0

    def _check_alias_match(self, jd_skill: str, resume_skill: str) -> float:
        """检查技能别名匹配"""
        jd_lower = jd_skill.strip().lower()
        res_lower = resume_skill.strip().lower()

        for canonical, aliases in self.SKILL_ALIASES.items():
            all_forms = [canonical] + aliases
            jd_match = any(a in jd_lower for a in all_forms)
            res_match = any(a in res_lower for a in all_forms)
            if jd_match and res_match:
                return 0.9
        return 0.0

    # ==================== 关键词匹配（原有逻辑增强） ====================

    def _keyword_match_score(self, jd_skill: str, resume_skill: str) -> float:
        """计算两个技能的关键词匹配分数"""
        jd_lower = jd_skill.strip().lower()
        res_lower = resume_skill.strip().lower()

        # 精确匹配
        if jd_lower == res_lower:
            return 1.0

        # 包含匹配
        if jd_lower in res_lower or res_lower in jd_lower:
            return 0.85

        # 别名匹配
        alias_score = self._check_alias_match(jd_skill, resume_skill)
        if alias_score > 0:
            return alias_score

        # 模糊匹配
        return SequenceMatcher(None, jd_lower, res_lower).ratio()

    def _find_best_match(
        self, jd_skill: str, resume_skills: List[str]
    ) -> tuple:
        """为一个JD技能找到简历中最匹配的技能，返回(分数, 匹配的简历技能)"""
        best_score = 0.0
        best_match = ""

        for res_skill in resume_skills:
            # 关键词匹配
            kw_score = self._keyword_match_score(jd_skill, res_skill)
            best_score_local = kw_score

            # 语义匹配（如果启用了Embedding）
            if self.embeddings and kw_score < 0.85:
                sem_score = self._compute_cosine_similarity(jd_skill, res_skill)
                # 取关键词和语义匹配的较高分
                best_score_local = max(best_score_local, sem_score)

            if best_score_local > best_score:
                best_score = best_score_local
                best_match = res_skill

        return best_score, best_match

    # ==================== 核心匹配方法 ====================

    def match(
        self, jd_skills: List[str], resume_skills: List[str]
    ) -> Dict[str, Any]:
        """技能匹配（支持语义匹配）"""
        jd_clean = [s.strip() for s in jd_skills if s.strip()]
        resume_clean = [s.strip() for s in resume_skills if s.strip()]

        matched: List[Dict[str, Any]] = []
        missing: List[str] = []

        for jd_skill in jd_clean:
            best_score, best_match = self._find_best_match(jd_skill, resume_clean)

            if best_score >= self.similarity_threshold:
                matched.append({
                    "jd_skill": jd_skill,
                    "resume_skill": best_match,
                    "match_score": round(best_score, 2),
                    "match_type": "semantic" if best_score >= self.semantic_threshold and best_match.lower() != jd_skill.lower() else "keyword",
                })
            else:
                missing.append(jd_skill)

        total = len(jd_clean) if jd_clean else 1
        score = round(len(matched) / total * 100)

        return {
            "score": score,
            "total_required": len(jd_clean),
            "matched_count": len(matched),
            "missing_count": len(missing),
            "matched_skills": [m["jd_skill"] for m in matched],
            "missing_skills": missing,
            "match_details": matched,
        }

    # ==================== 多维评分 ====================

    def _score_projects(
        self, jd_data: Dict[str, Any], resume_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """项目经验匹配评分"""
        jd_keywords = set()
        # 从JD提取项目相关关键词
        for skill in jd_data.get("skills", []):
            jd_keywords.add(skill.lower().strip())
        for resp in jd_data.get("responsibilities", []):
            for word in resp.split():
                if len(word) > 1:
                    jd_keywords.add(word.lower())
        for req in jd_data.get("requirements", []):
            for word in req.split():
                if len(word) > 1:
                    jd_keywords.add(word.lower())

        projects = resume_data.get("projects", [])
        if not projects:
            return {"score": 0, "project_count": 0, "highlights": []}

        project_scores: List[Dict[str, Any]] = []
        for proj in projects:
            proj_text = ""
            proj_text += proj.get("name", "") + " "
            proj_text += proj.get("description", "") + " "
            proj_text += " ".join(proj.get("tech_stack", [])) + " "
            proj_text += " ".join(proj.get("achievements", []))
            proj_text = proj_text.lower()

            hit_count = sum(1 for kw in jd_keywords if kw in proj_text)
            hit_ratio = hit_count / len(jd_keywords) if jd_keywords else 0
            project_scores.append({
                "name": proj.get("name", ""),
                "relevance": round(min(hit_ratio * 1.5, 1.0), 2),  # 放大系数
            })

        # 取最高相关度的项目
        best_projects = sorted(project_scores, key=lambda x: x["relevance"], reverse=True)[:3]
        avg_score = round(
            sum(p["relevance"] for p in best_projects) / max(len(best_projects), 1) * 100
        )

        return {
            "score": min(avg_score, 100),
            "project_count": len(projects),
            "highlights": best_projects,
        }

    def _score_experience(
        self, jd_data: Dict[str, Any], resume_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """经验背景匹配评分"""
        score = 50  # 基础分
        reasons: List[str] = []

        # 检查工作经验
        experience = resume_data.get("experience", [])
        jd_experience = jd_data.get("experience", "")

        if experience:
            score += 20
            reasons.append(f"有{len(experience)}段工作经历")
        else:
            reasons.append("暂无正式工作经历")

        # 检查学历
        education = resume_data.get("education", [])
        jd_education = jd_data.get("education", "")
        if education:
            for edu in education:
                degree = edu.get("degree", "").lower()
                if any(d in degree for d in ["硕士", "博士", "master", "phd"]):
                    score += 15
                    reasons.append("硕士及以上学历")
                    break
                elif any(d in degree for d in ["本科", "bachelor"]):
                    score += 10
                    reasons.append("本科学历")
                    break

        # 检查项目数量
        projects = resume_data.get("projects", [])
        if len(projects) >= 3:
            score += 15
            reasons.append(f"有{len(projects)}个项目经历")
        elif len(projects) >= 1:
            score += 5
            reasons.append(f"有{len(projects)}个项目经历")

        return {
            "score": min(score, 100),
            "reasons": reasons,
        }

    def multi_dimension_match(
        self, jd_data: Dict[str, Any], resume_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """多维评分：技能匹配度*50% + 项目经验匹配*30% + 经验背景匹配*20%"""
        # 1. 技能匹配
        skill_result = self.match_from_parsed(jd_data, resume_data)
        skill_score = skill_result["score"]

        # 2. 项目匹配
        project_result = self._score_projects(jd_data, resume_data)
        project_score = project_result["score"]

        # 3. 经验匹配
        experience_result = self._score_experience(jd_data, resume_data)
        experience_score = experience_result["score"]

        # 加权总分
        total_score = round(
            skill_score * 0.5 + project_score * 0.3 + experience_score * 0.2
        )

        # 生成分析文本
        analysis = self._generate_analysis(
            skill_result, project_result, experience_result, total_score
        )

        return {
            "score": total_score,
            "skill_score": skill_score,
            "project_score": project_score,
            "experience_score": experience_score,
            "skill_match": skill_result,
            "project_match": project_result,
            "experience_match": experience_result,
            "analysis": analysis,
        }

    def _generate_analysis(
        self,
        skill_result: Dict,
        project_result: Dict,
        experience_result: Dict,
        total_score: int,
    ) -> str:
        """生成匹配分析文本"""
        lines: List[str] = []

        if total_score >= 80:
            lines.append("综合匹配度较高，建议重点准备面试表达。")
        elif total_score >= 60:
            lines.append("综合匹配度良好，建议针对性补充缺失技能。")
        elif total_score >= 40:
            lines.append("有一定基础，建议系统学习后再投递。")
        else:
            lines.append("匹配度较低，建议先提升核心技能。")

        missing = skill_result.get("missing_skills", [])
        if missing:
            lines.append(f"缺失技能: {', '.join(missing[:5])}")

        highlights = project_result.get("highlights", [])
        if highlights:
            best = highlights[0]
            lines.append(f"最相关项目: {best['name']} (相关度{best['relevance']*100:.0f}%)")

        reasons = experience_result.get("reasons", [])
        if reasons:
            lines.append("背景: " + "; ".join(reasons))

        return " ".join(lines)

    # ==================== 兼容原有接口 ====================

    def match_from_parsed(
        self, jd_data: Dict[str, Any], resume_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """从解析后的JD和简历数据中匹配（兼容原有接口）"""
        jd_skills = list(jd_data.get("skills", []))
        resume_skills = list(resume_data.get("skills", []))

        # 从JD要求中提取技能关键词
        for req in jd_data.get("requirements", []):
            req_lower = req.lower()
            if any(
                kw in req_lower
                for kw in [
                    "熟练", "掌握", "熟悉", "精通", "了解",
                    "python", "java", "docker", "kubernetes",
                    "sql", "linux", "git", "langchain", "rag",
                    "faiss", "milvus", "fastapi", "llm", "agent",
                ]
            ):
                jd_skills.append(req)

        # 从简历项目中提取技术栈
        for proj in resume_data.get("projects", []):
            for tech in proj.get("tech_stack", []):
                if tech not in resume_skills:
                    resume_skills.append(tech)

        result = self.match(jd_skills, resume_skills)
        result["jd_skills_original"] = jd_skills
        result["resume_skills_original"] = resume_skills
        return result
