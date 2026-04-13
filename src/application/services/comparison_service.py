from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import akshare as ak
import pandas as pd

from agent_engine import DoubaoAgent
from utils.financial_tools import get_industry_peers_data


@dataclass
class Metric:
    key: str
    display_name: str
    is_positive: bool = True


@dataclass
class TrackTemplate:
    track_name: str
    focus: str
    metrics: list[Metric] = field(default_factory=list)


INDUSTRY_TEMPLATES = {
    "默认": TrackTemplate(
        "核心工业与综合制造",
        "盈利质量与资产负担对标",
        [
            Metric("净资产收益率(%)", "ROE"),
            Metric("销售净利率(%)", "净利率"),
            Metric("资产负债率(%)", "负债率", is_positive=False),
            Metric("营业总收入同比增长率(%)", "营收增速"),
        ],
    ),
    "证券": TrackTemplate(
        "互联网券商与证券服务",
        "资本回报、收入增速与杠杆结构对标",
        [
            Metric("净资产收益率(%)", "ROE"),
            Metric("营业总收入同比增长率(%)", "营收增速"),
            Metric("净利润同比增长率(%)", "净利润增速"),
            Metric("资产负债率(%)", "负债率", is_positive=False),
        ],
    ),
    "银行": TrackTemplate(
        "银行经营质量",
        "回报水平与资产负债结构对标",
        [
            Metric("净资产收益率(%)", "ROE"),
            Metric("基本每股收益(元)", "EPS"),
            Metric("资产负债率(%)", "负债率", is_positive=False),
            Metric("净利润同比增长率(%)", "净利润增速"),
        ],
    ),
    "白酒": TrackTemplate(
        "高端白酒品牌力",
        "盈利能力与增长质量对标",
        [
            Metric("净资产收益率(%)", "ROE"),
            Metric("销售毛利率(%)", "毛利率"),
            Metric("销售净利率(%)", "净利率"),
            Metric("营业总收入同比增长率(%)", "营收增速"),
        ],
    ),
    "新能源": TrackTemplate(
        "新能源制造",
        "盈利修复与周转效率对标",
        [
            Metric("净资产收益率(%)", "ROE"),
            Metric("销售净利率(%)", "净利率"),
            Metric("资产负债率(%)", "负债率", is_positive=False),
            Metric("营业总收入同比增长率(%)", "营收增速"),
        ],
    ),
    "安防": TrackTemplate(
        "安防与智能物联",
        "盈利能力与资产结构对标",
        [
            Metric("净资产收益率(%)", "ROE"),
            Metric("销售净利率(%)", "净利率"),
            Metric("资产负债率(%)", "负债率", is_positive=False),
            Metric("营业总收入同比增长率(%)", "营收增速"),
        ],
    ),
    "医疗器械": TrackTemplate(
        "医疗器械与高端设备",
        "盈利能力与成长性对标",
        [
            Metric("净资产收益率(%)", "ROE"),
            Metric("销售净利率(%)", "净利率"),
            Metric("销售毛利率(%)", "毛利率"),
            Metric("营业总收入同比增长率(%)", "营收增速"),
        ],
    ),
}


