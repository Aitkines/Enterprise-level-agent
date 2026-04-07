import streamlit as st
import streamlit.components.v1 as components


def _lock_sidebar_open() -> None:
    """强制侧栏保持展开，并隐藏所有开关按钮。"""
    components.html(
        """
        <script>
            const lockSidebar = () => {
                const doc = window.parent.document;
                if (!doc) return;

                const hideSelectors = [
                    '[data-testid="stSidebarContent"] > div:first-child',
                    '[data-testid="stSidebarContent"] > div:first-child *',
                    '[data-testid="stSidebarNav"] button',
                    '[data-testid="collapsedControl"]',
                    '[data-testid="collapsedControl"] button',
                    '[aria-label="Open sidebar"]',
                    '[aria-label="Close sidebar"]',
                    '[data-testid="stSidebarCollapseButton"]',
                    '[data-testid="stSidebarHeaderCollapseButton"]',
                    'button[aria-label*="sidebar"]'
                ];

                hideSelectors.forEach((selector) => {
                    doc.querySelectorAll(selector).forEach((el) => {
                        el.style.display = 'none';
                        el.style.visibility = 'hidden';
                        el.style.pointerEvents = 'none';
                    });
                });

                const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                if (!sidebar) return;

                const sidebarContent = doc.querySelector('[data-testid="stSidebarContent"]');
                if (sidebarContent && sidebarContent.firstElementChild) {
                    const closeControl = sidebarContent.firstElementChild;
                    closeControl.style.display = 'none';
                    closeControl.style.visibility = 'hidden';
                    closeControl.style.pointerEvents = 'none';
                    closeControl.style.width = '0';
                    closeControl.style.height = '0';
                    closeControl.style.overflow = 'hidden';
                    closeControl.style.margin = '0';
                    closeControl.style.padding = '0';
                }

                if (sidebar.getAttribute('aria-expanded') === 'false') {
                    const openButton = doc.querySelector('[aria-label="Open sidebar"], [data-testid="collapsedControl"] button, [data-testid="collapsedControl"]');
                    if (openButton) {
                        openButton.click();
                    }
                    sidebar.setAttribute('aria-expanded', 'true');
                }

                const wireConversationRows = () => {
                    const setMenuButtonVisible = (button, visible) => {
                        if (!button) return;
                        button.style.opacity = visible ? '1' : '0';
                        button.style.visibility = visible ? 'visible' : 'hidden';
                        button.style.pointerEvents = visible ? 'auto' : 'none';
                        button.style.transform = visible ? 'translateX(0)' : 'translateX(4px)';
                    };

                    const markerSelector = '[data-testid="stMarkdownContainer"]:has(.history-row-marker)';
                    doc.querySelectorAll(markerSelector).forEach((marker) => {
                        const rowShell = marker.nextElementSibling;
                        if (!rowShell) return;

                        rowShell.classList.add('history-row-shell');
                        if (marker.querySelector('.history-row-active-marker')) {
                            rowShell.classList.add('history-row-shell-active');
                        } else {
                            rowShell.classList.remove('history-row-shell-active');
                        }

                        if (marker.querySelector('.history-row-menu-open-marker')) {
                            rowShell.classList.add('history-row-shell-menu-open');
                        } else {
                            rowShell.classList.remove('history-row-shell-menu-open');
                        }

                        const columns = rowShell.querySelectorAll(':scope > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]');
                        if (columns.length >= 2) {
                            columns[0].classList.add('history-row-main-col');
                            columns[1].classList.add('history-row-menu-col');

                            const menuButtonWrap = columns[1].querySelector('.stButton');
                            if (menuButtonWrap) {
                                menuButtonWrap.classList.add('history-row-menu-button');
                                const menuButton = menuButtonWrap.querySelector('button');
                                setMenuButtonVisible(menuButton, false);

                                if (!rowShell.dataset.historyHoverBound) {
                                    rowShell.addEventListener('mouseenter', () => {
                                        setMenuButtonVisible(menuButtonWrap.querySelector('button'), true);
                                    });
                                    rowShell.addEventListener('mouseleave', () => {
                                        setMenuButtonVisible(menuButtonWrap.querySelector('button'), false);
                                    });
                                    rowShell.dataset.historyHoverBound = '1';
                                }
                            }
                        }
                    });

                    const actionSelector = '[data-testid="stMarkdownContainer"]:has(.history-actions-marker)';
                    doc.querySelectorAll(actionSelector).forEach((marker) => {
                        const actionShell = marker.nextElementSibling;
                        if (actionShell) {
                            actionShell.classList.add('history-actions-shell');
                        }
                    });

                    const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                    if (!sidebar) return;

                    const dotButtons = Array.from(sidebar.querySelectorAll('button')).filter((button) => {
                        const text = (button.textContent || '').trim();
                        return text === '⋯' || text === '...';
                    });

                    dotButtons.forEach((button) => {
                        setMenuButtonVisible(button, false);

                        const rowShell =
                            button.closest('div[data-testid="stHorizontalBlock"]')
                            || button.closest('div[data-testid="stVerticalBlock"]');
                        if (!rowShell) return;

                        rowShell.classList.add('history-row-shell');

                        if (!rowShell.dataset.dotHoverBound) {
                            rowShell.addEventListener('mouseenter', () => {
                                const rowButton = Array.from(rowShell.querySelectorAll('button')).find((candidate) => {
                                    const text = (candidate.textContent || '').trim();
                                    return text === '⋯' || text === '...';
                                });
                                setMenuButtonVisible(rowButton, true);
                            });
                            rowShell.addEventListener('mouseleave', () => {
                                const rowButton = Array.from(rowShell.querySelectorAll('button')).find((candidate) => {
                                    const text = (candidate.textContent || '').trim();
                                    return text === '⋯' || text === '...';
                                });
                                setMenuButtonVisible(rowButton, false);
                            });
                            rowShell.dataset.dotHoverBound = '1';
                        }
                    });
                };

                wireConversationRows();
            };

            lockSidebar();
            const observer = new MutationObserver(() => lockSidebar());
            observer.observe(window.parent.document.body, {
                childList: true,
                subtree: true,
                attributes: true,
            });
        </script>
        """,
        height=0,
        width=0,
    )


