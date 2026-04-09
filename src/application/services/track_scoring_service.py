from __future__ import annotations

import math
from typing import Any

import pandas as pd


class TrackScoringService:
    def _normalize_symbol(self, value: str | None) -> str:
        if not value:
            return ""
        digits = "".join(ch for ch in str(value) if ch.isdigit())
        return digits[:6] if len(digits) >= 6 else str(value).strip()

    def _build_metric_frame(self, snapshots, track_template):
        frame = pd.DataFrame(snapshots)
        metric_keys = [metric.key for metric in track_template.metrics]
        if frame.empty or "名称" not in frame.columns:
            return frame, metric_keys, []

        usable_metrics: list[str] = []
        for metric in track_template.metrics:
            if metric.key not in frame.columns:
                continue
            series = pd.to_numeric(frame[metric.key], errors="coerce")
            if int(series.notna().sum()) < 2:
                continue
            if int(series.dropna().nunique()) <= 1:
                continue
            usable_metrics.append(metric.key)

        return frame, metric_keys, usable_metrics

    def _build_weights(self, metric_frame: pd.DataFrame) -> pd.Series:
        if metric_frame.empty:
            return pd.Series(dtype=float)
        if len(metric_frame.columns) == 1:
            return pd.Series([1.0], index=metric_frame.columns, dtype=float)

        dispersion = metric_frame.std(ddof=0).replace(0, pd.NA).dropna()
        if dispersion.empty:
            equal_weight = 1.0 / len(metric_frame.columns)
            return pd.Series([equal_weight] * len(metric_frame.columns), index=metric_frame.columns, dtype=float)

        dispersion = dispersion.reindex(metric_frame.columns).fillna(float(dispersion.mean()))
        total = float(dispersion.sum())
        if not math.isfinite(total) or total <= 0:
            equal_weight = 1.0 / len(metric_frame.columns)
            return pd.Series([equal_weight] * len(metric_frame.columns), index=metric_frame.columns, dtype=float)
        return dispersion / total

    def _score_frame(self, metric_frame: pd.DataFrame, track_template) -> tuple[pd.DataFrame, pd.Series]:
        weights = self._build_weights(metric_frame)
        normalized = pd.DataFrame(index=metric_frame.index)

        for metric in track_template.metrics:
            if metric.key not in metric_frame.columns:
                continue
            series = metric_frame[metric.key].astype(float)
            col_min = float(series.min())
            col_max = float(series.max())
            if not math.isfinite(col_min) or not math.isfinite(col_max) or col_max == col_min:
                normalized[metric.key] = 0.5
                continue

            if metric.is_positive:
                normalized[metric.key] = (series - col_min) / (col_max - col_min)
            else:
                normalized[metric.key] = (col_max - series) / (col_max - col_min)

        weighted_scores = normalized.mul(weights, axis=1).sum(axis=1)
        result = pd.DataFrame(
            {
                "名称": metric_frame.index,
                "综合得分": weighted_scores,
            }
        ).sort_values(by="综合得分", ascending=False)
        result["排名"] = range(1, len(result) + 1)
        result = result[["排名", "名称", "综合得分"]]
        return result, weights

    def _build_reason_lines(self, target_row: pd.Series, metric_frame: pd.DataFrame, track_template) -> tuple[list[str], list[str]]:
        strengths: list[str] = []
        weaknesses: list[str] = []
        sample_count = len(metric_frame.index)

        for metric in track_template.metrics:
            if metric.key not in metric_frame.columns:
                continue
            series = metric_frame[metric.key].astype(float)
            if target_row.name not in series.index:
                continue

            rank_series = series.rank(ascending=not metric.is_positive, method="min")
            rank = int(rank_series.loc[target_row.name])
            label = metric.display_name

            if rank <= max(1, math.ceil(sample_count / 3)):
                strengths.append(f"{label}处于样本前列")
            elif rank >= max(2, sample_count - math.floor(sample_count / 3)):
                weaknesses.append(f"{label}处于样本后段")

        return strengths[:2], weaknesses[:2]

    def score_snapshots(self, symbol: str, snapshots, track_template):
        if not snapshots or not track_template:
            return {
                "status": "limited",
                "summary": "当前还没有形成可用的同赛道样本，暂时无法输出综合评估。",
                "conclusion": "建议先等待同行样本加载完成，再根据横向数据判断相对位置。",
                "reason_lines": ["系统尚未获取到足够的可比公司数据。"],
                "ranking_rows": [],
                "weight_rows": [],
            }

        frame, metric_keys, usable_metrics = self._build_metric_frame(snapshots, track_template)
        sample_count = len(frame.index)

        if sample_count < 2 or not usable_metrics:
            return {
                "status": "limited",
                "summary": "当前可比样本或有效指标不足，暂不形成稳定综合排名。",
                "conclusion": "可以先参考上方图表和同行快照；待更多公司或指标补齐后，再看综合得分会更稳。",
                "reason_lines": [
                    f"当前样本数为 {sample_count}，有效评分指标数为 {len(usable_metrics)}。",
                ],
                "ranking_rows": [],
                "weight_rows": [],
            }

        metric_frame = frame.set_index("名称")[usable_metrics].apply(pd.to_numeric, errors="coerce")
        metric_frame = metric_frame.apply(lambda column: column.fillna(column.median()), axis=0)

        ranking_df, weights = self._score_frame(metric_frame, track_template)
        ranking_rows = ranking_df.copy()
        ranking_rows["综合得分"] = ranking_rows["综合得分"].map(lambda value: round(float(value), 4))

        weight_rows = []
        for metric in track_template.metrics:
            if metric.key not in weights.index:
                continue
            weight_rows.append(
                {
                    "指标": metric.display_name,
                    "权重": f"{float(weights.loc[metric.key]) * 100:.1f}%",
                }
            )

        normalized_symbol = self._normalize_symbol(symbol)
        target_row = frame[frame["代码"].astype(str).str.contains(normalized_symbol, regex=False, na=False)]
        target_name = str(target_row.iloc[0]["名称"]) if not target_row.empty else str(ranking_rows.iloc[0]["名称"])
        target_rank_row = ranking_rows[ranking_rows["名称"] == target_name]
        target_rank = int(target_rank_row.iloc[0]["排名"]) if not target_rank_row.empty else None
        target_score = float(target_rank_row.iloc[0]["综合得分"]) if not target_rank_row.empty else None

        strength_lines, weakness_lines = self._build_reason_lines(
            metric_frame.loc[target_name],
            metric_frame,
            track_template,
        )

        reasons: list[str] = []
        if strength_lines:
            reasons.append("优势方面：" + "，".join(strength_lines) + "。")
        if weakness_lines:
            reasons.append("短板方面：" + "，".join(weakness_lines) + "。")
        if not reasons:
            reasons.append("当前各核心指标大多处于样本中游，暂未表现出特别突出的领先项或明显短板。")

        summary = (
            f"{target_name}在当前 {sample_count} 家同赛道公司中综合排名第 {target_rank}，"
            f"综合得分为 {target_score:.4f}。"
            if target_rank is not None and target_score is not None
            else f"当前已对 {sample_count} 家同赛道公司完成横向评分。"
        )
        conclusion = (
            f"从同赛道横向对比看，{target_name}目前处于"
            f"{'领先梯队' if target_rank is not None and target_rank <= max(1, math.ceil(sample_count / 3)) else '中间梯队' if target_rank is not None and target_rank < sample_count else '偏后梯队'}，"
            "后续需要结合盈利质量、增长持续性和资产结构变化继续跟踪。"
        )

        return {
            "status": "ready",
            "summary": summary,
            "conclusion": conclusion,
            "reason_lines": reasons,
            "sample_count": sample_count,
            "metric_count": len(usable_metrics),
            "target_name": target_name,
            "target_rank": target_rank,
            "target_score": round(target_score, 4) if target_score is not None else None,
            "ranking_rows": ranking_rows.to_dict(orient="records"),
            "weight_rows": weight_rows,
        }
