from __future__ import annotations

import re
from typing import Any

import plotly.graph_objects as go
import streamlit as st

from src.shared.response_payload import build_response_payload_from_text


def _repair_broken_markdown_tables(text: str) -> str:
    value = str(text or "")
    value = re.sub(r"\|\s+\|\s*(第\d+期\s+\|)", r"|\n| \1", value)

    lines = value.splitlines()
    repaired_lines: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if "|" in line and stripped.count("|") >= 2:
            separator_tokens: list[str] = []
            lookahead = index + 1
            while lookahead < len(lines):
                next_line = lines[lookahead].strip()
                if not next_line:
                    lookahead += 1
                    continue
                if "|" in next_line and not re.fullmatch(r"[|:\-\s]+", next_line):
                    break
                if re.fullmatch(r"[|:\-\s]+", next_line):
                    separator_tokens.extend(re.findall(r"[:\-]+", next_line))
                    lookahead += 1
                    continue
                break

            if separator_tokens:
                repaired_lines.append(line)
                repaired_lines.append("| " + " | ".join(separator_tokens) + " |")
                index = lookahead
                continue

        repaired_lines.append(line)
        index += 1

    return "\n".join(repaired_lines)


def _normalize_inline_section_headings(text: str) -> str:
    value = str(text or "")
    section_labels = (
        "关键事实",
        "核心事实",
        "分析",
        "依据来源",
        "风险提示",
        "总结",
        "结论",
    )
    section_pattern = "|".join(
        re.escape(f"{label}:") + "|" + re.escape(f"{label}：")
        for label in section_labels
    )
    return re.sub(
        rf"(?<!^)(?<!\n)\s+(({section_pattern}))\s*(?=(?:\d+\.\s|[\-\*]\s|$|[A-Za-z0-9\u4e00-\u9fff]))",
        r"\n\n\1\n\n",
        value,
    )


def _normalize_inline_analysis_followups(text: str) -> str:
    value = str(text or "")
    value = re.sub(
        r"(\d{4}-\d{2}-\d{2}\s*\|\s*[^\n]+?)\s+(如果只看这个指标[^\n]+)",
        r"\1\n\n分析：\n\n\2",
        value,
    )
    return value


def _normalize_trend_snapshot_tail(text: str) -> str:
    value = str(text or "")
    trend_markers = (
        "\u8fd14\u671f\u8d70\u52bf",
        "\u8fd13\u671f\u8d70\u52bf",
        "\u5386\u53f2\u6570\u636e\u5982\u4e0b",
        "\u6700\u8fd1\u4e09\u671f",
        "\u8fd1\u4e09\u671f",
        "\u6700\u8fd1\u56db\u671f",
        "\u8fd1\u56db\u671f",
    )
    snapshot_marker = "\u5ba2\u89c2\u8d22\u52a1\u6570\u636e\u53ef\u5148\u770b\u8fd9\u51e0\u9879"
    if not any(marker in value for marker in trend_markers):
        return value
    if snapshot_marker not in value:
        return value

    value = re.sub(
        r"\n*\u6700\u65b0\u62a5\u544a\u671f[:：][\s\S]*?(?=(?:\n{2,}(?:\u5206\u6790|\u4f9d\u636e\u6765\u6e90|\u5f15\u7528\u6765\u6e90|Analysis|Sources)[:：])|$)",
        "",
        value,
        flags=re.DOTALL,
    )
    return value.rstrip()


def _normalize_text2sql_period_reply(content: str, payload: dict[str, Any]) -> dict[str, Any]:
    raw_text = str(content or "").strip()
    if not raw_text:
        return payload

    lines = raw_text.splitlines()
    if len(lines) < 2:
        return payload

    title = lines[0].strip()
    conclusion_line = lines[1].strip()
    if "历史指标查询" not in title or not conclusion_line.startswith("结论："):
        return payload

    body = "\n".join(lines[2:]).strip()
    body = re.sub(
        r"(\d{4}-\d{2}-\d{2}\s*\|\s*[^\n]+)\s+(如果只看这个指标)",
        r"\1\n\n分析：\n\n\2",
        body,
    )
    payload["summary"] = conclusion_line
    payload["body"] = body
    payload["raw_text"] = raw_text
    return payload


