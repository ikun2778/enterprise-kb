"""
CareerCopilot 测试用例
运行方式: cd backend && python -m pytest tests/ -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.skill_matcher import SkillMatcher
from tools.file_parser import FileParser


# ==================== Case 1: 技能匹配测试 ====================

class TestSkillMatching:
    """测试技能匹配算法"""

    def setup_method(self):
        self.matcher = SkillMatcher()

    def test_exact_match(self):
        """精确匹配测试"""
        jd_skills = ["Python", "RAG", "FastAPI", "Docker"]
        resume_skills = ["Python", "RAG", "FastAPI"]
        result = self.matcher.match(jd_skills, resume_skills)
        assert result["matched_count"] == 3
        assert result["missing_count"] == 1
        assert "Docker" in result["missing_skills"]
        assert "Python" in result["matched_skills"]

    def test_fuzzy_match(self):
        """模糊匹配测试"""
        jd_skills = ["LangChain"]
        resume_skills = ["lang chain", "Python"]
        result = self.matcher.match(jd_skills, resume_skills)
        # "LangChain" 应该能匹配 "lang chain"
        assert result["matched_count"] >= 1

    def test_alias_match(self):
        """别名匹配测试"""
        jd_skills = ["大模型应用开发"]
        resume_skills = ["LLM Agent项目经验"]
        result = self.matcher.match(jd_skills, resume_skills)
        # "大模型" 和 "LLM" 应该通过别名匹配
        assert result["matched_count"] >= 1

    def test_empty_skills(self):
        """空技能列表测试"""
        result = self.matcher.match([], ["Python"])
        assert result["score"] == 0
        assert result["total_required"] == 0

    def test_all_matched(self):
        """全部匹配测试"""
        jd_skills = ["Python", "FastAPI"]
        resume_skills = ["Python", "FastAPI", "Docker"]
        result = self.matcher.match(jd_skills, resume_skills)
        assert result["score"] == 100
        assert result["missing_count"] == 0


# ==================== Case 2: 多维评分测试 ====================

class TestMultiDimensionMatch:
    """测试多维评分模型"""

    def setup_method(self):
        self.matcher = SkillMatcher()

    def test_multi_dimension_scoring(self):
        """多维评分测试"""
        jd_data = {
            "position": "AI Agent开发实习",
            "skills": ["Python", "RAG", "LangChain", "FastAPI"],
            "requirements": ["熟悉Python编程"],
            "responsibilities": ["参与Agent开发"],
            "education": "本科及以上",
            "experience": "",
        }
        resume_data = {
            "name": "测试候选人",
            "skills": ["Python", "RAG", "FastAPI"],
            "projects": [
                {
                    "name": "RAG知识库系统",
                    "description": "基于LangChain构建RAG系统",
                    "tech_stack": ["Python", "LangChain", "FAISS", "FastAPI"],
                    "achievements": ["支持多轮对话", "检索准确率90%"],
                }
            ],
            "experience": [],
            "education": [{"school": "测试大学", "degree": "本科", "major": "计算机"}],
        }
        result = self.matcher.multi_dimension_match(jd_data, resume_data)
        assert "score" in result
        assert "skill_score" in result
        assert "project_score" in result
        assert "experience_score" in result
        assert "analysis" in result
        # 总分应该是加权结果
        expected = round(result["skill_score"] * 0.5 + result["project_score"] * 0.3 + result["experience_score"] * 0.2)
        assert result["score"] == expected

    def test_project_scoring(self):
        """项目匹配评分测试"""
        jd_data = {
            "skills": ["Python", "RAG", "Docker"],
            "requirements": [],
            "responsibilities": [],
        }
        resume_data = {
            "projects": [
                {
                    "name": "RAG项目",
                    "description": "知识库问答",
                    "tech_stack": ["Python", "RAG", "FAISS"],
                    "achievements": [],
                }
            ]
        }
        result = self.matcher._score_projects(jd_data, resume_data)
        assert result["score"] > 0
        assert result["project_count"] == 1


# ==================== Case 3: 文件解析测试 ====================

class TestFileParser:
    """测试文件解析器"""

    def test_supported_extensions(self):
        """支持的文件类型测试"""
        assert FileParser.is_supported("test.pdf") is True
        assert FileParser.is_supported("test.md") is True
        assert FileParser.is_supported("test.txt") is True
        assert FileParser.is_supported("test.docx") is False
        assert FileParser.is_supported("test.png") is False

    def test_parse_text(self):
        """文本解析测试"""
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("这是一个测试文档\n包含中文内容")
            tmp_path = f.name
        try:
            doc = FileParser.parse(tmp_path)
            assert "测试文档" in doc.page_content
            assert doc.metadata["file_type"] == "txt"
        finally:
            os.unlink(tmp_path)

    def test_parse_markdown(self):
        """Markdown解析测试"""
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("# 测试标题\n\n这是测试内容\n\n## 子标题\n\n详细内容")
            tmp_path = f.name
        try:
            doc = FileParser.parse(tmp_path)
            assert "测试标题" in doc.page_content
            assert doc.metadata["file_type"] == "md"
        finally:
            os.unlink(tmp_path)


# ==================== Case 4: 岗位推荐测试 ====================

class TestJobRecommend:
    """测试岗位推荐"""

    def test_skill_extraction(self):
        """从JD内容提取技能测试"""
        content = "需要掌握Python和LangChain框架，熟悉FAISS向量数据库，了解Docker容器化部署"
        skills = JobRecommender._extract_skills_from_content(content)
        assert "Python" in skills
        assert "LangChain" in skills
        assert "FAISS" in skills
        assert "Docker" in skills

    def test_skill_matching(self):
        """岗位技能匹配测试"""
        user_skills = ["Python", "RAG", "FastAPI", "FAISS"]
        job_skills = ["Python", "RAG", "LangChain", "Docker"]
        matched, missing = JobRecommender._match_skills(user_skills, job_skills)
        assert "Python" in matched
        assert "RAG" in matched
        assert "LangChain" in missing
        assert "Docker" in missing


# 导入 JobRecommender 用于测试
from tools.job_recommend import JobRecommender


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
