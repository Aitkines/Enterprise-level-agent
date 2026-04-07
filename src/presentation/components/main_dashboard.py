import time
from datetime import datetime

import streamlit as st

from src.application.services.chat_service import ChatService
from src.application.services.company_service import CompanyService
from src.application.services.comparison_service import ComparisonService
from src.application.services.data_quality_service import DataQualityService
from src.application.services.dashboard_service import DashboardService
from src.application.services.report_service import ReportService
from src.application.services.track_scoring_service import TrackScoringService
from src.presentation.components.financial_panel import render_financial_tab
from src.presentation.components.sidebar import render_sidebar
from src.presentation.components.styles import apply_global_styles
from src.presentation.renderers.message_renderer import (
    build_chart_figure,
    fix_markdown_formatting,
    normalize_response_payload,
    render_latest_chart_card,
    render_response_payload,
    render_message_with_charts,
)
from src.presentation.state.session_state import (
    append_tool_log,
    ensure_session_defaults,
    get_visible_chat_messages,
    is_initial_chat_state,
    refresh_current_session_title,
    save_current_session,
    update_latest_tool_elapsed,
)
from src.presentation.state.followup_targeting import should_preserve_active_target

@st.cache_resource
def get_chat_service():
    return ChatService()

@st.cache_resource
def get_company_service():
    return CompanyService()

@st.cache_resource
def get_dashboard_service():
    return DashboardService()

@st.cache_resource
def get_report_service():
    return ReportService()

@st.cache_resource
def get_comparison_service():
    return ComparisonService()

@st.cache_resource
def get_data_quality_service():
    return DataQualityService()

@st.cache_resource
def get_track_scoring_service():
    return TrackScoringService()

chat_service = get_chat_service()
company_service = get_company_service()
dashboard_service = get_dashboard_service()
report_service = get_report_service()
comparison_service = get_comparison_service()
data_quality_service = get_data_quality_service()
track_scoring_service = get_track_scoring_service()

OVERVIEW_CACHE_TTL_SECONDS = 300


def render_top_nav() -> None:
    """渲染高效稳健的顶部导航条（基于 st.radio 的高度定制化实现）"""
    nav_options = ["🤖 决策引擎", "🔍 财务透视", "⚔️ 同赛道对比", "📄 研究报告"]
    current_nav = st.session_state.get("active_nav", "🤖 决策引擎")
    
    # 确保当前索引合法
    try:
        current_idx = nav_options.index(current_nav)
    except ValueError:
        current_idx = 0

    # 使用水平单选框作为导航内核
    # 其样式已在 styles.py 中通过 [data-testid="stHorizontalRadio"] 深度定制
    selected = st.radio(
        label="Global Navigation",
        options=nav_options,
        index=current_idx,
        horizontal=True,
        key="main_nav_radio_widget",
        label_visibility="collapsed"
    )
    
    # 检测变化并触发重绘
    if selected != current_nav:
        st.session_state.active_nav = selected
        st.rerun()

    return None


def _normalize_for_echo_match(text: str) -> str:
    """归一化文本以便进行重复内容匹配。"""
    return " ".join(str(text or "").split())


def _strip_redundant_assistant_echo(response: str, history_messages: list[dict]) -> str:
    """去除模型在新回答里误拼接的上一条完整助手回复。"""
    if not response or not history_messages:
        return response

    previous_assistant = ""
    for message in reversed(history_messages):
        if message.get("role") == "assistant":
            previous_assistant = str(message.get("content") or "").strip()
            if previous_assistant:
                break
    if len(previous_assistant) < 120:
        return response

    raw_index = response.find(previous_assistant)
    if raw_index >= 20 and len(response) - raw_index >= int(len(previous_assistant) * 0.75):
        trimmed = response[:raw_index].rstrip()
        if len(trimmed) >= 40:
            return trimmed

    normalized_prev = _normalize_for_echo_match(previous_assistant)
    normalized_resp = _normalize_for_echo_match(response)
    if len(normalized_prev) < 120:
        return response

    normalized_index = normalized_resp.find(normalized_prev)
    if normalized_index >= 40:
        prefix = normalized_resp[:normalized_index].strip()
        if len(prefix) >= 40:
            return prefix

    return response


