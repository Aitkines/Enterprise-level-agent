from __future__ import annotations

from datetime import datetime
import re

import streamlit as st

from src.infrastructure.repositories.session_repository import SessionRepository
from src.shared.session_title import (
    build_default_session_id,
    extract_session_preview,
    extract_session_title,
    normalize_manual_title,
)


DEFAULT_ASSISTANT_TEXT = "系统已就绪。请输入你想分析的公司、赛道或研究问题。"
DEFAULT_ASSISTANT_MESSAGE = {
    "role": "assistant",
    "content": DEFAULT_ASSISTANT_TEXT,
}


def ensure_session_defaults() -> None:
    defaults = {
        "active_target": None,
        "active_targets": [],
        "messages": [],
        "tool_calls_log": [],
        "latest_chart_data": None,
        "session_id": "last_session",
        "history_editing_file": None,
        "current_session_title": None,
        "current_session_manual_title": None,
        "history_action_target": None,
        "_session_restored_from_disk": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, (list, dict)) else value

    if not st.session_state.get("_session_restored_from_disk"):
        restored_messages = SessionRepository().load_messages_if_exists("last_session.json")
        if restored_messages:
            st.session_state.messages = restored_messages
            st.session_state.session_id = "last_session"
        st.session_state._session_restored_from_disk = True

    if not st.session_state.messages:
        st.session_state.messages = [DEFAULT_ASSISTANT_MESSAGE.copy()]
        SessionRepository().save_messages("last_session", st.session_state.messages)
    st.session_state.current_session_title = _extract_session_title(st.session_state.messages) or None


def _fresh_session_messages() -> list[dict]:
    return [DEFAULT_ASSISTANT_MESSAGE.copy()]


def _reset_to_fresh_session() -> None:
    st.session_state.messages = _fresh_session_messages()
    st.session_state.session_id = "last_session"
    st.session_state.current_session_title = None
    st.session_state.current_session_manual_title = None
    st.session_state.history_action_target = None
    st.session_state.active_target = None
    st.session_state.active_targets = []
    st.session_state.tool_calls_log = []
    st.session_state.latest_chart_data = None
    st.session_state.history_editing_file = None
    SessionRepository().save_messages("last_session", st.session_state.messages)


def is_seed_assistant_message(message: dict) -> bool:
    return (
        message.get("role") == "assistant"
        and str(message.get("content", "")).strip() == DEFAULT_ASSISTANT_TEXT
    )


def has_user_messages(messages: list[dict] | None = None) -> bool:
    messages = messages if messages is not None else st.session_state.get("messages", [])
    return any(message.get("role") == "user" and str(message.get("content", "")).strip() for message in messages)


def is_initial_chat_state(messages: list[dict] | None = None) -> bool:
    messages = messages if messages is not None else st.session_state.get("messages", [])
    return not has_user_messages(messages)


def get_visible_chat_messages(messages: list[dict] | None = None) -> list[dict]:
    messages = messages if messages is not None else st.session_state.get("messages", [])
    if is_initial_chat_state(messages):
        return []
    return [message for message in messages if not is_seed_assistant_message(message)]


def _has_meaningful_messages(messages: list[dict]) -> bool:
    return has_user_messages(messages)


def _build_history_session_id(messages: list[dict]) -> str:
    return build_default_session_id(_extract_session_title(messages))


