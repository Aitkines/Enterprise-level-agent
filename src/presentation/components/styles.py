import streamlit as st
import streamlit.components.v1 as components

def _lock_sidebar_open_stable() -> None:
    """强制侧栏保持展开，并隐藏所有开关按钮。"""
    components.html(
        """
        <script>
            const lockSidebar = () => {
                const doc = window.parent.document;
                if (!doc) return;
                
                // 1. 仅移除特定的、妨碍锁定的侧栏控件（不要移除 Content > div:first-child）
                const hideSelectors = [
                    '[data-testid="stSidebarNav"]',
                    '[data-testid="collapsedControl"]',
                    '[data-testid="stSidebarResizer"]',
                    '[data-testid="stSidebarResizeHandle"]',
                    '[data-testid="stSidebarCollapseButton"]',
                    '[aria-label="Open sidebar"]',
                    '[aria-label="Close sidebar"]',
                    'button[aria-label*="sidebar"]'
                ];
                hideSelectors.forEach(sel => {
                    doc.querySelectorAll(sel).forEach(el => {
                        el.style.display = 'none';
                        el.style.visibility = 'hidden';
                        el.style.pointerEvents = 'none';
                    });
                });

                // 2. 强制侧边栏宽度为 280px，并确保展开状态
                const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                if (sidebar) {
                    sidebar.style.cssText += `
                        width: 280px !important;
                        min-width: 280px !important;
                        max-width: 280px !important;
                        flex-basis: 280px !important;
                        flex-shrink: 0 !important;
                        transition: none !important;
                    `;
                    if (sidebar.getAttribute('aria-expanded') === 'false') {
                         sidebar.setAttribute('aria-expanded', 'true');
                    }
                    
                    const sidebarContent = sidebar.querySelector('[data-testid="stSidebarContent"]');
                    if (sidebarContent) {
                        sidebarContent.style.cssText += `
                            width: 280px !important;
                            min-width: 280px !important;
                            max-width: 280px !important;
                            background: #060b13 !important;
                        `;
                    }
                }
            };
            
            // 启动持久化锁定循环
            setInterval(lockSidebar, 100);
            lockSidebar();
        </script>

        <style>
            /* 修正侧边栏全局变量 */
            :root {{
                --sidebar-open-width: 280px !important;
            }}
            /* 基础布局锁定 */
            [data-testid="stSidebar"],
            [data-testid="stSidebar"] > div:first-child {{
                width: 280px !important;
                min-width: 280px !important;
                max-width: 280px !important;
                flex: 0 0 280px !important;
            }}
            const applyCyberpunkStyles = () => {
                const doc = window.parent.document;
                const chatInput = doc.querySelector('[data-testid="stChatInput"]');
                if (chatInput) {
                    // 外层绝对定位与定位
                    chatInput.style.cssText += `
                        background: linear-gradient(180deg, rgba(15, 23, 42, 0.98) 0%, rgba(8, 14, 28, 0.96) 100%) !important;
                        border: 1px solid rgba(0, 229, 255, 0.5) !important;
                        border-radius: 40px !important;
                        box-shadow: 0 0 30px rgba(0, 229, 255, 0.2), 0 15px 50px rgba(0, 0, 0, 0.6) !important;
                        width: 860px !important;
                        max-width: 90% !important;
                        margin: 0 auto !important;
                        position: fixed !important;
                        bottom: 0.8rem !important;
                        left: 50.5% !important;
                        transform: translateX(-50%) !important;
                        z-index: 99999 !important;
                        padding: 4px 12px !important;
                    `;

                    // 深度覆盖内部所有 div 的背景
                    chatInput.querySelectorAll('div').forEach(d => {
                        d.style.background = 'transparent';
                        d.style.backgroundColor = 'transparent';
                        d.style.border = 'none';
                        d.style.boxShadow = 'none';
                    });

                    // 文本域漂白
                    const textarea = chatInput.querySelector('textarea');
                    if (textarea) {
                        textarea.style.background = 'transparent';
                        textarea.style.backgroundColor = 'transparent';
                        textarea.style.color = '#FFFFFF';
                        textarea.style.border = 'none';
                    }

                    // 发送按钮
                    const button = chatInput.querySelector('button');
                    if (button) {
                        button.style.background = 'linear-gradient(135deg, #00C6FF 0%, #0072FF 100%)';
                        button.style.borderRadius = '50%';
                        button.style.boxShadow = '0 4px 15px rgba(0, 198, 255, 0.4)';
                    }
                }

                // 彻底销毁底部白条背景
                const stBottom = doc.querySelector('[data-testid="stBottom"]');
                if (stBottom) {
                    stBottom.style.background = 'transparent';
                    stBottom.style.backgroundColor = 'transparent';
                    stBottom.style.boxShadow = 'none';
                    const inner = stBottom.querySelector('div');
                    if(inner) inner.style.background = 'transparent';
                }
            };

            // 每 200ms 强制巡检一次，对抗 Streamlit React 的状态刷新
            setInterval(applyCyberpunkStyles, 200);
            
            const observer = new MutationObserver(() => {
                lockSidebar();
                applyCyberpunkStyles();
            });
            observer.observe(doc.body, { childList: true, subtree: true });
        </script>
        """,
        height=0,
        width=0,
    )

