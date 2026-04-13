from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from src.infrastructure.utils.file_processor import FileProcessor


ROOT_DIR = Path(__file__).resolve().parents[3]
COMPETITION_DOC_NAME = "赛题相关数据下载路径文档.pdf"

STRUCTURED_SOURCE_LINES = [
    "【赛题数据来源约束】",
    f"1. 赛题路径文档：{COMPETITION_DOC_NAME}",
    "2. 正文保持正常分析内容，不要重复堆叠来源说明。",
    "3. 数据来源说明统一在回答末尾追加，正文不要再单独写“来源：……”或“引自：……”。",
    "4. 财务报告官方披露入口包括：",
    "   - 上交所定期报告页：https://www.sse.com.cn/disclosure/listedinfo/regular/",
    "   - 深交所固定信息披露页：https://www.szse.cn/disclosure/listed/fixed/index.html",
    "   - 北交所公告披露页：https://www.bse.cn/disclosure/announcement.html",
    "5. 研究报告参考入口包括：",
    "   - 东方财富行业研报页：https://data.eastmoney.com/report/industry.jshtml",
    "   - 东方财富个股研报页：https://data.eastmoney.com/report/stock.jshtml",
    "6. 宏观数据参考入口：",
    "   - 国家统计局数据查询页：https://www.stats.gov.cn/sj/",
]

FINANCIAL_TOPIC_PATTERN = re.compile(
    r"(财务|报表|利润|营收|收入|净利|毛利|现金流|资产负债|估值|pe|pb|roe|roa|eps|业绩)",
    re.IGNORECASE,
)
DISCLOSURE_TOPIC_PATTERN = re.compile(
    r"(公告|披露|年报|中报|半年报|季报|三季报|一季报|快报|预告|问询|回复|回购|分红|股权激励|解禁)",
    re.IGNORECASE,
)
RESEARCH_TOPIC_PATTERN = re.compile(r"(研报|券商|评级|观点|一致预期|目标价)", re.IGNORECASE)
INDUSTRY_TOPIC_PATTERN = re.compile(r"(行业|赛道|产业链|渗透率|装机|需求|竞争格局|供给)", re.IGNORECASE)
MACRO_TOPIC_PATTERN = re.compile(r"(宏观|经济|社零|出口|pmi|cpi|ppi|gdp|利率|社融)", re.IGNORECASE)
FLOW_TOPIC_PATTERN = re.compile(r"(资金流|主力|北向|融资融券|龙虎榜|大宗交易)", re.IGNORECASE)
TARGET_WITH_LABEL_PATTERN = re.compile(r"([A-Za-z0-9\u4e00-\u9fa5·]{2,20})\s*[（(]\s*(\d{6})(?:\.[A-Za-z]{2})?\s*[)）]")
TARGET_PATTERN = re.compile(r"([A-Za-z0-9\u4e00-\u9fa5·]{2,20})?\s*[（(]?\s*(\d{6})(?:\.[A-Za-z]{2})?\s*[)）]?")


def _normalize_spaces(text: str) -> str:
    return " ".join(str(text or "").split())


def _compact_text(text: str, limit: int = 1600) -> str:
    return _normalize_spaces(text)[:limit]


def _is_low_quality_excerpt(text: str) -> bool:
    sample = _normalize_spaces(text)
    if not sample:
        return True
    question_ratio = sample.count("?") / max(len(sample), 1)
    cjk_count = sum(1 for char in sample if "\u4e00" <= char <= "\u9fff")
    return question_ratio >= 0.2 or cjk_count < 20