def _lock_sidebar_open_stable() -> None:
    """稳定版侧栏锁定：仅处理侧栏开关，避免反复观察属性造成页面卡顿。"""
    components.html(
        """
        <script>
            const doc = window.parent.document;
            let scheduled = false;

            const applySidebarLock = () => {
                if (!doc) return;

                const hideSelectors = [
                    '[data-testid="stSidebarContent"] > div:first-child',
                    '[data-testid="stSidebarContent"] > div:first-child *',
                    '[data-testid="stSidebarNav"] button',
                    '[data-testid="collapsedControl"]',
                    '[data-testid="collapsedControl"] button',
                    '[aria-label="Open sidebar"]',
                    '[aria-label="Close sidebar"]',
                    '[data-testid="stSidebarCollapseButton"]',
                    '[data-testid="stSidebarHeaderCollapseButton"]',
                    'button[aria-label*="sidebar"]',
                ];

                hideSelectors.forEach((selector) => {
                    doc.querySelectorAll(selector).forEach((el) => {
                        if (el.dataset.sidebarLockedStable === '1') return;
                        el.style.display = 'none';
                        el.style.visibility = 'hidden';
                        el.style.pointerEvents = 'none';
                        el.dataset.sidebarLockedStable = '1';
                    });
                });

                const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                if (!sidebar) return;

                const sidebarContent = doc.querySelector('[data-testid="stSidebarContent"]');
                if (sidebarContent && sidebarContent.firstElementChild) {
                    const closeControl = sidebarContent.firstElementChild;
                    if (closeControl.dataset.sidebarLockedStable !== '1') {
                        closeControl.style.display = 'none';
                        closeControl.style.visibility = 'hidden';
                        closeControl.style.pointerEvents = 'none';
                        closeControl.style.width = '0';
                        closeControl.style.height = '0';
                        closeControl.style.overflow = 'hidden';
                        closeControl.style.margin = '0';
                        closeControl.style.padding = '0';
                        closeControl.dataset.sidebarLockedStable = '1';
                    }
                }

                if (sidebar.getAttribute('aria-expanded') === 'false') {
                    const openButton = doc.querySelector('[aria-label="Open sidebar"], [data-testid="collapsedControl"] button, [data-testid="collapsedControl"]');
                    if (openButton) {
                        openButton.click();
                    }
                }
            };

            const scheduleSidebarLock = () => {
                if (scheduled) return;
                scheduled = true;
                window.requestAnimationFrame(() => {
                    scheduled = false;
                    applySidebarLock();
                });
            };

            scheduleSidebarLock();
            const observer = new MutationObserver(() => scheduleSidebarLock());
            observer.observe(window.parent.document.body, {
                childList: true,
                subtree: true,
            });
        </script>
        """,
        height=0,
        width=0,
    )