def _extract_compare_conclusion(lines: list[str], start_index: int) -> tuple[str, int]:
    if start_index >= len(lines):
        return "", start_index
    line = str(lines[start_index] or "").strip()
    if not line:
        return "", start_index
    if line.startswith("结论：") or line.startswith("结论:"):
        suffix = line.split("：", 1)[-1] if "：" in line else line.split(":", 1)[-1]
        if suffix.strip():
            return suffix.strip(), start_index + 1
        for index in range(start_index + 1, len(lines)):
            candidate = str(lines[index] or "").strip()
            if candidate:
                return candidate, index + 1
        return "", len(lines)
    return line, start_index + 1


def _looks_like_metric_compare_line(line: str) -> bool:
    value = str(line or "").strip()
    metric_markers = (
        "毛利率",
        "ROE",
        "负债率",
        "营收增长率",
        "归母净利润",
        "营业总收入",
        "经营现金流",
    )
    return "：" in value and any(marker in value for marker in metric_markers)


def _normalize_compare_reply_structure(text: str) -> str:
    value = str(text or "").strip()
    if not value or "关键指标对比如下" not in value or "结论" not in value:
        return value

    lines = [line.rstrip() for line in value.splitlines()]
    non_empty = [line.strip() for line in lines if line.strip()]
    if len(non_empty) < 3:
        return value

    intro_index = next((idx for idx, line in enumerate(lines) if "关键指标对比如下" in str(line)), None)
    conclusion_index = next((idx for idx, line in enumerate(lines) if str(line).strip().startswith("结论")), None)
    if intro_index is None or conclusion_index is None or conclusion_index <= intro_index:
        return value

    metric_lines = [str(line).strip() for line in lines[intro_index + 1 : conclusion_index] if str(line).strip()]
    metric_lines = [line for line in metric_lines if _looks_like_metric_compare_line(line)]
    if not metric_lines:
        return value

    conclusion_text, next_index = _extract_compare_conclusion(lines, conclusion_index)
    analysis_lines = [str(line).strip() for line in lines[next_index:] if str(line).strip()]

    rebuilt: list[str] = []
    if conclusion_text:
        rebuilt.append(f"结论：{conclusion_text}")
    else:
        rebuilt.append("结论：")
    rebuilt.append("")
    rebuilt.append("核心对比：")
    rebuilt.extend(metric_lines)
    if analysis_lines:
        rebuilt.append("")
        rebuilt.append("分析：")
        rebuilt.extend(analysis_lines)
    return "\n".join(rebuilt).strip()