def _format_live_reply_preview(live_response: str) -> str:
    text = str(live_response or "").strip()
    if not text:
        return ""
    return f"`模型正在回复中...`\n\n{text}▌"


def get_cached_data_overview() -> dict:
    now = time.time()
    cached_value = st.session_state.get("_data_overview_cache")
    cached_at = st.session_state.get("_data_overview_cache_at", 0.0)

    if cached_value is not None and now - cached_at < OVERVIEW_CACHE_TTL_SECONDS:
        return cached_value

    overview = dashboard_service.get_data_overview()
    st.session_state["_data_overview_cache"] = overview
    st.session_state["_data_overview_cache_at"] = now
    return overview


def _render_workspace_strip(system_status: dict) -> None:
    active_target = st.session_state.get("active_target") or "未锁定目标"
    target_count = len(st.session_state.get("active_targets", []))
    if not target_count and st.session_state.get("active_target"):
        target_count = 1

    items = [
        ("工作台", "企业研究智能体"),
        ("当前目标", active_target),
        ("识别实体", str(target_count)),
        ("消息数", str(system_status.get("msg_count", 0))),
        ("模型状态", str(system_status.get("api_status", "未知"))),
    ]
    items_html = "".join(
        (
            "<div class='workspace-strip-item'>"
            f"<span>{label}</span>"
            f"<strong>{value}</strong>"
            "</div>"
        )
        for label, value in items
    )
    st.markdown(f"<div class='workspace-strip'>{items_html}</div>", unsafe_allow_html=True)


