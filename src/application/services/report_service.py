from __future__ import annotations

import html
import json
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from agent_engine import DoubaoAgent


class ReportService:
    MAX_CONTEXT_MESSAGES = 24
    MAX_CONTEXT_ROUNDS = 10
    SOURCE_CONTEXT_PATTERN = re.compile(r"(来源|数据来源|资料来源|参考|引自|choice|wind|同花顺|东方财富|雪球|巨潮|ifind)", re.IGNORECASE)
    COMPANY_SPLIT_PATTERN = re.compile(r"(?:相较于|相比|对比|强于|弱于|优于|劣于|高于|低于|以及|与|和|及|、|的)")
    COMPANY_STOPWORDS = (
        "盈利能力",
        "分析主体",
        "当前分析",
        "核心赛道",
        "核心研判",
        "结论",
        "趋势",
        "来源",
        "财报",
        "年报",
        "季报",
        "数据",
        "报告",
        "行业",
        "赛道",
        "显著",
        "主体",
        "研判",
        "对比",
    )
    PDF_BROWSER_CANDIDATES = (
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    )

    def __init__(self):
        self.agent = DoubaoAgent()

    def _clean_text(self, value: Any) -> str:
        text = str(value or "")
        text = re.sub(r"\[CHART_DATA\][\s\S]*?\[/CHART_DATA\]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _message_text(self, message: dict[str, Any]) -> str:
        payload = message.get("payload")
        candidate_texts: list[Any] = []
        if isinstance(payload, dict):
            candidate_texts.extend(
                [
                    payload.get("body"),
                    payload.get("summary"),
                    payload.get("raw_text"),
                ]
            )
        candidate_texts.append(message.get("content"))

        for candidate in candidate_texts:
            cleaned = self._clean_text(candidate)
            if cleaned:
                return cleaned
        return ""

    def _format_role_label(self, role: str) -> str:
        return {"user": "用户提问", "assistant": "系统回答", "system": "系统设定"}.get(role, role or "消息")

    def _build_context(self, messages: list[dict[str, Any]]) -> str:
        recent_messages = messages[-self.MAX_CONTEXT_MESSAGES :]
        lines: list[str] = []
        for index, message in enumerate(recent_messages, start=1):
            content = self._message_text(message)
            if not content:
                continue
            if len(content) > 900:
                content = f"{content[:900]}……"
            role_label = self._format_role_label(str(message.get("role") or ""))
            lines.append(f"{index}. {role_label}：{content}")
        return "\n".join(lines)

    def _summarize_excerpt(self, text: str, limit: int = 140) -> str:
        cleaned = self._clean_text(text)
        if len(cleaned) <= limit:
            return cleaned
        return f"{cleaned[:limit]}……"

    def _build_conversation_rounds(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rounds: list[dict[str, Any]] = []
        current_round_messages: list[dict[str, Any]] = []
        current_user_prompt = ""
        assistant_parts: list[str] = []

        def flush_round() -> None:
            nonlocal current_round_messages, current_user_prompt, assistant_parts
            if not current_round_messages:
                return
            assistant_text = " ".join(part for part in assistant_parts if part).strip()
            rounds.append(
                {
                    "index": len(rounds) + 1,
                    "messages": current_round_messages,
                    "user_prompt": current_user_prompt or "本轮未识别到明确提问",
                    "assistant_summary": self._summarize_excerpt(
                        assistant_text or "本轮暂未形成明确回答内容。",
                        limit=180,
                    ),
                }
            )
            current_round_messages = []
            current_user_prompt = ""
            assistant_parts = []

        for message in messages:
            role = str(message.get("role") or "")
            message_text = self._message_text(message)
            if role == "user":
                if current_round_messages:
                    flush_round()
                current_round_messages = [message]
                current_user_prompt = self._summarize_excerpt(message_text, limit=90)
                assistant_parts = []
                continue

            if not current_round_messages:
                continue

            current_round_messages.append(message)
            if role == "assistant" and message_text:
                assistant_parts.append(message_text)

        flush_round()
        return rounds

    def _build_round_digest(self, messages: list[dict[str, Any]]) -> str:
        rounds = self._build_conversation_rounds(messages)
        if not rounds:
            return ""

        lines: list[str] = []
        for round_item in rounds[-self.MAX_CONTEXT_ROUNDS :]:
            lines.append(f"第{round_item['index']}轮问题：{round_item['user_prompt']}")
            lines.append(f"第{round_item['index']}轮结论：{round_item['assistant_summary']}")
        return "\n".join(lines)

    def _extract_json_block(self, raw_text: str) -> dict[str, Any] | None:
        cleaned = str(raw_text or "").strip()
        if not cleaned:
            return None

        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, flags=re.IGNORECASE)
        if fenced:
            cleaned = fenced.group(1).strip()

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            return None

        candidate = cleaned[start : end + 1]
        try:
            parsed = json.loads(candidate)
        except Exception:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _safe_string(self, value: Any, fallback: str = "") -> str:
        if value is None:
            return fallback
        text = self._clean_text(value)
        return text or fallback

    def _safe_list(self, value: Any, *, limit: int, fallback: list[str]) -> list[str]:
        if isinstance(value, list):
            items = [self._safe_string(item) for item in value]
            filtered = [item for item in items if item]
            if filtered:
                return filtered[:limit]
        return fallback[:limit]

    def _safe_sections(self, value: Any) -> list[dict[str, Any]]:
        sections: list[dict[str, Any]] = []
        if not isinstance(value, list):
            return sections

        for item in value[:6]:
            if not isinstance(item, dict):
                continue
            heading = self._safe_string(item.get("heading"))
            if not heading:
                continue
            sections.append(
                {
                    "heading": heading,
                    "lead": self._safe_string(item.get("lead")),
                    "paragraphs": self._safe_list(
                        item.get("paragraphs"),
                        limit=4,
                        fallback=[],
                    ),
                    "bullets": self._safe_list(
                        item.get("bullets"),
                        limit=5,
                        fallback=[],
                    ),
                }
            )
        return sections

    def _normalize_company_name(self, raw_name: str) -> str:
        candidate = self._clean_text(raw_name)
        if not candidate:
            return ""

        candidate = re.sub(
            r"^(当前分析主体为|当前研究主体为|研究主体为|分析主体为|主体为|当前主体为|公司为|企业为|其中|关于)",
            "",
            candidate,
        ).strip("：:，,。;； ")

        parts = [
            item.strip("：:，,。;； ")
            for item in self.COMPANY_SPLIT_PATTERN.split(candidate)
            if item.strip("：:，,。;； ")
        ]
        if parts:
            candidate = parts[-1]

        if not candidate or len(candidate) < 2 or len(candidate) > 18:
            return ""
        if not re.search(r"[\u4e00-\u9fa5A-Za-z]", candidate):
            return ""
        if any(stopword in candidate for stopword in self.COMPANY_STOPWORDS):
            return ""
        return candidate

    def _extract_target_mentions_from_text(self, text: str) -> list[str]:
        content = self._clean_text(text)
        if not content:
            return []

        mentions: list[str] = []
        pattern = re.compile(r"([A-Za-z0-9\u4e00-\u9fa5·]{2,30})\s*[（(]\s*(\d{6})(?:\.[A-Za-z]{2})?\s*[)）]")
        for match in pattern.finditer(content):
            prefix = content[max(0, match.start() - 12) : match.start()]
            if self.SOURCE_CONTEXT_PATTERN.search(prefix):
                continue

            company_name = self._normalize_company_name(match.group(1))
            code = match.group(2)
            if not company_name:
                continue

            normalized = f"{company_name}({code})"
            if normalized not in mentions:
                mentions.append(normalized)
        return mentions

    def _extract_target_mentions(self, messages: list[dict[str, Any]]) -> list[str]:
        mentions: list[str] = []
        for message in messages:
            payload = message.get("payload")
            candidate_texts = [
                self._message_text(message),
                self._safe_string(payload.get("body")) if isinstance(payload, dict) else "",
                self._safe_string(payload.get("summary")) if isinstance(payload, dict) else "",
            ]
            for text in candidate_texts:
                for normalized in self._extract_target_mentions_from_text(text):
                    if normalized not in mentions:
                        mentions.append(normalized)
        return mentions[:6]

    def _dedupe_labels(self, labels: list[str]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for label in labels:
            normalized = self._safe_string(label)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)
        return deduped

    def _resolve_pdf_browser(self) -> Path | None:
        for candidate in self.PDF_BROWSER_CANDIDATES:
            if candidate.exists():
                return candidate
        return None

    def _extract_source_notes(self, messages: list[dict[str, Any]]) -> list[str]:
        notes: list[str] = []
        for message in messages:
            payload = message.get("payload")
            if not isinstance(payload, dict):
                continue
            sources = payload.get("sources")
            if isinstance(sources, list):
                for source in sources:
                    source_text = self._safe_string(source)
                    if source_text and source_text not in notes:
                        notes.append(source_text)
        return notes[:6]

    def _fallback_payload(
        self,
        messages: list[dict[str, Any]],
        generated_at: datetime,
        active_target: str | None,
    ) -> dict[str, Any]:
        cleaned_messages = [
            {
                "role": str(message.get("role") or ""),
                "content": self._message_text(message),
            }
            for message in messages
            if self._message_text(message)
        ]
        user_messages = [item["content"] for item in cleaned_messages if item["role"] == "user"]
        assistant_messages = [item["content"] for item in cleaned_messages if item["role"] == "assistant"]
        latest_user = user_messages[-1] if user_messages else "当前会话围绕企业研究主题展开。"
        latest_assistant = assistant_messages[-1] if assistant_messages else "当前会话中尚未沉淀出足够充分的系统结论。"
        prior_assistant = assistant_messages[-2] if len(assistant_messages) >= 2 else ""
        mentioned_targets = self._extract_target_mentions(messages)
        source_notes = self._extract_source_notes(messages)
        target_label = self._safe_string(active_target, "当前会话主题")

        summary_points = [
            f"本报告基于 {generated_at.strftime('%Y年%m月%d日')} 前的会话内容整理，核心分析对象为 {target_label}。",
            "报告内容优先复核当前会话中已出现的财务、对比与风险信息，不额外扩展未经确认的数据结论。",
            f"当前研究范围主要围绕“{latest_user[:42]}”展开，重点保留对经营、财务与赛道位置的判断。",
        ]
        if mentioned_targets:
            summary_points.append(f"会话中涉及的关联标的包括：{'、'.join(mentioned_targets)}。")

        sections = [
            {
                "heading": "研究范围与任务边界",
                "lead": "本节用于说明本次报告的议题来源与信息边界。",
                "paragraphs": [
                    f"当前会话最近一轮核心问题为：{latest_user}",
                    "本报告仅基于本次会话中已经形成的分析材料进行整理，不额外引入未核实的外部论据。",
                ],
                "bullets": [
                    "若后续需要形成正式投委材料，建议在当前版本基础上继续补充原始财报、公告与行业公开资料。",
                ],
            },
            {
                "heading": "企业运营评估与问题诊断",
                "lead": "本节聚焦经营表现、核心短板与管理层需要重点追踪的问题。",
                "paragraphs": [
                    latest_assistant,
                    prior_assistant or "当前会话中尚未形成第二组可直接复用的结论段落。",
                ],
                "bullets": [
                    "建议围绕盈利能力、增长质量、现金流、资产负债结构与运营效率继续复核。",
                ],
            },
            {
                "heading": "风险与机会洞察",
                "lead": "本节用于区分当前会话中已提及的下行风险、上行机会与后续观察变量。",
                "paragraphs": [
                    "若当前会话已经出现风险、景气度、竞争格局或修复逻辑等判断，应在正式版本中进一步量化其影响强度与兑现条件。",
                ],
                "bullets": [
                    "识别业绩承压、价格战、政策扰动、需求放缓或资本开支不及预期等风险因子。",
                    "识别盈利修复、份额提升、产品升级、渠道改善或行业景气回升等机会因子。",
                ],
            },
            {
                "heading": "来源依据与结论归因",
                "lead": "本节用于说明当前结论的来源线索、逻辑拆解与后续核验方向。",
                "paragraphs": [
                    "本报告优先基于当前会话中已经形成的内容进行整理，若需进一步形成对外版本，仍需结合原始财报、公告、研究报告与公开数据库核验。",
                ],
                "bullets": source_notes
                or [
                    "当前会话暂未沉淀出明确的来源清单，建议后续补充财报、公告与行业公开材料。",
                ],
            },
            {
                "heading": "后续建议动作",
                "lead": "若需要提升报告严谨度，建议在下一轮补齐以下资料与分析动作。",
                "paragraphs": [
                    "建议补充最新一期财务报表原始数据、同行可比样本明细以及关键经营披露，以提高结论可追溯性。",
                ],
                "bullets": [
                    "补充年报或季报口径的核心财务指标。",
                    "补充同赛道横向样本的时间口径与披露日期。",
                    "补充风险因素的定量化描述与建议动作。",
                ],
            },
        ]

        return {
            "title": f"{target_label}研究报告",
            "subtitle": "基于当前会话材料整理的企业级研究摘要",
            "summary_points": summary_points[:4],
            "sections": sections,
            "risk_items": [
                "当前版本主要基于会话摘要整理，若会话本身存在数据缺口，则报告结论也会受到约束。",
                "若关键财务口径尚未披露或尚未同步到结构化数据源，部分判断可能仍停留在上一报告期。",
            ],
            "watch_points": [
                "跟踪最新财报与披露日期是否完成同步。",
                "跟踪同赛道可比样本是否出现新的结构性变化。",
            ],
            "closing": "本报告适合作为管理层讨论、投研例会或下一轮深度尽调前的内部基础稿。",
        }

    def _build_prompt(
        self,
        context: str,
        generated_at: datetime,
        active_target: str | None,
        messages: list[dict[str, Any]],
    ) -> str:
        target_label = self._safe_string(active_target, "当前会话主题")
        mentioned_targets = self._extract_target_mentions(messages)
        mentioned_text = "、".join(mentioned_targets) if mentioned_targets else "当前会话未明确出现其他可识别关联标的"
        return f"""
你是大型机构研究部负责人，请基于以下会话材料，为 {target_label} 生成一份正式、克制、具有企业研究部气质的中文报告草案。

当前生成时间：{generated_at.strftime("%Y-%m-%d %H:%M")}
关联标的：{mentioned_text}

请严格输出 JSON，不要输出 Markdown，不要输出代码块，不要补充额外解释。

JSON 结构如下：
{{
  "title": "报告标题",
  "subtitle": "副标题",
  "summary_points": ["3到5条执行摘要"],
  "sections": [
    {{
      "heading": "一级章节标题",
      "lead": "章节导语",
      "paragraphs": ["1到3段正文"],
      "bullets": ["1到5条要点"]
    }}
  ],
  "risk_items": ["2到4条风险提示"],
  "watch_points": ["2到4条后续观察点"],
  "closing": "收束性结论"
}}

写作要求：
1. 只基于当前会话里已经出现的信息进行整理和归纳，不要伪造来源，不要编造新的财务数字。
2. 语气要像大型企业研究院、投研中心或战略发展部正式出具的内部研究材料，避免口号式表达。
3. 结构要完整、清晰、专业，标题要简洁有力，正文要有判断、有依据、有边界。
4. 如果信息不足，要明确写出“依据当前会话信息暂无法进一步确认”之类的表述，不要硬编。
5. 章节内容应尽量覆盖：企业运营评估与问题诊断、风险与机会洞察、来源依据与结论归因、建议动作。
6. 如果当前会话中存在来源线索、数据来源或图表依据，请在章节中体现“来源依据”或“归因逻辑”，不要只给结果。
7. 全文必须为中文。

会话材料：
{context}
""".strip()

    def _fallback_payload_v2(
        self,
        messages: list[dict[str, Any]],
        generated_at: datetime,
        active_target: str | None,
    ) -> dict[str, Any]:
        cleaned_messages = [
            {
                "role": str(message.get("role") or ""),
                "content": self._message_text(message),
            }
            for message in messages
            if self._message_text(message)
        ]
        rounds = self._build_conversation_rounds(messages)
        displayed_rounds = rounds[: self.MAX_CONTEXT_ROUNDS]
        user_messages = [item["content"] for item in cleaned_messages if item["role"] == "user"]
        assistant_messages = [item["content"] for item in cleaned_messages if item["role"] == "assistant"]
        latest_user = user_messages[-1] if user_messages else "当前未提取到明确的用户问题。"
        latest_assistant = assistant_messages[-1] if assistant_messages else "当前未提取到完整的系统结论。"
        prior_assistant = assistant_messages[-2] if len(assistant_messages) >= 2 else ""
        mentioned_targets = self._extract_target_mentions(messages)
        source_notes = self._extract_source_notes(messages)
        target_label = self._safe_string(active_target, "当前研究主体")
        round_count = len(rounds)
        message_count = len(cleaned_messages)

        prompt_preview = "；".join(
            round_item["user_prompt"] for round_item in displayed_rounds[:4] if round_item.get("user_prompt")
        )
        round_bullets = [
            f"第{round_item['index']}轮：围绕“{round_item['user_prompt']}”展开，形成结论“{round_item['assistant_summary']}”。"
            for round_item in displayed_rounds
        ]
        if not round_bullets:
            round_bullets = ["当前没有形成可供归档的多轮研究纪要。"]

        convergence_bullets: list[str] = []
        if rounds:
            convergence_bullets.append(
                f"从轮次推进看，研究议题由“{rounds[0]['user_prompt']}”逐步延伸至“{rounds[-1]['user_prompt']}”。"
            )
        if len(rounds) >= 2:
            convergence_bullets.append(
                f"最近两轮输出显示，系统判断已从“{rounds[-2]['assistant_summary']}”收敛至“{rounds[-1]['assistant_summary']}”。"
            )
        if mentioned_targets:
            convergence_bullets.append(f"本次报告涉及的重点主体包括：{'、'.join(mentioned_targets)}。")
        if not convergence_bullets:
            convergence_bullets.append("当前对话尚未形成足够多的轮次，暂以已生成内容作为阶段性结论。")

        evidence_bullets = source_notes or [
            "当前消息中未附带结构化来源字段，正式归档前建议补充财报、公告或数据库截图。"
        ]

        summary_points = [
            f"本报告纳入 {round_count or 1} 轮对话、{message_count} 条有效消息，覆盖范围不只限于最新一轮。",
            f"当前研究主体为 {target_label}，最近一轮问题聚焦于“{self._summarize_excerpt(latest_user, 44)}”。",
            f"对话主线已形成阶段性判断：{self._summarize_excerpt(latest_assistant, 70)}",
            f"前序轮次关注点包括：{prompt_preview or '暂未提取到稳定的问题主线。'}",
        ]
        if source_notes:
            summary_points.append(f"可追溯来源线索包括：{'；'.join(source_notes[:3])}。")

        sections = [
            {
                "heading": "报告范围与任务界定",
                "lead": "本报告基于已选中的多轮对话自动归档，目标是将研究过程重组为正式、可追溯的输出。",
                "paragraphs": [
                    f"本次归档时间为 {generated_at.strftime('%Y-%m-%d %H:%M')}，研究对象定位为 {target_label}。",
                    f"对话中最新问题为“{latest_user}”，但报告已同步纳入此前轮次中的关键问题、分析过程与阶段性结论。",
                ],
                "bullets": [
                    f"纳入轮次：{round_count or 1} 轮",
                    f"纳入消息：{message_count} 条",
                    f"识别主体：{'、'.join(mentioned_targets) if mentioned_targets else target_label}",
                ],
            },
            {
                "heading": "分轮研究纪要",
                "lead": "以下内容按轮次回溯本次研究的推进过程，用于避免报告仅保留最新一轮结果。",
                "paragraphs": [
                    "系统已按用户提问与助手回答自动切分对话轮次，并提炼每一轮的主题与结论。",
                    "若前后轮次存在主题扩展、观点修正或结论收敛，均应在此处体现。",
                ],
                "bullets": round_bullets[:8],
            },
            {
                "heading": "关键信号与结论收敛",
                "lead": "从多轮输出看，当前结论并非单点回答，而是逐步汇总形成的阶段性判断。",
                "paragraphs": [
                    latest_assistant,
                    prior_assistant or "前序轮次的系统结论已并入分轮纪要中，用于辅助理解判断如何逐步形成。",
                ],
                "bullets": convergence_bullets[:5],
            },
            {
                "heading": "证据基础与引用线索",
                "lead": "报告应尽量保留来源提示，便于后续复核与正式交付。",
                "paragraphs": [
                    "当前版本优先使用消息 payload 中的来源线索，并结合正文中的主体识别信息进行归档。",
                    "若后续需要形成正式投资备忘录或高管汇报稿，建议补充披露日期、报告期及原始数据口径。",
                ],
                "bullets": evidence_bullets[:5],
            },
            {
                "heading": "后续跟踪建议",
                "lead": "在多轮对话已经形成主线的基础上，下一步应继续向数据化、证据化和正式化推进。",
                "paragraphs": [
                    "建议优先补充与当前结论直接相关的最新财务、行业对标、公告及经营数据，以增强报告的严谨性。",
                    "如果后续继续新增轮次，本报告应以相同逻辑追加归档，而不是被最新一轮完全覆盖。",
                ],
                "bullets": [
                    "补充最新披露日期与报告期，校验关键口径是否一致。",
                    "对重要判断增加来源说明、同比环比变化和同业对标。",
                    "在正式发布前复核是否存在前后轮次结论冲突或证据不足的问题。",
                ],
            },
        ]

        return {
            "title": f"{target_label}研究报告",
            "subtitle": f"基于 {round_count or 1} 轮对话自动生成，已合并历史轮次内容而非仅保留最新回复",
            "summary_points": summary_points[:5],
            "sections": sections,
            "risk_items": [
                "若前序轮次中的数据口径与最新轮次不同，而报告未进一步核验原始来源，可能影响结论一致性。",
                "当对话缺少结构化来源或披露日期时，报告只能形成阶段性判断，正式使用前仍需人工复核。",
            ],
            "watch_points": [
                "持续跟踪后续新增轮次是否引入新的研究问题、数据修正或结论变化。",
                "重点关注与核心判断直接相关的最新财报、公告、业绩快报和行业对标数据。",
            ],
            "closing": f"本报告已合并纳入 {round_count or 1} 轮对话中的重点议题与分析结论，后续若继续扩展对话，应在此基础上增量更新而不是覆盖历史研究过程。",
        }

    def _build_prompt_v2(
        self,
        context: str,
        generated_at: datetime,
        active_target: str | None,
        messages: list[dict[str, Any]],
    ) -> str:
        target_label = self._safe_string(active_target, "当前研究主体")
        mentioned_targets = self._extract_target_mentions(messages)
        mentioned_text = "、".join(mentioned_targets) if mentioned_targets else "未稳定识别到明确主体"
        source_notes = self._extract_source_notes(messages)
        source_text = "；".join(source_notes[:6]) if source_notes else "当前消息未附带结构化来源字段"
        rounds = self._build_conversation_rounds(messages)
        round_count = len(rounds)
        round_digest = self._build_round_digest(messages) or "暂无可用的轮次摘要。"

        return f"""
你是一名中文投研报告撰写专家，需要把多轮对话整理成正式、清晰、适合企业场景归档的研究报告。

任务要求：
1. 必须综合所有已纳入的对话轮次，不得只围绕最新一轮作答。
2. 如果前后轮次讨论了不同问题，必须体现议题如何扩展、结论如何收敛、判断是否发生修正。
3. 报告语言要正式、简洁、专业，不要照抄聊天口吻。
4. 所有标题、段落和要点都必须使用中文。
5. 只输出一个 JSON 对象，不要输出 Markdown，不要输出代码块，不要补充解释。
6. summary_points 输出 3 至 5 条。
7. sections 输出 4 至 6 个板块，每个板块包含 heading、lead、paragraphs、bullets。
8. sections 中必须至少有一个板块明确体现“多轮研究纪要”或“研究过程回顾”，以证明已经纳入历史轮次。
9. 如果证据不足，可以写“待进一步核验”，但不能忽略前序轮次。

报告参数：
- 研究主体：{target_label}
- 生成时间：{generated_at.strftime("%Y-%m-%d %H:%M")}
- 纳入轮次：{round_count or 1} 轮
- 识别主体：{mentioned_text}
- 来源线索：{source_text}

分轮摘要：
{round_digest}

对话上下文：
{context}

请严格按照以下 JSON 结构返回：
{{
  "title": "报告标题",
  "subtitle": "报告副标题",
  "summary_points": ["要点1", "要点2", "要点3"],
  "sections": [
    {{
      "heading": "章节标题",
      "lead": "章节导语",
      "paragraphs": ["段落1", "段落2"],
      "bullets": ["要点1", "要点2"]
    }}
  ],
  "risk_items": ["风险1", "风险2"],
  "watch_points": ["关注点1", "关注点2"],
  "closing": "结尾总结"
}}
""".strip()

    def _request_report_payload(
        self,
        messages: list[dict[str, Any]],
        generated_at: datetime,
        active_target: str | None,
    ) -> dict[str, Any]:
        context = self._build_context(messages)
        if not context:
            return self._fallback_payload_v2(messages, generated_at, active_target)

        prompt = self._build_prompt_v2(context, generated_at, active_target, messages)
        try:
            response = self.agent.client.chat.completions.create(
                model=self.agent.model_endpoint,
                messages=[
                    {"role": "system", "content": self.agent.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.25,
                max_tokens=4096,
            )
            raw_content = response.choices[0].message.content
            parsed = self._extract_json_block(raw_content)
            if parsed:
                return parsed
        except Exception:
            pass
        return self._fallback_payload_v2(messages, generated_at, active_target)

    def _normalize_payload(
        self,
        payload: dict[str, Any],
        messages: list[dict[str, Any]],
        generated_at: datetime,
        active_target: str | None,
    ) -> dict[str, Any]:
        fallback = self._fallback_payload_v2(messages, generated_at, active_target)
        summary_points = self._safe_list(
            payload.get("summary_points"),
            limit=5,
            fallback=fallback["summary_points"],
        )
        sections = self._safe_sections(payload.get("sections")) or fallback["sections"]
        risk_items = self._safe_list(
            payload.get("risk_items"),
            limit=4,
            fallback=fallback["risk_items"],
        )
        watch_points = self._safe_list(
            payload.get("watch_points"),
            limit=4,
            fallback=fallback["watch_points"],
        )
        return {
            "title": self._safe_string(payload.get("title"), fallback["title"]),
            "subtitle": self._safe_string(payload.get("subtitle"), fallback["subtitle"]),
            "summary_points": summary_points,
            "sections": sections,
            "risk_items": risk_items,
            "watch_points": watch_points,
            "closing": self._safe_string(payload.get("closing"), fallback["closing"]),
        }

    def _render_badges(self, badges: list[str]) -> str:
        if not badges:
            return ""
        return "".join(
            f'<span class="rs-chip">{html.escape(item)}</span>'
            for item in badges
            if item
        )

    def _render_list(self, items: list[str], class_name: str) -> str:
        if not items:
            return ""
        list_items = "".join(f"<li>{html.escape(item)}</li>" for item in items if item)
        return f'<ul class="{class_name}">{list_items}</ul>'

    def _render_sections(self, sections: list[dict[str, Any]]) -> str:
        rendered_sections: list[str] = []
        for index, section in enumerate(sections, start=1):
            paragraphs = "".join(
                f'<p class="rs-section__paragraph">{html.escape(paragraph)}</p>'
                for paragraph in section.get("paragraphs", [])
                if paragraph
            )
            bullets = self._render_list(section.get("bullets", []), "rs-bullet-list")
            rendered_sections.append(
                f"""
                <section class="rs-section">
                  <div class="rs-section__index">{index:02d}</div>
                  <div class="rs-section__body">
                    <div class="rs-section__eyebrow">核心章节</div>
                    <h2>{html.escape(section.get("heading", ""))}</h2>
                    <p class="rs-section__lead">{html.escape(section.get("lead", ""))}</p>
                    {paragraphs}
                    {bullets}
                  </div>
                </section>
                """
            )
        return "".join(rendered_sections)

    def _render_html(
        self,
        payload: dict[str, Any],
        generated_at: datetime,
        active_target: str | None,
        messages: list[dict[str, Any]],
    ) -> str:
        target_label = self._safe_string(active_target, "当前会话主题")
        mentioned_targets = self._extract_target_mentions(messages)
        badges = self._dedupe_labels([target_label, *mentioned_targets[:4]])
        generated_text = generated_at.strftime("%Y年%m月%d日 %H:%M")
        summary_cards = "".join(
            f'<article class="rs-summary-card"><span class="rs-summary-card__label">执行摘要</span><p>{html.escape(point)}</p></article>'
            for point in payload["summary_points"]
        )
        risk_html = self._render_list(payload["risk_items"], "rs-bullet-list rs-bullet-list--risk")
        watch_html = self._render_list(payload["watch_points"], "rs-bullet-list")

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{html.escape(payload["title"])}</title>
    <style>
      @page {{
        size: A4;
        margin: 14mm 12mm 16mm;
      }}

      :root {{
        --navy-950: #08111d;
        --navy-900: #0d1b2a;
        --navy-700: #28435f;
        --slate-100: #f5f7fa;
        --slate-200: #e7ebf1;
        --slate-300: #d5dce5;
        --slate-500: #6b7785;
        --slate-700: #314052;
        --text-main: #162332;
        --text-soft: #556579;
        --gold: #b58a4f;
        --gold-soft: rgba(181, 138, 79, 0.16);
        --line: rgba(17, 24, 39, 0.08);
      }}

      * {{
        box-sizing: border-box;
      }}

      html, body {{
        margin: 0;
        padding: 0;
        background:
          radial-gradient(circle at top left, rgba(181, 138, 79, 0.08), transparent 24%),
          linear-gradient(180deg, #edf1f6, #e7edf4);
        color: var(--text-main);
        font-family: "PingFang SC", "Hiragino Sans GB", "Noto Sans SC", "Microsoft YaHei UI", sans-serif;
      }}

      body {{
        padding: 40px 24px 72px;
      }}

      .rs-document {{
        width: min(1180px, 100%);
        margin: 0 auto;
        background: rgba(255, 255, 255, 0.94);
        border: 1px solid rgba(13, 27, 42, 0.08);
        border-radius: 30px;
        box-shadow: 0 32px 80px rgba(15, 23, 42, 0.14);
        overflow: hidden;
      }}

      .rs-cover {{
        position: relative;
        padding: 44px 48px 38px;
        background:
          radial-gradient(circle at top right, rgba(181, 138, 79, 0.18), transparent 26%),
          linear-gradient(135deg, #0a1624, #12263b 58%, #17324b);
        color: #f7f4ee;
      }}

      .rs-cover::after {{
        content: "";
        position: absolute;
        inset: 0;
        background:
          linear-gradient(90deg, transparent, rgba(255,255,255,0.04), transparent),
          repeating-linear-gradient(
            90deg,
            transparent 0,
            transparent 52px,
            rgba(255,255,255,0.03) 52px,
            rgba(255,255,255,0.03) 53px
          );
        pointer-events: none;
      }}

      .rs-cover__top {{
        position: relative;
        z-index: 1;
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 24px;
      }}

      .rs-brand {{
        display: grid;
        gap: 8px;
      }}

      .rs-brand__eyebrow {{
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.22em;
        text-transform: uppercase;
        color: rgba(255, 245, 230, 0.78);
      }}

      .rs-brand__name {{
        font-family: "Songti SC", "STSong", "Noto Serif SC", serif;
        font-size: 42px;
        line-height: 1.12;
        letter-spacing: 0.02em;
        margin: 0;
        font-weight: 700;
      }}

      .rs-brand__subtitle {{
        margin: 0;
        max-width: 760px;
        font-size: 16px;
        line-height: 1.85;
        color: rgba(243, 240, 234, 0.84);
      }}

      .rs-stamp {{
        min-width: 208px;
        padding: 16px 18px;
        border-radius: 18px;
        border: 1px solid rgba(255,255,255,0.14);
        background: rgba(255,255,255,0.06);
        backdrop-filter: blur(10px);
      }}

      .rs-stamp span {{
        display: block;
        font-size: 11px;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: rgba(255, 244, 229, 0.7);
        margin-bottom: 8px;
      }}

      .rs-stamp strong {{
        display: block;
        font-size: 15px;
        line-height: 1.7;
        font-weight: 600;
      }}

      .rs-cover__meta {{
        position: relative;
        z-index: 1;
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 26px;
      }}

      .rs-chip {{
        display: inline-flex;
        align-items: center;
        padding: 8px 14px;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.12);
        background: rgba(255,255,255,0.06);
        color: rgba(255,248,239,0.92);
        font-size: 13px;
      }}

      .rs-main {{
        padding: 34px 42px 44px;
      }}

      .rs-panel {{
        border: 1px solid var(--line);
        border-radius: 24px;
        padding: 26px 28px;
        background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(248,250,252,0.92));
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.7);
      }}

      .rs-panel + .rs-panel {{
        margin-top: 22px;
      }}

      .rs-panel__eyebrow {{
        display: inline-block;
        margin-bottom: 12px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: var(--gold);
      }}

      .rs-panel h2 {{
        margin: 0;
        font-family: "Songti SC", "STSong", "Noto Serif SC", serif;
        font-size: 28px;
        line-height: 1.25;
        color: var(--navy-900);
      }}

      .rs-panel__lead {{
        margin: 14px 0 0;
        font-size: 15px;
        line-height: 1.9;
        color: var(--text-soft);
      }}

      .rs-summary-grid {{
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 16px;
        margin-top: 24px;
      }}

      .rs-summary-card {{
        padding: 20px 22px;
        border-radius: 20px;
        border: 1px solid rgba(17, 24, 39, 0.07);
        background:
          radial-gradient(circle at top right, rgba(181, 138, 79, 0.08), transparent 26%),
          linear-gradient(180deg, #ffffff, #f8fafc);
      }}

      .rs-summary-card__label {{
        display: inline-block;
        margin-bottom: 10px;
        color: var(--gold);
        font-size: 12px;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        font-weight: 700;
      }}

      .rs-summary-card p {{
        margin: 0;
        color: var(--text-main);
        font-size: 15px;
        line-height: 1.9;
      }}

      .rs-section {{
        display: grid;
        grid-template-columns: 74px minmax(0, 1fr);
        gap: 18px;
        padding: 24px 0;
        border-bottom: 1px solid var(--line);
      }}

      .rs-section:last-child {{
        border-bottom: none;
        padding-bottom: 0;
      }}

      .rs-section:first-child {{
        padding-top: 0;
      }}

      .rs-section__index {{
        display: flex;
        align-items: flex-start;
        justify-content: center;
        padding-top: 4px;
        font-family: "Songti SC", "STSong", "Noto Serif SC", serif;
        font-size: 28px;
        line-height: 1;
        color: var(--gold);
      }}

      .rs-section__eyebrow {{
        color: var(--gold);
        font-size: 11px;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        font-weight: 700;
        margin-bottom: 8px;
      }}

      .rs-section__body h2 {{
        margin: 0;
        font-family: "Songti SC", "STSong", "Noto Serif SC", serif;
        font-size: 24px;
        line-height: 1.3;
        color: var(--navy-900);
      }}

      .rs-section__lead {{
        margin: 12px 0 0;
        color: var(--slate-700);
        font-weight: 600;
        line-height: 1.85;
      }}

      .rs-section__paragraph {{
        margin: 12px 0 0;
        color: var(--text-main);
        font-size: 15px;
        line-height: 1.95;
      }}

      .rs-bullet-list {{
        margin: 16px 0 0;
        padding: 0;
        list-style: none;
        display: grid;
        gap: 10px;
      }}

      .rs-bullet-list li {{
        position: relative;
        padding-left: 18px;
        color: var(--text-main);
        line-height: 1.9;
      }}

      .rs-bullet-list li::before {{
        content: "";
        position: absolute;
        left: 0;
        top: 11px;
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: var(--gold);
        box-shadow: 0 0 0 5px var(--gold-soft);
      }}

      .rs-bullet-list--risk li::before {{
        background: #8f3f3f;
        box-shadow: 0 0 0 5px rgba(143, 63, 63, 0.12);
      }}

      .rs-double-column {{
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 18px;
      }}

      .rs-note {{
        margin-top: 20px;
        padding: 16px 18px;
        border-radius: 18px;
        background: linear-gradient(180deg, rgba(181, 138, 79, 0.08), rgba(181, 138, 79, 0.03));
        border: 1px solid rgba(181, 138, 79, 0.18);
        color: var(--slate-700);
        line-height: 1.85;
      }}

      .rs-footer {{
        margin-top: 24px;
        padding-top: 18px;
        border-top: 1px solid var(--line);
        display: flex;
        justify-content: space-between;
        gap: 18px;
        flex-wrap: wrap;
        color: var(--slate-500);
        font-size: 13px;
        line-height: 1.8;
      }}

      @media (max-width: 900px) {{
        body {{
          padding: 20px 12px 36px;
        }}

        .rs-cover,
        .rs-main {{
          padding: 24px 20px;
        }}

        .rs-cover__top,
        .rs-double-column,
        .rs-summary-grid {{
          grid-template-columns: 1fr;
          display: grid;
        }}

        .rs-stamp {{
          min-width: 0;
        }}

        .rs-section {{
          grid-template-columns: 1fr;
          gap: 12px;
        }}

        .rs-section__index {{
          justify-content: flex-start;
        }}
      }}

      @media print {{
        html, body {{
          background: #ffffff;
        }}

        body {{
          padding: 0;
        }}

        .rs-document {{
          width: 100%;
          border: none;
          border-radius: 0;
          box-shadow: none;
        }}
      }}
    </style>
  </head>
  <body>
    <article class="rs-document">
      <header class="rs-cover">
        <div class="rs-cover__top">
          <div class="rs-brand">
            <span class="rs-brand__eyebrow">Radiant Surface Research</span>
            <h1 class="rs-brand__name">{html.escape(payload["title"])}</h1>
            <p class="rs-brand__subtitle">{html.escape(payload["subtitle"])}</p>
          </div>
          <aside class="rs-stamp">
            <span>Document Note</span>
            <strong>生成时间：{html.escape(generated_text)}</strong>
            <strong>报告对象：{html.escape(target_label)}</strong>
          </aside>
        </div>
        <div class="rs-cover__meta">{self._render_badges(badges)}</div>
      </header>

      <main class="rs-main">
        <section class="rs-panel">
          <span class="rs-panel__eyebrow">Executive Summary</span>
          <h2>执行摘要</h2>
          <p class="rs-panel__lead">以下内容基于当前会话中已经形成的分析信息进行归纳整理，旨在提供适用于管理层讨论、投研例会与内部沟通的正式化研究底稿。</p>
          <div class="rs-summary-grid">
            {summary_cards}
          </div>
        </section>

        <section class="rs-panel">
          <span class="rs-panel__eyebrow">Core Analysis</span>
          <h2>核心分析章节</h2>
          {self._render_sections(payload["sections"])}
        </section>

        <section class="rs-panel">
          <span class="rs-panel__eyebrow">Risk And Tracking</span>
          <h2>风险提示与后续观察</h2>
          <div class="rs-double-column">
            <div>
              <p class="rs-section__lead">风险提示</p>
              {risk_html}
            </div>
            <div>
              <p class="rs-section__lead">后续观察点</p>
              {watch_html}
            </div>
          </div>
          <div class="rs-note">{html.escape(payload["closing"])}</div>
          <div class="rs-footer">
            <span>本报告为当前会话材料的结构化整理版本，适用于内部研究、管理决策讨论与继续尽调前的底稿沉淀。</span>
            <span>若需形成正式对外材料，仍建议结合原始公告、财报、行业数据库与公开披露信息进一步复核。</span>
          </div>
        </section>
      </main>
    </article>
  </body>
</html>
"""

    def build_pdf_report(self, messages, generated_at, active_target) -> bytes:
        html_bytes = self.build_html_report(messages, generated_at, active_target)
        browser_path = self._resolve_pdf_browser()
        if browser_path is None:
            raise RuntimeError("未找到可用的浏览器内核，暂时无法生成 PDF。")

        workspace_tmp_root = Path(__file__).resolve().parents[3] / "data" / ".report_tmp"
        workspace_tmp_root.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="report_pdf_", dir=workspace_tmp_root) as tmp_dir:
            tmp_path = Path(tmp_dir)
            html_path = tmp_path / "report.html"
            pdf_path = tmp_path / "report.pdf"
            user_data_dir = tmp_path / "edge_profile"
            user_data_dir.mkdir(parents=True, exist_ok=True)
            html_path.write_bytes(html_bytes)

            command = [
                str(browser_path),
                "--headless",
                "--no-sandbox",
                "--disable-gpu",
                f"--user-data-dir={user_data_dir}",
                "--allow-file-access-from-files",
                "--no-pdf-header-footer",
                f"--print-to-pdf={pdf_path}",
                html_path.resolve().as_uri(),
            ]
            completed = subprocess.run(
                command,
                capture_output=True,
                timeout=90,
                check=False,
            )
            if completed.returncode != 0 or not pdf_path.exists():
                stderr_text = completed.stderr.decode("utf-8", errors="ignore") if completed.stderr else ""
                stdout_text = completed.stdout.decode("utf-8", errors="ignore") if completed.stdout else ""
                error_text = (stderr_text or stdout_text).strip()
                raise RuntimeError(f"PDF 生成失败：{error_text or '浏览器导出未成功完成'}")

            return pdf_path.read_bytes()

    def build_html_report(self, messages, generated_at, active_target):
        payload = self._request_report_payload(messages, generated_at, active_target)
        normalized_payload = self._normalize_payload(payload, messages, generated_at, active_target)
        html_report = self._render_html(normalized_payload, generated_at, active_target, messages)
        return html_report.encode("utf-8")