class LocalKnowledgeService:
    def __init__(self) -> None:
        self.doc_path = ROOT_DIR / COMPETITION_DOC_NAME

    def build_context(
        self,
        prompt: str,
        active_target: str | None = None,
        active_targets: list[str] | None = None,
    ) -> str:
        excerpt = self._load_excerpt(self.doc_path)
        sections = [
            "[系统内置赛题数据路径约束。请直接输出正常中文分析，不要输出乱码、奇怪符号或重复来源说明。]",
            "\n".join(STRUCTURED_SOURCE_LINES),
        ]
        if excerpt:
            sections.append(f"### 赛题相关数据下载路径文档摘录\n{excerpt}")
        return "\n\n".join(sections)

    def _normalize_target_label(self, raw_label: str | None, symbol: str) -> str:
        label = _normalize_spaces(raw_label or "").strip("：:，,。;； ")
        if label:
            label = re.sub(r"(如果|需要|请|帮我|看看|分析|研究|解读|关于|对于|针对|围绕)", "", label)
            label = label.strip("：:，,。;； ")
        return f"{label}({symbol})" if label else f"标的({symbol})"

    def _collect_targets(
        self,
        prompt: str,
        reply: str,
        active_target: str | None,
        active_targets: list[str] | None,
    ) -> list[tuple[str, str]]:
        targets: list[tuple[str, str]] = []
        seen_symbols: set[str] = set()
        candidate_values = [active_target or "", *(active_targets or []), prompt, reply]

        for value in candidate_values:
            normalized_value = str(value or "")

            for match in TARGET_WITH_LABEL_PATTERN.finditer(normalized_value):
                symbol = match.group(2)
                if not symbol or symbol in seen_symbols:
                    continue
                label = self._normalize_target_label(match.group(1), symbol)
                seen_symbols.add(symbol)
                targets.append((symbol, label))

            for match in TARGET_PATTERN.finditer(normalized_value):
                symbol = match.group(2)
                if not symbol or symbol in seen_symbols:
                    continue
                label = self._normalize_target_label(match.group(1), symbol)
                seen_symbols.add(symbol)
                targets.append((symbol, label))
        return targets[:3]

    def _detect_topics(self, prompt: str, reply: str, uploaded_file_names: list[str]) -> dict[str, bool]:
        text = "\n".join([prompt or "", reply or "", " ".join(uploaded_file_names or [])])
        return {
            "financial": bool(FINANCIAL_TOPIC_PATTERN.search(text)),
            "disclosure": bool(DISCLOSURE_TOPIC_PATTERN.search(text)),
            "research": bool(RESEARCH_TOPIC_PATTERN.search(text)),
            "industry": bool(INDUSTRY_TOPIC_PATTERN.search(text)),
            "macro": bool(MACRO_TOPIC_PATTERN.search(text)),
            "flow": bool(FLOW_TOPIC_PATTERN.search(text)),
        }

    def _market_disclosure_entry(self, symbol: str, label: str) -> str:
        if symbol.startswith(("600", "601", "603", "605", "688", "689")):
            return f"{label} 上交所定期报告入口：https://www.sse.com.cn/disclosure/listedinfo/regular/"
        if symbol.startswith(("000", "001", "002", "003", "300", "301")):
            return f"{label} 深交所固定信息披露入口：https://www.szse.cn/disclosure/listed/fixed/index.html"
        if symbol.startswith(("4", "8", "9")):
            return f"{label} 北交所公告入口：https://www.bse.cn/disclosure/announcement.html"
        return f"{label} 巨潮公告检索页：https://www.cninfo.com.cn/new/fulltextSearch?keyWord={symbol}"

    def build_source_note(
        self,
        prompt: str = "",
        reply: str = "",
        active_target: str | None = None,
        active_targets: list[str] | None = None,
        uploaded_file_names: list[str] | None = None,
    ) -> str:
        deduped_uploaded = list(dict.fromkeys(name for name in (uploaded_file_names or []) if _normalize_spaces(name)))
        topics = self._detect_topics(prompt, reply, deduped_uploaded)
        targets = self._collect_targets(prompt, reply, active_target, active_targets)
        has_specific_topic = any(topics.values())

        entries: list[str] = [f"赛题路径文档：{self.doc_path}"]

        if deduped_uploaded:
            entries.append(f"本次上传材料：{'；'.join(deduped_uploaded)}")

        for symbol, label in targets:
            if topics["financial"] or topics["disclosure"] or topics["research"] or topics["industry"] or topics["flow"] or not has_specific_topic:
                entries.append(f"{label} 个股数据页：https://data.eastmoney.com/stockdata/{symbol}.html")

            if topics["disclosure"] or topics["financial"] or topics["research"] or topics["flow"] or not has_specific_topic:
                entries.append(f"{label} 公告大全页：https://data.eastmoney.com/notice/{symbol}.html")
                entries.append(f"{label} 巨潮公告检索页：https://www.cninfo.com.cn/new/fulltextSearch?keyWord={symbol}")
                entries.append(self._market_disclosure_entry(symbol, label))

            if topics["flow"]:
                entries.append(f"{label} 资金流向页：https://data.eastmoney.com/zjlx/{symbol}.html")

        if topics["research"]:
            entries.append("个股研报入口：https://data.eastmoney.com/report/stock.jshtml")

        if topics["industry"]:
            entries.append("行业研报入口：https://data.eastmoney.com/report/industry.jshtml")

        if topics["macro"] or topics["industry"]:
            entries.append("国家统计局数据查询页：https://www.stats.gov.cn/sj/")

        deduped_entries: list[str] = []
        for entry in entries:
            normalized = _normalize_spaces(entry)
            if normalized and normalized not in deduped_entries:
                deduped_entries.append(normalized)

        return "\n".join(["数据来源说明", *[f"{index}. {entry}" for index, entry in enumerate(deduped_entries, start=1)]])

    @staticmethod
    @lru_cache(maxsize=4)
    def _load_excerpt(path: Path) -> str:
        if not path.exists():
            return ""
        try:
            raw = path.read_bytes()
            parsed = FileProcessor.process_file(path.name, raw) or ""
            excerpt = _compact_text(parsed)
            if _is_low_quality_excerpt(excerpt):
                return ""
            return excerpt
        except Exception:
            return ""
