import os
import re
import sys
from typing import Any

import akshare as ak
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.application.dto.financial_dto import FinancialTableDTO
from src.infrastructure.utils.symbol_resolver import resolver


SUMMARY_TITLE = "\u8d22\u52a1\u6458\u8981\uff08\u8fd1 8 \u671f\uff09"
DISCLOSURE_TITLE = "\u62ab\u9732\u8fdb\u5ea6"
BALANCE_TITLE = "\u6700\u65b0\u8d44\u4ea7\u8d1f\u503a\u8868\uff08\u6838\u5fc3\u9879\uff09"
INCOME_TITLE = "\u6700\u65b0\u5229\u6da6\u8868\uff08\u6838\u5fc3\u9879\uff09"
CASHFLOW_TITLE = "\u6700\u65b0\u73b0\u91d1\u6d41\u91cf\u8868\uff08\u6838\u5fc3\u9879\uff09"

META_FIELDS = [
    ("\u62a5\u544a\u7c7b\u578b", ["REPORT_DATE_NAME", "REPORT_TYPE", "\u7c7b\u578b"]),
    ("\u516c\u544a\u65e5\u671f", ["NOTICE_DATE", "\u516c\u544a\u65e5\u671f"]),
    ("\u5e01\u79cd", ["CURRENCY", "\u5e01\u79cd"]),
    ("\u5ba1\u8ba1\u72b6\u6001", ["OPINION_TYPE", "OSOPINION_TYPE", "\u662f\u5426\u5ba1\u8ba1"]),
    ("\u66f4\u65b0\u65e5\u671f", ["UPDATE_DATE", "\u66f4\u65b0\u65e5\u671f"]),
]

BALANCE_METRICS = [
    ("\u8d27\u5e01\u8d44\u91d1", ["\u8d27\u5e01\u8d44\u91d1", "MONETARYFUNDS"]),
    ("\u5e94\u6536\u8d26\u6b3e", ["\u5e94\u6536\u8d26\u6b3e", "ACCOUNTS_RECE"]),
    ("\u5b58\u8d27", ["\u5b58\u8d27", "INVENTORY"]),
    ("\u6d41\u52a8\u8d44\u4ea7\u5408\u8ba1", ["\u6d41\u52a8\u8d44\u4ea7\u5408\u8ba1", "TOTAL_CURRENT_ASSETS"]),
    ("\u975e\u6d41\u52a8\u8d44\u4ea7\u5408\u8ba1", ["\u975e\u6d41\u52a8\u8d44\u4ea7\u5408\u8ba1", "TOTAL_NONCURRENT_ASSETS"]),
    ("\u8d44\u4ea7\u603b\u8ba1", ["\u8d44\u4ea7\u603b\u8ba1", "TOTAL_ASSETS"]),
    ("\u5e94\u4ed8\u8d26\u6b3e", ["\u5e94\u4ed8\u8d26\u6b3e", "ACCOUNTS_PAYABLE"]),
    ("\u5408\u540c\u8d1f\u503a", ["\u5408\u540c\u8d1f\u503a", "CONTRACT_LIAB"]),
    ("\u6d41\u52a8\u8d1f\u503a\u5408\u8ba1", ["\u6d41\u52a8\u8d1f\u503a\u5408\u8ba1", "TOTAL_CURRENT_LIAB"]),
    ("\u975e\u6d41\u52a8\u8d1f\u503a\u5408\u8ba1", ["\u975e\u6d41\u52a8\u8d1f\u503a\u5408\u8ba1", "TOTAL_NONCURRENT_LIAB"]),
    ("\u8d1f\u503a\u5408\u8ba1", ["\u8d1f\u503a\u5408\u8ba1", "TOTAL_LIABILITIES"]),
    ("\u5f52\u6bcd\u80a1\u4e1c\u6743\u76ca\u5408\u8ba1", ["\u5f52\u5c5e\u4e8e\u6bcd\u516c\u53f8\u80a1\u4e1c\u6743\u76ca\u5408\u8ba1", "TOTAL_PARENT_EQUITY", "PARENT_EQUITY_BALANCE"]),
    ("\u80a1\u4e1c\u6743\u76ca\u5408\u8ba1", ["\u6240\u6709\u8005\u6743\u76ca(\u6216\u80a1\u4e1c\u6743\u76ca)\u5408\u8ba1", "TOTAL_EQUITY"]),
]

