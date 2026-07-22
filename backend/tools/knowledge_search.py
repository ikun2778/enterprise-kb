"""
RAG 知识检索 Tool - 封装现有 rag_engine 的知识检索能力
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class KnowledgeSearchTool:
    """知识检索工具：根据技能缺口从知识库中检索学习资料"""

    def __init__(self, rag_engine):
        self.rag_engine = rag_engine

    def search(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        results = self.rag_engine.hybrid_search(query, top_k=top_k)
        return {
            "query": query,
            "results_count": len(results),
            "results": [
                {
                    "content": doc.page_content[:500],
                    "metadata": doc.metadata,
                    "score": doc.metadata.get("rrf_score", 0),
                }
                for doc in results
            ],
        }

    def search_skill_gap(
        self, missing_skills: List[str], top_k_per_skill: int = 2
    ) -> Dict[str, Any]:
        all_results: List[Dict[str, Any]] = []
        for skill in missing_skills:
            queries = [
                f"{skill} 教程 入门",
                f"{skill} 面试题",
                f"{skill} 项目实战",
            ]
            skill_results: List[Dict[str, Any]] = []
            for query in queries:
                results = self.rag_engine.hybrid_search(
                    query, top_k=top_k_per_skill
                )
                for doc in results:
                    item = {
                        "content": doc.page_content[:500],
                        "metadata": doc.metadata,
                        "score": doc.metadata.get("rrf_score", 0),
                    }
                    if item not in skill_results:
                        skill_results.append(item)
                if skill_results:
                    break

            all_results.append(
                {
                    "skill": skill,
                    "results": skill_results[:top_k_per_skill],
                }
            )

        return {
            "missing_skills": missing_skills,
            "skill_results": all_results,
        }

    def get_learning_plan(
        self, missing_skills: List[str]
    ) -> List[Dict[str, Any]]:
        plan: List[Dict[str, Any]] = []
        for skill in missing_skills:
            search_result = self.search(f"{skill} 学习路径 教程", top_k=2)
            plan.append(
                {
                    "skill": skill,
                    "priority": "high",
                    "resources": search_result["results"],
                }
            )
        return plan