def _normalize_track_list_reply_structure(text: str) -> str:
    value = str(text or "").strip()
    title_marker = "\u8d5b\u9053\u516c\u53f8\u5217\u8868\u67e5\u8be2"
    if not value or title_marker not in value or "\u5171\u547d\u4e2d" not in value:
        return value

    lines = [line.rstrip() for line in value.splitlines()]
    intro_index = next(
        (
            idx
            for idx, line in enumerate(lines)
            if "\u5171\u547d\u4e2d" in str(line) and "\u6392\u5e8f\u5982\u4e0b" in str(line)
        ),
        None,
    )
    if intro_index is None:
        return value

    sample_lines: list[str] = []
    analysis_lines: list[str] = []
    collecting_samples = False

    for raw_line in lines[intro_index + 1 :]:
        line = str(raw_line or "").strip()
        if not line:
            continue
        if " | " in line:
            collecting_samples = True
            sample_lines.append(line)
            continue
        if collecting_samples:
            analysis_lines.append(line)

    if not sample_lines:
        return value

    intro_line = str(lines[intro_index]).strip()
    match = re.search(r"(.+?)\u8d5b\u9053.*?\u5171\u547d\u4e2d\s*(\d+)\s*\u5bb6", intro_line)
    track_name = match.group(1).strip() if match else "\u5f53\u524d"
    company_count = match.group(2) if match else str(len(sample_lines))
    top_label = sample_lines[0].split("|", 1)[0].strip()
    second_label = sample_lines[1].split("|", 1)[0].strip() if len(sample_lines) >= 2 else ""

    rebuilt: list[str] = [
        f"\u7ed3\u8bba\uff1a\u5f53\u524d\u6837\u672c\u4e2d\uff0c{track_name}\u8d5b\u9053\u5171\u547d\u4e2d {company_count} \u5bb6\u4ee3\u8868\u516c\u53f8\uff0c"
        f"\u5176\u4e2d\u5e02\u503c\u9760\u524d\u7684\u662f {top_label}\u3002"
    ]
    rebuilt.append("")
    rebuilt.append("\u8d5b\u9053\u6837\u672c\uff1a")
    rebuilt.extend(sample_lines)
    rebuilt.append("")
    rebuilt.append("\u5206\u6790\uff1a")
    rebuilt.append(
        f"\u4ece\u5f53\u524d\u6837\u672c\u770b\uff0c{top_label} \u662f {track_name}\u8d5b\u9053\u91cc\u4f53\u91cf\u548c\u5173\u6ce8\u5ea6\u66f4\u9ad8\u7684\u516c\u53f8\uff0c"
        "\u9002\u5408\u4f5c\u4e3a\u8fd9\u4e2a\u8d5b\u9053\u7684\u9996\u8981\u89c2\u5bdf\u5bf9\u8c61\u3002"
    )
    if second_label:
        rebuilt.append(
            f"\u5982\u679c\u5148\u770b\u5934\u90e8\u6837\u672c\uff0c{top_label} \u4e0e {second_label} \u6784\u6210\u4e86\u8fd9\u4e2a\u8d5b\u9053\u5f53\u524d\u6700\u503c\u5f97"
            "\u4f18\u5148\u5bf9\u6bd4\u7684\u4e24\u5bb6\u516c\u53f8\uff0c\u540e\u7eed\u53ef\u4ee5\u987a\u7740\u6bdb\u5229\u7387\u3001ROE\u3001\u8425\u6536\u589e\u901f"
            "\u548c\u98ce\u9669\u70b9\u7ee7\u7eed\u5f80\u4e0b\u6bd4\u3002"
        )
    rebuilt.extend(analysis_lines)
    return "\n".join(rebuilt).strip()


def _looks_like_placeholder_stream_reply(text: str) -> bool:
    value = str(text or "").strip()
    if not value:
        return True
    placeholder_markers = (
        "我来为您",
        "我来帮您",
        "让我先获取",
        "首先让我获取",
        "我先获取",
        "我先查询",
        "我来为您获取",
        "我来为您详细分析",
        "我来为您详细说明",
    )
    fetch_markers = (
        "获取",
        "查询",
        "整理",
        "支撑分析",
        "来支撑分析",
        "进一步分析",
    )
    if len(value) <= 100 and any(marker in value for marker in placeholder_markers):
        return True
    if any(marker in value for marker in placeholder_markers) and any(marker in value for marker in fetch_markers):
        return True
    if any(marker in value for marker in placeholder_markers) and not any(
        keyword in value for keyword in ("结论", "营收", "净利润", "毛利率", "负债率", "ROE")
    ):
        return True
    return False


def _format_source_badge(source: str) -> str:
    source_key = str(source or "").strip().lower()
    label_map = {
        "text2sql": "text2sql",
        "market_intelligence": "market_intelligence",
        "decision_agent": "decision_agent",
        "legacy_text": "legacy_text",
        "unknown": "unknown",
    }
    return label_map.get(source_key, source_key or "unknown")