def apply_global_styles(is_new_chat: bool = False) -> None:
    """应用专属 CSS 样式并处理布局。"""
    
    st.markdown(
        f"""
        <style>
            /* 1. 核心胶囊外盖 - 强制置于最底部并覆盖原生白背景 */
            [data-testid="stChatInput"] {{
                background: linear-gradient(180deg, rgba(15, 23, 42, 0.98) 0%, rgba(8, 14, 28, 0.96) 100%) !important;
                border: 1px solid rgba(0, 229, 255, 0.4) !important;
                border-radius: 40px !important;
                box-shadow: 0 0 30px rgba(0, 229, 255, 0.1), 0 15px 50px rgba(0, 0, 0, 0.6) !important;
                padding: 4px 12px !important;
                width: 860px !important;
                max-width: 90% !important;
                margin: 0 auto !important;
                position: fixed !important;
                bottom: 0.5rem !important;
                left: 50.5% !important;
                transform: translateX(-50%) !important;
                z-index: 99999 !important;
            }}
            
            /* 关键暴力破解：强制所有内部 wrapper 透明，暴露出下方的渐变壳子 */
            [data-testid="stChatInput"] > div,
            [data-testid="stChatInput"] > div > div,
            [data-testid="stChatInput"] [data-baseweb="base-input"],
            [data-testid="stChatInput"] textarea {{
                background: transparent !important;
                background-color: transparent !important;
                border: none !important;
                box-shadow: none !important;
                color: #FFFFFF !important;
                line-height: 1.6 !important;
            }}
            
            /* 输入框占位符 */
            [data-testid="stChatInput"] textarea::placeholder {{
                color: rgba(255, 255, 255, 0.4) !important;
            }}

            /* 发送按钮样式 */
            [data-testid="stChatInput"] button {{
                background: linear-gradient(135deg, #00C6FF 0%, #0072FF 100%) !important;
                border-radius: 50% !important;
                padding: 6px !important;
                margin-right: 2px !important;
                width: 40px !important;
                height: 40px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                box-shadow: 0 4px 15px rgba(0, 114, 255, 0.3) !important;
                transition: all 0.2s !important;
            }}
            
            [data-testid="stChatInput"] button:hover {{ transform: scale(1.1) !important; }}

            [data-testid="stBottom"], [data-testid="stBottomBlockContainer"] {{
                background: transparent !important;
                padding-bottom: 0 !important;
                margin-bottom: 0 !important;
            }}

            @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
            :root {{
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
            }}
            .stApp {{
                background:
                    radial-gradient(circle at top left, rgba(37, 99, 235, 0.14), transparent 28%),
                    radial-gradient(circle at top right, rgba(14, 165, 233, 0.08), transparent 24%),
                    linear-gradient(180deg, #07101c 0%, #040912 100%) !important;
                font-family: 'Rajdhani', sans-serif !important;
            }}
            header[data-testid="stHeader"] {{ visibility: hidden; height: 0; }}
            .block-container {{
                padding-top: 1rem !important;
                padding-bottom: 5.4rem !important;
                max-width: calc(100vw - 2.6rem) !important;
            }}
            .cockpit-card {{
                background: linear-gradient(180deg, rgba(10, 18, 32, 0.94) 0%, rgba(8, 15, 27, 0.88) 100%) !important;
                backdrop-filter: blur(18px) !important;
                border: 1px solid var(--line-soft) !important;
                border-radius: 22px !important;
                padding: 24px !important;
                margin-bottom: 24px !important;
                position: relative;
                color: var(--text-main) !important;
                box-shadow: 0 24px 48px rgba(2, 6, 23, 0.45) !important;
                overflow: hidden;
            }}
            .chart-tag-top {{
                position: absolute;
                top: 20px;
                right: 24px;
                padding: 4px 12px;
                background: rgba(0, 229, 255, 0.12);
                border: 1px solid rgba(0, 229, 255, 0.3);
                border-radius: 6px;
                color: #00E5FF;
                font-size: 0.65rem;
                font-family: 'Orbitron', sans-serif;
                letter-spacing: 1px;
                text-transform: uppercase;
                font-weight: 700;
            }}
            .analyst-verdict-box {{
                margin-top: 20px;
                background: rgba(15, 23, 42, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
                padding: 16px;
                position: relative;
                transition: all 0.3s ease;
            }}
            .analyst-verdict-box:hover {{
                background: rgba(15, 23, 42, 0.7);
                border-color: rgba(56, 189, 248, 0.3);
            }}
            .verdict-label {{
                font-size: 0.68rem;
                font-weight: 700;
                color: #7DD3FC;
                text-transform: uppercase;
                letter-spacing: 1.5px;
                margin-bottom: 8px;
                font-family: 'Rajdhani', sans-serif;
            }}
            .verdict-content {{
                font-size: 0.88rem;
                line-height: 1.65;
                color: #E2E8F0;
                font-family: 'Rajdhani', sans-serif;
                font-weight: 400;
            }}
            .cockpit-card::before,
            .cockpit-card::after {{ display: none !important; }}
            .panel-kicker {{
                font-size: 0.68rem !important;
                letter-spacing: 0.18em !important;
                text-transform: uppercase !important;
                color: rgba(125, 211, 252, 0.82) !important;
                margin-bottom: 0.45rem !important;
                font-weight: 700 !important;
            }}
            .card-label {{ font-size: 0.72rem !important; font-weight: 600 !important; color: rgba(148,163,184,0.85) !important; letter-spacing: 1.5px !important; text-transform: uppercase; margin-bottom: 6px !important; display: block !important; font-family: 'Rajdhani', sans-serif !important; white-space: nowrap !important; }}
            .card-value {{ font-size: 1.5rem !important; font-weight: 700 !important; color: #38BDF8 !important; font-family: 'Orbitron', sans-serif !important; line-height: 1.2 !important; white-space: nowrap !important; }}
            .card-value-sm {{ font-size: 1.15rem !important; font-weight: 700 !important; color: #38BDF8 !important; font-family: 'Orbitron', sans-serif !important; line-height: 1.2 !important; }}
            .card-value-purple {{ font-size: 1.1rem !important; font-weight: 700 !important; color: #818CF8 !important; font-family: 'Orbitron', sans-serif !important; }}
            .card-sep {{ font-size: 0.85rem !important; color: #475569 !important; margin: 0 4px !important; }}
            .card-sub {{ font-size: 0.75rem !important; color: rgba(148,163,184,0.55) !important; display: block !important; margin-top: 6px !important; font-family: 'Rajdhani', sans-serif !important; }}
            .ai-insight-box {{
                background: linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(30, 41, 59, 0.7) 100%) !important;
                border-left: 4px solid #38BDF8 !important;
                border-top: 1px solid rgba(56, 189, 248, 0.15) !important;
                border-right: 1px solid rgba(56, 189, 248, 0.1) !important;
                border-bottom: 1px solid rgba(56, 189, 248, 0.1) !important;
                border-radius: 12px !important;
                padding: 1.5rem !important;
                margin: 1.5rem 0 !important;
                color: #E2E8F0 !important;
                line-height: 1.7 !important;
                font-size: 0.94rem !important;
                backdrop-filter: blur(12px) !important;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4) !important;
            }}
            .ai-insight-box strong {{
                color: #7DD3FC !important;
                font-weight: 700 !important;
            }}
            
            .card-tag {{ display: inline-block !important; padding: 3px 10px !important; margin: 3px !important; border-radius: 4px !important; background: rgba(56,189,248,0.1) !important; color: #38BDF8 !important; font-size: 0.72rem !important; border: 1px solid rgba(56,189,248,0.25) !important; font-family: 'Rajdhani', sans-serif !important; font-weight: 500 !important; }}
            .chain-title {{ font-size: 0.98rem !important; font-weight: 700 !important; color: #f8fafc !important; letter-spacing: 0.04em !important; display: block !important; margin-bottom: 10px !important; font-family: 'Rajdhani', sans-serif !important; }}
            .chain-item {{ padding: 10px 0 !important; border-bottom: 1px solid rgba(148, 163, 184, 0.08) !important; font-size: 0.84rem !important; font-family: 'Rajdhani', sans-serif !important; color: #CBD5E1 !important; }}
            .chain-tool {{ color: #e5eef9 !important; font-weight: 700 !important; }}
            .chain-time {{ color: rgba(148, 163, 184, 0.66) !important; font-size: 0.7rem !important; }}
            .chain-meta {{ margin-top: 0.25rem !important; color: rgba(203, 213, 225, 0.58) !important; font-size: 0.73rem !important; line-height: 1.45 !important; }}
            .chain-status-ok,
            .chain-status-error {{
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
            }}
            .chain-status-ok {{
                background: rgba(16, 185, 129, 0.14) !important;
                color: #6ee7b7 !important;
                border: 1px solid rgba(16, 185, 129, 0.24) !important;
            }}
            .chain-status-error {{
                background: rgba(248, 113, 113, 0.12) !important;
                color: #fca5a5 !important;
                border: 1px solid rgba(248, 113, 113, 0.22) !important;
            }}
            .chain-empty {{ padding: 22px 0 !important; text-align: left !important; color: rgba(203, 213, 225, 0.52) !important; font-size: 0.82rem !important; font-family: 'Rajdhani', sans-serif !important; line-height: 1.6 !important; }}
            .status-row {{ font-size: 0.78rem !important; font-family: 'Rajdhani', sans-serif !important; color: #CBD5E1 !important; line-height: 2.2 !important; }}
            .status-highlight {{ color: #38BDF8 !important; font-weight: 600 !important; }}
            .status-dim {{ color: #475569 !important; font-size: 0.72rem !important; }}
            .hero-title {{ text-align: center; font-family: 'Orbitron', sans-serif !important; letter-spacing: 10px; color: #38BDF8 !important; text-shadow: 0 0 25px rgba(56,189,248,0.6); font-size: 1.8rem !important; margin: 2px 0 !important; }}
            .sub-title-scan {{ font-size: 0.85rem !important; letter-spacing: 5px !important; font-family: 'Rajdhani', sans-serif !important; color: rgba(148,163,184,0.6) !important; }}
            div[data-testid="stBottom"] {{
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
            }}
            div[data-testid="stBottom"] > div,
            div[data-testid="stBottom"] > div > div {{
                width: auto !important;
                max-width: none !important;
                flex: 0 0 auto !important;
                display: contents !important;
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
            }}
            [data-testid="stChatInput"] {{
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
            }}
            [data-testid="stChatInput"] > div {{
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                padding: 0 !important;
                width: auto !important;
                display: contents !important;
            }}
            [data-testid="stChatInput"] form {{
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
            .workspace-strip {{
                display: grid !important;
                grid-template-columns: repeat(5, minmax(0, 1fr)) !important;
                gap: 0.85rem !important;
                margin: 0.15rem 0 1rem !important;
            }}
            .workspace-strip-item {{
                background: linear-gradient(180deg, rgba(10, 20, 36, 0.9) 0%, rgba(8, 15, 28, 0.82) 100%) !important;
                border: 1px solid var(--line-soft) !important;
                border-radius: 16px !important;
                padding: 0.9rem 1rem !important;
                box-shadow: 0 10px 24px rgba(2, 6, 23, 0.18) !important;
            }}
            .workspace-strip-item span {{
                display: block !important;
                color: rgba(148, 163, 184, 0.74) !important;
                font-size: 0.68rem !important;
                letter-spacing: 0.14em !important;
                text-transform: uppercase !important;
                margin-bottom: 0.4rem !important;
            }}
            .workspace-strip-item strong {{
                display: block !important;
                color: #f8fafc !important;
                font-size: 0.92rem !important;
                font-weight: 700 !important;
                line-height: 1.35 !important;
                word-break: break-word !important;
            }}
            .analysis-deck-header {{
                margin: 1.4rem 0 0.75rem !important;
                padding: 0.2rem 0 0 !important;
            }}
            .analysis-deck-title {{
                color: #f8fafc !important;
                font-size: 1.32rem !important;
                font-weight: 700 !important;
                line-height: 1.2 !important;
            }}
            .analysis-deck-sub {{
                color: rgba(203, 213, 225, 0.66) !important;
                font-size: 0.9rem !important;
                line-height: 1.65 !important;
                margin-top: 0.35rem !important;
            /* --- 欢迎语巨幕布局终极锁定 --- */
            #welcome_shell_stable_box {{
                width: 100% !important;
                max-width: 1000px !important;
                margin: 0 auto !important;
                padding-top: 18vh !important; /* 核心垂直偏移 */
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
                justify-content: flex-start !important;
                text-align: center !important;
                z-index: 1 !important;
            }}
            #welcome_title_hero {{
                font-family: 'Orbitron', 'PingFang SC', sans-serif !important;
                font-size: clamp(2.8rem, 5vw, 4.2rem) !important;
                background: linear-gradient(135deg, #ffffff 0%, #94a3b8 100%) !important;
                -webkit-background-clip: text !important;
                -webkit-text-fill-color: transparent !important;
                font-weight: 800 !important;
                margin-bottom: 1.5rem !important;
                text-shadow: 0 4px 20px rgba(0, 0, 0, 0.4) !important;
                line-height: 1.2 !important;
            }}
            #welcome_sub_hero {{
                max-width: 820px !important;
                color: rgba(226, 232, 240, 0.72) !important;
                font-size: 1.12rem !important;
                line-height: 1.8 !important;
                font-weight: 500 !important;
                letter-spacing: 0.8px !important;
            }}
            /* 修正 Markdown 默认容器对居中的干扰 */
            [data-testid="stMarkdownContainer"]:has(#welcome_shell_stable_box) {{
                width: 100% !important;
                max-width: 100% !important;
                display: flex !important;
                justify-content: center !important;
                align-items: center !important;
            }}
                display: none !important;
            }}
            /* 主内容区留出底部空间 */
            section[data-testid="stMain"] .block-container {{
                padding-bottom: 90px !important;
            }}
            .stApp h1,.stApp h2,.stApp h3,.stApp h4 {{ color: #E2E8F0 !important; }}
            .stApp p,.stApp span,.stApp li,.stApp label,.stApp div {{ color: #E2E8F0 !important; }}
            div[data-testid="stChatMessage"] {{
                background: linear-gradient(180deg, rgba(10, 20, 36, 0.97) 0%, rgba(7, 14, 27, 0.95) 100%) !important;
                border: 1px solid rgba(148, 163, 184, 0.12) !important;
                border-radius: 18px !important;
                padding: 0.45rem 0.5rem !important;
                box-shadow: 0 10px 24px rgba(2, 6, 23, 0.14) !important;
                margin-bottom: 0.75rem !important;
                overflow: visible !important;
            }}
            /* 回复区中文排版：贴近专业报告的阅读感，避免过度科幻字体影响可读性 */
            .stChatMessage [data-testid="stMarkdownContainer"] {{
                font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans SC", "Helvetica Neue", Arial, sans-serif !important;
                color: #EAF2FF !important;
                letter-spacing: 0.01em !important;
                padding-bottom: 0.18rem !important;
            }}
            .stChatMessage [data-testid="stMarkdownContainer"] p {{
                font-size: 1.1rem !important;
                line-height: 1.9 !important;
                margin: 0.42rem 0 0.5rem !important;
                color: #EAF2FF !important;
                font-weight: 500 !important;
            }}
            .stChatMessage [data-testid="stMarkdownContainer"] li {{
                font-size: 1.08rem !important;
                line-height: 1.88 !important;
                margin: 0.32rem 0 !important;
                color: #EAF2FF !important;
                font-weight: 500 !important;
            }}
            .stChatMessage [data-testid="stMarkdownContainer"] ul,
            .stChatMessage [data-testid="stMarkdownContainer"] ol {{
                margin-top: 0.32rem !important;
                margin-bottom: 0.58rem !important;
                padding-left: 1.42rem !important;
            }}
            .stChatMessage [data-testid="stMarkdownContainer"] strong {{
                font-weight: 760 !important;
                color: #F8FAFC !important;
            }}
            .stChatMessage [data-testid="stMarkdownContainer"] h1 {{
                font-size: 1.46rem !important;
                line-height: 1.5 !important;
                font-weight: 780 !important;
                margin: 0.35rem 0 0.52rem !important;
                color: #F8FAFC !important;
                letter-spacing: 0 !important;
            }}
            .stChatMessage [data-testid="stMarkdownContainer"] h2 {{
                font-size: 1.3rem !important;
                line-height: 1.52 !important;
                font-weight: 760 !important;
                margin: 0.45rem 0 0.5rem !important;
                color: #F8FAFC !important;
            }}
            .stChatMessage [data-testid="stMarkdownContainer"] h3 {{
                font-size: 1.18rem !important;
                line-height: 1.56 !important;
                font-weight: 730 !important;
                margin: 0.36rem 0 0.44rem !important;
                color: #F8FAFC !important;
            }}
            .stChatMessage [data-testid="stMarkdownContainer"] hr {{
                border: 0 !important;
                border-top: 1px solid rgba(148, 163, 184, 0.28) !important;
                margin: 1rem 0 0.9rem !important;
            }}
            .stTabs [data-baseweb="tab-list"] {{
                background: rgba(8, 15, 27, 0.72) !important;
                border: 1px solid rgba(148, 163, 184, 0.14) !important;
                border-radius: 16px 16px 0 0 !important;
                gap: 0.25rem !important;
                padding: 0.35rem 0.35rem 0 !important;
            }}
            .stTabs [data-baseweb="tab"] {{
                font-size: 0.95rem !important;
                font-weight: 700 !important;
                color: rgba(148,163,184,0.76) !important;
                padding: 0.95rem 1.25rem !important;
                font-family: 'Rajdhani', sans-serif !important;
                letter-spacing: 0.03em !important;
                border-bottom: 2px solid transparent !important;
                border-radius: 12px 12px 0 0 !important;
            }}
            .stTabs [aria-selected="true"] {{
                color: #f8fafc !important;
                border-bottom: 2px solid #7dd3fc !important;
            }}
            [data-testid="stSidebar"],
            [data-testid="stSidebarContent"] {{
                background: #060b13 !important;
                background-color: #060b13 !important;
                background-image: linear-gradient(180deg, #060b13 0%, #04080f 100%) !important;
            }}
            [data-testid="stSidebar"] {{
                border-right: 1px solid rgba(148, 163, 184, 0.1) !important;
                width: 280px !important;
                min-width: 280px !important;
                max-width: 280px !important;
                flex: 0 0 280px !important;
                cursor: default !important;
                transition: none !important;
            }}
            [data-testid="stSidebar"] > div:first-child {{
                width: 280px !important;
                min-width: 280px !important;
                max-width: 280px !important;
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                height: 100vh !important;
                overflow-y: auto !important;
                transition: none !important;
                will-change: auto !important;
            }}
            [data-testid="stSidebarResizer"],
            [data-testid="stSidebarResizeHandle"],
            [aria-label="Resize sidebar"],
            [data-testid="stSidebarNav"] + div {{
                cursor: default !important;
                pointer-events: none !important;
            }}
            [data-testid="stSidebar"][aria-expanded="true"],
            [data-testid="stSidebar"][aria-expanded="false"] {{
                width: var(--sidebar-open-width) !important;
                min-width: var(--sidebar-open-width) !important;
                width: 280px !important;
                min-width: 280px !important;
                max-width: 280px !important;
                flex: 0 0 280px !important;
            }}
            [data-testid="stSidebar"][aria-expanded="true"] > div:first-child,
            [data-testid="stSidebar"][aria-expanded="false"] > div:first-child {{
                margin-left: 0 !important;
                transform: none !important;
            }}
            [data-testid="collapsedControl"] {{
                display: none !important;
            }}
            [data-testid="stSidebarContent"] > div:first-child,
            [data-testid="stSidebarContent"] > div:first-child *,
            [data-testid="stSidebarNav"] button,
            [aria-label="Open sidebar"],
            [aria-label="Close sidebar"],
            [data-testid="stSidebarCollapseButton"],
            [data-testid="stSidebarHeaderCollapseButton"] {{
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
            }}
            [data-testid="stSidebarUserContent"] {{
                padding-top: 0.55rem !important;
            }}
            [data-testid="stSidebar"] .sidebar-brand {{
                display: flex !important;
                align-items: center !important;
                gap: 12px !important;
                margin-top: 0.15rem !important;
                margin-bottom: 16px !important;
                padding: 6px 2px 8px !important;
            }}
            [data-testid="stSidebar"] .sidebar-logo {{
                width: 58px !important;
                height: 52px !important;
                background: rgba(59, 130, 246, 0.1) !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                position: relative !important;
                clip-path: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%) !important;
                border: 1px solid rgba(56, 189, 248, 0.4) !important;
                box-shadow: 0 0 15px rgba(56, 189, 248, 0.3) !important;
                backdrop-filter: blur(10px) !important;
                animation: logo-float 3s infinite ease-in-out !important;
            }}
            [data-testid="stSidebar"] .sidebar-logo::before {{
                content: "" !important;
                position: absolute !important;
                inset: -2px !important;
                background: linear-gradient(45deg, #3b82f6, #06b6d4, transparent) !important;
                z-index: -1 !important;
                clip-path: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%) !important;
                opacity: 0.5 !important;
            }}
            @keyframes logo-float {{
                0%, 100% {{ transform: translateY(0) rotate(0deg); }}
                50% {{ transform: translateY(-5px) rotate(2deg); }}
            }}
            [data-testid="stSidebar"] .sidebar-logo-ring {{
                position: absolute !important;
                inset: 3px !important;
                border: 1.5px solid rgba(255, 255, 255, 0.4) !important;
                border-radius: 14px !important;
            }}
            [data-testid="stSidebar"] .sidebar-logo-core {{
                position: relative !important;
                z-index: 1 !important;
                font-family: 'Orbitron', sans-serif !important;
                font-size: 1.4rem !important;
                font-weight: 900 !important;
                color: #00E5FF !important;
                text-shadow: 0 0 10px rgba(0, 229, 255, 0.8), 0 0 20px rgba(0, 229, 255, 0.4) !important;
                -webkit-background-clip: text !important;
                letter-spacing: -2px !important;
            }}
            [data-testid="stSidebar"] .sidebar-brand-copy {{
                min-width: 0 !important;
            }}
            [data-testid="stSidebar"] .sidebar-brand-title {{
                background: linear-gradient(to right, #ffffff, #94a3b8) !important;
                -webkit-background-clip: text !important;
                -webkit-text-fill-color: transparent !important;
                font-size: 1.4rem !important;
                font-weight: 800 !important;
                letter-spacing: 3px !important;
                font-family: 'Orbitron', sans-serif !important;
                filter: drop-shadow(0 0 5px rgba(125, 211, 252, 0.3)) !important;
            }}
            [data-testid="stSidebar"] .sidebar-brand-sub {{
                color: #94a3b8 !important;
                font-size: 0.65rem !important;
                letter-spacing: 1.5px !important;
                text-transform: uppercase !important;
                font-weight: 500 !important;
                margin-top: 4px !important;
                font-family: 'Rajdhani', sans-serif !important;
            }}
            [data-testid="stSidebar"] .sidebar-status {{
                background: linear-gradient(180deg, rgba(10, 20, 36, 0.78) 0%, rgba(8, 15, 27, 0.72) 100%) !important;
                border: 1px solid rgba(148, 163, 184, 0.12) !important;
                border-radius: 16px !important;
                padding: 12px 13px !important;
                margin-bottom: 14px !important;
            }}
            [data-testid="stSidebar"] .sidebar-status-item {{
                font-size: 0.77rem !important;
                color: #dbeafe !important;
                line-height: 1.7 !important;
            }}
            [data-testid="stSidebar"] .sidebar-metrics {{
                display: grid !important;
                grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
                gap: 8px !important;
                margin-bottom: 14px !important;
            }}
            [data-testid="stSidebar"] .sidebar-metric {{
                background: rgba(255, 255, 255, 0.035) !important;
                border: 1px solid rgba(148, 163, 184, 0.1) !important;
                border-radius: 14px !important;
                padding: 11px 8px !important;
                text-align: center !important;
            }}
            [data-testid="stSidebar"] .sidebar-metric span {{
                display: block !important;
                color: rgba(148,163,184,0.72) !important;
                font-size: 0.67rem !important;
                margin-bottom: 4px !important;
            }}
            [data-testid="stSidebar"] .sidebar-metric strong {{
                color: #f8fafc !important;
                font-size: 0.92rem !important;
                font-family: 'Orbitron', sans-serif !important;
            }}
            [data-testid="stSidebar"] .sidebar-section-label {{
                margin-top: 32px !important;
                margin-bottom: 12px !important;
                font-size: 0.8rem !important;
                color: rgba(148, 163, 184, 0.5) !important;
                font-weight: 600 !important;
                letter-spacing: 1px !important;
            }}
            [data-testid="stSidebar"] .sidebar-section-hint {{
                font-size: 0.78rem !important;
                color: rgba(148,163,184,0.6) !important;
                margin-bottom: 10px !important;
                line-height: 1.5 !important;
            }}
            [data-testid="stSidebar"] .stButton > button {{
                border-radius: 12px !important;
                min-height: 2.4rem !important;
                justify-content: flex-start !important;
                text-align: left !important;
                font-family: 'Rajdhani', sans-serif !important;
                font-weight: 600 !important;
            }}
            [data-testid="stSidebar"] .stButton > button[kind="secondary"] {{
                background: transparent !important;
                border: none !important;
                color: #ffffff !important;
                font-size: 1rem !important;
                padding: 0 !important;
                min-height: auto !important;
            }}
            [data-testid="stSidebar"] .stButton > button[kind="primary"] {{
                background: rgba(30, 41, 59, 0.4) !important;
                border: 1px solid rgba(56, 189, 248, 0.2) !important;
                border-radius: 12px !important;
                color: #ffffff !important;
                width: 100% !important;
                padding: 0.6rem 1rem !important;
            }}
            [data-testid="stSidebar"] .stTextInput input {{
                border-radius: 10px !important;
                border: 1px solid rgba(56, 189, 248, 0.35) !important;
                background: rgba(15, 23, 42, 0.7) !important;
                color: #E2E8F0 !important;
            }}
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-marker),
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-actions-marker) {{
                display: none !important;
                margin: 0 !important;
                padding: 0 !important;
            }}
            [data-testid="stSidebar"] .history-row-shell {{
                margin: 0.28rem 0 !important;
                padding: 0.18rem 0 !important;
                border-radius: 18px !important;
                transition: background 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease !important;
            }}
            [data-testid="stSidebar"] .history-row-shell:hover {{
                background: rgba(255, 255, 255, 0.03) !important;
            }}
            [data-testid="stSidebar"] .history-row-shell.history-row-shell-active {{
                background: linear-gradient(180deg, rgba(14, 165, 233, 0.08) 0%, rgba(255, 255, 255, 0.04) 100%) !important;
                box-shadow: inset 0 0 0 1px rgba(125, 211, 252, 0.1) !important;
            }}
            [data-testid="stSidebar"] .history-row-shell > div[data-testid="stHorizontalBlock"] {{
                align-items: center !important;
                gap: 0.35rem !important;
            }}
            [data-testid="stSidebar"] .history-row-shell > div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
                display: flex !important;
                align-items: stretch !important;
            }}
            [data-testid="stSidebar"] .history-row-shell .history-row-main-col .stButton {{
                width: 100% !important;
            }}
            [data-testid="stSidebar"] .history-row-shell .history-row-main-col .stButton > button {{
                width: 100% !important;
                min-height: 3.25rem !important;
                border-radius: 18px !important;
                padding: 0.65rem 0.9rem !important;
                line-height: 1.4 !important;
                white-space: normal !important;
            }}
            [data-testid="stSidebar"] .history-row-shell .history-row-menu-col {{
                justify-content: center !important;
            }}
            [data-testid="stSidebar"] .history-row-shell .history-row-menu-button > button {{
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
            }}
            [data-testid="stSidebar"] .history-row-shell:hover .history-row-menu-button > button {{
                opacity: 1 !important;
                visibility: visible !important;
                pointer-events: auto !important;
                transform: translateX(0) !important;
            }}
            [data-testid="stSidebar"] .history-row-shell .history-row-menu-button > button:hover {{
                background: rgba(255, 255, 255, 0.12) !important;
            }}
            [data-testid="stSidebar"] .history-actions-shell {{
                margin: -0.05rem 0 0.45rem 0 !important;
                padding: 0.42rem !important;
                border-radius: 14px !important;
                background: rgba(8, 15, 27, 0.9) !important;
                border: 1px solid rgba(148, 163, 184, 0.12) !important;
                box-shadow: 0 10px 24px rgba(2, 6, 23, 0.16) !important;
            }}
            [data-testid="stSidebar"] .history-actions-shell .stButton > button {{
                min-height: 2rem !important;
                border-radius: 10px !important;
                justify-content: center !important;
                font-size: 0.88rem !important;
                padding-left: 0.55rem !important;
                padding-right: 0.55rem !important;
            }}
            [data-testid="stSidebar"] .history-actions-shell .stTextInput input {{
                min-height: 2.2rem !important;
                border-radius: 10px !important;
                font-size: 0.9rem !important;
            }}
            [data-testid="stSidebar"] .history-actions-shell .stCaptionContainer,
            [data-testid="stSidebar"] .history-actions-shell [data-testid="stCaptionContainer"] {{
                margin-bottom: 0.2rem !important;
            }}
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-marker) + div[data-testid="stVerticalBlock"] {{
                margin: 0.28rem 0 !important;
                padding: 0.18rem 0 !important;
                border-radius: 18px !important;
                transition: background 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease !important;
            }}
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-marker) + div[data-testid="stVerticalBlock"]:hover {{
                background: rgba(255, 255, 255, 0.03) !important;
            }}
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-active-marker) + div[data-testid="stVerticalBlock"] {{
                background: linear-gradient(180deg, rgba(14, 165, 233, 0.08) 0%, rgba(255, 255, 255, 0.04) 100%) !important;
                box-shadow: inset 0 0 0 1px rgba(125, 211, 252, 0.1) !important;
            }}
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-marker) + div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] {{
                align-items: center !important;
                gap: 0.35rem !important;
            }}
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-marker) + div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
                display: flex !important;
                align-items: stretch !important;
            }}
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-marker) + div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child .stButton {{
                width: 100% !important;
            }}
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-marker) + div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child .stButton > button {{
                width: 100% !important;
                min-height: 3.25rem !important;
                border-radius: 18px !important;
                padding: 0.65rem 0.9rem !important;
                line-height: 1.4 !important;
                white-space: normal !important;
            }}
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-marker) + div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child {{
                justify-content: center !important;
            }}
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-marker) + div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child .stButton > button {{
                min-height: 1.8rem !important;
                width: 2.2rem !important;
                min-width: 2.2rem !important;
                background: #232a35 !important;
                border: none !important;
                color: #ffffff !important;
                border-radius: 8px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                font-size: 1.2rem !important;
                padding: 0 !important;
            }}
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-marker) + div[data-testid="stVerticalBlock"]:hover > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child .stButton > button,
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-menu-open-marker) + div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child .stButton > button {{
                opacity: 1 !important;
                visibility: visible !important;
                pointer-events: auto !important;
            }}
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-row-marker) + div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child .stButton > button:hover {{
                background: rgba(255, 255, 255, 0.12) !important;
            }}
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-actions-marker) + div[data-testid="stVerticalBlock"] {{
                margin: -0.05rem 0 0.45rem 0 !important;
                padding: 0.42rem !important;
                border-radius: 14px !important;
                background: rgba(8, 15, 27, 0.9) !important;
                border: 1px solid rgba(148, 163, 184, 0.12) !important;
                box-shadow: 0 10px 24px rgba(2, 6, 23, 0.16) !important;
            }}
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-actions-marker) + div[data-testid="stVerticalBlock"] .stButton > button {{
                min-height: 2rem !important;
                border-radius: 10px !important;
                justify-content: center !important;
                font-size: 0.88rem !important;
                padding-left: 0.55rem !important;
                padding-right: 0.55rem !important;
            }}
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-actions-marker) + div[data-testid="stVerticalBlock"] .stTextInput input {{
                min-height: 2.2rem !important;
                border-radius: 10px !important;
                font-size: 0.9rem !important;
            }}
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-actions-marker) + div[data-testid="stVerticalBlock"] .stCaptionContainer,
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.history-actions-marker) + div[data-testid="stVerticalBlock"] [data-testid="stCaptionContainer"] {{
                margin-bottom: 0.2rem !important;
            }}
            @media (max-width: 1280px) {{
                .workspace-strip {{
                    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
                }}
            }}

            /* =========================================================
               ChatGPT 风格对话布局覆写 (Chat Message Overrides)
               ========================================================= */
               
            /* 1. 【终极剥离】彻底移除模型回复的内外侧包裹框、所有的扩展控件框、甚至由 Markdown 动态生成的卡片框，使其达到绝对的大气透视 */
            [data-testid="stChatMessage"]:has(.is-assistant-marker),
            [data-testid="stChatMessage"]:has(.is-assistant-marker) > div,
            [data-testid="stChatMessage"]:has(.is-assistant-marker) [data-testid="stChatMessageContent"] {{
                background-color: transparent !important;
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                max-width: 100% !important;
            }}
            [data-testid="stChatMessage"]:has(.is-assistant-marker) {{
                padding: 1.5rem 0 !important; 
                margin-top: 0.5rem !important;
                margin-bottom: 2rem !important;
            }}
            
            /* 暴力突破：如果是原生 st.status 或自带边框的 markdown 容器，剥除其伪装 */
            [data-testid="stChatMessage"]:has(.is-assistant-marker) [data-testid="stStatusWidget"],
            [data-testid="stChatMessage"]:has(.is-assistant-marker) [data-testid="stExpander"],
            [data-testid="stChatMessage"]:has(.is-assistant-marker) [data-testid="stStatusWidget"] > div[data-baseweb="block"],
            [data-testid="stChatMessage"]:has(.is-assistant-marker) [data-testid="stExpander"] > details,
            [data-testid="stChatMessage"]:has(.is-assistant-marker) .cockpit-card {{
                background-color: transparent !important;
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                padding-left: 0 !important;
            }}
            
            /* 2. 将 User（用户提问）移至右侧，做成现代风格气泡 */
            [data-testid="stChatMessage"]:has(.is-user-marker) {{
                background-color: rgba(47, 47, 47, 0.6) !important; /* 深灰色气泡背景 */
                border: 1px solid rgba(255, 255, 255, 0.05) !important;
                border-radius: 1.6rem !important;
                border-bottom-right-radius: 0.3rem !important; /* 右侧气泡尾巴 */
                padding: 0.8rem 1.4rem !important;
                margin: 1.5rem 0 1.5rem auto !important; /* 靠右对齐关键 */
                max-width: 75% !important; 
                width: max-content !important; 
                display: flex !important;
                flex-direction: row-reverse !important; /* 头像放到右侧 */
                gap: 1rem !important;
                align-items: center !important;
            }}
            
            /* 极其粗暴地隐藏普通用户的默认占位头像，不管它叫什么名字或套了几层容器 */
            [data-testid="stChatMessage"]:has(.is-user-marker) [data-testid="chatAvatarIcon-user"],
            [data-testid="stChatMessage"]:has(.is-user-marker) [data-testid="stChatMessageAvatar"],
            [data-testid="stChatMessage"]:has(.is-user-marker) > div:first-child:not([data-testid="stChatMessageContent"]) {{
                display: none !important;
                width: 0 !important;
                height: 0 !important;
                margin: 0 !important;
                padding: 0 !important;
                opacity: 0 !important;
                visibility: hidden !important;
                position: absolute !important;
            }}
            
            [data-testid="stChatMessage"]:has(.is-user-marker) [data-testid="stChatMessageContent"] {{
                display: flex !important;
                flex-direction: column !important;
                justify-content: center !important;
                padding: 0 !important;
                margin: 0 !important;
                min-height: 100% !important;
            }}
            
            [data-testid="stChatMessage"]:has(.is-user-marker) .stMarkdown {{
                width: auto !important;
                margin: 0 !important;
            }}
            
            [data-testid="stChatMessage"]:has(.is-user-marker) [data-testid="stMarkdownContainer"] p {{
                margin: 0 !important;
                padding: 0 !important;
                line-height: normal !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }}
            
            /* 提问区域输入框文本垂直居中修正 */
            [data-testid="stChatInput"] textarea {{
                padding-top: 0.8rem !important;
                padding-bottom: 0.8rem !important;
                line-height: 1.5 !important;
                align-content: center !important;
            }}
            /* =========================================================
               顶部导航栏 (Top Navigation Radio) 恢复模式 - 固定在顶部
               ========================================================= */
            [data-testid="stRadio"] {{
                position: fixed !important;
                top: 1.5rem !important;
                left: calc(var(--sidebar-open-width, 300px) + calc((100vw - var(--sidebar-open-width, 300px)) / 2)) !important;
                transform: translateX(-50%) !important;
                z-index: 99999 !important;
            }}
            /* 当侧边栏在较小屏幕收起时的回退居中 */
            @media (max-width: 991px) {{
                [data-testid="stRadio"] {{
                    left: 50% !important;
                }}
            }}
            [data-testid="stRadio"] > div[role="radiogroup"] {{
                display: flex !important;
                flex-direction: row !important;
                gap: 0.5rem !important;
                background: rgba(8, 15, 27, 0.85) !important;
                border: 1px solid rgba(148, 163, 184, 0.14) !important;
                border-radius: 16px !important;
                padding: 0.4rem !important;
                width: fit-content !important;
                align-items: center !important;
                margin: 0 !important;
                backdrop-filter: blur(16px) !important;
                -webkit-backdrop-filter: blur(16px) !important;
                box-shadow: 0 10px 40px -10px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.05) !important;
            }}
            [data-testid="stRadio"] > div[role="radiogroup"] label {{
                background: transparent !important;
                border-radius: 10px !important;
                padding: 0.5rem 1.4rem !important;
                cursor: pointer !important;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
                margin: 0 !important;
            }}
            [data-testid="stRadio"] > div[role="radiogroup"] label:hover {{
                background: rgba(255, 255, 255, 0.06) !important;
            }}
            /* 选中状态 */
            [data-testid="stRadio"] > div[role="radiogroup"] label[data-checked="true"] {{
                background: linear-gradient(180deg, rgba(14, 165, 233, 0.15) 0%, rgba(15, 23, 42, 0.4) 100%) !important;
                border: 1px solid rgba(125, 211, 252, 0.2) !important;
                box-shadow: 0 4px 12px rgba(2, 6, 23, 0.2) !important;
            }}
            /* 隐藏原生的单选圆圈 */
            [data-testid="stRadio"] > div[role="radiogroup"] label > div:first-child:not([data-testid="stMarkdownContainer"]) {{
                display: none !important;
                width: 0 !important;
                margin: 0 !important;
                padding: 0 !important;
            }}
            /* 文字样式 */
            [data-testid="stRadio"] > div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] {{
                color: rgba(148,163,184,0.76) !important;
                font-weight: 600 !important;
                font-family: 'Rajdhani', sans-serif !important;
                letter-spacing: 0.03em !important;
                font-size: 0.95rem !important;
                line-height: 1 !important;
            }}
            [data-testid="stRadio"] > div[role="radiogroup"] label[data-checked="true"] div[data-testid="stMarkdownContainer"] p {{
                color: #f8fafc !important;
                text-shadow: 0 0 10px rgba(56, 189, 248, 0.4) !important;
            }}
            [data-testid="stRadio"] > div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p {{
                margin: 0 !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    _lock_sidebar_open_stable()
