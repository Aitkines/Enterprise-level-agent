from __future__ import annotations

from typing import Any

import pandas as pd


class DataQualityService:
    def build_track_data_quality(self, snapshots, metric_keys, metric_display_map):
        if not snapshots:
            return {
                "sample_count": 0,
                "overall_coverage": 0.0,
                "metric_rows": [],
                "source_stats": [],
                "latest_period_stats": [],
            }

        frame = pd.DataFrame(snapshots)
        sample_count = len(frame.index)
        metric_rows: list[dict[str, Any]] = []
        coverage_values: list[float] = []

        for metric_key in metric_keys:
            if metric_key not in frame.columns:
                metric_rows.append(
                    {
                        "metric": metric_display_map.get(metric_key, metric_key),
                        "coverage": 0.0,
                        "missing_count": sample_count,
                    }
                )
                coverage_values.append(0.0)
                continue

            numeric_series = pd.to_numeric(frame[metric_key], errors="coerce")
            valid_count = int(numeric_series.notna().sum())
            missing_count = int(sample_count - valid_count)
            coverage = float(valid_count / sample_count) if sample_count else 0.0
            coverage_values.append(coverage)
            metric_rows.append(
                {
                    "metric": metric_display_map.get(metric_key, metric_key),
                    "coverage": round(coverage, 4),
                    "missing_count": missing_count,
                }
            )

        overall_coverage = sum(coverage_values) / len(coverage_values) if coverage_values else 0.0

        return {
            "sample_count": sample_count,
            "overall_coverage": round(overall_coverage, 4),
            "metric_rows": metric_rows,
            "source_stats": [],
            "latest_period_stats": [],
        }