def fix_markdown_formatting(text: str) -> str:
    value = _normalize_track_list_reply_structure(
        _normalize_compare_reply_structure(
            _normalize_trend_snapshot_tail(
                _normalize_inline_analysis_followups(
                    _normalize_inline_section_headings(_repair_broken_markdown_tables(text))
                )
            )
        )
    )
    lines = value.splitlines()
    normalized_lines: list[str] = []

    for index, line in enumerate(lines):
        stripped = line.strip()
        prev_line = lines[index - 1] if index > 0 else ""

        if re.fullmatch(r"#{1,6}", stripped):
            continue

        if "|" in line:
            normalized_lines.append(line)
            continue

        if re.match(r"#{1,4}\s", stripped) and normalized_lines and normalized_lines[-1].strip():
            normalized_lines.append("")
            normalized_lines.append(line)
            continue

        is_horizontal_rule = bool(re.fullmatch(r"-{3,}\s*", stripped))
        if is_horizontal_rule and "|" not in prev_line and normalized_lines and normalized_lines[-1].strip():
            normalized_lines.append("")
            normalized_lines.append(line)
            continue

        if re.match(r"[\-\*]\s", stripped) and normalized_lines and normalized_lines[-1].strip():
            normalized_lines.append("")
            normalized_lines.append(line)
            continue

        normalized_lines.append(line)

    normalized = "\n".join(normalized_lines)
    normalized = re.sub(r"\n{4,}", "\n\n\n", normalized)
    return normalized.strip("\n")


def build_chart_figure(chart_data: dict, height: int = 350, compact: bool = False) -> go.Figure:
    fig = go.Figure()
    chart_type = chart_data.get("chart_type", "bar")

    for series in chart_data.get("datasets", []):
        if chart_type == "line":
            fig.add_trace(
                go.Scatter(
                    x=chart_data["x_labels"],
                    y=series["data"],
                    mode="lines+markers",
                    name=series["name"],
                )
            )
        else:
            fig.add_trace(
                go.Bar(
                    x=chart_data["x_labels"],
                    y=series["data"],
                    name=series["name"],
                )
            )

    layout_kwargs = {
        "template": "plotly_dark",
        "height": height,
    }
    if compact:
        layout_kwargs["margin"] = dict(l=5, r=5, t=15, b=5)
        layout_kwargs["legend"] = dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=9),
        )
    else:
        layout_kwargs["margin"] = dict(l=10, r=10, t=30, b=10)

    fig.update_layout(**layout_kwargs)
    return fig


def normalize_response_payload(
    content: str | None = None,
    payload: dict[str, Any] | None = None,
    source: str = "unknown",
) -> dict[str, Any]:
    if payload:
        normalized = dict(payload)
        normalized.setdefault("version", "1.0")
        normalized.setdefault("source", source)
        normalized.setdefault("summary", "")
        normalized.setdefault("body", "")
        normalized.setdefault("sections", [])
        normalized.setdefault("sources", [])
        normalized.setdefault("chart", None)
        if str(content or "").strip():
            content_payload = build_response_payload_from_text(
                str(content or ""),
                source=str(normalized.get("source") or source),
            )
            existing_body = str(normalized.get("body") or "").strip()
            existing_sections = normalized.get("sections") or []
            should_preserve_payload = bool(existing_body or existing_sections) and _looks_like_placeholder_stream_reply(
                content_payload.get("body", str(content or ""))
            )
            if should_preserve_payload:
                normalized.setdefault("raw_text", str(normalized.get("raw_text") or existing_body))
            else:
                normalized["raw_text"] = content_payload.get("raw_text", str(content or ""))
                normalized["body"] = content_payload.get("body", str(content or ""))
                normalized["summary"] = content_payload.get("summary", normalized.get("summary", ""))
                if not normalized.get("sources"):
                    normalized["sources"] = content_payload.get("sources", [])
                if not normalized.get("chart"):
                    normalized["chart"] = content_payload.get("chart")
                if str(normalized.get("source") or source) == "text2sql":
                    normalized = _normalize_text2sql_period_reply(str(content or ""), normalized)
        else:
            normalized.setdefault("raw_text", str(normalized.get("raw_text") or ""))
        return normalized
    return build_response_payload_from_text(str(content or ""), source=source)