INCOME_METRICS = [
    ("\u8425\u4e1a\u603b\u6536\u5165", ["\u8425\u4e1a\u603b\u6536\u5165", "TOTAL_OPERATE_INCOME"]),
    ("\u8425\u4e1a\u6536\u5165", ["\u8425\u4e1a\u6536\u5165", "OPERATE_INCOME"]),
    ("\u8425\u4e1a\u603b\u6210\u672c", ["\u8425\u4e1a\u603b\u6210\u672c", "TOTAL_OPERATE_COST"]),
    ("\u8425\u4e1a\u6210\u672c", ["\u8425\u4e1a\u6210\u672c", "OPERATE_COST"]),
    ("\u9500\u552e\u8d39\u7528", ["\u9500\u552e\u8d39\u7528", "SALE_EXPENSE"]),
    ("\u7ba1\u7406\u8d39\u7528", ["\u7ba1\u7406\u8d39\u7528", "MANAGE_EXPENSE"]),
    ("\u7814\u53d1\u8d39\u7528", ["\u7814\u53d1\u8d39\u7528", "RESEARCH_EXPENSE"]),
    ("\u8d22\u52a1\u8d39\u7528", ["\u8d22\u52a1\u8d39\u7528", "FINANCE_EXPENSE"]),
    ("\u8425\u4e1a\u5229\u6da6", ["\u8425\u4e1a\u5229\u6da6", "OPERATE_PROFIT"]),
    ("\u5229\u6da6\u603b\u989d", ["\u5229\u6da6\u603b\u989d", "TOTAL_PROFIT"]),
    ("\u6240\u5f97\u7a0e\u8d39\u7528", ["\u6240\u5f97\u7a0e\u8d39\u7528", "INCOME_TAX"]),
    ("\u51c0\u5229\u6da6", ["\u51c0\u5229\u6da6", "NETPROFIT"]),
    ("\u5f52\u6bcd\u51c0\u5229\u6da6", ["\u5f52\u5c5e\u4e8e\u6bcd\u516c\u53f8\u6240\u6709\u8005\u7684\u51c0\u5229\u6da6", "PARENT_NETPROFIT"]),
    ("\u57fa\u672c\u6bcf\u80a1\u6536\u76ca", ["\u57fa\u672c\u6bcf\u80a1\u6536\u76ca", "BASIC_EPS"]),
]

