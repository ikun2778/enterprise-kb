# CareerCopilot

基于 RAG + Agent 的智能求职分析系统

## 项目简介

CareerCopilot 是一个面向求职者的 AI 求职助手 Agent。用户上传岗位 JD 和简历，系统通过多个 Agent Tool 协同工作，自动完成技能匹配、差距分析、简历优化、面试模拟和岗位推荐，输出完整的求职分析报告。

## 核心功能

- **JD 智能解析**：LLM 从岗位描述中提取结构化信息（技能、职责、学历等）
- **简历解析**：自动提取简历中的技能、项目经历、工作背景
- **多维评分模型**：技能匹配度 x 50% + 项目经验匹配 x 30% + 经验背景匹配 x 20%
- **语义技能匹配**：Embedding cosine similarity + 关键词匹配 + 同义词识别
- **知识库检索**：针对缺失技能从 RAG 知识库检索学习资料
- **面试问题生成**：根据 JD 和简历生成技术题、项目追问和参考答案
- **简历优化 Agent**：根据 JD 要求优化简历项目描述（STAR 法则）
- **面试模拟 Agent**：AI 面试官，支持出题、回答、评分、反馈
- **岗位推荐**：根据用户技能匹配知识库中的岗位 JD
- **Markdown 报告**：输出包含匹配度、差距分析、学习建议、面试题的完整报告

## 技术架构

```
用户输入（JD + 简历）
         ↓
    FastAPI / Streamlit
         ↓
    Career Agent
         ↓
  ┌──────┼──────┬──────┬──────┬──────┐
  ↓      ↓      ↓      ↓      ↓      ↓
JD解析  简历解析  技能匹配  岗位推荐  简历优化  面试模拟
  Tool    Tool    Tool    Tool    Tool    Tool
         ↓
    RAG 知识库（FAISS + BM25 + RRF）
         ↓
    LLM（Moonshot API）
         ↓
    Markdown 求职分析报告
```

## 技术亮点

| 能力 | 实现 |
|------|------|
| RAG 检索增强生成 | FAISS + BM25 + RRF 混合检索 |
| 父子文档检索 | 小块检索提高精度，大块上下文保持完整性 |
| Agent 多 Tool 协作 | 8 个专用 Tool 协同完成求职分析全流程 |
| 多维评分模型 | 技能 50% + 项目 30% + 经验 20% 加权评分 |
| 语义技能匹配 | Embedding cosine similarity 识别相关技能 |
| LLM 结构化解析 | Prompt Engineering 提取结构化 JSON |
| 简历优化 Agent | STAR 法则 + 量化成果 + 技术栈匹配 |
| AI 面试模拟 | 出题 → 回答 → 评分 → 反馈闭环 |
| 岗位推荐 | 基于技能画像匹配知识库岗位 JD |
| 流式输出 | 支持实时显示分析结果 |
| 多轮对话 | 支持求职咨询的上下文记忆 |

## 技术栈

| 组件 | 技术选型 |
|------|----------|
| Agent 框架 | LangChain |
| Embedding | HuggingFace BGE (bge-small-zh-v1.5) |
| 向量数据库 | FAISS |
| 稀疏检索 | BM25 |
| 混合重排 | RRF (Reciprocal Rank Fusion) |
| LLM | MiMo (mimo-v2.5-pro, OpenAI兼容协议) |
| Web 框架 | FastAPI |
| 前端 Demo | Streamlit |
| 文件解析 | PyMuPDF |
| 数值计算 | NumPy |

## 快速开始

### 方式一：Docker 部署（推荐）

```bash
git clone <repo-url>
cd enterprise-kb

# 配置环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入 MIMO_API_KEY

# 一键启动
docker-compose up -d
```

启动后访问：
- Streamlit 前端：`http://localhost:8501`
- FastAPI 后端：`http://localhost:8000`
- API 文档：`http://localhost:8000/docs`

