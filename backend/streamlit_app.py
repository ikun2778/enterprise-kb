"""
CareerCopilot Streamlit Demo
启动方式: streamlit run streamlit_app.py
"""

import json
import os
import requests
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api")

# ==================== 页面配置 ====================
st.set_page_config(page_title="CareerCopilot", page_icon="🚀", layout="wide")

# ==================== 自定义样式 ====================
st.markdown("""
<style>
    .stApp { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e1e2e 0%, #2d2d44 100%);
    }
    [data-testid="stSidebar"] .stMarkdown { color: #e0e0e0; }

    .hero-title {
        font-size: 2.2rem; font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .hero-sub { color: #888; font-size: 1rem; margin-bottom: 1.5rem; }

    .score-big { font-size: 3.5rem; font-weight: 800; text-align: center; margin: 0.3rem 0; }
    .score-high { color: #22c55e; } .score-mid { color: #f59e0b; } .score-low { color: #ef4444; }
    .score-label { text-align: center; color: #888; font-size: 0.9rem; margin-top: -0.3rem; }

    .step-row { display: flex; align-items: center; gap: 0.7rem; padding: 0.4rem 0; font-size: 0.92rem; }
    .step-dot { width: 22px; height: 22px; border-radius: 50%; display: inline-flex;
        align-items: center; justify-content: center; font-size: 0.7rem; color: white; flex-shrink: 0; }
    .step-done { background: #22c55e; }
    .step-run  { background: #3b82f6; animation: pulse 1.2s infinite; }
    .step-wait { background: #d1d5db; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }

    .skill-tag { display: inline-block; padding: 0.2rem 0.7rem; border-radius: 999px;
        font-size: 0.8rem; margin: 0.15rem; font-weight: 500; }
    .skill-match { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
    .skill-miss  { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }

    .qa-card { background: #f8fafc; border-left: 4px solid #3b82f6;
        border-radius: 0 8px 8px 0; padding: 0.8rem 1rem; margin: 0.5rem 0; }

    .metric-card { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 10px;
        padding: 1.2rem; text-align: center; }
    .metric-value { font-size: 1.8rem; font-weight: 700; }
    .metric-label { color: #6b7280; font-size: 0.85rem; margin-top: 0.2rem; }

    .stTabs [data-baseweb="tab-list"] { gap: 1.5rem; }
    .stTabs [data-baseweb="tab"] { font-size: 0.95rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ==================== 状态管理 ====================
if "page" not in st.session_state:
    st.session_state.page = "input"       # input → analyzing → results
if "result" not in st.session_state:
    st.session_state.result = None
if "interview_state" not in st.session_state:
    st.session_state.interview_state = None

# ==================== 侧边栏 ====================
with st.sidebar:
    st.markdown("## 🚀 CareerCopilot")
    st.caption("AI 求职分析助手")
    st.divider()
    api_url = st.text_input("API 地址", value=API_BASE, label_visibility="collapsed")
    st.caption("后端 API 地址")
    st.divider()
    st.markdown("#### 📋 示例岗位")
    for ex in ["AI Agent开发实习", "RAG工程师", "LLM应用开发工程师", "Python后端开发"]:
        st.markdown(f"  • {ex}")
    st.divider()
    st.markdown("#### 🛠 技术栈")
    st.markdown("RAG + Agent + Tool Calling")
    st.markdown("FAISS · BM25 · RRF · LangChain · MiMo")
    st.divider()
    st.caption("v2.0.0 · MIT License")


# ==================== 工具函数 ====================
def run_analysis(api_url, jd_file, resume_file, jd_text, resume_text):
    """执行分析并更新 session_state"""
    steps = {
        1: "解析 JD & 简历",
        2: "技能匹配评分",
        3: "知识库检索",
        4: "面试题 & 简历优化",
        5: "岗位推荐",
        6: "生成报告",
    }
    step_status = {s: "wait" for s in steps}
    progress_area = st.container()

    try:
        # 构建请求
        if jd_file or resume_file:
            files, data = {}, {}
            if jd_file:
                files["jd_file"] = (jd_file.name, jd_file.getvalue(), jd_file.type or "application/octet-stream")
            else:
                data["jd_text"] = jd_text
            if resume_file:
                files["resume_file"] = (resume_file.name, resume_file.getvalue(), resume_file.type or "application/octet-stream")
            else:
                data["resume_text"] = resume_text
            resp = requests.post(f"{api_url}/career/analyze-upload", files=files, data=data, timeout=300, stream=True)
        else:
            resp = requests.post(f"{api_url}/career/analyze-stream", json={"jd_text": jd_text, "resume_text": resume_text}, timeout=300, stream=True)

        if resp.status_code != 200:
            st.error(f"分析失败: {resp.text}")
            return

        final_result, error_msg = None, None

        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            event = json.loads(line[6:])
            step = event.get("step", 0)
            status = event.get("status", "")
            message = event.get("message", "")

            if status == "error":
                error_msg = message
                break
            elif status == "processing" and step in step_status:
                step_status[step] = "run"
            elif status == "done" and step in step_status:
                step_status[step] = "done"
            elif status == "complete":
                final_result = event.get("data", {})
                for s in step_status:
                    step_status[s] = "done"

            # 渲染进度条
            with progress_area:
                cols = st.columns(len(steps))
                for i, (s, label) in enumerate(steps.items()):
                    with cols[i]:
                        if step_status[s] == "done":
                            st.success(f"✓ {label}")
                        elif step_status[s] == "run":
                            st.info(f"● {label}")
                        else:
                            st.caption(f"○ {label}")

        if error_msg:
            st.error(f"分析失败: {error_msg}")
        elif final_result:
            st.session_state.result = final_result
            st.session_state.page = "results"
            st.rerun()
        else:
            st.warning("分析未完成")

    except Exception as e:
        st.error(f"请求失败: {e}")


def render_score(score):
    """渲染大字得分"""
    cls = "score-high" if score >= 70 else ("score-mid" if score >= 50 else "score-low")
    st.markdown(f'<div class="score-big {cls}">{score}%</div>', unsafe_allow_html=True)
    st.markdown('<p class="score-label">综合匹配度</p>', unsafe_allow_html=True)


# ==================== 页面：输入 ====================
if st.session_state.page == "input":
    st.markdown('<div class="hero-title">CareerCopilot</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">上传 JD 和简历，AI Agent 自动完成技能匹配、差距分析、面试准备、简历优化</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 📄 岗位 JD")
        jd_file = st.file_uploader("上传 JD 文件", type=["pdf", "md", "txt"], key="jd_file", label_visibility="collapsed")
        jd_text = ""
        if jd_file:
            st.caption(f"📎 {jd_file.name} ({jd_file.size // 1024}KB)")
        else:
            jd_text = st.text_area("或粘贴 JD 文本", height=200, placeholder="粘贴岗位 JD 文本...", key="jd_input", label_visibility="collapsed")

    with col2:
        st.markdown("##### 📋 简历")
        resume_file = st.file_uploader("上传简历文件", type=["pdf", "md", "txt"], key="resume_file", label_visibility="collapsed")
        resume_text = ""
        if resume_file:
            st.caption(f"📎 {resume_file.name} ({resume_file.size // 1024}KB)")
        else:
            resume_text = st.text_area("或粘贴简历文本", height=200, placeholder="粘贴简历文本...", key="resume_input", label_visibility="collapsed")

    st.markdown("")
    if st.button("🚀 开始分析", type="primary", use_container_width=True):
        has_jd = jd_file is not None or (jd_text and jd_text.strip())
        has_resume = resume_file is not None or (resume_text and resume_text.strip())
        if not has_jd or not has_resume:
            st.error("请上传或粘贴 JD 和简历内容")
        else:
            st.session_state.page = "analyzing"
            # 保存输入到 session_state 以便分析函数使用
            st.session_state._jd_file = jd_file
            st.session_state._resume_file = resume_file
            st.session_state._jd_text = jd_text
            st.session_state._resume_text = resume_text
            st.rerun()

# ==================== 页面：分析中 ====================
elif st.session_state.page == "analyzing":
    st.markdown('<div class="hero-title">CareerCopilot</div>', unsafe_allow_html=True)
    st.markdown("##### ⚡ AI Agent 正在分析中...")
    st.markdown("")

    run_analysis(
        api_url,
        st.session_state.get("_jd_file"),
        st.session_state.get("_resume_file"),
        st.session_state.get("_jd_text", ""),
        st.session_state.get("_resume_text", ""),
    )

    # 如果分析失败停留在当前页，显示返回按钮
    if st.session_state.page == "analyzing":
        st.markdown("")
        if st.button("← 返回重新输入"):
            st.session_state.page = "input"
            st.rerun()

# ==================== 页面：结果 ====================
elif st.session_state.page == "results":
    result = st.session_state.result
    score = result.get("score", 0)
    skill_match = result.get("skill_match", {})
    matched = skill_match.get("matched_skills", [])
    missing = result.get("missing_skills", [])
    questions = result.get("interview_questions", {})
    tech_qs = questions.get("technical_questions", [])
    proj_qs = questions.get("project_questions", [])
    opt = result.get("resume_optimization", {})
    optimizations = opt.get("optimizations", [])
    recs = result.get("job_recommendations", {})
    recommendations = recs.get("recommendations", [])

    # ---- 顶部：标题 + 分数 + 重新分析 ----
    top_l, top_c, top_r = st.columns([1, 2, 1])
    with top_l:
        if st.button("← 重新分析"):
            st.session_state.page = "input"
            st.session_state.result = None
            st.rerun()
    with top_c:
        render_score(score)
    with top_r:
        level = result.get("report", {}).get("level", "")
        st.caption("")
        st.caption("")
        st.markdown(f'<p style="text-align:right;color:#888">{level}</p>', unsafe_allow_html=True)

    st.markdown("")

    # ---- 三维评分 ----
    c1, c2, c3 = st.columns(3)
    for col, label, key in [(c1, "🎯 技能匹配", "skill_score"), (c2, "📁 项目匹配", "project_score"), (c3, "💼 经验匹配", "experience_score")]:
        with col:
            v = skill_match.get(key, 0)
            color = "#22c55e" if v >= 70 else ("#f59e0b" if v >= 50 else "#ef4444")
            st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:{color}">{v}%</div><div class="metric-label">{label}</div></div>', unsafe_allow_html=True)

    st.markdown("")

    # ---- 技能标签 ----
    if matched or missing:
        tags = ""
        for s in matched[:12]:
            tags += f'<span class="skill-tag skill-match">✓ {s}</span>'
        for s in missing[:12]:
            tags += f'<span class="skill-tag skill-miss">✗ {s}</span>'
        st.markdown(tags, unsafe_allow_html=True)
        st.markdown("")

    # ---- Tab 结果区 ----
    tab_labels = ["📊 分析报告"]
    if tech_qs or proj_qs:
        tab_labels.append(f"🎯 面试题 ({len(tech_qs) + len(proj_qs)})")
    tab_labels.append(f"✏️ 简历优化 ({len(optimizations)})" if optimizations else "✏️ 简历优化")
    tab_labels.append(f"💼 推荐岗位 ({len(recommendations)})" if recommendations else "💼 推荐岗位")

    tabs = st.tabs(tab_labels)
    tab_idx = 0

    # Tab 1: 分析报告
    with tabs[tab_idx]:
        report = result.get("report", {})
        md_report = report.get("summary", "")
        if md_report:
            st.markdown(md_report)
    tab_idx += 1

    # Tab 2: 面试题
    if tech_qs or proj_qs:
        with tabs[tab_idx]:
            if tech_qs:
                st.markdown("**技术题**")
                for i, q in enumerate(tech_qs[:8], 1):
                    with st.expander(f"Q{i}. {q.get('question', '')}"):
                        st.caption(f"难度: {q.get('difficulty', 'medium')}  ·  分类: {q.get('category', '')}")
                        st.markdown(f"**参考答案:** {q.get('reference_answer', '')}")
            if proj_qs:
                st.markdown("**项目追问**")
                for i, q in enumerate(proj_qs[:5], 1):
                    with st.expander(f"Q{i}. {q.get('question', '')}"):
                        st.caption(f"针对: {q.get('target_project', '')}")
                        st.markdown(f"**参考答案:** {q.get('reference_answer', '')}")
        tab_idx += 1

    # Tab 3: 简历优化
    with tabs[tab_idx]:
        if optimizations:
            for i, o in enumerate(optimizations, 1):
                st.markdown(f"**{i}. {o.get('project_name', '项目')}**")
                col_l, col_r = st.columns(2)
                with col_l:
                    st.caption("原始描述")
                    st.info(o.get("original", "")[:200])
                with col_r:
                    st.caption("优化后")
                    st.success(o.get("optimized", "")[:200])
                st.caption(f"💡 {o.get('reason', '')}")
                st.divider()
        else:
            st.info("当前分析未生成简历优化建议。可能原因：简历项目描述已足够清晰，或知识库中缺少相关参考案例。")
    tab_idx += 1

    # Tab 4: 推荐岗位
    with tabs[tab_idx]:
        if recommendations:
            for rec in recommendations:
                r_score = rec.get("score", 0)
                color = "#22c55e" if r_score >= 70 else ("#f59e0b" if r_score >= 50 else "#ef4444")
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**{rec.get('position', '')}**")
                    st.caption(rec.get("reason", ""))
                with c2:
                    st.markdown(f'<p style="text-align:right;font-size:1.3rem;font-weight:700;color:{color}">{r_score}%</p>', unsafe_allow_html=True)
                st.divider()
        else:
            st.info("当前未匹配到推荐岗位。可能原因：知识库中岗位JD数据不足，或你的技能组合较为独特。可通过「知识库问答」了解更多岗位信息。")

    # ---- 底部信息 ----
    st.markdown("")
    tools = result.get("tools_used", [])
    if tools:
        st.caption(f"🤖 Agent 调用链: {' → '.join(tools)}")

# ==================== Tab: 面试模拟（独立页面入口） ====================
# 在侧边栏添加面试模拟入口
with st.sidebar:
    st.markdown("")
    if st.button("🎤 面试模拟", use_container_width=True):
        st.session_state.page = "interview"
        st.rerun()
    if st.button("📚 知识库问答", use_container_width=True):
        st.session_state.page = "qa"
        st.rerun()

# ==================== 页面：面试模拟 ====================
if st.session_state.page == "interview":
    st.markdown("### 🎤 AI 面试模拟")
    st.caption("选择岗位和难度，AI 面试官会出题并评价你的回答")

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        position = st.selectbox("岗位", ["AI Agent开发", "RAG工程师", "LLM应用开发工程师", "Python后端开发"], label_visibility="collapsed")
    with c2:
        difficulty = st.selectbox("难度", ["easy", "medium", "hard"], label_visibility="collapsed")
    with c3:
        if st.button("🎤 开始面试", type="primary", use_container_width=True):
            with st.spinner("面试官准备中..."):
                try:
                    resp = requests.post(f"{api_url}/mock-interview/start", json={"position": position, "difficulty": difficulty}, timeout=60)
                    if resp.status_code == 200:
                        st.session_state.interview_state = resp.json()
                        st.rerun()
                    else:
                        st.error(f"失败: {resp.text}")
                except Exception as e:
                    st.error(f"请求失败: {e}")

    if st.button("← 返回首页"):
        st.session_state.page = "input"
        st.rerun()

    # 面试进行中
    if st.session_state.interview_state:
        q_data = st.session_state.interview_state.get("question_data", {})
        question = q_data.get("question", "")
        key_points = q_data.get("key_points", [])
        ref_answer = q_data.get("reference_answer", "")

        st.markdown("")
        st.markdown(f'<div class="qa-card"><strong>🎤 面试官：</strong>{question}</div>', unsafe_allow_html=True)

        user_answer = st.text_area("你的回答", height=120, key="interview_answer", placeholder="输入你的回答...")

        if st.button("📤 提交回答", type="primary"):
            if not user_answer:
                st.warning("请输入你的回答")
            else:
                with st.spinner("面试官评价中..."):
                    try:
                        resp = requests.post(f"{api_url}/mock-interview/answer", json={
                            "position": position, "question": question,
                            "key_points": key_points, "reference_answer": ref_answer,
                            "user_answer": user_answer,
                        }, timeout=60)
                        if resp.status_code == 200:
                            ev = resp.json().get("evaluation", {})
                            score = ev.get("score", 0)
                            color = "#22c55e" if score >= 75 else ("#f59e0b" if score >= 60 else "#ef4444")

                            st.markdown(f'<div class="score-big" style="color:{color};font-size:2rem">{score}分</div>', unsafe_allow_html=True)
                            st.markdown(f"**评价:** {ev.get('feedback', '')}")

                            s_col, w_col = st.columns(2)
                            with s_col:
                                for s in ev.get("strengths", []):
                                    st.markdown(f"✅ {s}")
                            with w_col:
                                for w in ev.get("weaknesses", []):
                                    st.markdown(f"⚠️ {w}")

                            improved = ev.get("improved_answer", "")
                            if improved:
                                with st.expander("💡 参考答案"):
                                    st.markdown(improved)
                        else:
                            st.error(f"评价失败: {resp.text}")
                    except Exception as e:
                        st.error(f"请求失败: {e}")

# ==================== 页面：知识库问答 ====================
if st.session_state.page == "qa":
    st.markdown("### 📚 知识库问答")
    st.caption("基于 RAG 检索的知识库智能问答")

    if st.button("← 返回首页"):
        st.session_state.page = "input"
        st.rerun()

    st.markdown("")
    query = st.text_input("", placeholder="输入问题，例如：什么是 RAG？", key="kb_query", label_visibility="collapsed")

    if st.button("🔍 搜索", type="primary", key="kb_search"):
        if query:
            with st.spinner("检索中..."):
                try:
                    resp = requests.post(f"{api_url}/chat/send", json={"message": query}, timeout=60)
                    if resp.status_code == 200:
                        result = resp.json()
                        st.markdown(result.get("answer", ""))
                        sources = result.get("sources", [])
                        if sources:
                            with st.expander("📎 参考来源"):
                                for s in sources:
                                    st.markdown(f"- {s.get('metadata', {}).get('source', '')}")
                    else:
                        st.error(f"查询失败: {resp.text}")
                except Exception as e:
                    st.error(f"请求失败: {e}")