CASHFLOW_METRICS = [
    ("\u7ecf\u8425\u6d3b\u52a8\u73b0\u91d1\u6d41\u5165\u5c0f\u8ba1", ["\u7ecf\u8425\u6d3b\u52a8\u73b0\u91d1\u6d41\u5165\u5c0f\u8ba1", "TOTAL_OPERATE_INFLOW"]),
    ("\u7ecf\u8425\u6d3b\u52a8\u73b0\u91d1\u6d41\u51fa\u5c0f\u8ba1", ["\u7ecf\u8425\u6d3b\u52a8\u73b0\u91d1\u6d41\u51fa\u5c0f\u8ba1", "TOTAL_OPERATE_OUTFLOW"]),
    ("\u7ecf\u8425\u6d3b\u52a8\u73b0\u91d1\u6d41\u51c0\u989d", ["\u7ecf\u8425\u6d3b\u52a8\u4ea7\u751f\u7684\u73b0\u91d1\u6d41\u91cf\u51c0\u989d", "NETCASH_OPERATE"]),
    ("\u6295\u8d44\u6d3b\u52a8\u73b0\u91d1\u6d41\u5165\u5c0f\u8ba1", ["\u6295\u8d44\u6d3b\u52a8\u73b0\u91d1\u6d41\u5165\u5c0f\u8ba1", "TOTAL_INVEST_INFLOW"]),
    ("\u6295\u8d44\u6d3b\u52a8\u73b0\u91d1\u6d41\u51fa\u5c0f\u8ba1", ["\u6295\u8d44\u6d3b\u52a8\u73b0\u91d1\u6d41\u51fa\u5c0f\u8ba1", "TOTAL_INVEST_OUTFLOW"]),
    ("\u6295\u8d44\u6d3b\u52a8\u73b0\u91d1\u6d41\u51c0\u989d", ["\u6295\u8d44\u6d3b\u52a8\u4ea7\u751f\u7684\u73b0\u91d1\u6d41\u91cf\u51c0\u989d", "NETCASH_INVEST"]),
    ("\u7b79\u8d44\u6d3b\u52a8\u73b0\u91d1\u6d41\u5165\u5c0f\u8ba1", ["\u7b79\u8d44\u6d3b\u52a8\u73b0\u91d1\u6d41\u5165\u5c0f\u8ba1", "TOTAL_FINANCE_INFLOW"]),
    ("\u7b79\u8d44\u6d3b\u52a8\u73b0\u91d1\u6d41\u51fa\u5c0f\u8ba1", ["\u7b79\u8d44\u6d3b\u52a8\u73b0\u91d1\u6d41\u51fa\u5c0f\u8ba1", "TOTAL_FINANCE_OUTFLOW"]),
    ("\u7b79\u8d44\u6d3b\u52a8\u73b0\u91d1\u6d41\u51c0\u989d", ["\u7b79\u8d44\u6d3b\u52a8\u4ea7\u751f\u7684\u73b0\u91d1\u6d41\u91cf\u51c0\u989d", "NETCASH_FINANCE"]),
    ("\u73b0\u91d1\u53ca\u73b0\u91d1\u7b49\u4ef7\u7269\u51c0\u589e\u52a0\u989d", ["\u73b0\u91d1\u53ca\u73b0\u91d1\u7b49\u4ef7\u7269\u51c0\u589e\u52a0\u989d", "CCE_ADD"]),
    ("\u671f\u521d\u73b0\u91d1\u53ca\u73b0\u91d1\u7b49\u4ef7\u7269\u4f59\u989d", ["\u671f\u521d\u73b0\u91d1\u53ca\u73b0\u91d1\u7b49\u4ef7\u7269\u4f59\u989d", "BEGIN_CCE"]),
    ("\u671f\u672b\u73b0\u91d1\u53ca\u73b0\u91d1\u7b49\u4ef7\u7269\u4f59\u989d", ["\u671f\u672b\u73b0\u91d1\u53ca\u73b0\u91d1\u7b49\u4ef7\u7269\u4f59\u989d", "END_CCE"]),
]