def apply_global_styles() -> None:
    """应用赛博朋克大屏专属 CSS 样式。"""
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
            :root {
                --sidebar-open-width: 304px;
                --surface-0: #06111f;
                --surface-1: rgba(10, 20, 36, 0.88);
                --surface-2: rgba(15, 23, 42, 0.82);
                --surface-3: rgba(30, 41, 59, 0.38);
                --line-soft: rgba(148, 163, 184, 0.16);
                --line-strong: rgba(96, 165, 250, 0.24);
                --text-main: #e5eef9;
                --text-sub: rgba(203, 213, 225, 0.72);
                --brand: #7dd3fc;
            }
            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(37, 99, 235, 0.14), transparent 28%),
                    radial-gradient(circle at top right, rgba(14, 165, 233, 0.08), transparent 24%),
                    linear-gradient(180deg, #07101c 0%, #040912 100%) !important;
                font-family: 'Rajdhani', sans-serif !important;
            }
            header[data-testid="stHeader"] { visibility: hidden; height: 0; }
            .block-container {
                padding-top: 1rem !important;
                padding-bottom: 5.4rem !important;
                max-width: calc(100vw - 2.6rem) !important;
            }
            .cockpit-card {
                background: linear-gradient(180deg, rgba(10, 18, 32, 0.94) 0%, rgba(8, 15, 27, 0.88) 100%) !important;
                backdrop-filter: blur(18px) !important;
                border: 1px solid var(--line-soft) !important;
                border-radius: 18px !important;
                padding: 16px 18px !important;
                margin-bottom: 14px !important;
                position: relative;
                color: var(--text-main) !important;
                box-shadow: 0 14px 34px rgba(2, 6, 23, 0.32) !important;
            }
            .cockpit-card::before,
            .cockpit-card::after { display: none !important; }
            .panel-kicker {
                font-size: 0.68rem !important;
                letter-spacing: 0.18em !important;
                text-transform: uppercase !important;
                color: rgba(125, 211, 252, 0.82) !important;
                margin-bottom: 0.45rem !important;
                font-weight: 700 !important;
            }
            .card-label { font-size: 0.72rem !important; font-weight: 600 !important; color: rgba(148,163,184,0.85) !important; letter-spacing: 1.5px !important; text-transform: uppercase; margin-bottom: 6px !important; display: block !important; font-family: 'Rajdhani', sans-serif !important; white-space: nowrap !important; }
            .card-value { font-size: 1.5rem !important; font-weight: 700 !important; color: #38BDF8 !important; font-family: 'Orbitron', sans-serif !important; line-height: 1.2 !important; white-space: nowrap !important; }
            .card-value-sm { font-size: 1.15rem !important; font-weight: 700 !important; color: #38BDF8 !important; font-family: 'Orbitron', sans-serif !important; line-height: 1.2 !important; }
            .card-value-purple { font-size: 1.1rem !important; font-weight: 700 !important; color: #818CF8 !important; font-family: 'Orbitron', sans-serif !important; }
            .card-sep { font-size: 0.85rem !important; color: #475569 !important; margin: 0 4px !important; }
            .card-sub { font-size: 0.75rem !important; color: rgba(148,163,184,0.55) !important; display: block !important; margin-top: 6px !important; font-family: 'Rajdhani', sans-serif !important; }
            .card-tag { display: inline-block !important; padding: 3px 10px !important; margin: 3px !important; border-radius: 4px !important; background: rgba(56,189,248,0.1) !important; color: #38BDF8 !important; font-size: 0.72rem !important; border: 1px solid rgba(56,189,248,0.25) !important; font-family: 'Rajdhani', sans-serif !important; font-weight: 500 !important; }
            .chain-title { font-size: 0.98rem !important; font-weight: 700 !important; color: #f8fafc !important; letter-spacing: 0.04em !important; display: block !important; margin-bottom: 10px !important; font-family: 'Rajdhani', sans-serif !important; }
            .chain-item { padding: 10px 0 !important; border-bottom: 1px solid rgba(148, 163, 184, 0.08) !important; font-size: 0.84rem !important; font-family: 'Rajdhani', sans-serif !important; color: #CBD5E1 !important; }
            .chain-tool { color: #e5eef9 !important; font-weight: 700 !important; }
            .chain-time { color: rgba(148, 163, 184, 0.66) !important; font-size: 0.7rem !important; }
            .chain-meta { margin-top: 0.25rem !important; color: rgba(203, 213, 225, 0.58) !important; font-size: 0.73rem !important; line-height: 1.45 !important; }
            .chain-status-ok,
            .chain-status-error {
                display: inline-flex !important;
                align-items: center !important;
                justify-content: center !important;
                min-width: 2.2rem !important;
                height: 1.4rem !important;
                border-radius: 999px !important;
                margin-right: 0.45rem !important;
                font-size: 0.68rem !important;
                font-weight: 700 !important;
                letter-spacing: 0.08em !important;
            }
            .chain-status-ok {
                background: rgba(16, 185, 129, 0.14) !important;
                color: #6ee7b7 !important;
                border: 1px solid rgba(16, 185, 129, 0.24) !important;
            }
            .chain-status-error {
                background: rgba(248, 113, 113, 0.12) !important;
                color: #fca5a5 !important;
                border: 1px solid rgba(248, 113, 113, 0.22) !important;
            }
            .chain-empty { padding: 22px 0 !important; text-align: left !important; color: rgba(203, 213, 225, 0.52) !important; font-size: 0.82rem !important; font-family: 'Rajdhani', sans-serif !important; line-height: 1.6 !important; }
            .status-row { font-size: 0.78rem !important; font-family: 'Rajdhani', sans-serif !important; color: #CBD5E1 !important; line-height: 2.2 !important; }
            .status-highlight { color: #38BDF8 !important; font-weight: 600 !important; }
            .status-dim { color: #475569 !important; font-size: 0.72rem !important; }
            .hero-title { text-align: center; font-family: 'Orbitron', sans-serif !important; letter-spacing: 10px; color: #38BDF8 !important; text-shadow: 0 0 25px rgba(56,189,248,0.6); font-size: 1.8rem !important; margin: 2px 0 !important; }
            .sub-title-scan { font-size: 0.85rem !important; letter-spacing: 5px !important; font-family: 'Rajdhani', sans-serif !important; color: rgba(148,163,184,0.6) !important; }
            div[data-testid="stBottom"] {
                position: fixed !important;
                bottom: 35px !important;
                z-index: 9999;
                display: flex !important;
                justify-content: center !important;
                left: var(--sidebar-open-width) !important;
                right: 0 !important;
                width: calc(100vw - var(--sidebar-open-width)) !important;
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                transition: none !important;
            }
            div[data-testid="stBottom"] > div,
            div[data-testid="stBottom"] > div > div {
                width: auto !important;
                max-width: none !important;
                flex: 0 0 auto !important;
                display: contents !important;
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
            }
            [data-testid="stChatInput"] {
                background: transparent !important;
                border: none !important;
                border-radius: 0 !important;
                width: auto !important;
                max-width: none !important;
                font-family: 'Rajdhani', sans-serif !important;
                box-shadow: none !important;
                backdrop-filter: none !important;
                padding: 0 !important;
                margin: 0 auto !important;
                display: contents !important;
            }
            [data-testid="stChatInput"] > div {
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                padding: 0 !important;
                width: auto !important;
                display: contents !important;
            }
            [data-testid="stChatInput"] form {
                background: #2f2f2f !important;
                border: none !important;
                border-radius: 999px !important;
                box-shadow: none !important;
                padding: 0.42rem 0.52rem !important;
                width: min(1320px, calc(100vw - 4.5rem)) !important;
                min-width: min(1320px, calc(100vw - 4.5rem)) !important;
                max-width: min(1320px, calc(100vw - 4.5rem)) !important;
                margin: 0 auto !important;
                display: flex !important;
                align-items: center !important;
                gap: 0.35rem !important;
            }
            [data-testid="stChatInput"] form > div:first-child {
                flex: 1 1 auto !important;
                min-width: 0 !important;
                width: 100% !important;
            }
            [data-testid="stChatInput"] form > div:last-child {
                flex: 0 0 auto !important;
            }
            [data-testid="stChatInput"] textarea,
            [data-testid="stChatInput"] input {
                width: 100% !important;
                font-size: 1rem !important;
                line-height: 1.6 !important;
                padding-left: 0.65rem !important;
                padding-right: 0.65rem !important;
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                color: #f3f4f6 !important;
            }
            [data-testid="stChatInput"] [data-baseweb="textarea"],
            [data-testid="stChatInput"] [data-baseweb="base-input"] {
                width: 100% !important;
                min-width: 0 !important;
                flex: 1 1 auto !important;
                background: transparent !important;
            }
            [data-testid="stChatInput"] textarea::placeholder,
            [data-testid="stChatInput"] input::placeholder {
                color: rgba(255, 255, 255, 0.58) !important;
            }
            [data-testid="stChatInput"] button {
                border-radius: 999px !important;
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
            }
            .workspace-strip {
                display: grid !important;
                grid-template-columns: repeat(5, minmax(0, 1fr)) !important;
                gap: 0.85rem !important;
                margin: 0.15rem 0 1rem !important;
            }
            .workspace-strip-item {
                background: linear-gradient(180deg, rgba(10, 20, 36, 0.9) 0%, rgba(8, 15, 28, 0.82) 100%) !important;
                border: 1px solid var(--line-soft) !important;
                border-radius: 16px !important;
                padding: 0.9rem 1rem !important;
                box-shadow: 0 10px 24px rgba(2, 6, 23, 0.18) !important;
            }
            .workspace-strip-item span {
                display: block !important;
                color: rgba(148, 163, 184, 0.74) !important;
                font-size: 0.68rem !important;
                letter-spacing: 0.14em !important;
                text-transform: uppercase !important;
                margin-bottom: 0.4rem !important;
            }
            .workspace-strip-item strong {
                display: block !important;
                color: #f8fafc !important;
                font-size: 0.92rem !important;
                font-weight: 700 !important;
                line-height: 1.35 !important;
                word-break: break-word !important;
            }
            .analysis-deck-header {
                margin: 1.4rem 0 0.75rem !important;
                padding: 0.2rem 0 0 !important;
            }
            .analysis-deck-title {
                color: #f8fafc !important;
                font-size: 1.32rem !important;
                font-weight: 700 !important;
                line-height: 1.2 !important;
            }
            .analysis-deck-sub {
                color: rgba(203, 213, 225, 0.66) !important;
                font-size: 0.9rem !important;
                line-height: 1.65 !important;
                margin-top: 0.35rem !important;
                max-width: 760px !important;
            }
            .welcome-shell {
                min-height: 54vh !important;
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
                justify-content: center !important;
                text-align: center !important;
                padding: 2.8rem 1rem 0 !important;
            }
            .welcome-title {
                font-size: clamp(2.1rem, 4vw, 3.4rem) !important;
                line-height: 1.02 !important;
                font-weight: 700 !important;
                color: #f8fafc !important;
                letter-spacing: -0.03em !important;
                margin-bottom: 1rem !important;
            }
            .welcome-sub {
                max-width: 760px !important;
                color: rgba(226, 232, 240, 0.68) !important;
                font-size: 1rem !important;
                line-height: 1.9 !important;
            }
            .prompt-shell {
                margin-top: 0.85rem !important;
                margin-bottom: 0.45rem !important;
                max-width: 840px !important;
                margin-left: auto !important;
                margin-right: auto !important;
                width: 100% !important;
            }
            .prompt-shell-empty {
                margin-top: -0.65rem !important;
            }
            [data-testid="stForm"]:has(input[aria-label="主输入框"]) {
                width: 100% !important;
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                padding: 0 !important;
            }
            [data-testid="stForm"]:has(input[aria-label="主输入框"]) form {
                width: 100% !important;
            }
            [data-testid="stForm"]:has(input[aria-label="主输入框"]) [data-testid="stHorizontalBlock"] {
                align-items: center !important;
                gap: 0.65rem !important;
                background: linear-gradient(180deg, rgba(15, 23, 42, 0.96) 0%, rgba(11, 18, 32, 0.9) 100%) !important;
                border: 1px solid rgba(148, 163, 184, 0.14) !important;
                border-radius: 999px !important;
                padding: 0.34rem 0.48rem !important;
                box-shadow: 0 12px 30px rgba(2, 6, 23, 0.22) !important;
            }
            [data-testid="stForm"]:has(input[aria-label="主输入框"]) .stTextInput {
                flex: 1 1 auto !important;
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
            }
            [data-testid="stForm"]:has(input[aria-label="主输入框"]) .stTextInput > div,
            [data-testid="stForm"]:has(input[aria-label="主输入框"]) .stTextInput > div > div {
                width: 100% !important;
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                border-radius: 0 !important;
                padding: 0 !important;
            }
            [data-testid="stForm"]:has(input[aria-label="主输入框"]) .stTextInput [data-baseweb="base-input"] {
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                border-radius: 0 !important;
            }
            input[aria-label="主输入框"] {
                height: 64px !important;
                border-radius: 999px !important;
                border: none !important;
                outline: none !important;
                background: transparent !important;
                color: #f8fafc !important;
                padding: 0 1.4rem !important;
                box-shadow: none !important;
                font-size: 1.02rem !important;
            }
            input[aria-label="主输入框"]::placeholder {
                color: rgba(203, 213, 225, 0.56) !important;
            }
            [data-testid="stForm"]:has(input[aria-label="主输入框"]) [data-testid="stFormSubmitButton"] button {
                height: 64px !important;
                min-width: 64px !important;
                border-radius: 999px !important;
                border: none !important;
                background: transparent !important;
                color: #f8fafc !important;
                box-shadow: none !important;
                font-size: 1.3rem !important;
            }
            [data-testid="stForm"]:has(input[aria-label="主输入框"]) [data-testid="stFormSubmitButton"] button:hover {
                background: rgba(255,255,255,0.08) !important;
            }
            .stApp h1,.stApp h2,.stApp h3,.stApp h4 { color: #E2E8F0 !important; }
            .stApp p,.stApp span,.stApp li,.stApp label,.stApp div { color: #E2E8F0 !important; }
            div[data-testid="stChatMessage"] {
                background: linear-gradient(180deg, rgba(10, 20, 36, 0.97) 0%, rgba(7, 14, 27, 0.95) 100%) !important;
                border: 1px solid rgba(148, 163, 184, 0.12) !important;
                border-radius: 18px !important;
                padding: 0.45rem 0.5rem !important;
                box-shadow: 0 10px 24px rgba(2, 6, 23, 0.14) !important;
                margin-bottom: 0.75rem !important;
                overflow: visible !important;
            }
            /* 回复区中文排版：贴近专业报告的阅读感，避免过度科幻字体影响可读性 */
            .stChatMessage [data-testid="stMarkdownContainer"] {
                font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans SC", "Helvetica Neue", Arial, sans-serif !important;
                color: #EAF2FF !important;
                letter-spacing: 0.01em !important;
                padding-bottom: 0.18rem !important;
            }
            .stChatMessage [data-testid="stMarkdownContainer"] p {
                font-size: 1.1rem !important;
                line-height: 1.9 !important;
                margin: 0.42rem 0 0.5rem !important;
                color: #EAF2FF !important;
                font-weight: 500 !important;
            }
            .stChatMessage [data-testid="stMarkdownContainer"] li {
                font-size: 1.08rem !important;
                line-height: 1.88 !important;
                margin: 0.32rem 0 !important;
                color: #EAF2FF !important;
                font-weight: 500 !important;
            }
            .stChatMessage [data-testid="stMarkdownContainer"] ul,
            .stChatMessage [data-testid="stMarkdownContainer"] ol {
                margin-top: 0.32rem !important;
                margin-bottom: 0.58rem !important;
                padding-left: 1.42rem !important;
            }
            .stChatMessage [data-testid="stMarkdownContainer"] strong {
                font-weight: 760 !important;
                color: #F8FAFC !important;
            }
            .stChatMessage [data-testid="stMarkdownContainer"] h1 {
                font-size: 1.46rem !important;
                line-height: 1.5 !important;
                font-weight: 780 !important;
                margin: 0.35rem 0 0.52rem !important;
                color: #F8FAFC !important;
                letter-spacing: 0 !important;
            }
            .stChatMessage [data-testid="stMarkdownContainer"] h2 {
                font-size: 1.3rem !important;
                line-height: 1.52 !important;
                font-weight: 760 !important;
                margin: 0.45rem 0 0.5rem !important;
                color: #F8FAFC !important;
            }
            .stChatMessage [data-testid="stMarkdownContainer"] h3 {
                font-size: 1.18rem !important;
                line-height: 1.56 !important;
                font-weight: 730 !important;
                margin: 0.36rem 0 0.44rem !important;
                color: #F8FAFC !important;
            }
            .stChatMessage [data-testid="stMarkdownContainer"] hr {
                border: 0 !important;
                border-top: 1px solid rgba(148, 163, 184, 0.28) !important;
                margin: 1rem 0 0.9rem !important;
            }
            .stTabs [data-baseweb="tab-list"] {
                background: rgba(8, 15, 27, 0.72) !important;
                border: 1px solid rgba(148, 163, 184, 0.14) !important;
                border-radius: 16px 16px 0 0 !important;
                gap: 0.25rem !important;
                padding: 0.35rem 0.35rem 0 !important;
            }
            .stTabs [data-baseweb="tab"] {
                font-size: 0.95rem !important;
                font-weight: 700 !important;
                color: rgba(148,163,184,0.76) !important;
                padding: 0.95rem 1.25rem !important;
                font-family: 'Rajdhani', sans-serif !important;
                letter-spacing: 0.03em !important;
                border-bottom: 2px solid transparent !important;
                border-radius: 12px 12px 0 0 !important;
            }
            .stTabs [aria-selected="true"] {
                color: #f8fafc !important;
                border-bottom: 2px solid #7dd3fc !important;
                background: linear-gradient(180deg, rgba(14, 165, 233, 0.08) 0%, rgba(15, 23, 42, 0.2) 100%) !important;
            }
            .stTabs [data-baseweb="tab-panel"] {
                background: linear-gradient(180deg, rgba(10, 20, 36, 0.8) 0%, rgba(7, 14, 27, 0.74) 100%) !important;
                border: 1px solid rgba(148, 163, 184, 0.12) !important;
                border-top: none !important;
                border-radius: 0 0 18px 18px !important;
                padding: 18px !important;
            }
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, rgba(6, 12, 24, 0.98) 0%, rgba(4, 9, 18, 0.98) 100%) !important;
                border-right: 1px solid rgba(148, 163, 184, 0.14) !important;
                width: var(--sidebar-open-width) !important;
                min-width: var(--sidebar-open-width) !important;
                max-width: var(--sidebar-open-width) !important;
                flex: 0 0 var(--sidebar-open-width) !important;
                cursor: default !important;
                transition: none !important;
            }
            [data-testid="stSidebar"] > div:first-child {
                width: var(--sidebar-open-width) !important;
                min-width: var(--sidebar-open-width) !important;
                max-width: var(--sidebar-open-width) !important;
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                height: 100vh !important;
                overflow-y: auto !important;
                transition: none !important;
                will-change: auto !important;
            }
            [data-testid="stSidebarResizer"],
            [data-testid="stSidebarResizeHandle"],
            [aria-label="Resize sidebar"],
            [data-testid="stSidebarNav"] + div {
                cursor: default !important;
                pointer-events: none !important;
            }
            [data-testid="stSidebar"][aria-expanded="true"],
            [data-testid="stSidebar"][aria-expanded="false"] {
                width: var(--sidebar-open-width) !important;
                min-width: var(--sidebar-open-width) !important;
                max-width: var(--sidebar-open-width) !important;
                flex: 0 0 var(--sidebar-open-width) !important;
            }
            [data-testid="stSidebar"][aria-expanded="true"] > div:first-child,
            [data-testid="stSidebar"][aria-expanded="false"] > div:first-child {
                margin-left: 0 !important;
                transform: none !important;
            }
            [data-testid="collapsedControl"] {
                display: none !important;
            }
            [data-testid="stSidebarContent"] > div:first-child,
            [data-testid="stSidebarContent"] > div:first-child *,
            [data-testid="stSidebarNav"] button,
            [aria-label="Open sidebar"],
            [aria-label="Close sidebar"],
            [data-testid="stSidebarCollapseButton"],
            [data-testid="stSidebarHeaderCollapseButton"] {
                display: none !important;
                visibility: hidden !important;
                pointer-events: none !important;
                opacity: 0 !important;
                width: 0 !important;
                height: 0 !important;
                min-width: 0 !important;
                min-height: 0 !important;
                max-width: 0 !important;
                max-height: 0 !important;
                overflow: hidden !important;
                margin: 0 !important;
                padding: 0 !important;
                border: none !important;
            }
            [data-testid="stSidebarUserContent"] {
                padding-top: 0.55rem !important;
            }
            [data-testid="stSidebar"] .sidebar-brand {
                display: flex !important;
                align-items: center !important;
                gap: 12px !important;
                margin-top: 0.15rem !important;
                margin-bottom: 16px !important;
                padding: 6px 2px 8px !important;
            }
            [data-testid="stSidebar"] .sidebar-logo {
                width: 52px !important;
                height: 52px !important;
                border-radius: 16px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                position: relative !important;
                overflow: hidden !important;
                background:
                    radial-gradient(circle at 35% 35%, rgba(255,255,255,0.92) 0%, rgba(125,211,252,0.56) 36%, rgba(37,99,235,0.92) 100%) !important;
                color: #eff6ff !important;
                box-shadow: 0 12px 30px rgba(37, 99, 235, 0.2) !important;
            }
            [data-testid="stSidebar"] .sidebar-logo-ring {
                position: absolute !important;
                inset: 7px !important;
                border: 1px solid rgba(255,255,255,0.35) !important;
                border-radius: 14px !important;
                box-shadow: inset 0 0 14px rgba(255,255,255,0.16) !important;
            }
            [data-testid="stSidebar"] .sidebar-logo-core {
                position: relative !important;
                z-index: 1 !important;
                font-family: 'Orbitron', 'Microsoft YaHei', sans-serif !important;
                font-size: 1.15rem !important;
                font-weight: 700 !important;
                color: #f8fafc !important;
                text-shadow: 0 0 18px rgba(255,255,255,0.35) !important;
            }
            [data-testid="stSidebar"] .sidebar-brand-copy {
                min-width: 0 !important;
            }
            [data-testid="stSidebar"] .sidebar-brand-title {
                color: #f8fafc !important;
                font-size: 1.15rem !important;
                font-weight: 700 !important;
                letter-spacing: 1px !important;
                line-height: 1.2 !important;
            }
            [data-testid="stSidebar"] .sidebar-brand-sub {
                color: rgba(148,163,184,0.78) !important;
                font-size: 0.75rem !important;
                margin-top: 4px !important;
                line-height: 1.45 !important;
            }
            [data-testid="stSidebar"] .sidebar-status {
                background: linear-gradient(180deg, rgba(10, 20, 36, 0.78) 0%, rgba(8, 15, 27, 0.72) 100%) !important;
                border: 1px solid rgba(148, 163, 184, 0.12) !important;
                border-radius: 16px !important;
                padding: 12px 13px !important;
                margin-bottom: 14px !important;
            }
            [data-testid="stSidebar"] .sidebar-status-item {
                font-size: 0.77rem !important;
                color: #dbeafe !important;
                line-height: 1.7 !important;
            }
            [data-testid="stSidebar"] .sidebar-metrics {
                display: grid !important;
                grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
                gap: 8px !important;
                margin-bottom: 14px !important;
            }
            [data-testid="stSidebar"] .sidebar-metric {
                background: rgba(255, 255, 255, 0.035) !important;
                border: 1px solid rgba(148, 163, 184, 0.1) !important;
                border-radius: 14px !important;
                padding: 11px 8px !important;
                text-align: center !important;
            }
            [data-testid="stSidebar"] .sidebar-metric span {
                display: block !important;
                color: rgba(148,163,184,0.72) !important;
                font-size: 0.67rem !important;
                margin-bottom: 4px !important;
            }
            [data-testid="stSidebar"] .sidebar-metric strong {
                color: #f8fafc !important;
                font-size: 0.92rem !important;
                font-family: 'Orbitron', sans-serif !important;
            }
            [data-testid="stSidebar"] .sidebar-section-label {
                margin-top: 18px !important;
                margin-bottom: 8px !important;
                font-size: 0.75rem !important;
                letter-spacing: 1.4px !important;
                text-transform: uppercase !important;
                color: rgba(148,163,184,0.85) !important;
                font-family: 'Rajdhani', sans-serif !important;
                font-weight: 700 !important;
            }
            [data-testid="stSidebar"] .sidebar-section-hint {
                font-size: 0.78rem !important;
                color: rgba(148,163,184,0.6) !important;
                margin-bottom: 10px !important;
                line-height: 1.5 !important;
            }
            [data-testid="stSidebar"] .stButton > button {
                border-radius: 12px !important;
                min-height: 2.4rem !important;
                justify-content: flex-start !important;
                text-align: left !important;
                font-family: 'Rajdhani', sans-serif !important;
                font-weight: 600 !important;
            }
            [data-testid="stSidebar"] .stButton > button[kind="secondary"] {
                background: transparent !important;
                border: none !important;
                color: #E5E7EB !important;
                box-shadow: none !important;
                padding-left: 0.65rem !important;
                padding-right: 0.65rem !important;
            }
            [data-testid="stSidebar"] .stButton > button[kind="primary"] {
                background: linear-gradient(180deg, rgba(14, 165, 233, 0.2) 0%, rgba(30, 41, 59, 0.38) 100%) !important;
                border: 1px solid rgba(125, 211, 252, 0.12) !important;
                color: #F8FAFC !important;
                box-shadow: none !important;
                padding-left: 0.65rem !important;
                padding-right: 0.65rem !important;
            }
            [data-testid="stSidebar"] .stTextInput input {
                border-radius: 10px !important;
                border: 1px solid rgba(56, 189, 248, 0.35) !important;
                background: rgba(15, 23, 42, 0.7) !important;
                color: #E2E8F0 !important;
            }
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-marker),
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-actions-marker) {
                display: none !important;
                margin: 0 !important;
                padding: 0 !important;
            }
            [data-testid="stSidebar"] .history-row-shell {
                margin: 0.28rem 0 !important;
                padding: 0.18rem 0 !important;
                border-radius: 18px !important;
                transition: background 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease !important;
            }
            [data-testid="stSidebar"] .history-row-shell:hover {
                background: rgba(255, 255, 255, 0.03) !important;
            }
            [data-testid="stSidebar"] .history-row-shell.history-row-shell-active {
                background: linear-gradient(180deg, rgba(14, 165, 233, 0.08) 0%, rgba(255, 255, 255, 0.04) 100%) !important;
                box-shadow: inset 0 0 0 1px rgba(125, 211, 252, 0.1) !important;
            }
            [data-testid="stSidebar"] .history-row-shell > div[data-testid="stHorizontalBlock"] {
                align-items: center !important;
                gap: 0.35rem !important;
            }
            [data-testid="stSidebar"] .history-row-shell > div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                display: flex !important;
                align-items: stretch !important;
            }
            [data-testid="stSidebar"] .history-row-shell .history-row-main-col .stButton {
                width: 100% !important;
            }
            [data-testid="stSidebar"] .history-row-shell .history-row-main-col .stButton > button {
                width: 100% !important;
                min-height: 3.25rem !important;
                border-radius: 18px !important;
                padding: 0.65rem 0.9rem !important;
                line-height: 1.4 !important;
                white-space: normal !important;
            }
            [data-testid="stSidebar"] .history-row-shell .history-row-menu-col {
                justify-content: center !important;
            }
            [data-testid="stSidebar"] .history-row-shell .history-row-menu-button > button {
                min-height: 2.4rem !important;
                width: 2.4rem !important;
                min-width: 2.4rem !important;
                padding: 0 !important;
                border-radius: 12px !important;
                justify-content: center !important;
                background: rgba(255, 255, 255, 0.06) !important;
                border: 1px solid rgba(148, 163, 184, 0.12) !important;
                color: rgba(226, 232, 240, 0.9) !important;
                opacity: 0 !important;
                visibility: hidden !important;
                pointer-events: none !important;
                transform: translateX(4px) !important;
                transition: opacity 0.16s ease, transform 0.16s ease, background 0.16s ease !important;
            }
            [data-testid="stSidebar"] .history-row-shell:hover .history-row-menu-button > button {
                opacity: 1 !important;
                visibility: visible !important;
                pointer-events: auto !important;
                transform: translateX(0) !important;
            }
            [data-testid="stSidebar"] .history-row-shell .history-row-menu-button > button:hover {
                background: rgba(255, 255, 255, 0.12) !important;
            }
            [data-testid="stSidebar"] .history-actions-shell {
                margin: -0.05rem 0 0.45rem 0 !important;
                padding: 0.42rem !important;
                border-radius: 14px !important;
                background: rgba(8, 15, 27, 0.9) !important;
                border: 1px solid rgba(148, 163, 184, 0.12) !important;
                box-shadow: 0 10px 24px rgba(2, 6, 23, 0.16) !important;
            }
            [data-testid="stSidebar"] .history-actions-shell .stButton > button {
                min-height: 2rem !important;
                border-radius: 10px !important;
                justify-content: center !important;
                font-size: 0.88rem !important;
                padding-left: 0.55rem !important;
                padding-right: 0.55rem !important;
            }
            [data-testid="stSidebar"] .history-actions-shell .stTextInput input {
                min-height: 2.2rem !important;
                border-radius: 10px !important;
                font-size: 0.9rem !important;
            }
            [data-testid="stSidebar"] .history-actions-shell .stCaptionContainer,
            [data-testid="stSidebar"] .history-actions-shell [data-testid="stCaptionContainer"] {
                margin-bottom: 0.2rem !important;
            }
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-marker) + div[data-testid="stVerticalBlock"] {
                margin: 0.28rem 0 !important;
                padding: 0.18rem 0 !important;
                border-radius: 18px !important;
                transition: background 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease !important;
            }
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-marker) + div[data-testid="stVerticalBlock"]:hover {
                background: rgba(255, 255, 255, 0.03) !important;
            }
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-active-marker) + div[data-testid="stVerticalBlock"] {
                background: linear-gradient(180deg, rgba(14, 165, 233, 0.08) 0%, rgba(255, 255, 255, 0.04) 100%) !important;
                box-shadow: inset 0 0 0 1px rgba(125, 211, 252, 0.1) !important;
            }
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-marker) + div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] {
                align-items: center !important;
                gap: 0.35rem !important;
            }
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-marker) + div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                display: flex !important;
                align-items: stretch !important;
            }
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-marker) + div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child .stButton {
                width: 100% !important;
            }
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-marker) + div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child .stButton > button {
                width: 100% !important;
                min-height: 3.25rem !important;
                border-radius: 18px !important;
                padding: 0.65rem 0.9rem !important;
                line-height: 1.4 !important;
                white-space: normal !important;
            }
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-marker) + div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child {
                justify-content: center !important;
            }
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-marker) + div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child .stButton > button {
                min-height: 2.4rem !important;
                width: 2.4rem !important;
                min-width: 2.4rem !important;
                padding: 0 !important;
                border-radius: 12px !important;
                justify-content: center !important;
                background: rgba(255, 255, 255, 0.06) !important;
                border: 1px solid rgba(148, 163, 184, 0.12) !important;
                color: rgba(226, 232, 240, 0.9) !important;
                opacity: 0 !important;
                pointer-events: none !important;
                transform: translateX(4px) !important;
                transition: opacity 0.16s ease, transform 0.16s ease, background 0.16s ease !important;
            }
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-marker) + div[data-testid="stVerticalBlock"]:hover > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child .stButton > button,
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-menu-open-marker) + div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child .stButton > button {
                opacity: 1 !important;
                pointer-events: auto !important;
                transform: translateX(0) !important;
            }
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-marker) + div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child .stButton > button:hover {
                background: rgba(255, 255, 255, 0.12) !important;
            }
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-actions-marker) + div[data-testid="stVerticalBlock"] {
                margin: -0.05rem 0 0.45rem 0 !important;
                padding: 0.42rem !important;
                border-radius: 14px !important;
                background: rgba(8, 15, 27, 0.9) !important;
                border: 1px solid rgba(148, 163, 184, 0.12) !important;
                box-shadow: 0 10px 24px rgba(2, 6, 23, 0.16) !important;
            }
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-actions-marker) + div[data-testid="stVerticalBlock"] .stButton > button {
                min-height: 2rem !important;
                border-radius: 10px !important;
                justify-content: center !important;
                font-size: 0.88rem !important;
                padding-left: 0.55rem !important;
                padding-right: 0.55rem !important;
            }
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-actions-marker) + div[data-testid="stVerticalBlock"] .stTextInput input {
                min-height: 2.2rem !important;
                border-radius: 10px !important;
                font-size: 0.9rem !important;
            }
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-actions-marker) + div[data-testid="stVerticalBlock"] .stCaptionContainer,
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-actions-marker) + div[data-testid="stVerticalBlock"] [data-testid="stCaptionContainer"] {
                margin-bottom: 0.2rem !important;
            }
            @media (max-width: 1280px) {
                .workspace-strip {
                    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    _lock_sidebar_open_stable()
