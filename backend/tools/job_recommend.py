"""
岗位推荐工具 - 根据用户技能和经验推荐适合岗位
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class JobRecommender:
    """岗位推荐器：根据用户技能匹配知识库中的岗位JD"""

    def __init__(self, rag_engine):
        self.rag_engine = rag_engine

    def recommend(
        self,
        user_skills: List[str],
        top_k: int = 3,
    ) -> Dict[str, Any]:
        query = " ".join(user_skills[:10])

        # 优先用元数据过滤搜索岗位JD
        results = self.rag_engine.metadata_filtered_search(
            query, {"category": "岗位JD"}, top_k=top_k * 2
        )

        # fallback: 普通搜索后过滤
        if not results:
            results = self.rag_engine.hybrid_search(query, top_k=top_k * 3)
            results = [r for r in results if r.metadata.get("category") == "岗位JD"]

        # fallback2: 如果还是没有，直接按文档名搜索
        if not results:
            results = self.rag_engine.hybrid_search("岗位 JD 招聘", top_k=top_k * 3)
            results = [r for r in results if "JD" in r.metadata.get("document_name", "") or "岗位" in r.metadata.get("category", "")]

        # fallback3: 用所有岗位JD父文档
        if not results:
            all_jd = self.rag_engine.filter_documents_by_category("岗位JD")
            if all_jd:
                results = all_jd[:top_k * 2]

        recommendations: List[Dict[str, Any]] = []
        for doc in results[:top_k]:
            doc_name = doc.metadata.get("document_name", "")
            content = doc.page_content

            # 提取岗位技能要求
            job_skills = self._extract_skills_from_content(content)
            matched, missing = self._match_skills(user_skills, job_skills)
            score = round(len(matched) / max(len(job_skills), 1) * 100)

            recommendations.append({
                "position": doc_name,
                "score": score,
                "matched_skills": matched,
                "missing_skills": missing,
                "reason": self._build_reason(matched, missing),
                "source": doc.metadata.get("relative_path", ""),
            })

        # 按分数排序
        recommendations.sort(key=lambda x: x["score"], reverse=True)

        return {
            "user_skills": user_skills,
            "recommendations": recommendations[:top_k],
        }

    def recommend_from_resume(
        self, resume_data: Dict[str, Any], top_k: int = 3
    ) -> Dict[str, Any]:
        skills = list(resume_data.get("skills", []))
        for proj in resume_data.get("projects", []):
            for tech in proj.get("tech_stack", []):
                if tech not in skills:
                    skills.append(tech)
        return self.recommend(skills, top_k)

    @staticmethod
    def _extract_skills_from_content(content: str) -> List[str]:
        """从岗位JD文档中提取技能关键词"""
        skills: List[str] = []
        skill_keywords = [
            "Python", "Java", "Go", "C++", "JavaScript",
            "LangChain", "LlamaIndex", "FastAPI", "Django", "Flask",
            "FAISS", "Milvus", "Pinecone", "Chroma",
            "Docker", "Kubernetes", "Linux", "Git",
            "MySQL", "PostgreSQL", "Redis", "MongoDB",
            "RAG", "Agent", "LLM", "Transformer",
            "PyTorch", "TensorFlow", "HuggingFace",
            "OpenAI", "Claude", "Moonshot",
            "BM25", "Embedding", "向量数据库",
            "Prompt Engineering", "LoRA", "QLoRA",
            "pytest", "CI/CD", "Jenkins",
        ]
        content_lower = content.lower()
        for kw in skill_keywords:
            if kw.lower() in content_lower:
                skills.append(kw)
        return skills

    @staticmethod
    def _match_skills(
        user_skills: List[str], job_skills: List[str]
    ) -> tuple:
        user_lower = {s.strip().lower() for s in user_skills}
        matched: List[str] = []
        missing: List[str] = []

        for skill in job_skills:
            if skill.lower() in user_lower:
                matched.append(skill)
            else:
                # 检查部分匹配
                found = False
                for us in user_skills:
                    if skill.lower() in us.lower() or us.lower() in skill.lower():
                        matched.append(skill)
                        found = True
                        break
                if not found:
                    missing.append(skill)

        return matched, missing

    @staticmethod
    def _build_reason(matched: List[str], missing: List[str]) -> str:
        parts: List[str] = []
        if matched:
            parts.append(f"已具备{len(matched)}项核心技能({', '.join(matched[:3])})")
        if missing:
            parts.append(f"缺少{len(missing)}项({', '.join(missing[:3])})")
        return "; ".join(parts) if parts else "待评估"