def _clean_title_text(text: str) -> str:
    cleaned = str(text or "")
    cleaned = re.sub(r"```chart\s*\{.*?\}\s*```", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"```.*?```", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"^#{1,6}\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^[-*•]\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\d+\.\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _split_sentences(text: str) -> list[str]:
    cleaned = _clean_title_text(text)
    if not cleaned:
        return []
    parts = re.split(r"[。！？；;\n]+", cleaned)
    return [part.strip() for part in parts if part and part.strip()]


def _first_sentence(text: str) -> str:
    sentences = _split_sentences(text)
    return sentences[0] if sentences else ""


def _first_user_question(messages: list[dict]) -> str:
    for message in messages:
        if message.get("role") == "user":
            text = str(message.get("content", "")).strip()
            if text:
                return text
    return ""


def _first_assistant_answer(messages: list[dict]) -> str:
    saw_user = False
    for message in messages:
        role = message.get("role")
        if role == "user":
            saw_user = True
            continue
        if role != "assistant" or not saw_user:
            continue
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        if content == DEFAULT_ASSISTANT_TEXT:
            continue
        return content
    return ""


def _compose_title_from_answer(answer: str) -> str:
    full_text = _clean_title_text(answer)[:600]
    if not full_text:
        return ""

    if re.search(r"(正在|执行中|处理中|思考中|请稍后|加载中)", full_text):
        return ""

    company_finance_match = re.search(
        r"(?:为您|帮您|针对|关于)?([^\s，。；：:]{2,16})(?:\(\d{6}\))?(?:的)?(财务信息|财务数据|财务情况|财务状况|财务表现|财务指标|财报)",
        full_text,
    )
    if company_finance_match:
        company = company_finance_match.group(1).strip()
        company = re.sub(
            r"^(我来|我将|我会|让我|为您|帮您|先|现在|分析|解读|梳理|介绍|总结|评估|查询|检索|对比)+(一下|下)?",
            "",
            company,
        ).strip()
        company = re.sub(r"的$", "", company).strip()
        if company and len(company) >= 2:
            return f"{company}财务分析"[:16]

    action_prefix_pattern = re.compile(
        r"^(我来为您|我来帮您|我将为您|我会为您|让我|先为您|下面为您|我先|我可以为您|可以为您|好的|当然|没问题|明白了|收到|根据[^，。]*[，,]|基于[^，。]*[，,]|由于[^，。]*[，,]|当前[^，。]*[，,])"
    )
    noisy_sentence_pattern = re.compile(
        r"(我来为您|我将为您|让我|先查询|先检索|尝试搜索|无法检索|未能获取|知识库|请稍后|建议您|可以前往|如果需要)"
    )

    best_sentence = ""
    best_score = -10
    for sentence in _split_sentences(full_text)[:6]:
        candidate = sentence.strip()
        candidate = action_prefix_pattern.sub("", candidate).strip()
        candidate = re.sub(r"^(以下|如下|结论|结果|当前|本次|已为你|已整理|可以看到|综合来看|总体上|整体上)", "", candidate).strip()
        candidate = re.sub(r"(如下|如下所示)$", "", candidate).strip()
        candidate = re.sub(r"[：:]\s*$", "", candidate).strip()
        if len(candidate) < 4:
            continue

        score = 0
        if not noisy_sentence_pattern.search(candidate):
            score += 3
        if re.search(r"(财务|毛利率|ROE|负债率|营收|净利润|现金流|赛道|TOPSIS|熵权|评级|研报)", candidate, flags=re.IGNORECASE):
            score += 3
        if re.search(r"[A-Za-z0-9\u4e00-\u9fff]{2,16}(?:\(\d{6}\))?", candidate):
            score += 1
        if len(candidate) <= 22:
            score += 1
        if re.search(r"(无法|未能|失败|异常|错误|缺失|不足)", candidate):
            score -= 4

        if score > best_score:
            best_score = score
            best_sentence = candidate

    if best_score <= 0:
        return ""
    return best_sentence[:16]


def _extract_session_title(messages: list[dict]) -> str:
    return extract_session_title(messages, seed_text=DEFAULT_ASSISTANT_TEXT)


def refresh_current_session_title(messages: list[dict] | None = None) -> None:
    payload = messages if messages is not None else st.session_state.get("messages", [])
    st.session_state.current_session_title = _extract_session_title(payload) or None


def _sanitize_manual_title(value: str) -> str:
    return normalize_manual_title(value)


def rename_current_session_title(new_title: str) -> None:
    cleaned = _sanitize_manual_title(new_title)
    st.session_state.current_session_manual_title = cleaned or None
    if cleaned:
        st.session_state.current_session_title = cleaned
    else:
        refresh_current_session_title(st.session_state.get("messages", []))
    save_current_session()


def delete_current_session() -> None:
    _reset_to_fresh_session()


def _extract_session_preview(messages: list[dict]) -> str:
    return extract_session_preview(messages, seed_text=DEFAULT_ASSISTANT_TEXT)


def archive_current_session() -> None:
    messages = st.session_state.get("messages", [])
    if not _has_meaningful_messages(messages):
        return

    repository = SessionRepository()
    session_id = st.session_state.get("session_id", "last_session")
    if session_id == "last_session":
        preferred_title = st.session_state.get("current_session_manual_title")
        preferred_session_id = preferred_title or _build_history_session_id(messages)
        session_id = repository.resolve_session_id(preferred_session_id)
    repository.save_messages(session_id, messages)
    st.session_state.session_id = session_id


def start_new_session() -> None:
    archive_current_session()
    _reset_to_fresh_session()


def list_history_files(limit: int = 20) -> list[str]:
    return SessionRepository().list_history_files(limit=limit)


def list_history_previews(limit: int = 20) -> list[dict]:
    current_session_id = st.session_state.get("session_id", "last_session")
    previews = SessionRepository().list_session_previews(limit=limit)
    for preview in previews:
        preview["active"] = preview["session_id"] == current_session_id
    return previews


def get_current_session_preview() -> dict | None:
    session_id = st.session_state.get("session_id", "last_session")
    if session_id != "last_session":
        return None

    messages = st.session_state.get("messages", [])
    manual_title = st.session_state.get("current_session_manual_title")
    cached_title = st.session_state.get("current_session_title")
    return {
        "session_id": session_id,
        "title": manual_title or cached_title or _extract_session_title(messages) or "新对话",
        "preview": _extract_session_preview(messages),
        "updated_at": "当前会话",
        "active": True,
        "filename": None,
    }


def load_history_session(filename: str) -> None:
    st.session_state.messages = SessionRepository().load_messages(filename)
    st.session_state.session_id = filename.replace(".json", "")
    st.session_state.current_session_title = None
    st.session_state.current_session_manual_title = None
    st.session_state.history_action_target = None
    for key in list(st.session_state.keys()):
        if str(key).startswith("confirm_delete_"):
            st.session_state.pop(key, None)
    st.session_state.tool_calls_log = []
    st.session_state.latest_chart_data = None
    st.session_state.history_editing_file = None


def rename_history_session(filename: str, new_title: str) -> str:
    repository = SessionRepository()
    new_filename = repository.rename_session(filename, new_title)
    if st.session_state.get("session_id") == filename.replace(".json", ""):
        st.session_state.session_id = new_filename.replace(".json", "")
    st.session_state.history_editing_file = None
    return new_filename


def delete_history_session(filename: str) -> None:
    SessionRepository().delete_session(filename)
    for key in list(st.session_state.keys()):
        if str(key).startswith("confirm_delete_"):
            st.session_state.pop(key, None)
    if st.session_state.get("session_id") == filename.replace(".json", ""):
        _reset_to_fresh_session()
    elif st.session_state.get("history_editing_file") == filename:
        st.session_state.history_editing_file = None


def save_current_session() -> None:
    session_id = st.session_state.get("session_id", "last_session")
    SessionRepository().save_messages(session_id, st.session_state.get("messages", []))


def append_tool_log(
    tool: str,
    success: bool = True,
    elapsed: str = "",
    info: str = "",
) -> None:
    st.session_state.tool_calls_log.append(
        {
            "tool": tool,
            "success": success,
            "elapsed": elapsed,
            "info": info,
            "time": datetime.now().strftime("%H:%M:%S"),
        }
    )


def update_latest_tool_elapsed(elapsed_seconds: float) -> None:
    if not st.session_state.get("tool_calls_log"):
        return
    st.session_state.tool_calls_log[-1]["elapsed"] = f"{round(elapsed_seconds, 1)}s"
