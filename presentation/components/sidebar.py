import streamlit as st

from src.presentation.state.session_state import (
    delete_current_session,
    delete_history_session,
    get_current_session_preview,
    list_history_previews,
    load_history_session,
    rename_current_session_title,
    rename_history_session,
    start_new_session,
)


def _delete_confirm_key(session_key: str) -> str:
    return f"confirm_delete_{session_key}"


def _action_mode_key(session_key: str) -> str:
    return f"history_action_mode_{session_key}"


def _clear_all_delete_confirm_states() -> None:
    for key in list(st.session_state.keys()):
        if str(key).startswith("confirm_delete_"):
            st.session_state.pop(key, None)


def _clear_all_action_modes() -> None:
    for key in list(st.session_state.keys()):
        if str(key).startswith("history_action_mode_"):
            st.session_state.pop(key, None)


def _close_history_action_panel() -> None:
    st.session_state["history_action_target"] = None
    _clear_all_delete_confirm_states()
    _clear_all_action_modes()


def _render_logo_block(system_status: dict, overview: dict) -> None:
    st.markdown(
        (
            '<div class="sidebar-brand">'
            '<div class="sidebar-logo">'
            '<span class="sidebar-logo-ring"></span>'
            '<span class="sidebar-logo-core">光</span>'
            "</div>"
            '<div class="sidebar-brand-copy">'
            '<div class="sidebar-brand-title">光之耀面</div>'
            '<div class="sidebar-brand-sub">企业研究与多维分析工作台</div>'
            "</div></div>"
        ),
        unsafe_allow_html=True,
    )

    status_items = [
        f"模型接口 {system_status['api_status']}",
        f"知识库 {'就绪' if system_status['kb_ready'] else '未就绪'}",
        f"当前会话 {system_status['msg_count']} 条消息",
    ]
    st.markdown(
        "<div class='sidebar-status'>"
        + "".join(f"<div class='sidebar-status-item'>{item}</div>" for item in status_items)
        + "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        (
            "<div class='sidebar-metrics'>"
            f"<div class='sidebar-metric'><span>覆盖公司</span><strong>{overview['company_count']}</strong></div>"
            f"<div class='sidebar-metric'><span>行业数</span><strong>{overview['industry_count']}</strong></div>"
            f"<div class='sidebar-metric'><span>平均毛利率</span><strong>{overview['avg_gross_margin']}%</strong></div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_history_actions(preview: dict) -> None:
    filename = preview.get("filename")
    session_key = preview.get("session_id", "session")
    mode_key = _action_mode_key(session_key)
    mode = st.session_state.get(mode_key, "menu")

    if mode == "menu":
        rename_col, delete_col = st.columns(2)
        with rename_col:
            if st.button("重命名", key=f"rename_menu_{session_key}", use_container_width=True):
                st.session_state[mode_key] = "rename"
                st.rerun()
        with delete_col:
            if st.button("删除", key=f"delete_menu_{session_key}", use_container_width=True):
                st.session_state[mode_key] = "delete"
                st.rerun()
        return

    if mode == "rename":
        new_title = st.text_input(
            "重命名会话",
            value=preview.get("title", ""),
            key=f"rename_input_{session_key}",
            label_visibility="collapsed",
            placeholder="输入新的会话名称",
        )
        save_col, cancel_col = st.columns(2)
        with save_col:
            if st.button("保存", key=f"rename_save_{session_key}", use_container_width=True):
                if filename:
                    rename_history_session(filename, new_title)
                else:
                    rename_current_session_title(new_title)
                _close_history_action_panel()
                st.rerun()
        with cancel_col:
            if st.button("取消", key=f"rename_cancel_{session_key}", use_container_width=True):
                st.session_state[mode_key] = "menu"
                st.rerun()
        return

    confirm_key = _delete_confirm_key(session_key)
    st.session_state[confirm_key] = True
    warning_text = "确认删除当前对话？" if not filename else "确认删除这条历史对话？"
    st.caption(warning_text)
    confirm_col, cancel_col = st.columns(2)
    with confirm_col:
        if st.button("确认", key=f"delete_confirm_{session_key}", use_container_width=True):
            if filename:
                delete_history_session(filename)
            else:
                delete_current_session()
            _close_history_action_panel()
            st.rerun()
    with cancel_col:
        if st.button("取消", key=f"delete_cancel_{session_key}", use_container_width=True):
            st.session_state[mode_key] = "menu"
            st.session_state.pop(confirm_key, None)
            st.rerun()


def _render_session_row(preview: dict) -> None:
    title = preview.get("title", "未命名会话")
    session_key = preview.get("session_id", title)
    active = preview.get("active", False)
    filename = preview.get("filename")
    is_menu_open = st.session_state.get("history_action_target") == session_key

    marker_classes = ["history-row-marker"]
    if active:
        marker_classes.append("history-row-active-marker")
    if is_menu_open:
        marker_classes.append("history-row-menu-open-marker")
    st.markdown(f"<div class='{' '.join(marker_classes)}'></div>", unsafe_allow_html=True)

    with st.container():
        title_col, menu_col = st.columns([9, 1])

        with title_col:
            button_type = "primary" if active else "secondary"
            if filename:
                if st.button(
                    title,
                    key=f"open_{session_key}",
                    use_container_width=True,
                    type=button_type,
                ):
                    load_history_session(filename)
                    _close_history_action_panel()
                    st.rerun()
            else:
                st.button(
                    title,
                    key=f"open_live_{session_key}",
                    use_container_width=True,
                    type="primary",
                    disabled=True,
                )

        with menu_col:
            if st.button("⋯", key=f"menu_toggle_{session_key}", help="更多操作", use_container_width=True):
                opened_target = st.session_state.get("history_action_target")
                st.session_state["history_action_target"] = None if opened_target == session_key else session_key
                _clear_all_delete_confirm_states()
                _clear_all_action_modes()
                st.rerun()

    if is_menu_open:
        st.markdown("<div class='history-actions-marker'></div>", unsafe_allow_html=True)
        with st.container():
            _render_history_actions(preview)


def render_sidebar(system_status: dict, overview: dict) -> None:
    with st.sidebar:
        _render_logo_block(system_status, overview)

        if st.button("新建对话", use_container_width=True):
            start_new_session()
            _close_history_action_panel()
            st.rerun()

        st.markdown('<div class="sidebar-section-label">当前对话</div>', unsafe_allow_html=True)
        current_preview = get_current_session_preview()
        if current_preview is not None:
            _render_session_row(current_preview)
        else:
            st.markdown(
                '<div class="sidebar-section-hint">当前打开的是历史会话，已在下方高亮显示。</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div class="sidebar-section-label">历史记录</div>', unsafe_allow_html=True)
        history_previews = list_history_previews(limit=20)
        if not history_previews:
            st.markdown(
                '<div class="sidebar-section-hint">还没有历史会话，先开始一轮分析吧。</div>',
                unsafe_allow_html=True,
            )

        for preview in history_previews:
            _render_session_row(preview)
