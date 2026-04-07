import sys
import os
import streamlit as st

# 将项目根目录和 src 目录加入 Python 搜索路径
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

# 必须在所有涉及 streamlit 命令的 import 之前调用
st.set_page_config(
    page_title="光之耀面",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.presentation.components.main_dashboard import render_app

if __name__ == "__main__":
    # 启动全量 UI 渲染
    render_app()
