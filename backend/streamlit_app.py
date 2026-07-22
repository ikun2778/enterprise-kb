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
    /* 全局字体 */
    .stApp { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }

    /* 主标题 */
    .hero-title {
        font-size: 2.4rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .hero-sub {
        color: #888;
        font-size: 1.05rem;
        margin-bottom: 2rem;
    }

    /* 卡片 */
    .card {
        background: #ffffff;
        border: 1px solid #e8e8e8;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .card-dark {
        background: #1e1e2e;
        border: 1px solid #333;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }

    /* 分数大字 */
    .score-big {
        font-size: 3rem;
        font-weight: 800;
        text-align: center;
        margin: 0.5rem 0;
    }
    .score-high { color: #22c55e; }
    .score-mid  { color: #f59e0b; }
    .score-low  { color: #ef4444; }

    /* 进度步骤 */
    .step-item {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        padding: 0.5rem 0;
        font-size: 0.95rem;
    }
    .step-dot {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 0.75rem;
        color: white;
        flex-shrink: 0;
    }
    .step-done { background: #22c55e; }
    .step-run  { background: #3b82f6; animation: pulse 1.5s infinite; }
    .step-wait { background: #d1d5db; }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    /* 技能标签 */
    .skill-tag {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 999px;
        font-size: 0.82rem;
        margin: 0.2rem;
        font-weight: 500;
    }
    .skill-match { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
    .skill-miss  { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }

    /* 面试问题卡片 */
    .qa-card {
        background: #f8fafc;
        border-left: 4px solid #3b82f6;
        border-radius: 0 8px 8px 0;
        padding: 1rem 1.2rem;
        margin: 0.8rem 0;
    }

    /* 侧边栏 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e1e2e 0%, #2d2d44 100%);
    }
    [data-testid="stSidebar"] .stMarkdown { color: #e0e0e0; }
    [data-testid="stSidebar"] .stTextInput label { color: #ccc; }

    /* 隐藏默认元素 */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    /* Tab样式 */
    .stTabs [data-baseweb="tab-list"] { gap: 2rem; }
    .stTabs [data-baseweb="tab"] {
        font-size: 1rem;
        font-weight: 600;
        padding: 0.5rem 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 侧边栏 ====================
with st.sidebar:
    st.markdown("## 🚀 CareerCopilot")
    st.caption("AI 求职分析助手")
    st.divider()

    api_url = st.text_input("API 地址", value=API_BASE, label_visibility="collapsed")
    st.caption("后端 API 地址")

    st.divider()
    st.markdown("#### 📋 示例岗位")
    examples = [
        "AI Agent开发实习",
        "RAG工程师",
        "LLM应用开发工程师",
        "Python后端开发",
    ]
    for ex in examples:
        st.markdown(f"  • {ex}")

    st.divider()
    st.markdown("#### 🛠 技术栈")
    st.markdown("RAG + Agent + Tool Calling")
    st.markdown("FAISS · BM25 · RRF")
    st.markdown("LangChain · MiMo · FastAPI")

    st.divider()
    st.caption("v2.0.0 · MIT License")

# ==================== 主页面 Hero ====================
st.markdown('<div class="hero-title">CareerCopilot</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">上传 JD 和简历，AI Agent 自动完成技能匹配、差距分析、面试准备、简历优化</div>', unsafe_allow_html=True)

# ==================== Tabs ====================
tab1, tab2, tab3 = st.tabs(["🎯 求职分析", "🎤 面试模拟", "📚 知识库问答"])

# ==================== Tab 1: 求职分析 ====================
with tab1:
    col_input, col_result = st.columns([1, 1.2])

    with col_input:
        # ---- JD 输入 ----
        st.markdown("##### 📄 岗位 JD")
        jd_file = st.file_uploader(
            "上传 JD 文件", type=["pdf", "md", "txt"], key="jd_file", label_visibility="collapsed",
            help="支持 PDF / Markdown / TXT 格式",
        )
        jd_text = ""
        if jd_file:
            st.caption(f"已上传: {jd_file.name} ({jd_file.size // 1024}KB)")
        else:
            jd_text = st.text_area(
                "或粘贴 JD 文本", height=150, placeholder="粘贴岗位 JD 文本...", key="jd_input", label_visibility="collapsed"
            )

        st.markdown("")

        # ---- 简历输入 ----
        st.markdown("##### 📋 简历")
        resume_file = st.file_uploader(
            "上传简历文件", type=["pdf", "md", "txt"], key="resume_file", label_visibility="collapsed",
            help="支持 PDF / Markdown / TXT 格式",
        )
        resume_text = ""
        if resume_file:
            st.caption(f"已上传: {resume_file.name} ({resume_file.size // 1024}KB)")
        else:
            resume_text = st.text_area(
                "或粘贴简历文本", height=150, placeholder="粘贴简历文本...", key="resume_input", label_visibility="collapsed"
            )

        analyze_btn = st.button("🚀 开始分析", type="primary", use_container_width=True)

    with col_result:
        if analyze_btn:
            has_jd = jd_file is not None or (jd_text and jd_text.strip())
            has_resume = resume_file is not None or (resume_text and resume_text.strip())
            if not has_jd or not has_resume:
                st.error("请上传或粘贴 JD 和简历内容")
            else:
                # 进度显示区
                st.markdown("##### ⚡ Agent 分析进度")
                progress_area = st.container()

                try:
                    # 构建请求：文件上传走 /analyze-upload，纯文本走 /analyze-stream
                    if jd_file or resume_file:
                        files = {}
                        data = {}
                        if jd_file:
                            files["jd_file"] = (jd_file.name, jd_file.getvalue(), jd_file.type or "application/octet-stream")
                        else:
                            data["jd_text"] = jd_text
                        if resume_file:
                            files["resume_file"] = (resume_file.name, resume_file.getvalue(), resume_file.type or "application/octet-stream")
                        else:
                            data["resume_text"] = resume_text
                        resp = requests.post(
                            f"{api_url}/career/analyze-upload",
                            files=files,
                            data=data,
                            timeout=300,
                            stream=True,
                        )
                    else:
                        resp = requests.post(
                            f"{api_url}/career/analyze-stream",
                            json={"jd_text": jd_text, "resume_text": resume_text},
                            timeout=300,
                            stream=True,
                        )

                    if resp.status_code != 200:
                        st.error(f"分析失败: {resp.text}")
                    else:
                        # 步骤状态跟踪
                        steps = {
                            1: "解析 JD & 简历",
                            3: "技能匹配评分",
                            4: "知识库检索",
                            5: "面试题 & 简历优化",
                            7: "岗位推荐",
                            8: "生成报告",
                        }
                        step_status = {s: "wait" for s in steps}
                        final_result = None

                        for line in resp.iter_lines(decode_unicode=True):
                            if not line or not line.startswith("data: "):
                                continue
                            event = json.loads(line[6:])

                            step = event.get("step", 0)
                            status = event.get("status", "")
                            message = event.get("message", "")

                            if status == "processing" and step in step_status:
                                step_status[step] = "run"
                            elif status == "done" and step in step_status:
                                step_status[step] = "done"
                            elif status == "complete":
                                final_result = event.get("data", {})
                                for s in step_status:
                                    step_status[s] = "done"

                            # 渲染进度
                            with progress_area:
                                html = ""
                                for s, label in steps.items():
                                    icon = "✓" if step_status[s] == "done" else ("●" if step_status[s] == "run" else "○")
                                    cls = "step-done" if step_status[s] == "done" else ("step-run" if step_status[s] == "run" else "step-wait")
                                    msg = f" — {message}" if step == s and status == "processing" else ""
                                    html += f'<div class="step-item"><span class="step-dot {cls}">{icon}</span>{label}<span style="color:#888;font-size:0.85rem">{msg}</span></div>'
                                st.markdown(html, unsafe_allow_html=True)

                        # 展示最终结果
                        if final_result:
                            st.divider()
                            score = final_result.get("score", 0)
                            score_cls = "score-high" if score >= 70 else ("score-mid" if score >= 50 else "score-low")

                            st.markdown(f'<div class="score-big {score_cls}">{score}%</div>', unsafe_allow_html=True)
                            st.markdown('<p style="text-align:center;color:#888;margin-top:-0.5rem">综合匹配度</p>', unsafe_allow_html=True)

                            # 三维评分
                            skill_match = final_result.get("skill_match", {})
                            c1, c2, c3 = st.columns(3)
                            c1.metric("🎯 技能匹配", f"{skill_match.get('skill_score', score)}%")
                            c2.metric("📁 项目匹配", f"{skill_match.get('project_score', 0)}%")
                            c3.metric("💼 经验匹配", f"{skill_match.get('experience_score', 0)}%")

                            st.divider()

                            # 匹配 / 缺失技能
                            matched = skill_match.get("matched_skills", [])
                            missing = final_result.get("missing_skills", [])

                            if matched or missing:
                                st.markdown("##### 🏷 技能标签")
                                tags_html = ""
                                for s in matched[:10]:
                                    tags_html += f'<span class="skill-tag skill-match">✓ {s}</span>'
                                for s in missing[:10]:
                                    tags_html += f'<span class="skill-tag skill-miss">✗ {s}</span>'
                                st.markdown(tags_html, unsafe_allow_html=True)

                            # Markdown 报告
                            report = final_result.get("report", {})
                            md_report = report.get("summary", "")
                            if md_report:
                                with st.expander("📊 完整分析报告", expanded=True):
                                    st.markdown(md_report)

                            # 面试题
                            questions = final_result.get("interview_questions", {})
                            tech_qs = questions.get("technical_questions", [])
                            if tech_qs:
                                with st.expander(f"🎯 预测面试题 ({len(tech_qs)}道)"):
                                    for q in tech_qs[:5]:
                                        st.markdown(f'<div class="qa-card"><strong>{q.get("question", "")}</strong></div>', unsafe_allow_html=True)
                                        st.caption(f"难度: {q.get('difficulty', 'medium')}  ·  {q.get('reference_answer', '')[:100]}")

                            # 简历优化
                            opt = final_result.get("resume_optimization", {})
                            optimizations = opt.get("optimizations", [])
                            if optimizations:
                                with st.expander(f"✏️ 简历优化建议 ({len(optimizations)}条)"):
                                    for o in optimizations:
                                        st.markdown(f"**{o.get('project_name', '项目')}**")
                                        st.markdown(f"> 原始: {o.get('original', '')[:120]}")
                                        st.success(f"优化: {o.get('optimized', '')[:150]}")
                                        st.caption(f"原因: {o.get('reason', '')}")

                            # 岗位推荐
                            recs = final_result.get("job_recommendations", {})
                            recommendations = recs.get("recommendations", [])
                            if recommendations:
                                with st.expander("💼 推荐岗位"):
                                    for rec in recommendations:
                                        r_score = rec.get("score", 0)
                                        color = "#22c55e" if r_score >= 70 else ("#f59e0b" if r_score >= 50 else "#ef4444")
                                        st.markdown(f"**{rec.get('position', '')}** — <span style='color:{color}'>{r_score}%</span>", unsafe_allow_html=True)
                                        st.caption(rec.get("reason", ""))

                            # 工具调用记录
                            tools = final_result.get("tools_used", [])
                            if tools:
                                st.caption(f"🤖 Agent 调用链: {' → '.join(tools)}")

                except Exception as e:
                    st.error(f"请求失败: {e}")

        else:
            # 未点击分析时的引导
            st.markdown("""
            <div style="text-align:center;padding:4rem 2rem;color:#aaa;">
                <div style="font-size:3rem;margin-bottom:1rem;">🎯</div>
                <div style="font-size:1.1rem;">填写 JD 和简历，点击「开始分析」</div>
                <div style="font-size:0.9rem;margin-top:0.5rem;">AI Agent 将自动完成 8 步分析</div>
            </div>
            """, unsafe_allow_html=True)

# ==================== Tab 2: 面试模拟 ====================
with tab2:
    if "interview_state" not in st.session_state:
        st.session_state.interview_state = None
        st.session_state.asked_questions = []
        st.session_state.interview_history = []

    # 面试设置
    with st.container():
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            position = st.selectbox(
                "选择岗位",
                ["AI Agent开发", "RAG工程师", "LLM应用开发工程师", "Python后端开发"],
                label_visibility="collapsed",
            )
        with c2:
            difficulty = st.selectbox("难度", ["easy", "medium", "hard"], label_visibility="collapsed")
        with c3:
            start_btn = st.button("🎤 开始面试", type="primary", use_container_width=True)

    if start_btn:
        with st.spinner("面试官准备中..."):
            try:
                resp = requests.post(
                    f"{api_url}/mock-interview/start",
                    json={"position": position, "difficulty": difficulty},
                    timeout=60,
                )
                if resp.status_code == 200:
                    result = resp.json()
                    st.session_state.interview_state = result
                    st.session_state.asked_questions = []
                    st.session_state.interview_history = []
                    st.rerun()
                else:
                    st.error(f"失败: {resp.text}")
            except Exception as e:
                st.error(f"请求失败: {e}")

    # 面试进行中
    if st.session_state.interview_state:
        q_data = st.session_state.interview_state.get("question_data", {})
        question = q_data.get("question", "")
        key_points = q_data.get("key_points", [])
        ref_answer = q_data.get("reference_answer", "")

        st.markdown(f'<div class="qa-card"><strong>🎤 面试官：</strong>{question}</div>', unsafe_allow_html=True)

        user_answer = st.text_area("你的回答", height=120, key="interview_answer", placeholder="输入你的回答...")

        c1, c2 = st.columns([1, 4])
        with c1:
            submit_btn = st.button("📤 提交回答", type="primary", use_container_width=True)

        if submit_btn and user_answer:
            with st.spinner("面试官评价中..."):
                try:
                    resp = requests.post(
                        f"{api_url}/mock-interview/answer",
                        json={
                            "position": position,
                            "question": question,
                            "key_points": key_points,
                            "reference_answer": ref_answer,
                            "user_answer": user_answer,
                        },
                        timeout=60,
                    )
                    if resp.status_code == 200:
                        eval_result = resp.json().get("evaluation", {})
                        score = eval_result.get("score", 0)

                        # 得分展示
                        score_color = "#22c55e" if score >= 75 else ("#f59e0b" if score >= 60 else "#ef4444")
                        st.markdown(f'<div class="score-big" style="color:{score_color};font-size:2rem">{score}分</div>', unsafe_allow_html=True)

                        # 评价
                        st.markdown(f"**评价:** {eval_result.get('feedback', '')}")

                        # 优缺点
                        strengths = eval_result.get("strengths", [])
                        weaknesses = eval_result.get("weaknesses", [])
                        if strengths or weaknesses:
                            c1, c2 = st.columns(2)
                            with c1:
                                if strengths:
                                    st.markdown("**✅ 优点**")
                                    for s in strengths:
                                        st.markdown(f"  - {s}")
                            with c2:
                                if weaknesses:
                                    st.markdown("**⚠️ 不足**")
                                    for w in weaknesses:
                                        st.markdown(f"  - {w}")

                        # 更好回答
                        improved = eval_result.get("improved_answer", "")
                        if improved:
                            with st.expander("💡 参考答案"):
                                st.markdown(improved)
                    else:
                        st.error(f"评价失败: {resp.text}")
                except Exception as e:
                    st.error(f"请求失败: {e}")
        elif submit_btn:
            st.warning("请输入你的回答")

# ==================== Tab 3: 知识库问答 ====================
with tab3:
    query = st.text_input("", placeholder="输入问题，例如：什么是 RAG？", key="kb_query", label_visibility="collapsed")

    if st.button("🔍 搜索", type="primary", key="kb_search"):
        if query:
            with st.spinner("检索中..."):
                try:
                    resp = requests.post(
                        f"{api_url}/chat/send",
                        json={"message": query},
                        timeout=60,
                    )
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