def _render_empty_chat_state() -> None:
    st.markdown(
        """
        <div id="welcome_shell_stable_box" class="welcome-shell">
            <div id="welcome_title_hero" class="welcome-title">今天想研究什么？</div>
            <div id="welcome_sub_hero" class="welcome-sub">
                输入公司、赛道或研究问题，光之耀面会为你整理公司画像、财务摘要与横向对比结果。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _handle_prompt_submission(prompt: str) -> None:
    cleaned_prompt = prompt.strip()
    if not cleaned_prompt:
        return

    targets = company_service.identify_target_companies(cleaned_prompt)
    if targets:
        st.session_state.active_targets = targets
        st.session_state.active_target = targets[0]
        append_tool_log(
            tool="目标识别",
            success=True,
            elapsed="12ms",
            info=f"识别到实体：{', '.join(targets)}",
        )
    else:
        current_active_target = st.session_state.get("active_target")
        if should_preserve_active_target(cleaned_prompt, current_active_target):
            append_tool_log(
                tool="目标识别",
                success=True,
                elapsed="8ms",
                info=f"未识别到新实体，沿用当前目标：{current_active_target}",
            )
        else:
            st.session_state.active_targets = []
            st.session_state.active_target = None

    st.session_state.messages.append({"role": "user", "content": cleaned_prompt})
    # 核心修复：设置待处理查询信号，触发分析引擎
    st.session_state.pending_query = cleaned_prompt
    save_current_session()
    st.rerun()


def render_chat_panel(show_chart: bool = True):
    empty_state = is_initial_chat_state()
    chat_box = st.container(border=False)

    with chat_box:
        if empty_state:
            _render_empty_chat_state()
        else:
            for message in get_visible_chat_messages():
                with st.chat_message(message["role"]):
                    if message["role"] == "assistant":
                        st.markdown("<div class='is-assistant-marker' style='display:none'></div>", unsafe_allow_html=True)
                        payload = message.get("payload")
                        if payload:
                            render_response_payload(payload, show_chart=show_chart)
                        else:
                            render_message_with_charts(message["content"], show_chart=show_chart)
                    else:
                        st.markdown("<div class='is-user-marker' style='display:none'></div>", unsafe_allow_html=True)
                        st.markdown(message["content"])

    # 原生st.chat_input 天然固定在页面最底部，无需CSS hack
    prompt = st.chat_input(
        placeholder="输入公司、赛道或你想研究的问题",
        key="main_chat_input",
    )
    if prompt:
        _handle_prompt_submission(prompt)

    return chat_box


def render_right_panel(container=None) -> None:
    """渲染右侧图像看板，包含当前会话中所有的图表洞察"""
    messages = st.session_state.get("messages", [])
    
    # 提取所有包含图表的助手回复
    historic_charts = []
    for msg in messages:
        if msg.get("role") == "assistant":
            payload = msg.get("payload")
            if payload and payload.get("chart"):
                historic_charts.append(payload["chart"])
    
    # 获取当前正在生成的图表（如果有）
    streaming_chart = st.session_state.get("latest_chart_data")
    
    with (container if container is not None else st.container()):
        if not historic_charts and not streaming_chart:
            st.markdown(
                """
                <div style="background:rgba(30,41,59,0.3); border:1px dashed rgba(56,189,248,0.2); border-radius:12px; padding:40px 20px; text-align:center; margin-top:20px;">
                    <div style="font-size:2rem; margin-bottom:15px; opacity:0.4;">📊</div>
                    <div style="color:rgba(56,189,248,0.6); font-family:'Orbitron', sans-serif; font-size:0.85rem; letter-spacing:2px;">等待视觉洞察</div>
                    <div style="color:rgba(148,163,184,0.4); font-size:0.75rem; margin-top:8px;">
                        当 AI 在分析中生成趋势图或分布图时，<br>
                        将在此处按时间顺序进行累计展示。
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            # 渲染历史图表
            for idx, chart in enumerate(historic_charts):
                st.markdown(f"###### 洞察 #{idx + 1}")
                render_latest_chart_card(chart)
                st.markdown("---")
            
            # 渲染流式中的图表
            if streaming_chart:
                # 如果最新的历史图表和流式图表是一样的，则不重复显示（避免 st.rerun 前后的瞬间重影）
                if not historic_charts or str(streaming_chart) != str(historic_charts[-1]):
                    st.markdown("###### 实时分析中...")
                    render_latest_chart_card(streaming_chart)


def render_report_tab() -> None:
    st.markdown(
        '<span style="font-size:0.9rem; color:#94A3B8;">基于当前会话内容整理生成正式研究报告。</span>',
        unsafe_allow_html=True,
    )
    if st.button("生成研究报告", use_container_width=True, key="generate_report"):
        messages = st.session_state.get("messages", [])
        if messages and len(messages) > 1:
            report_html = report_service.build_html_report(
                messages,
                generated_at=datetime.now(),
                active_target=st.session_state.get("active_target"),
            )
            st.download_button(
                label="下载研究报告",
                data=report_html,
                file_name=f"research_report_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
                mime="text/html",
                use_container_width=True,
                key="download_report",
            )
        else:
            st.warning("请先完成至少一次有效分析，再生成研究报告。")


def render_industry_comparison_tab() -> None:
    active_target = st.session_state.get("active_target")
    if not active_target:
        st.info("请先在对话中识别一个目标公司，系统会基于该公司的二级赛道展示横向对比。")
        return

    _, symbol = company_service.parse_company_choice(active_target)
    snapshots = comparison_service.get_peer_snapshots_for_symbol(symbol, limit=10)
    if not snapshots:
        st.warning("当前无法生成同赛道对比数据。")
        return

    track_template = comparison_service.get_track_template_for_symbol(symbol)
    chart_specs = comparison_service.build_track_chart_specs(symbol, limit=10, max_metrics=4)
    metric_keys = [metric.key for metric in track_template.metrics] if track_template else []
    metric_display_map = (
        {metric.key: metric.display_name for metric in track_template.metrics}
        if track_template
        else {}
    )
    quality_result = data_quality_service.build_track_data_quality(
        snapshots=snapshots,
        metric_keys=metric_keys,
        metric_display_map=metric_display_map,
    )
    scoring_result = track_scoring_service.score_snapshots(
        snapshots=snapshots,
        track_template=track_template,
    )
    st.markdown(
        '<span style="font-size:0.9rem; color:#94A3B8;">基于统一公司画像与财务模型生成同赛道比较结果。</span>',
        unsafe_allow_html=True,
    )
    if track_template is not None:
        st.caption(f"赛道模板：{track_template.track_name} | {track_template.focus}")

    if chart_specs:
        chart_cols = st.columns(2)
        for index, chart_spec in enumerate(chart_specs):
            with chart_cols[index % 2]:
                from streamlit_echarts import st_echarts
                from src.presentation.renderers.message_renderer import build_echarts_option
                st_echarts(
                    options=build_echarts_option(chart_spec, height=320),
                    height="320px",
                    key=f"track_chart_{symbol}_{index}",
                )

    st.markdown("#### 数据溯源与质量")
    info_col1, info_col2, info_col3 = st.columns(3)
    info_col1.metric("赛道样本公司数", quality_result.get("sample_count", 0))
    info_col2.metric(
        "指标整体覆盖率",
        f"{quality_result.get('overall_coverage', 0.0) * 100:.1f}%",
    )
    info_col3.metric("评分状态", "可计算" if scoring_result.get("ok") else "样本不足")

    if quality_result.get("metric_rows"):
        st.dataframe(quality_result["metric_rows"], use_container_width=True, height=220)

    source_stats = quality_result.get("source_stats") or []
    if source_stats:
        with st.expander("查看来源分布与报告期分布", expanded=False):
            st.markdown("**来源分布**")
            st.dataframe(source_stats, use_container_width=True, height=170)
            period_stats = quality_result.get("latest_period_stats") or []
            if period_stats:
                st.markdown("**报告期分布**")
                st.dataframe(period_stats, use_container_width=True, height=170)

    st.markdown("#### 赛道评分卡（熵权 + TOPSIS）")
    if scoring_result.get("ok"):
        st.dataframe(scoring_result["ranking_df"], use_container_width=True, height=240)
        st.dataframe(scoring_result["weight_df"], use_container_width=True, height=220)
    else:
        st.info(scoring_result.get("reason", "当前样本不足，暂不能计算评分。"))

    st.dataframe(
        comparison_service.snapshots_to_focused_dataframe(snapshots, track_template),
        use_container_width=True,
        height=420,
    )

    # --- 新增：AI 智能赛道解读 ---
    st.markdown("#### 🤖 智能赛道分析")
    if st.button("生成 AI 赛道深度解读", key=f"ai_peer_analysis_{symbol}"):
        with st.spinner("正在调度决策引擎分析赛道分布..."):
            df = comparison_service.snapshots_to_focused_dataframe(snapshots, track_template)
            ai_insight_stream = comparison_service.analyze_peers_with_agent(active_target, df)
            
            # 使用流式容器显示
            insight_container = st.empty()
            full_insight = ""
            for chunk in ai_insight_stream:
                full_insight += chunk
                insight_container.markdown(f'<div class="ai-insight-box">{full_insight}▌</div>', unsafe_allow_html=True)
            insight_container.markdown(f'<div class="ai-insight-box">{full_insight}</div>', unsafe_allow_html=True)


def render_dashboard_view() -> None:
    """渲染全轨道同步主视图 (双栏布局)"""
    col1, col2 = st.columns([1.8, 1.2], gap="large")
    
    with col1:
        render_chat_panel()
        render_pending_agent_response()
        
    with col2:
        render_right_panel()


def render_chat_panel(show_chart: bool = True):
    empty_state = is_initial_chat_state()
    chat_box = st.container(border=False)

    with chat_box:
        if empty_state:
            _render_empty_chat_state()
        else:
            for message in get_visible_chat_messages():
                with st.chat_message(message["role"]):
                    if message["role"] == "assistant":
                        st.markdown("<div class='is-assistant-marker' style='display:none'></div>", unsafe_allow_html=True)
                        payload = message.get("payload")
                        if payload:
                            render_response_payload(payload, show_chart=show_chart)
                        else:
                            render_message_with_charts(message["content"], show_chart=show_chart)
                    else:
                        st.markdown("<div class='is-user-marker' style='display:none'></div>", unsafe_allow_html=True)
                        st.markdown(message["content"])

    # 原生st.chat_input 天然固定在页面最底部
    prompt = st.chat_input(
        placeholder="输入公司、赛道或你想研究的问题",
        key="main_chat_input",
    )
    if prompt:
        _handle_prompt_submission(prompt)

    return chat_box


def render_pending_agent_response() -> None:
    if not st.session_state.get("pending_query"):
        return

    query = st.session_state.pending_query
    # 修复：直接从 session_state 获取历史记录
    history = st.session_state.get("messages", [])
    
    # 开启单轨流式渲染
    with st.chat_message("assistant"):
        status_placeholder = st.empty()
        response_placeholder = st.empty()
        
        try:
            response = ""
            detected_chart = None
            
            # 开始流式调用分析引擎
            for chunk in chat_service.run_query_stream(
                query, 
                chat_history=history,
                active_target=st.session_state.get("active_target"),
                active_targets=st.session_state.get("active_targets", [])
            ):
                if isinstance(chunk, str):
                    response += chunk
                    # 实时解析当前文段
                    live_payload = normalize_response_payload(response)
                    # 在对话区显示即时文案
                    response_placeholder.markdown(live_payload.get("body", "") + "▌")
                    
                    # 如果有图表，流式模式下也渲染在下方
                    if live_payload.get("chart") and not detected_chart:
                        detected_chart = live_payload["chart"]
                        render_latest_chart_card(detected_chart)
            
            # 结束后的最终清理与保存
            final_payload = normalize_response_payload(response)
            st.session_state.messages.append({
                "role": "assistant",
                "content": response,
                "payload": final_payload
            })
            # 清除当前待处理状态
            st.session_state.pending_query = None
            refresh_current_session_title(st.session_state.messages)
            save_current_session()
            # 触发重刷以固化本轨道及其图表
            st.rerun()
            
        except Exception as exc:
            st.error(f"分析引擎故障: {str(exc)}")
            st.session_state.pending_query = None


def render_app() -> None:
    ensure_session_defaults()

    empty_state = is_initial_chat_state()
    apply_global_styles(is_new_chat=empty_state)
    render_sidebar()

    # 仅在非空状态（已开始对话）时渲染顶部导航
    if not empty_state:
        render_top_nav()
    
    active_view = st.session_state.get("active_nav", "🤖 决策引擎")

    # 如果是空状态，强制渲染决策引擎（Chat）页面，且不带顶栏
    if empty_state:
        render_dashboard_view()
    else:
        # 非空状态下的多网页路由
        if active_view == "🤖 决策引擎":
            render_dashboard_view()
        elif active_view == "🔍 财务透视":
            st.markdown('<div class="main-content-wrapper"></div>', unsafe_allow_html=True)
            render_financial_tab()
        elif active_view == "⚔️ 同赛道对比":
            st.markdown('<div class="main-content-wrapper"></div>', unsafe_allow_html=True)
            render_industry_comparison_tab()
        elif active_view == "📄 研究报告":
            st.markdown('<div class="main-content-wrapper"></div>', unsafe_allow_html=True)
            render_report_tab()
