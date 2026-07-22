"""
CareerCopilot Streamlit Demo
启动方式: streamlit run streamlit_app.py
"""

import json
import os
import requests
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api")

st.set_page_config(page_title="CareerCopilot", page_icon="💼", layout="wide")

st.title("CareerCopilot - 智能求职分析助手")
st.caption("基于 RAG + Agent 的智能求职分析系统")

# ==================== 侧边栏：岗位选择 ====================
with st.sidebar:
    st.header("设置")
    api_url = st.text_input("API地址", value=API_BASE)
    st.divider()
    st.markdown("### 示例岗位")
    st.code("AI Agent开发实习\nRAG工程师\nLLM应用开发工程师\nPython后端开发")

# ==================== 主页面 ====================
tab1, tab2, tab3 = st.tabs(["求职分析", "面试模拟", "知识库问答"])

# ---- Tab 1: 求职分析 ----
with tab1:
    st.header("求职分析")

    col1, col2 = st.columns(2)

    with col1:
        jd_text = st.text_area(
            "岗位JD",
            height=250,
            placeholder="粘贴岗位JD文本...",
            key="jd_input",
        )

    with col2:
        resume_text = st.text_area(
            "简历内容",
            height=250,
            placeholder="粘贴简历文本...",
            key="resume_input",
        )

    if st.button("开始分析", type="primary", use_container_width=True):
        if not jd_text or not resume_text:
            st.error("请填写JD和简历内容")
        else:
            # SSE 流式分析 — 实时显示进度
            progress_placeholder = st.empty()
            result_area = st.container()

            try:
                resp = requests.post(
                    f"{api_url}/career/analyze-stream",
                    json={"jd_text": jd_text, "resume_text": resume_text},
                    timeout=300,
                    stream=True,
                )

                if resp.status_code != 200:
                    st.error(f"分析失败: {resp.text}")
                else:
                    final_result = None
                    for line in resp.iter_lines(decode_unicode=True):
                        if not line or not line.startswith("data: "):
                            continue
                        event = json.loads(line[6:])

                        step = event.get("step", 0)
                        status = event.get("status", "")
                        message = event.get("message", "")

                        if status == "processing":
                            progress_placeholder.info(f"⏳ {message}")
                        elif status == "done":
                            progress_placeholder.success(f"✅ {message}")
                        elif status == "complete":
                            final_result = event.get("data", {})
                            progress_placeholder.success("✅ 分析完成！")
                        elif status == "error":
                            progress_placeholder.error(f"❌ {message}")

                    # 展示最终结果
                    if final_result:
                        with result_area:
                            score = final_result.get("score", 0)
                            st.metric("综合匹配度", f"{score}%")

                            skill_match = final_result.get("skill_match", {})
                            col_a, col_b, col_c = st.columns(3)
                            with col_a:
                                st.metric("技能匹配", f"{skill_match.get('skill_score', score)}%")
                            with col_b:
                                st.metric("项目匹配", f"{skill_match.get('project_score', 0)}%")
                            with col_c:
                                st.metric("经验匹配", f"{skill_match.get('experience_score', 0)}%")

                            report = final_result.get("report", {})
                            md_report = report.get("summary", "")
                            if md_report:
                                st.markdown(md_report)

                            missing = final_result.get("missing_skills", [])
                            if missing:
                                st.subheader("缺失技能")
                                for skill in missing:
                                    st.markdown(f"- {skill}")

                            questions = final_result.get("interview_questions", {})
                            tech_qs = questions.get("technical_questions", [])
                            if tech_qs:
                                st.subheader("预测面试题")
                                for q in tech_qs[:5]:
                                    with st.expander(q.get("question", "")):
                                        st.markdown(f"**难度**: {q.get('difficulty', '')}")
                                        st.markdown(f"**参考答案**: {q.get('reference_answer', '')}")

                            opt = final_result.get("resume_optimization", {})
                            optimizations = opt.get("optimizations", [])
                            if optimizations:
                                st.subheader("简历优化建议")
                                for o in optimizations:
                                    with st.expander(f"优化: {o.get('project_name', '')}"):
                                        st.markdown(f"**原始**: {o.get('original', '')}")
                                        st.markdown(f"**优化后**: {o.get('optimized', '')}")
                                        st.markdown(f"**原因**: {o.get('reason', '')}")

                            recs = final_result.get("job_recommendations", {})
                            recommendations = recs.get("recommendations", [])
                            if recommendations:
                                st.subheader("推荐岗位")
                                for rec in recommendations:
                                    st.markdown(
                                        f"- **{rec.get('position', '')}** (匹配度: {rec.get('score', 0)}%)"
                                        f"\n  {rec.get('reason', '')}"
                                    )

                            tools = final_result.get("tools_used", [])
                            st.caption(f"Agent调用工具: {', '.join(tools)}")

            except Exception as e:
                st.error(f"请求失败: {e}")

# ---- Tab 2: 面试模拟 ----
with tab2:
    st.header("AI面试模拟")

    if "interview_state" not in st.session_state:
        st.session_state.interview_state = None
        st.session_state.asked_questions = []

    col1, col2 = st.columns([1, 1])
    with col1:
        position = st.selectbox(
            "选择岗位",
            ["AI Agent开发", "RAG工程师", "LLM应用开发工程师", "Python后端开发"],
        )
    with col2:
        difficulty = st.selectbox("难度", ["easy", "medium", "hard"])

    if st.button("开始面试", key="start_interview"):
        with st.spinner("面试官准备问题中..."):
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
                    st.rerun()
                else:
                    st.error(f"失败: {resp.text}")
            except Exception as e:
                st.error(f"请求失败: {e}")

    # 显示当前问题
    if st.session_state.interview_state:
        q_data = st.session_state.interview_state.get("question_data", {})
        question = q_data.get("question", "")
        key_points = q_data.get("key_points", [])
        ref_answer = q_data.get("reference_answer", "")

        st.subheader("面试问题")
        st.info(question)

        user_answer = st.text_area("你的回答", height=150, key="interview_answer")

        if st.button("提交回答", key="submit_answer"):
            if not user_answer:
                st.warning("请输入你的回答")
            else:
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
                            st.metric("得分", f"{score}分")
                            st.markdown(f"**评价**: {eval_result.get('feedback', '')}")
                            strengths = eval_result.get("strengths", [])
                            weaknesses = eval_result.get("weaknesses", [])
                            if strengths:
                                st.markdown("**优点**: " + "; ".join(strengths))
                            if weaknesses:
                                st.markdown("**不足**: " + "; ".join(weaknesses))
                            improved = eval_result.get("improved_answer", "")
                            if improved:
                                with st.expander("更好的回答示例"):
                                    st.markdown(improved)
                        else:
                            st.error(f"评价失败: {resp.text}")
                    except Exception as e:
                        st.error(f"请求失败: {e}")

# ---- Tab 3: 知识库问答 ----
with tab3:
    st.header("知识库问答")
    query = st.text_input("输入问题", placeholder="什么是RAG？", key="kb_query")

    if st.button("搜索", key="kb_search"):
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
                            with st.expander("参考来源"):
                                for s in sources:
                                    st.markdown(f"- {s.get('metadata', {}).get('source', '')}")
                    else:
                        st.error(f"查询失败: {resp.text}")
                except Exception as e:
                    st.error(f"请求失败: {e}")
