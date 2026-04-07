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

chat_service = ChatService()
company_service = CompanyService()
dashboard_service = DashboardService()
report_service = ReportService()
comparison_service = ComparisonService()
data_quality_service = DataQualityService()
track_scoring_service = TrackScoringService()

OVERVIEW_CACHE_TTL_SECONDS = 300


def _normalize_for_echo_match(text: str) -> str:
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
        <div class="welcome-shell">
            <div class="welcome-title">今天想研究什么？</div>
            <div class="welcome-sub">
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
    save_current_session()
    st.rerun()


def _render_prompt_form(form_key: str, input_key: str, empty_state: bool) -> None:
    shell_class = "prompt-shell prompt-shell-empty" if empty_state else "prompt-shell"
    st.markdown(f"<div class='{shell_class}'>", unsafe_allow_html=True)
    with st.form(form_key, clear_on_submit=True, border=False):
        input_col, button_col = st.columns([22, 1])
        with input_col:
            prompt = st.text_input(
                "主输入框",
                key=input_key,
                label_visibility="collapsed",
                placeholder="输入公司、赛道或你想研究的问题",
            )
        with button_col:
            submitted = st.form_submit_button("➤", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if submitted:
        _handle_prompt_submission(prompt)


def render_chat_panel():
    empty_state = is_initial_chat_state()
    chat_box = st.container(height=500 if empty_state else 560, border=False)

    with chat_box:
        if empty_state:
            _render_empty_chat_state()
        else:
            for message in get_visible_chat_messages():
                with st.chat_message(message["role"]):
                    if message["role"] == "assistant":
                        payload = message.get("payload")
                        if payload:
                            render_response_payload(payload)
                        else:
                            render_message_with_charts(message["content"])
                    else:
                        st.markdown(message["content"])

    if empty_state:
        left_spacer, center_col, right_spacer = st.columns([0.25, 11.5, 0.25])
        with center_col:
            _render_prompt_form("empty_prompt_form", "empty_prompt_input", empty_state=True)
    else:
        _render_prompt_form("chat_prompt_form", "chat_prompt_input", empty_state=False)

    return chat_box


def render_right_panel() -> None:
    st.markdown(
        '<div class="cockpit-card"><div class="panel-kicker">智能体控制台</div><span class="chain-title">执行链路</span>',
        unsafe_allow_html=True,
    )
    tool_logs = st.session_state.get("tool_calls_log", [])
    if tool_logs:
        log_html = ""
        for log_entry in tool_logs[-6:]:
            success = log_entry.get("success", True)
            status_icon = "正常" if success else "异常"
            status_class = "chain-status-ok" if success else "chain-status-error"
            tool_name = log_entry.get("tool", "未知步骤")
            elapsed = log_entry.get("elapsed", "")
            info = log_entry.get("info", "")
            elapsed_str = f' <span class="chain-time">({elapsed})</span>' if elapsed else ""
            info_str = f'<div class="chain-meta">{info}</div>' if info else ""
            log_html += (
                f'<div class="chain-item"><span class="{status_class}">{status_icon}</span> '
                f'<span class="chain-tool">{tool_name}</span>{elapsed_str}{info_str}</div>'
            )
        st.markdown(log_html, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="chain-empty">当前暂无执行任务。新的分析启动后，这里会自动显示关键步骤与状态。</div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    render_latest_chart_card(st.session_state.get("latest_chart_data"))


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
                st.plotly_chart(
                    build_chart_figure(chart_spec, height=320, compact=False),
                    use_container_width=True,
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


def render_bottom_tabs() -> None:
    st.markdown('<div style="margin-top:10px;"></div>', unsafe_allow_html=True)
    st.markdown(
        (
            '<div class="analysis-deck-header">'
            '<div class="panel-kicker">分析工作区</div>'
            '<div class="analysis-deck-title">研究工作台</div>'
            '<div class="analysis-deck-sub">围绕当前目标开展财务核验、同赛道对比与正式研究报告输出。</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )
    financial_tab, compare_tab, report_tab = st.tabs(["财务数据", "同赛道对比", "研究报告"])

    with financial_tab:
        render_financial_tab()

    with compare_tab:
        render_industry_comparison_tab()

    with report_tab:
        render_report_tab()


def render_pending_agent_response(chat_box) -> None:
    messages = st.session_state.get("messages", [])
    if not messages or messages[-1]["role"] != "user":
        return

    last_prompt = messages[-1]["content"]
    with chat_box:
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            status_placeholder = st.empty()
            try:
                response = ""
                response_payload = None
                current_tool_start = None

                for chunk in chat_service.run_query_stream(
                    last_prompt,
                    chat_history=messages[:-1],
                    active_target=st.session_state.get("active_target"),
                    active_targets=st.session_state.get("active_targets", []),
                ):
                    if isinstance(chunk, str):
                        response += chunk
                        live_response = _strip_redundant_assistant_echo(
                            fix_markdown_formatting(response),
                            messages[:-1],
                        ).strip()
                        if live_response:
                            status_placeholder.markdown(
                                "<div style='font-size:0.82rem; color:#94A3B8; margin-top:0.35rem;'>???????...</div>",
                                unsafe_allow_html=True,
                            )
                            response_placeholder.markdown(live_response + "▌")
                        else:
                            response_placeholder.empty()
                    elif isinstance(chunk, dict) and "status" in chunk:
                        status_text = chunk["status"]
                        if "决策链执行中" in status_text:
                            tool_name = chat_service.extract_tool_name(status_text)
                            current_tool_start = time.time()
                            append_tool_log(tool=tool_name, success=True)
                        elif "处理完成" in status_text and current_tool_start is not None:
                            update_latest_tool_elapsed(time.time() - current_tool_start)
                            current_tool_start = None
                        status_placeholder.markdown(
                            f"<div style='font-size:0.82rem; color:#94A3B8; margin-top:0.35rem;'>{status_text}</div>",
                            unsafe_allow_html=True,
                        )
                    elif isinstance(chunk, dict) and "response_payload" in chunk:
                        response_payload = chunk["response_payload"]

                response = fix_markdown_formatting(response)
                response = _strip_redundant_assistant_echo(response, messages[:-1])
                response_payload = normalize_response_payload(
                    content=response,
                    payload=response_payload,
                    source=(response_payload or {}).get("source", "chat"),
                )
                stored_content = response or str(response_payload.get("raw_text") or response_payload.get("body") or "")
                status_placeholder.empty()
                response_placeholder.empty()
                st.session_state.latest_chart_data = response_payload.get("chart")
                render_response_payload(response_payload)
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": stored_content,
                        "payload": response_payload,
                    }
                )
                refresh_current_session_title(st.session_state.messages)
                save_current_session()
            except Exception as exc:
                response_placeholder.empty()
                status_placeholder.empty()
                st.error(f"智能体运行异常: {exc}")


def render_app() -> None:
    ensure_session_defaults()
    st.set_page_config(
        page_title="光之耀面",
        page_icon="✨",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    apply_global_styles()
    overview = get_cached_data_overview()
    system_status = dashboard_service.get_system_status(
        msg_count=len(st.session_state.get("messages", []))
    )
    render_sidebar(system_status=system_status, overview=overview)

    empty_state = is_initial_chat_state()
    if empty_state:
        chat_box = render_chat_panel()
    else:
        col_center, col_right = st.columns([3.2, 1.08], gap="large")
        with col_center:
            _render_workspace_strip(system_status)
            chat_box = render_chat_panel()
        with col_right:
            render_right_panel()

        render_bottom_tabs()

    render_pending_agent_response(chat_box)
