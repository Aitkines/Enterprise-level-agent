import os

base_dir = r"c:\Users\Lenovo\Desktop\项目agent2.0\src\presentation\components"

# 1. Read the dumped static CSS (which has normal {} braces)
with open(os.path.join(base_dir, "css_dump_1.txt"), "r", encoding="utf-8") as f:
    css_content = f.read()

# We need to escape { and } for f-string, but wait! The dumped string has 
# <style>\n@import ...
# We'll strip the <style> tags and escape the braces.
css_content = css_content.replace("<style>", "").replace("</style>", "").strip()
css_content_escaped = css_content.replace("{", "{{").replace("}", "}}")

# 2. Add the custom ChatGPT style overrides that aren't in the compiled pyc string
chatgpt_styles = """
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
            
            [data-testid="stChatMessage"]:has(.is-user-marker) .stMarkdown {{
                width: auto !important;
                margin: 0 !important;
            }}
            [data-testid="stChatMessage"]:has(.is-user-marker) [data-testid="stMarkdownContainer"] p {{
                margin: 0 !important;
                padding: 0 !important;
                line-height: 1.5 !important;
                display: inline-block !important;
            }}
"""

# 3. Combine it
python_code = f'''import streamlit as st
import streamlit.components.v1 as components

def _lock_sidebar_open_stable() -> None:
    """强制侧栏保持展开，并隐藏所有开关按钮（更稳定的版本）。"""
    components.html(
        """
        <script>
            const lockSidebar = () => {{
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

                hideSelectors.forEach((selector) => {{
                    doc.querySelectorAll(selector).forEach((el) => {{
                        el.style.display = 'none';
                        el.style.visibility = 'hidden';
                        el.style.pointerEvents = 'none';
                    }});
                }});

                const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                if (!sidebar) return;

                if (sidebar.getAttribute('aria-expanded') === 'false') {{
                    const openButton = doc.querySelector('[aria-label="Open sidebar"], [data-testid="collapsedControl"] button, [data-testid="collapsedControl"]');
                    if (openButton) {{
                        openButton.click();
                    }}
                    sidebar.setAttribute('aria-expanded', 'true');
                }}
            }};

            lockSidebar();
            const observer = new MutationObserver(() => lockSidebar());
            observer.observe(window.parent.document.body, {{
                childList: true,
                subtree: true,
                attributes: true,
            }});
        </script>
        """,
        height=0,
        width=0,
    )

def apply_global_styles(is_new_chat: bool = False) -> None:
    """应用专属 CSS 样式并处理布局。"""
    
    pos_style = """
            [data-testid="stForm"] {{
                position: relative !important;
                bottom: auto !important;
                left: auto !important;
                margin: 2.15rem auto 7.5rem !important;
                width: calc((100vw - var(--sidebar-open-width) - 3.2rem) * 0.76) !important;
                max-width: 1200px !important;
                display: block !important;
            }}
    """ if is_new_chat else """
            [data-testid="stForm"] {{
                position: fixed !important;
                bottom: 1.5rem !important;
                left: calc(var(--sidebar-open-width) + 1.25rem) !important;
                width: calc((100vw - var(--sidebar-open-width) - 3.2rem) * 0.76) !important;
                max-width: 1200px !important;
                display: block !important;
            }}
    """

    st.markdown(
        f"""
        <style>
            {{pos_style}}
{css_content_escaped}
{chatgpt_styles}
        </style>
        """,
        unsafe_allow_html=True,
    )
    _lock_sidebar_open_stable()
'''


with open(os.path.join(base_dir, "styles.py"), "w", encoding="utf-8") as out:
    out.write(python_code)
print("Finished rebuilding styles.py")