class ComparisonService:
    ABSTRACT_CACHE_TTL = 900
    DISCLOSURE_CACHE_TTL = 900
    STATIC_SNAPSHOT_POOL: dict[str, dict[str, Any]] = {
        "300059": {
            "名称": "东方财富",
            "代码": "300059",
            "报告期": "2025-12-31",
            "净资产收益率(%)": 13.15,
            "销售净利率(%)": 342.12,
            "销售毛利率(%)": 84.48,
            "资产负债率(%)": 76.62,
            "营业总收入同比增长率(%)": 38.46,
            "净利润同比增长率(%)": 25.75,
            "基本每股收益(元)": 0.77,
        },
        "300033": {
            "名称": "同花顺",
            "代码": "300033",
            "报告期": "2025-12-31",
            "净资产收益率(%)": 33.77,
            "销售净利率(%)": 53.16,
            "销售毛利率(%)": 91.54,
            "资产负债率(%)": 40.05,
            "营业总收入同比增长率(%)": 44.0,
            "净利润同比增长率(%)": 75.79,
            "基本每股收益(元)": 5.96,
        },
        "300803": {
            "名称": "指南针",
            "代码": "300803",
            "报告期": "2025-12-31",
            "净资产收益率(%)": 8.17,
            "销售净利率(%)": 14.65,
            "销售毛利率(%)": 87.44,
            "资产负债率(%)": 81.91,
            "营业总收入同比增长率(%)": 40.39,
            "净利润同比增长率(%)": 118.74,
            "基本每股收益(元)": 0.38,
        },
        "600030": {
            "名称": "中信证券",
            "代码": "600030",
            "报告期": "2025-12-31",
            "净资产收益率(%)": 9.4,
            "销售净利率(%)": 41.42,
            "销售毛利率(%)": None,
            "资产负债率(%)": 84.35,
            "营业总收入同比增长率(%)": 28.8,
            "净利润同比增长率(%)": 38.58,
            "基本每股收益(元)": 1.96,
        },
        "601995": {
            "名称": "中金公司",
            "代码": "601995",
            "报告期": "2025-12-31",
            "净资产收益率(%)": 8.02,
            "销售净利率(%)": 34.41,
            "销售毛利率(%)": None,
            "资产负债率(%)": 84.11,
            "营业总收入同比增长率(%)": 33.5,
            "净利润同比增长率(%)": 71.93,
            "基本每股收益(元)": 1.88,
        },
        "601688": {
            "名称": "华泰证券",
            "代码": "601688",
            "报告期": "2025-12-31",
            "净资产收益率(%)": 7.92,
            "销售净利率(%)": 45.72,
            "销售毛利率(%)": None,
            "资产负债率(%)": 80.79,
            "营业总收入同比增长率(%)": 6.83,
            "净利润同比增长率(%)": 6.72,
            "基本每股收益(元)": 1.73,
        },
    }

    FALLBACK_PEER_MAP: dict[str, list[tuple[str, str]]] = {
        "300059": [
            ("300059", "东方财富"),
            ("300033", "同花顺"),
            ("300803", "指南针"),
            ("600030", "中信证券"),
            ("601995", "中金公司"),
            ("601688", "华泰证券"),
        ],
        "300750": [
            ("300750", "宁德时代"),
            ("002594", "比亚迪"),
            ("300014", "亿纬锂能"),
            ("300207", "欣旺达"),
            ("002074", "国轩高科"),
            ("688567", "孚能科技"),
            ("300073", "当升科技"),
            ("002460", "赣锋锂业"),
            ("002812", "恩捷股份"),
            ("688005", "容百科技"),
        ],
        "300760": [
            ("300760", "迈瑞医疗"),
            ("002223", "鱼跃医疗"),
            ("300003", "乐普医疗"),
            ("688271", "联影医疗"),
            ("300347", "泰格医药"),
            ("300015", "爱尔眼科"),
            ("600763", "通策医疗"),
            ("688617", "惠泰医疗"),
        ],
        "002415": [
            ("002415", "海康威视"),
            ("002236", "大华股份"),
            ("688475", "萤石网络"),
            ("300496", "中科创达"),
            ("002214", "大立科技"),
            ("300275", "梅安森"),
            ("603660", "苏州科达"),
            ("688277", "天智航"),
        ],
        "600519": [
            ("600519", "贵州茅台"),
            ("000858", "五粮液"),
            ("000568", "泸州老窖"),
            ("600809", "山西汾酒"),
            ("603369", "今世缘"),
            ("002304", "洋河股份"),
            ("000596", "古井贡酒"),
            ("600702", "舍得酒业"),
            ("603198", "迎驾贡酒"),
        ],
        "601012": [
            ("601012", "隆基绿能"),
            ("300274", "阳光电源"),
            ("688472", "阿特斯"),
            ("688223", "晶科能源"),
            ("600438", "通威股份"),
            ("002129", "TCL中环"),
            ("600732", "爱旭股份"),
            ("688390", "固德威"),
            ("605117", "德业股份"),
        ],
        "600900": [
            ("600900", "长江电力"),
            ("600011", "华能国际"),
            ("600025", "华能水电"),
            ("600795", "国电电力"),
            ("600886", "国投电力"),
            ("600905", "三峡能源"),
            ("001289", "龙源电力"),
            ("003816", "中国广核"),
        ],
    }

    SYMBOL_TEMPLATE_HINTS = {
        "300059": "证券",
        "300033": "证券",
        "300803": "证券",
        "600030": "证券",
        "601995": "证券",
        "601688": "证券",
        "000001": "银行",
        "600036": "银行",
        "600519": "白酒",
        "000858": "白酒",
        "000568": "白酒",
        "600809": "白酒",
        "300750": "新能源",
        "002594": "新能源",
        "300014": "新能源",
        "002074": "新能源",
        "002415": "安防",
        "002236": "安防",
        "688475": "安防",
        "300760": "医疗器械",
        "002223": "医疗器械",
        "300003": "医疗器械",
    }

    INDUSTRY_KEYWORDS = {
        "证券": ["证券", "互联网金融", "金融服务", "多元金融"],
        "银行": ["银行"],
        "白酒": ["白酒", "酿酒"],
        "新能源": ["电池", "新能源", "光伏", "储能"],
        "安防": ["安防", "智能物联", "软件开发", "计算机设备"],
        "医疗器械": ["医疗器械", "医疗设备", "医药商业"],
    }

    def __init__(self):
        self.agent = DoubaoAgent()
        self._abstract_cache: dict[str, tuple[float, pd.Series | None]] = {}
        self._disclosure_cache: dict[tuple[str, str], tuple[float, pd.DataFrame]] = {}

    def _normalize_symbol(self, symbol: str) -> str:
        match = re.search(r"\d{6}", str(symbol or ""))
        return match.group(0) if match else str(symbol or "").strip()

    def _disclosure_market(self, symbol: str) -> str:
        if symbol.startswith(("4", "8")):
            return "北交所"
        if symbol.startswith(("5", "6", "9")):
            return "沪市"
        return "深市"

    def _safe_fetch(self, fetcher, **kwargs):
        try:
            return fetcher(**kwargs)
        except Exception:
            return pd.DataFrame()

    def _get_disclosure_frame(self, market: str, period: str) -> pd.DataFrame:
        cache_key = (market, period)
        now = time.time()
        cached = self._disclosure_cache.get(cache_key)
        if cached and now - cached[0] < self.DISCLOSURE_CACHE_TTL:
            return cached[1]

        frame = self._safe_fetch(ak.stock_report_disclosure, market=market, period=period)
        if not isinstance(frame, pd.DataFrame):
            frame = pd.DataFrame()
        self._disclosure_cache[cache_key] = (now, frame)
        return frame

    def _latest_booking_date(self, row: pd.Series) -> Any:
        for column in ["三次变更", "二次变更", "初次变更", "首次预约"]:
            if column in row.index and pd.notna(row.get(column)):
                return row.get(column)
        return pd.NA

    def _period_label_from_date(self, report_date: Any) -> str | None:
        parsed = pd.to_datetime(report_date, errors="coerce")
        if pd.isna(parsed):
            return None
        year = parsed.year
        month = parsed.month
        if month == 3:
            return f"{year}一季"
        if month == 6:
            return f"{year}半年报"
        if month == 9:
            return f"{year}三季"
        if month == 12:
            return f"{year}年报"
        return None

    def _report_period_from_label(self, label: str | None) -> str | None:
        if not label:
            return None
        match = re.match(r"^(\d{4})(一季|半年报|三季|年报)$", str(label).strip())
        if not match:
            return None
        year, suffix = match.groups()
        day_map = {
            "一季": "03-31",
            "半年报": "06-30",
            "三季": "09-30",
            "年报": "12-31",
        }
        return f"{year}-{day_map[suffix]}"

    def _normalize_report_period(self, value: Any) -> str | None:
        if value is None or pd.isna(value):
            return None
        text = str(value).strip()
        if not text:
            return None

        label_period = self._report_period_from_label(text)
        if label_period:
            return label_period

        parsed = pd.to_datetime(text, errors="coerce")
        if pd.notna(parsed):
            return parsed.strftime("%Y-%m-%d")

        digits = re.sub(r"\D", "", text)
        if len(digits) == 8:
            parsed_digits = pd.to_datetime(digits, format="%Y%m%d", errors="coerce")
            if pd.notna(parsed_digits):
                return parsed_digits.strftime("%Y-%m-%d")

        return text

    def _recent_disclosure_periods(self) -> list[str]:
        current_year = datetime.now().year
        periods: list[str] = []
        for year in range(current_year, current_year - 3, -1):
            periods.extend(
                [
                    f"{year}年报",
                    f"{year}三季",
                    f"{year}半年报",
                    f"{year}一季",
                ]
            )
        return periods

    def _resolve_disclosure_meta(self, symbol: str, report_period: str | None) -> dict[str, Any]:
        normalized_symbol = self._normalize_symbol(symbol)
        if not normalized_symbol:
            return {}

        market = self._disclosure_market(normalized_symbol)
        target_label = self._period_label_from_date(report_period)
        candidate_periods = [target_label] if target_label else []
        candidate_periods.extend(self._recent_disclosure_periods())

        seen: set[str] = set()
        unique_periods = [period for period in candidate_periods if period and not (period in seen or seen.add(period))]

        for period in unique_periods:
            frame = self._get_disclosure_frame(market, period)
            if frame.empty or "股票代码" not in frame.columns:
                continue

            matched = frame[frame["股票代码"].astype(str).str.zfill(6) == normalized_symbol]
            if matched.empty:
                continue

            row = matched.iloc[0]
            actual_disclosure = row.get("实际披露")
            latest_booking = self._latest_booking_date(row)
            disclosure_date = actual_disclosure if pd.notna(actual_disclosure) else latest_booking
            if pd.isna(disclosure_date):
                continue

            return {
                "报告期": self._report_period_from_label(period),
                "披露日期": str(disclosure_date),
            }

        return {}

    def _enrich_snapshot_dates(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        enriched = snapshot.copy()
        symbol = self._normalize_symbol(enriched.get("代码"))
        if symbol:
            enriched["代码"] = symbol

        report_period = self._normalize_report_period(enriched.get("报告期"))
        disclosure_meta = self._resolve_disclosure_meta(symbol, report_period) if symbol else {}

        if report_period:
            enriched["报告期"] = report_period
        elif disclosure_meta.get("报告期"):
            enriched["报告期"] = disclosure_meta["报告期"]

        if disclosure_meta.get("披露日期"):
            enriched["披露日期"] = disclosure_meta["披露日期"]

        return enriched

    def _parse_numeric(self, value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)

        text = str(value).strip()
        if not text or text in {"False", "None", "nan", "N/A"}:
            return None

        multiplier = 1.0
        if text.endswith("%"):
            text = text[:-1]
        if "万亿" in text:
            multiplier = 10000.0
            text = text.replace("万亿", "")
        elif "亿" in text:
            multiplier = 1.0
            text = text.replace("亿", "")
        elif "万" in text:
            multiplier = 0.0001
            text = text.replace("万", "")

        text = text.replace(",", "")
        try:
            return float(text) * multiplier
        except ValueError:
            return None

    def _latest_abstract_row(self, symbol: str) -> pd.Series | None:
        cached = self._abstract_cache.get(symbol)
        now = time.time()
        if cached and now - cached[0] < self.ABSTRACT_CACHE_TTL:
            return cached[1]

        frame = self._safe_fetch(ak.stock_financial_abstract_ths, symbol=symbol)
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            self._abstract_cache[symbol] = (now, None)
            return None
        if "报告期" in frame.columns:
            sortable = pd.to_datetime(frame["报告期"], errors="coerce")
            frame = frame.assign(_sort_date=sortable).sort_values("_sort_date", ascending=False).drop(columns="_sort_date")
        latest_row = frame.iloc[0]
        self._abstract_cache[symbol] = (now, latest_row)
        return latest_row

    def _build_snapshot_from_abstract(self, symbol: str, company_name: str) -> dict[str, Any] | None:
        row = self._latest_abstract_row(symbol)
        if row is None:
            static_snapshot = self.STATIC_SNAPSHOT_POOL.get(symbol)
            if static_snapshot:
                static_snapshot = static_snapshot.copy()
                static_report_period = self._normalize_report_period(static_snapshot.get("报告期"))
                static_snapshot["名称"] = company_name
                static_snapshot["代码"] = symbol
                static_snapshot.pop("报告期", None)
                enriched_snapshot = self._enrich_snapshot_dates(static_snapshot)
                if static_report_period and not enriched_snapshot.get("报告期"):
                    enriched_snapshot["报告期"] = static_report_period
                if static_report_period and enriched_snapshot.get("报告期") != static_report_period:
                    enriched_snapshot["指标口径"] = static_report_period
                return enriched_snapshot
            return None

        snapshot = {
            "名称": company_name,
            "代码": symbol,
            "报告期": self._normalize_report_period(row.get("报告期")),
        }

        field_map = {
            "净资产收益率(%)": ["净资产收益率-摊薄", "净资产收益率"],
            "销售净利率(%)": ["销售净利率"],
            "销售毛利率(%)": ["销售毛利率"],
            "资产负债率(%)": ["资产负债率"],
            "营业总收入同比增长率(%)": ["营业总收入同比增长率"],
            "净利润同比增长率(%)": ["净利润同比增长率"],
            "基本每股收益(元)": ["基本每股收益"],
        }

        valid_metric_count = 0
        for output_key, candidates in field_map.items():
            numeric_value = None
            for candidate in candidates:
                if candidate not in row.index:
                    continue
                numeric_value = self._parse_numeric(row.get(candidate))
                if numeric_value is not None:
                    break
            snapshot[output_key] = round(float(numeric_value), 2) if numeric_value is not None else None
            if numeric_value is not None:
                valid_metric_count += 1

        return self._enrich_snapshot_dates(snapshot) if valid_metric_count else None

    def _merge_snapshot_records(
        self,
        primary: list[dict[str, Any]] | None,
        secondary: list[dict[str, Any]] | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen_symbols: set[str] = set()

        for source_list in (primary or [], secondary or []):
            if isinstance(source_list, list):
                records = source_list
            elif isinstance(source_list, dict):
                records = [source_list]
            else:
                records = []

            for record in records:
                symbol = self._normalize_symbol(
                    record.get("代码") or record.get("股票代码") or record.get("证券代码")
                )
                dedupe_key = symbol or str(
                    record.get("名称") or record.get("股票简称") or record.get("公司名称") or record
                )
                if dedupe_key in seen_symbols:
                    continue
                seen_symbols.add(dedupe_key)
                merged.append(record)
                if len(merged) >= limit:
                    return merged

        return merged

    def _build_fallback_snapshots(self, symbol: str, limit: int = 10) -> list[dict[str, Any]]:
        peer_candidates = self._resolve_fallback_peer_candidates(symbol)[:limit]
        snapshots: list[dict[str, Any]] = []

        if not peer_candidates:
            return snapshots

        with ThreadPoolExecutor(max_workers=min(6, len(peer_candidates))) as executor:
            future_map = {
                executor.submit(self._build_snapshot_from_abstract, peer_code, peer_name): (peer_code, peer_name)
                for peer_code, peer_name in peer_candidates
            }
            ordered_results: dict[str, dict[str, Any]] = {}
            for future in as_completed(future_map):
                peer_code, _ = future_map[future]
                try:
                    snapshot = future.result()
                except Exception:
                    snapshot = None
                if snapshot:
                    ordered_results[peer_code] = snapshot

        for peer_code, _ in peer_candidates:
            snapshot = ordered_results.get(peer_code)
            if snapshot:
                snapshots.append(snapshot)
        return snapshots

    def _resolve_fallback_peer_candidates(self, symbol: str) -> list[tuple[str, str]]:
        normalized_symbol = self._normalize_symbol(symbol)
        ordered_candidates: list[tuple[str, str]] = []
        seen_symbols: set[str] = set()

        def append_candidates(candidates: list[tuple[str, str]] | None) -> None:
            for peer_code, peer_name in candidates or []:
                normalized_peer_code = self._normalize_symbol(peer_code)
                if normalized_peer_code in seen_symbols:
                    continue
                seen_symbols.add(normalized_peer_code)
                ordered_candidates.append((normalized_peer_code, peer_name))

        exact_candidates = self.FALLBACK_PEER_MAP.get(normalized_symbol)
        if exact_candidates:
            append_candidates(exact_candidates)
            return ordered_candidates

        for peer_candidates in self.FALLBACK_PEER_MAP.values():
            if any(self._normalize_symbol(peer_code) == normalized_symbol for peer_code, _ in peer_candidates):
                append_candidates(peer_candidates)

        if ordered_candidates:
            return ordered_candidates

        template_key = self._resolve_template_key(normalized_symbol)

        for seed_symbol, peer_candidates in self.FALLBACK_PEER_MAP.items():
            if self._resolve_template_key(seed_symbol) == template_key:
                append_candidates(peer_candidates)

        return ordered_candidates

    def get_peer_snapshots_for_symbol(self, symbol, limit=10):
        normalized_symbol = self._normalize_symbol(symbol)
        df = get_industry_peers_data(normalized_symbol, limit=limit)
        industry_snapshots: list[dict[str, Any]] = []
        if isinstance(df, pd.DataFrame) and not df.empty:
            industry_snapshots = [self._enrich_snapshot_dates(record) for record in df.to_dict("records")]

        fallback_snapshots = self._build_fallback_snapshots(normalized_symbol, limit=limit)
        return self._merge_snapshot_records(industry_snapshots, fallback_snapshots, limit=limit)

    def _resolve_template_key(self, symbol: str) -> str:
        normalized_symbol = self._normalize_symbol(symbol)
        hinted = self.SYMBOL_TEMPLATE_HINTS.get(normalized_symbol)
        if hinted:
            return hinted

        try:
            info = ak.stock_individual_info_em(symbol=normalized_symbol)
            if isinstance(info, pd.DataFrame) and not info.empty and "item" in info.columns:
                industry_rows = info[info["item"].isin(["行业", "板块"])]
                if not industry_rows.empty:
                    industry_text = str(industry_rows.iloc[0]["value"])
                    for template_key, keywords in self.INDUSTRY_KEYWORDS.items():
                        if any(keyword in industry_text for keyword in keywords):
                            return template_key
        except Exception:
            pass

        return "默认"

    def get_track_template_for_symbol(self, symbol):
        template_key = self._resolve_template_key(symbol)
        return INDUSTRY_TEMPLATES.get(template_key, INDUSTRY_TEMPLATES["默认"])

    def build_track_chart_specs(self, symbol, limit=10, max_metrics=4):
        # AI辅助标注（序号3）：
        # 工具/时间：Doubao-Seed-2.0-lite，2026-03-31 09:00-12:00。
        # 对应表格：数据处理与代码辅助。
        # 本段“指标筛选 -> 图表数据组织 -> 结论文案补全”的生成脚本思路参考了 AI 建议，
        # 最终图表字段、排序逻辑和展示文案由人工按项目页面结构调整。
        snapshots = self.get_peer_snapshots_for_symbol(symbol, limit=limit)
        track_template = self.get_track_template_for_symbol(symbol)
        if not snapshots or not track_template:
            return []

        frame = pd.DataFrame(snapshots)
        if frame.empty or "名称" not in frame.columns:
            return []

        x_labels = frame["名称"].astype(str).tolist()
        chart_specs: list[dict[str, Any]] = []

        for metric in track_template.metrics[:max_metrics]:
            if metric.key not in frame.columns:
                continue
            values = pd.to_numeric(frame[metric.key], errors="coerce")
            valid_mask = values.notna()
            if not valid_mask.any():
                continue

            metric_frame = frame.loc[valid_mask].copy()
            metric_values = values.loc[valid_mask].astype(float)
            metric_labels = metric_frame["名称"].astype(str).tolist()
            if not metric_labels:
                continue

            leader_index = metric_values.idxmax() if metric.is_positive else metric_values.idxmin()
            leader_name = str(frame.loc[leader_index, "名称"])
            leader_value = float(metric_values.loc[leader_index])
            direction = "最高" if metric.is_positive else "最低"

            chart_specs.append(
                {
                    "title": f"{metric.display_name}行业对标",
                    "chart_type": "bar",
                    "x_labels": metric_labels,
                    "datasets": [
                        {
                            "name": metric.display_name,
                            "data": [round(float(value), 2) for value in metric_values.tolist()],
                        }
                    ],
                    "analyst_verdict": (
                        f"{leader_name}在{metric.display_name}维度处于样本中{direction}位，"
                        f"当前值约为{leader_value:.2f}。"
                    ),
                    "strategic_highlight": f"样本数 {len(metric_labels)} | 赛道核心指标横向对比",
                }
            )

        return chart_specs

    def snapshots_to_focused_dataframe(self, snapshots, track_template):
        if not snapshots:
            return pd.DataFrame()
        frame = pd.DataFrame(snapshots)
        if track_template is None or frame.empty:
            return frame
        desired_columns = ["名称", "代码", "报告期", "披露日期"] + [metric.key for metric in track_template.metrics]
        available_columns = [column for column in desired_columns if column in frame.columns]
        return frame[available_columns]

    def analyze_peers_with_agent(self, symbol, snapshots_df):
        data_json = snapshots_df.to_json(orient="records", force_ascii=False)
        prompt = f"""
        请根据以下行业赛道竞对数据进行深度解读分析，目标标的是 [{symbol}]。

        数据展示（JSON 格式）：
        {data_json}

        要求：
        1. 分析目标公司在 ROE、负债率、净利率等维度相对于同行的优势与短板。
        2. 基于 2026 年时点，判断当前赛道景气度与未来风险。
        3. 使用顶尖商业分析师的口吻，输出 300-500 字的分点结论。
        """

        return self.agent.chat(prompt)
