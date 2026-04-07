import streamlit as st

from src.application.dto.financial_dto import FinancialTableDTO
from src.application.services.financial_service import FinancialService


@st.cache_data
def load_financial_data(symbol_raw: str = "300750") -> FinancialTableDTO | None:
    return FinancialService().get_financial_table(symbol_raw)


def render_target_financials(target_name: str) -> None:
    financial_table = load_financial_data(target_name)
    if financial_table is not None and not financial_table.is_empty():
        df = financial_table.to_dataframe()
        st.markdown(
            (
                '<div style="color:#38BDF8; font-size:0.9rem; margin-bottom:10px;">'
                f'📡 目标实体财务链路已建立: <span style="color:#FFF;">{target_name}</span></div>'
            ),
            unsafe_allow_html=True,
        )
        st.caption(
            f"📌 数据来源：{financial_table.source} | 共 {financial_table.row_count} 期历史数据 | 单位：{financial_table.unit_hint}"
        )
        st.dataframe(
            df.style.format(precision=2, na_rep="—"),
            use_container_width=True,
            height=450,
        )
    else:
        st.info(
            f"该企业 ({target_name}) 暂无本地结构化财务报表，系统正在调度远程智能体进行深度扫描与信息提取..."
        )


def render_financial_tab() -> None:
    active_target = st.session_state.get("active_target")
    if not active_target:
        st.markdown(
            """
            <div style="background:rgba(15,23,42,0.6); border:1px dashed rgba(56,189,248,0.3); border-radius:12px; padding:60px 20px; text-align:center; margin-top:20px;">
                <div style="font-size:3rem; margin-bottom:20px; opacity:0.6;">📡</div>
                <div style="color:#38BDF8; font-family:'Orbitron', sans-serif; font-size:1.2rem; letter-spacing:4px;">系统待命</div>
                <div style="color:#94A3B8; font-size:0.9rem; margin-top:10px;">
                    目标财务实体链路未激活。<br>
                    请在对话区输入“分析[公司名]”或类似指令以激活特定数据链路。
                </div>
                <div style="margin-top:20px; font-size:0.7rem; color:rgba(56,189,248,0.2); font-family:monospace;">
                    等待分析指令 // 目标识别模块已就绪
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    render_target_financials(active_target)
