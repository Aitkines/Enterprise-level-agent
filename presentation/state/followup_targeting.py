from __future__ import annotations

import re


def should_preserve_active_target(prompt: str, current_active_target: str | None) -> bool:
    if not current_active_target:
        return False

    text = str(prompt or "").strip().lower()
    if not text:
        return False

    if re.search(r"\b\d{6}\b", text):
        return False

    contextual_followup_keywords = (
        "分析一下",
        "分析下",
        "再分析",
        "详细",
        "更详细",
        "展开",
        "继续",
        "接着说",
        "再说一下",
        "再讲一下",
        "讲一下",
        "说一下",
        "说明一下",
        "介绍一下",
        "情况",
        "信息",
        "概况",
        "解释一下",
        "详细点",
        "具体点",
        "多说一点",
        "补充一下",
        "还有呢",
        "没了",
    )
    return any(keyword in text for keyword in contextual_followup_keywords)
