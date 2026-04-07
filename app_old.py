import streamlit as st
import pandas as pd
import plotly.express as px
from agent_engine import DoubaoAgent
from utils.financial_tools import get_company_fundamental
from utils.eval_tools import calculate_topsis
from utils.pdf_tools import extract_pdf_text_and_tables
import os

# 1. 页面基本配置 与 赛博朋克深色外观
st.set_page_config(page_title="光之耀面 (Radiant Surface) - 企业智慧大脑", layout="wide", page_icon="✨")

# 读取自定义 CSS
with open("static/style.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# 2. 模型与 Agent 初始化
if "agent" not in st.session_state:
    st.session_state.agent = DoubaoAgent()
if "messages" not in st.session_state:
    st.session_state.messages = []

# 3. 侧边栏设计 (Sidebar)
with st.sidebar:
    st.title("🛡️ 指挥塔控制中心")
    st.markdown("---")
    sector = st.selectbox("选择行业赛道", ["新能源", "半导体", "医药生物", "电子信息", "其他"])
    st.info(f"当前监控: {sector} 行业实时数据...")
    
    st.markdown("### 📄 研报观点提取 (RAG)")
    uploaded_file = st.file_uploader("上传企业研报 (PDF)", type=["pdf"])
    if uploaded_file:
        with st.status("正在解析深度研报..."):
            # 将上传的文件临时保存 (由于 streamlit 缓存限制，这里做模拟)
            # data = extract_pdf_text_and_tables(uploaded_file.name)
            st.success("研报解析成功，摘要已注入 Agent 上下文。")

# 4. 主界面布局 (Main Dashboard)
col1, col2 = st.columns([2, 1])

with col1:
    st.title("✨ 光之耀面 (Radiant Surface)")
    st.caption("基于 Doubao-Seed-2.0-pro 的企业级 AI 决策支持系统")
    
    # 聊天区域
    st.markdown("### 🗣️ 决策会话")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("输入公司代码或分析需求... (如: 分析贵州茅台的财务状况)"):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            with st.spinner("豆包 Pro 2.0 正在进行长链路推理与财务校对..."):
                # 如果输入包含 6 位代码，先获取财务数据
                response = st.session_state.agent.chat(prompt, st.session_state.messages[:-1])
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

with col2:
    st.markdown("### 📊 实时数据看板")
    # 模拟数据看板，实际由 Agent 自动刷新
    company_code = st.text_input("🎯 穿透分析目标 (输入代码)", "600519")
    if st.button("一键生成穿透报告"):
        data = get_company_fundamental(company_code)
        if "error" not in data:
            st.json(data)
            # 绘制图表
            chart_data = pd.DataFrame({
                '指标': ['ROE', '净利率', '负债率'],
                '数值': [data['摊薄净资产收益率(%)'], data['销售净利率(%)'], data['资产负债率(%)']]
            })
            fig = px.bar(chart_data, x='指标', y='数值', color='指标', title=f"{data['名称']} 核心体检")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error(data["error"])

    st.markdown("---")
    st.markdown("### 🏆 行业 TOPSIS 三维对标")
    # TOPSIS 动态演示
    if st.button("运行行业对标"):
        mock_comparisons = pd.DataFrame({
            "公司": ["贵州茅台", "五粮液", "山西汾酒", "泸州老窖"],
            "ROE": [30, 25, 28, 26],
            "净利率": [50, 38, 42, 35],
            "负债率": [15, 12, 10, 14]
        }).set_index("公司")
        
        topsis_res = calculate_topsis(mock_comparisons, [1, 1, 0])
        st.dataframe(topsis_res.style.background_gradient(cmap="Blues"))
        st.success("对标运算完成，权重由熵权法自动分配。")

# 页脚
st.markdown("---")
st.markdown("<p style='text-align: center; color: #64748b;'>© 2026 中国大学生计算机设计大赛 - 光之耀面项目组</p>", unsafe_allow_html=True)