```bash
# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 方式二：Cloud Studio / 本地运行

```bash
git clone <repo-url>
cd enterprise-kb/backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 MIMO_API_KEY
```

启动后端：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

启动前端（新终端）：

```bash
streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501
```

### 方式三：终端问答

```bash
cd enterprise-kb/backend
python cli.py
```

## API 接口

### 求职分析

```
POST /api/career/analyze
```

请求体：

```json
{
  "jd_text": "岗位JD文本...",
  "resume_text": "简历文本..."
}
```

响应包含：`score`（综合评分）、`skill_match`（多维评分详情）、`missing_skills`、`learning_plan`、`interview_questions`、`resume_optimization`、`job_recommendations`、`report`（Markdown报告）

### 面试模拟

```
POST /api/mock-interview/start     # 开始面试，获取问题
POST /api/mock-interview/answer    # 提交回答，获取评分
```

### 对话问答

```
POST /api/chat/send
```

### 知识库管理

```
GET  /api/knowledge/stats
POST /api/knowledge/rebuild
POST /api/knowledge/search
```

## 项目结构

```
enterprise-kb/
├── Dockerfile                     # Docker 镜像构建
├── docker-compose.yml             # 双服务编排（backend + web）
├── .dockerignore                  # Docker 构建排除
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── rag_engine.py      # RAG 引擎（FAISS + BM25 + RRF）
│   │   │   ├── agent.py           # Agent 核心（8个Tool + 求职分析 + 面试模拟）
│   │   │   └── memory.py          # 会话记忆管理
│   │   ├── api/
│   │   │   ├── analyze.py         # 求职分析 API
│   │   │   ├── mock_interview.py  # 面试模拟 API
│   │   │   ├── chat.py            # 对话 API
│   │   │   ├── knowledge.py       # 知识库 API
│   │   │   └── document.py        # 文档管理 API
│   │   ├── models/
│   │   │   ├── schemas.py         # 通用数据模型
│   │   │   └── career.py          # 求职分析 + 面试模拟数据模型
│   │   ├── services/
│   │   │   └── report_generator.py # Markdown 报告生成
│   │   ├── config.py              # 配置管理
│   │   └── main.py                # FastAPI 入口
│   ├── tools/
│   │   ├── file_parser.py         # 统一文件解析（PDF/MD/TXT）
│   │   ├── jd_parser.py           # JD 结构化解析
│   │   ├── resume_parser.py       # 简历结构化解析
│   │   ├── skill_matcher.py       # 多维评分 + 语义匹配
│   │   ├── knowledge_search.py    # RAG 知识检索 Tool
│   │   ├── interview_generator.py # 面试问题生成
│   │   ├── resume_optimizer.py    # 简历优化 Agent
│   │   ├── mock_interview.py      # 面试模拟 Agent
│   │   └── job_recommend.py       # 岗位推荐
│   ├── tests/
│   │   └── test_career.py         # 测试用例
│   ├── data/knowledge_base/       # 知识库文档（19篇）
│   │   ├── AI岗位技能/            # 7篇
│   │   ├── 面试题库/              # 3篇
│   │   ├── 项目案例/              # 3篇
│   │   └── 岗位JD/               # 6篇
│   ├── streamlit_app.py           # Streamlit 前端 Demo
│   ├── cli.py                     # 终端交互入口
│   ├── requirements.txt
│   └── .env.example
└── README.md
```

## 知识库内容

| 类别 | 内容 | 文档数 |
|------|------|--------|
| AI 岗位技能 | RAG工程师、Agent开发、LangChain、FastAPI、Docker、FAISS、Milvus | 7篇 |
| 面试题库 | Python面试题、RAG面试题、Agent面试题 | 3篇 |
| 项目案例 | RAG项目、Agent项目、FastAPI项目 | 3篇 |
| 岗位 JD | AI Agent实习、RAG工程师、LLM应用开发、Python后端、测试开发、大模型应用 | 6篇 |

## 测试

```bash
cd backend
python -m pytest tests/ -v
```

测试用例覆盖：
- Case 1：技能匹配（精确匹配、模糊匹配、别名匹配）
- Case 2：多维评分（技能+项目+经验加权）
- Case 3：文件解析（PDF/MD/TXT）
- Case 4：岗位推荐（技能提取、岗位匹配）

## 开发能力展示

```
Python + LangChain + RAG + Agent + Tool Calling + FastAPI + LLM Application
```

本项目作为 AI Agent 开发 / RAG 工程师 / 大模型应用开发岗位的作品展示。

## 许可证

MIT License
