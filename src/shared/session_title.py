import re

def build_default_session_id(title):
    if not title:
        return "session"
    return re.sub(r'[^\w\s-]', '', title).strip().lower()[:20]

def extract_session_preview(messages, seed_text=""):
    for msg in messages:
        if msg["role"] == "user":
            return msg["content"][:100]
    return ""

def extract_session_title(messages, seed_text=""):
    for msg in messages:
        if msg["role"] == "user":
            return msg["content"][:15]
    return "新对话"

def normalize_manual_title(value):
    return (value or "").strip()[:16]