def render_response_payload(payload: dict[str, Any]) -> None:
    normalized = normalize_response_payload(payload=payload)
    source = _format_source_badge(str(normalized.get("source") or "unknown"))
    summary = str(normalized.get("summary") or "").strip()
    body = fix_markdown_formatting(str(normalized.get("body") or "").strip())
    sections = normalized.get("sections") or []
    sources = [str(item).strip() for item in normalized.get("sources") or [] if str(item).strip()]
    chart = normalized.get("chart")

    show_summary = bool(summary)
    if show_summary and body:
        normalized_summary = " ".join(summary.split())
        normalized_body = " ".join(body.split())
        if normalized_body.startswith(normalized_summary):
            show_summary = False

    if show_summary:
        st.markdown(f"**{summary}**")

    if body:
        st.markdown(body)
    elif sections:
        for section in sections:
            title = str(section.get("title") or "").strip()
            section_body = fix_markdown_formatting(str(section.get("body") or "").strip())
            items = [str(item).strip() for item in section.get("items") or [] if str(item).strip()]
            if title:
                st.markdown(f"**{title}**")
            if section_body:
                st.markdown(section_body)
            if items:
                for item in items:
                    st.markdown(f"- {item}")

    if chart:
        st.session_state.latest_chart_data = chart
        st.plotly_chart(build_chart_figure(chart), use_container_width=True)

    if sources:
        with st.expander("引用来源", expanded=False):
            for source in sources:
                st.markdown(f"- {source}")


def render_message_with_charts(content: str) -> None:
    payload = build_response_payload_from_text(content, source="legacy_text")
    render_response_payload(payload)


def render_latest_chart_card(chart_data: dict | None) -> None:
    if not chart_data:
        return

    st.markdown(
        (
            '<div class="cockpit-card">'
            '<div class="panel-kicker">洞察快照</div>'
            '<span class="chain-title">最新分析视图</span>'
            f'<span style="font-size:0.78rem !important; color:rgba(203,213,225,0.72) !important; '
            f'display:block; margin-top:2px; line-height:1.5;">{chart_data.get("title", "数据可视化")}</span>'
        ),
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        build_chart_figure(chart_data, height=280, compact=True),
        use_container_width=True,
        key="live_lab_chart",
    )
    st.markdown("</div>", unsafe_allow_html=True)


def render_response_payload(payload: dict[str, Any]) -> None:
    normalized = normalize_response_payload(payload=payload)
    source = _format_source_badge(str(normalized.get("source") or "unknown"))
    summary = str(normalized.get("summary") or "").strip()
    body = fix_markdown_formatting(str(normalized.get("body") or "").strip())
    sections = normalized.get("sections") or []
    sources = [str(item).strip() for item in normalized.get("sources") or [] if str(item).strip()]
    chart = normalized.get("chart")

    show_summary = bool(summary)
    if show_summary and body:
        normalized_summary = " ".join(summary.split())
        normalized_body = " ".join(body.split())
        if normalized_body.startswith(normalized_summary):
            show_summary = False

    if show_summary:
        st.markdown(f"**{summary}**")

    if body:
        st.markdown(body)
    elif sections:
        for section in sections:
            title = str(section.get("title") or "").strip()
            section_body = fix_markdown_formatting(str(section.get("body") or "").strip())
            items = [str(item).strip() for item in section.get("items") or [] if str(item).strip()]
            if title:
                st.markdown(f"**{title}**")
            if section_body:
                st.markdown(section_body)
            if items:
                for item in items:
                    st.markdown(f"- {item}")

    if chart:
        st.session_state.latest_chart_data = chart
        st.plotly_chart(build_chart_figure(chart), use_container_width=True)

    if sources:
        with st.expander("引用来源", expanded=False):
            for source in sources:
                st.markdown(f"- {source}")