class FinancialService:
    def _resolve_symbol(self, symbol_raw: str) -> str | None:
        resolved = resolver.resolve(str(symbol_raw or "").strip())
        symbol_match = re.search(r"\d{6}", str(resolved))
        return symbol_match.group(0) if symbol_match else None

    def _market_symbol(self, symbol: str, upper: bool = True) -> str:
        market = "SH" if symbol.startswith(("5", "6", "9")) else "SZ"
        if symbol.startswith(("4", "8")):
            market = "BJ"
        market = market if upper else market.lower()
        return f"{market}{symbol}"

    def _disclosure_market(self, symbol: str) -> str:
        if symbol.startswith(("4", "8")):
            return "\u5317\u4ea4\u6240"
        if symbol.startswith(("5", "6", "9")):
            return "\u6caa\u5e02"
        return "\u6df1\u5e02"

    def _safe_fetch(self, fetcher, **kwargs) -> pd.DataFrame:
        try:
            frame = fetcher(**kwargs)
            if isinstance(frame, pd.DataFrame) and not frame.empty:
                return frame
        except Exception:
            return pd.DataFrame()
        return pd.DataFrame()

    def _clean_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        if frame is None or frame.empty:
            return pd.DataFrame()
        cleaned = frame.copy()
        cleaned = cleaned.mask(cleaned.eq(""))
        cleaned = cleaned.mask(cleaned.eq("False"))
        cleaned = cleaned.mask(cleaned.eq(False))
        return cleaned

    def _trim_recent_periods(self, frame: pd.DataFrame, date_columns: list[str], limit: int) -> pd.DataFrame:
        if frame is None or frame.empty:
            return pd.DataFrame()
        trimmed = frame.copy()
        date_column = next((column for column in date_columns if column in trimmed.columns), None)
        if date_column is None:
            return trimmed.head(limit)

        sortable_dates = pd.to_datetime(trimmed[date_column], errors="coerce")
        if sortable_dates.notna().any():
            trimmed = (
                trimmed.assign(_sort_date=sortable_dates)
                .sort_values("_sort_date", ascending=False)
                .drop(columns="_sort_date")
            )
        return trimmed.head(limit)

    def _frame_non_null_ratio(self, frame: pd.DataFrame) -> float:
        if frame is None or frame.empty:
            return 0.0
        total_cells = frame.shape[0] * frame.shape[1]
        if total_cells == 0:
            return 0.0
        return float(frame.notna().sum().sum()) / float(total_cells)

    def _drop_sparse_columns(self, frame: pd.DataFrame, keep_columns: list[str], min_non_null_ratio: float) -> pd.DataFrame:
        if frame is None or frame.empty:
            return pd.DataFrame()
        retained_columns: list[str] = []
        for column in frame.columns:
            if column in keep_columns:
                retained_columns.append(column)
                continue
            ratio = float(frame[column].notna().mean())
            if ratio >= min_non_null_ratio:
                retained_columns.append(column)
        return frame[retained_columns]

    def _latest_date(self, frame: pd.DataFrame, date_columns: list[str]) -> pd.Timestamp | None:
        if frame is None or frame.empty:
            return None
        for column in date_columns:
            if column not in frame.columns:
                continue
            parsed = pd.to_datetime(frame[column], errors="coerce").dropna()
            if not parsed.empty:
                return parsed.max()
        return None

    def _pick_latest_frame(
        self,
        preferred_frame: pd.DataFrame,
        fallback_frame: pd.DataFrame,
        date_columns: list[str],
    ) -> pd.DataFrame:
        preferred_date = self._latest_date(preferred_frame, date_columns)
        fallback_date = self._latest_date(fallback_frame, date_columns)
        if preferred_date is not None and (fallback_date is None or preferred_date >= fallback_date):
            return preferred_frame
        if fallback_date is not None:
            return fallback_frame
        return pd.DataFrame()

    def _lookup_first_value(self, row: pd.Series, candidates: list[str]) -> Any:
        for candidate in candidates:
            if candidate in row.index:
                value = row.get(candidate)
                if pd.notna(value):
                    return value
        return pd.NA

    def _statement_to_core_rows(
        self,
        frame: pd.DataFrame,
        report_column: str,
        metric_map: list[tuple[str, list[str]]],
        source_name: str,
    ) -> list[dict[str, Any]]:
        if frame is None or frame.empty:
            return []

        latest_row = frame.iloc[0]
        metadata: dict[str, Any] = {"\u6765\u6e90": source_name}
        for output_label, candidates in META_FIELDS:
            value = self._lookup_first_value(latest_row, candidates)
            if pd.notna(value):
                metadata[output_label] = value

        rows: list[dict[str, Any]] = []
        for display_name, candidates in metric_map:
            value = self._lookup_first_value(latest_row, candidates)
            if pd.isna(value):
                continue
            rows.append(
                {
                    "\u62a5\u544a\u65e5": latest_row.get(report_column),
                    "\u9879\u76ee": display_name,
                    "\u6570\u503c": value,
                    **metadata,
                }
            )
        return rows

    def _build_section(self, key: str, title: str, frame: pd.DataFrame) -> dict[str, Any] | None:
        if frame is None or frame.empty:
            return None
        return {"key": key, "title": title, "rows": frame.to_dict(orient="records")}

    def _period_label_from_date(self, report_date: pd.Timestamp | None) -> str | None:
        if report_date is None:
            return None
        year = report_date.year
        month = report_date.month
        if month == 3:
            return f"{year}\u4e00\u5b63"
        if month == 6:
            return f"{year}\u534a\u5e74\u62a5"
        if month == 9:
            return f"{year}\u4e09\u5b63"
        if month == 12:
            return f"{year}\u5e74\u62a5"
        return None

    def _upcoming_periods(self, latest_report_date: pd.Timestamp | None) -> list[str]:
        if latest_report_date is None:
            return []
        year = latest_report_date.year
        month = latest_report_date.month
        if month == 3:
            return [f"{year}\u534a\u5e74\u62a5", f"{year}\u4e09\u5b63"]
        if month == 6:
            return [f"{year}\u4e09\u5b63", f"{year}\u5e74\u62a5"]
        if month == 9:
            return [f"{year}\u5e74\u62a5", f"{year + 1}\u4e00\u5b63"]
        if month == 12:
            return [f"{year + 1}\u4e00\u5b63", f"{year + 1}\u534a\u5e74\u62a5"]
        return []

    def _latest_booking_date(self, row: pd.Series) -> Any:
        for column in ["\u4e09\u6b21\u53d8\u66f4", "\u4e8c\u6b21\u53d8\u66f4", "\u521d\u6b21\u53d8\u66f4", "\u9996\u6b21\u9884\u7ea6"]:
            if column in row.index and pd.notna(row.get(column)):
                return row.get(column)
        return pd.NA

    def _fetch_disclosure_rows(self, symbol: str, periods: list[str]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if not periods:
            return rows

        market = self._disclosure_market(symbol)
        for period in periods:
            frame = self._clean_frame(self._safe_fetch(ak.stock_report_disclosure, market=market, period=period))
            if frame.empty or "\u80a1\u7968\u4ee3\u7801" not in frame.columns:
                continue

            matched = frame[frame["\u80a1\u7968\u4ee3\u7801"].astype(str).str.zfill(6) == symbol]
            if matched.empty:
                continue

            row = matched.iloc[0]
            actual_disclosure = row.get("\u5b9e\u9645\u62ab\u9732")
            latest_booking = self._latest_booking_date(row)
            status = (
                "\u5df2\u62ab\u9732"
                if pd.notna(actual_disclosure)
                else "\u9884\u7ea6\u4e2d"
                if pd.notna(latest_booking)
                else "\u6682\u65e0\u9884\u7ea6"
            )
            explanation = (
                f"\u5df2\u4e8e {actual_disclosure} \u62ab\u9732"
                if pd.notna(actual_disclosure)
                else f"\u8ba1\u5212\u4e8e {latest_booking} \u62ab\u9732"
                if pd.notna(latest_booking)
                else "\u672a\u5728\u5f53\u524d\u516c\u5f00\u6570\u636e\u6e90\u4e2d\u67e5\u5230\u9884\u7ea6\u4fe1\u606f"
            )
            rows.append(
                {
                    "\u62a5\u544a\u671f": period,
                    "\u62ab\u9732\u72b6\u6001": status,
                    "\u6700\u65b0\u9884\u7ea6": latest_booking,
                    "\u5b9e\u9645\u62ab\u9732": actual_disclosure,
                    "\u8bf4\u660e": explanation,
                }
            )
        return rows

    def get_financial_table(self, symbol_raw: str) -> FinancialTableDTO | None:
        symbol = self._resolve_symbol(symbol_raw)
        if symbol is None:
            return FinancialTableDTO(
                error=f"\u672a\u80fd\u4ece\u5f53\u524d\u6807\u7684\u4e2d\u89e3\u6790\u51fa\u6709\u6548\u80a1\u7968\u4ee3\u7801: {symbol_raw}",
                source="AkShare",
                unit_hint="\u5143/\u6bd4\u7387",
            )

        market_symbol_upper = self._market_symbol(symbol, upper=True)
        market_symbol_lower = self._market_symbol(symbol, upper=False)

        summary_frame = self._trim_recent_periods(
            self._clean_frame(self._safe_fetch(ak.stock_financial_abstract_ths, symbol=symbol)),
            ["\u62a5\u544a\u671f"],
            limit=8,
        )
        summary_frame = self._drop_sparse_columns(summary_frame, keep_columns=["\u62a5\u544a\u671f"], min_non_null_ratio=0.35)
        latest_summary_date = self._latest_date(summary_frame, ["\u62a5\u544a\u671f"])

        balance_sina = self._trim_recent_periods(
            self._clean_frame(
                self._safe_fetch(ak.stock_financial_report_sina, stock=market_symbol_lower, symbol="\u8d44\u4ea7\u8d1f\u503a\u8868")
            ),
            ["\u62a5\u544a\u65e5"],
            limit=1,
        )
        income_sina = self._trim_recent_periods(
            self._clean_frame(
                self._safe_fetch(ak.stock_financial_report_sina, stock=market_symbol_lower, symbol="\u5229\u6da6\u8868")
            ),
            ["\u62a5\u544a\u65e5"],
            limit=1,
        )
        cashflow_sina = self._trim_recent_periods(
            self._clean_frame(
                self._safe_fetch(ak.stock_financial_report_sina, stock=market_symbol_lower, symbol="\u73b0\u91d1\u6d41\u91cf\u8868")
            ),
            ["\u62a5\u544a\u65e5"],
            limit=1,
        )

        latest_sina_date = max(
            [
                date
                for date in [
                    self._latest_date(balance_sina, ["\u62a5\u544a\u65e5"]),
                    self._latest_date(income_sina, ["\u62a5\u544a\u65e5"]),
                    self._latest_date(cashflow_sina, ["\u62a5\u544a\u65e5"]),
                ]
                if date is not None
            ],
            default=None,
        )

        use_em_statements = latest_summary_date is not None and (
            latest_sina_date is None or latest_summary_date > latest_sina_date
        )

        sources = {"AkShare", "\u540c\u82b1\u987a"}

        if use_em_statements:
            balance_em = self._trim_recent_periods(
                self._clean_frame(self._safe_fetch(ak.stock_balance_sheet_by_report_em, symbol=market_symbol_upper)),
                ["REPORT_DATE"],
                limit=1,
            )
            income_em = self._trim_recent_periods(
                self._clean_frame(self._safe_fetch(ak.stock_profit_sheet_by_report_em, symbol=market_symbol_upper)),
                ["REPORT_DATE"],
                limit=1,
            )
            cashflow_em = self._trim_recent_periods(
                self._clean_frame(self._safe_fetch(ak.stock_cash_flow_sheet_by_report_em, symbol=market_symbol_upper)),
                ["REPORT_DATE"],
                limit=1,
            )

            balance_frame = self._pick_latest_frame(balance_em, balance_sina, ["REPORT_DATE", "\u62a5\u544a\u65e5"])
            income_frame = self._pick_latest_frame(income_em, income_sina, ["REPORT_DATE", "\u62a5\u544a\u65e5"])
            cashflow_frame = self._pick_latest_frame(cashflow_em, cashflow_sina, ["REPORT_DATE", "\u62a5\u544a\u65e5"])

            balance_rows = self._statement_to_core_rows(
                balance_frame,
                "REPORT_DATE" if "REPORT_DATE" in balance_frame.columns else "\u62a5\u544a\u65e5",
                BALANCE_METRICS,
                "\u4e1c\u65b9\u8d22\u5bcc" if "REPORT_DATE" in balance_frame.columns else "\u65b0\u6d6a\u8d22\u7ecf",
            )
            income_rows = self._statement_to_core_rows(
                income_frame,
                "REPORT_DATE" if "REPORT_DATE" in income_frame.columns else "\u62a5\u544a\u65e5",
                INCOME_METRICS,
                "\u4e1c\u65b9\u8d22\u5bcc" if "REPORT_DATE" in income_frame.columns else "\u65b0\u6d6a\u8d22\u7ecf",
            )
            cashflow_rows = self._statement_to_core_rows(
                cashflow_frame,
                "REPORT_DATE" if "REPORT_DATE" in cashflow_frame.columns else "\u62a5\u544a\u65e5",
                CASHFLOW_METRICS,
                "\u4e1c\u65b9\u8d22\u5bcc" if "REPORT_DATE" in cashflow_frame.columns else "\u65b0\u6d6a\u8d22\u7ecf",
            )
            if balance_rows or income_rows or cashflow_rows:
                sources.add("\u4e1c\u65b9\u8d22\u5bcc")
        else:
            balance_rows = self._statement_to_core_rows(balance_sina, "\u62a5\u544a\u65e5", BALANCE_METRICS, "\u65b0\u6d6a\u8d22\u7ecf")
            income_rows = self._statement_to_core_rows(income_sina, "\u62a5\u544a\u65e5", INCOME_METRICS, "\u65b0\u6d6a\u8d22\u7ecf")
            cashflow_rows = self._statement_to_core_rows(cashflow_sina, "\u62a5\u544a\u65e5", CASHFLOW_METRICS, "\u65b0\u6d6a\u8d22\u7ecf")
            if balance_rows or income_rows or cashflow_rows:
                sources.add("\u65b0\u6d6a\u8d22\u7ecf")

        latest_statement_date = max(
            [
                date
                for date in [
                    self._latest_date(pd.DataFrame(balance_rows), ["\u62a5\u544a\u65e5"]),
                    self._latest_date(pd.DataFrame(income_rows), ["\u62a5\u544a\u65e5"]),
                    self._latest_date(pd.DataFrame(cashflow_rows), ["\u62a5\u544a\u65e5"]),
                    latest_summary_date,
                ]
                if date is not None
            ],
            default=None,
        )

        disclosure_rows = self._fetch_disclosure_rows(
            symbol,
            [
                period
                for period in [self._period_label_from_date(latest_statement_date), *self._upcoming_periods(latest_statement_date)]
                if period
            ],
        )
        if disclosure_rows:
            sources.add("\u5de8\u6f6e\u8d44\u8baf")

        sections = [
            section
            for section in [
                self._build_section("summary", SUMMARY_TITLE, summary_frame),
                self._build_section("disclosure", DISCLOSURE_TITLE, pd.DataFrame(disclosure_rows)),
                self._build_section("balance_sheet", BALANCE_TITLE, pd.DataFrame(balance_rows)),
                self._build_section("income_statement", INCOME_TITLE, pd.DataFrame(income_rows)),
                self._build_section("cashflow_statement", CASHFLOW_TITLE, pd.DataFrame(cashflow_rows)),
            ]
            if section is not None and self._frame_non_null_ratio(pd.DataFrame(section["rows"])) >= 0.2
        ]

        if not sections:
            return FinancialTableDTO(
                error="\u6682\u672a\u4ece\u516c\u5f00\u6570\u636e\u6e90\u83b7\u53d6\u5230\u8be5\u516c\u53f8\u7684\u8d22\u52a1\u62a5\u8868\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\uff0c\u6216\u76f4\u63a5\u4f7f\u7528 6 \u4f4d\u80a1\u7968\u4ee3\u7801\u67e5\u8be2\u3002",
                source="AkShare",
                unit_hint="\u5143/\u6bd4\u7387",
            )

        summary_rows = sections[0]["rows"] if sections else []
        return FinancialTableDTO(
            data=summary_rows,
            sections=sections,
            source=" / ".join(sorted(sources)),
            unit_hint="\u5143/\u6bd4\u7387",
        )
