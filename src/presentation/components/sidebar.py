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


def _render_logo_block() -> None:
    # 注入侧边栏专属品牌样式，确保在 Streamlit 嵌套结构中生效
    st.markdown(
        """
        <style>
            .sidebar-brand {
                display: flex !important;
                align-items: center !important;
                gap: 14px !important;
                margin: 5px 0 25px 0 !important;
                padding: 10px !important;
                background: rgba(255, 255, 255, 0.02) !important;
                border-radius: 20px !important;
                border: 1px solid rgba(255, 255, 255, 0.05) !important;
            }
            .sidebar-logo {
                width: 60px !important;
                height: 54px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                position: relative !important;
                clip-path: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%) !important;
                background: linear-gradient(135deg, rgba(59, 130, 246, 0.2) 0%, rgba(6, 182, 212, 0.1) 100%) !important;
                border: 1px solid rgba(56, 189, 248, 0.5) !important;
                backdrop-filter: blur(12px) !important;
                box-shadow: 0 0 20px rgba(56, 189, 248, 0.2) !important;
                animation: logo-float 4s infinite ease-in-out !important;
            }
            .sidebar-logo-inner {
                position: absolute !important;
                inset: 3px !important;
                clip-path: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%) !important;
                background: rgba(0, 229, 255, 0.05) !important;
                border: 0.5px solid rgba(255, 255, 255, 0.1) !important;
            }
            .sidebar-logo-core {
                position: relative !important;
                z-index: 2 !important;
                font-family: 'Orbitron', 'PingFang SC', sans-serif !important;
                font-size: 1.5rem !important;
                font-weight: 900 !important;
                color: #00E5FF !important;
                text-shadow: 0 0 12px rgba(0, 229, 255, 0.8), 0 0 25px rgba(0, 229, 255, 0.3) !important;
                display: block !important;
                line-height: 1 !important;
            }
            .sidebar-brand-title {
                background: linear-gradient(to right, #ffffff 0%, #cbd5e1 100%) !important;
                -webkit-background-clip: text !important;
                -webkit-text-fill-color: transparent !important;
                font-size: 1.3rem !important;
                font-weight: 800 !important;
                letter-spacing: 2px !important;
                font-family: 'Orbitron', 'PingFang SC', sans-serif !important;
                margin-bottom: 2px !important;
            }
            .sidebar-brand-sub {
                color: #64748b !important;
                font-size: 0.65rem !important;
                letter-spacing: 1px !important;
                font-weight: 600 !important;
                text-transform: uppercase !important;
                font-family: 'Rajdhani', sans-serif !important;
            }
            @keyframes logo-float {
                0%, 100% { transform: translateY(0) rotate(0deg); }
                50% { transform: translateY(-4px) rotate(1deg); }
            }
        </style>
        <div class="sidebar-brand">
            <div class="sidebar-logo">
                <div class="sidebar-logo-inner"></div>
                <div class="sidebar-logo-core">光</div>
            </div>
            <div class="sidebar-brand-copy">
                <div class="sidebar-brand-title">光之耀面</div>
                <div class="sidebar-brand-sub">Enterprise Intelligence Hub</div>
            </div>
        </div>
        """,
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
        # 调整比例，使操作按钮更靠右且更小
        title_col, menu_col = st.columns([8.5, 1.5])

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
            # 这里的 ⋯ 将由 styles.py 中的 CSS 进行样式定制
            with st.popover("⋯", use_container_width=True):
                if st.button("✏️ 重命名", key=f"rename_pop_{session_key}", use_container_width=True):
                    st.session_state[_action_mode_key(session_key)] = "rename"
                    st.session_state["history_action_target"] = session_key
                    _clear_all_delete_confirm_states()
                    st.rerun()
                if st.button("🗑️ 删除", key=f"delete_pop_{session_key}", use_container_width=True):
                    st.session_state[_action_mode_key(session_key)] = "delete"
                    st.session_state["history_action_target"] = session_key
                    _clear_all_delete_confirm_states()
                    st.rerun()


def render_sidebar() -> None:
    with st.sidebar:
        _render_logo_block()

        st.markdown('<div class="new-chat-marker"></div>', unsafe_allow_html=True)
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

        current_session_id = current_preview.get("session_id") if current_preview else None
        for preview in history_previews:
            if current_session_id and preview.get("session_id") == current_session_id:
                continue
            _render_session_row(preview)
