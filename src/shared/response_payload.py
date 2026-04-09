import json
import re
from typing import Any, Dict, List, Optional, Tuple


ChartPayload = Dict[str, Any]

COMMON_METRIC_TOKENS = (
    "roe",
    "roa",
    "eps",
    "pe",
    "pb",
    "营收",
    "收入",
    "利润",
    "净利",
    "毛利",
    "毛利率",
    "净利率",
    "增长",
    "增速",
    "周转",
    "周转率",
    "乘数",
    "负债",
    "现金流",
    "费用率",
    "产能",
    "销量",
    "吨价",
    "占比",
    "比率",
    "%",
)

LOCALIZATION_RULES: List[Tuple[re.Pattern[str], str]] = [
    (re.compile(r"\brevenue growth rate\b", re.IGNORECASE), "营收增长率"),
    (re.compile(r"\brevenue\b", re.IGNORECASE), "营收"),
    (re.compile(r"\bgross margin\b", re.IGNORECASE), "毛利率"),
    (re.compile(r"\bnet margin\b", re.IGNORECASE), "销售净利率"),
    (re.compile(r"\boperating margin\b", re.IGNORECASE), "营业利润率"),
    (re.compile(r"\basset turnover\b", re.IGNORECASE), "总资产周转率"),
    (re.compile(r"\bequity multiplier\b", re.IGNORECASE), "权益乘数"),
    (re.compile(r"\binventory turnover\b", re.IGNORECASE), "存货周转率"),
    (re.compile(r"\bdebt ratio\b", re.IGNORECASE), "资产负债率"),
    (re.compile(r"\bcomparison\b", re.IGNORECASE), "对比"),
    (re.compile(r"\btrend\b", re.IGNORECASE), "趋势"),
    (re.compile(r"\bperiod\b", re.IGNORECASE), "期间"),
    (re.compile(r"\bcompany\b", re.IGNORECASE), "公司"),
    (re.compile(r"\bmetric\b", re.IGNORECASE), "指标"),
    (re.compile(r"\bvisual brief\b", re.IGNORECASE), "可视化简报"),
    (re.compile(r"\banalyst verdict\b", re.IGNORECASE), "图表结论"),
]

BANNED_VERDICT_PATTERNS = [
    re.compile(r"系统.*恢复可视化"),
    re.compile(r"文本数值回填"),
    re.compile(r"建议结合原始论证"),
    re.compile(r"auto.?recover", re.IGNORECASE),
    re.compile(r"restor", re.IGNORECASE),
]


def _parse_float(raw: Any) -> Optional[float]:
    cleaned = re.sub(r"[^0-9.\-]", "", str(raw or ""))
    if not cleaned or cleaned in {"-", ".", "-."}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _localize_text(text: str) -> str:
    localized = str(text or "").strip()
    for pattern, replacement in LOCALIZATION_RULES:
        localized = pattern.sub(replacement, localized)
    return localized


def _extract_source_lines(raw_text: str) -> List[str]:
    matches = re.findall(r"\[\d+\]\s+(.*)", raw_text)
    return [item.strip() for item in matches if item.strip()]


def _extract_chart_json_blocks(raw_text: str) -> Tuple[List[ChartPayload], str]:
    charts: List[ChartPayload] = []
    body_text = raw_text

    patterns = [
        re.compile(r"\[CHART_DATA\]\s*({[\s\S]*?})\s*\[/CHART_DATA\]", re.IGNORECASE),
        re.compile(r"```(?:json)?\s*({[\s\S]*?\"chart_type\"[\s\S]*?})\s*```", re.IGNORECASE),
    ]

    for pattern in patterns:
        for match in pattern.finditer(raw_text):
            json_text = match.group(1)
            if not json_text:
                continue
            try:
                chart = json.loads(json_text.strip())
            except Exception:
                continue
            if isinstance(chart, dict) and chart.get("chart_type"):
                charts.append(chart)
                body_text = body_text.replace(match.group(0), "")

    return charts, body_text.strip()


def _looks_temporal_axis(labels: List[str]) -> bool:
    if len(labels) < 2:
        return False
    return all(bool(re.fullmatch(r"(19|20)\d{2}", str(label).strip())) for label in labels)


def _contains_metric_token(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(token in lowered for token in COMMON_METRIC_TOKENS)


def _series_names_look_like_metrics(names: List[str]) -> bool:
    if len(names) < 2:
        return False
    return sum(1 for name in names if _contains_metric_token(name)) >= 2


def _metric_name_from_title(title: str, fallback: str) -> str:
    normalized = _localize_text(title)
    normalized = re.sub(r"(趋势对比|趋势图|趋势|对比图|对比|比较图|图表)$", "", normalized).strip(" ：:-")
    return normalized or fallback


def _build_chart(
    title: str,
    x_labels: List[str],
    datasets: List[Dict[str, Any]],
    analyst_verdict: str = "",
    chart_type: str = "line",
    strategic_highlight: str = "",
) -> ChartPayload:
    return {
        "title": title,
        "chart_type": chart_type,
        "x_labels": x_labels,
        "datasets": datasets,
        "analyst_verdict": analyst_verdict,
        "strategic_highlight": strategic_highlight,
    }


def _build_single_series_temporal_verdict(metric_name: str, labels: List[str], values: List[float]) -> str:
    start_label = labels[0]
    end_label = labels[-1]
    start_value = values[0]
    end_value = values[-1]
    delta = end_value - start_value
    if delta > 0:
        direction = "上升"
        implication = "整体表现改善"
    elif delta < 0:
        direction = "下降"
        implication = "整体表现走弱"
    else:
        direction = "基本持平"
        implication = "整体表现较为稳定"
    return (
        f"{start_label}至{end_label}年，{metric_name}由{_format_number(start_value)}"
        f"{direction}至{_format_number(end_value)}，{implication}。"
    )


def _build_category_comparison_verdict(metric_name: str, labels: List[str], values: List[float]) -> str:
    highest_index = max(range(len(values)), key=lambda index: values[index])
    lowest_index = min(range(len(values)), key=lambda index: values[index])
    highest_label = labels[highest_index]
    lowest_label = labels[lowest_index]
    highest_value = values[highest_index]
    lowest_value = values[lowest_index]
    return (
        f"图中显示，{metric_name}在{highest_label}最高，为{_format_number(highest_value)}；"
        f"在{lowest_label}最低，为{_format_number(lowest_value)}。这说明不同对象之间存在明显差异。"
    )


def _build_single_entity_metric_snapshot_verdict(entity_name: str, labels: List[str], values: List[float]) -> str:
    highest_index = max(range(len(values)), key=lambda index: values[index])
    lowest_index = min(range(len(values)), key=lambda index: values[index])
    return (
        f"图中显示，{entity_name}在{labels[highest_index]}上的数值最高，为{_format_number(values[highest_index])}；"
        f"在{labels[lowest_index]}上的数值最低，为{_format_number(values[lowest_index])}。"
        f"这说明该主体不同指标的表现分化较为明显。"
    )


def _build_multi_company_temporal_verdict(
    metric_name: str,
    years: List[str],
    datasets: List[Dict[str, Any]],
) -> str:
    start_year = years[0]
    end_year = years[-1]
    company_segments: List[str] = []
    latest_ranking: List[Tuple[str, float]] = []
    first_year_values: List[Tuple[str, float]] = []

    for dataset in datasets:
        company = str(dataset["name"])
        values = [float(value) for value in dataset["data"]]
        company_segments.append(
            f"{company}由{_format_number(values[0])}变为{_format_number(values[-1])}"
        )
        latest_ranking.append((company, values[-1]))
        first_year_values.append((company, values[0]))

    latest_ranking.sort(key=lambda item: item[1], reverse=True)
    first_year_values.sort(key=lambda item: item[1], reverse=True)

    leader_name, leader_value = latest_ranking[0]
    trailer_name, trailer_value = latest_ranking[-1]
    latest_gap = leader_value - trailer_value
    opening_gap = first_year_values[0][1] - first_year_values[-1][1]

    if len(latest_ranking) == 2:
        gap_phrase = "差距扩大" if latest_gap > opening_gap else "差距收窄" if latest_gap < opening_gap else "差距基本稳定"
    else:
        gap_phrase = f"{leader_name}保持领先"

    return (
        f"{start_year}至{end_year}年，{metric_name}方面，"
        f"{'；'.join(company_segments)}；{end_year}年{leader_name}最高，为{_format_number(leader_value)}，"
        f"{trailer_name}最低，为{_format_number(trailer_value)}，{gap_phrase}。"
    )


def _coerce_numeric_series(values: List[Any]) -> Optional[List[float]]:
    parsed_values: List[float] = []
    for value in values:
        parsed = _parse_float(value)
        if parsed is None:
            return None
        parsed_values.append(parsed)
    return parsed_values if len(parsed_values) >= 2 else None


def _normalize_dataset(raw_dataset: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    name = _localize_text(str(raw_dataset.get("name") or raw_dataset.get("label") or "系列"))
    raw_values = raw_dataset.get("data")
    if not isinstance(raw_values, list):
        return None
    values = _coerce_numeric_series(raw_values)
    if values is None:
        return None
    return {"name": name, "data": values}


def _sanitize_chart(chart: ChartPayload) -> Optional[ChartPayload]:
    x_labels = [_localize_text(str(label)) for label in (chart.get("x_labels") or []) if str(label).strip()]
    raw_datasets = chart.get("datasets") or chart.get("series") or []
    if not isinstance(raw_datasets, list):
        return None

    datasets: List[Dict[str, Any]] = []
    for item in raw_datasets:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_dataset(item)
        if normalized is None:
            continue
        if x_labels and len(normalized["data"]) != len(x_labels):
            continue
        datasets.append(normalized)

    if len(x_labels) < 2 or not datasets:
        return None

    title = _localize_text(str(chart.get("title") or chart.get("chart_name") or "图表"))
    chart_type = str(chart.get("chart_type") or "bar").lower()
    temporal = _looks_temporal_axis(x_labels)

    if chart_type == "line" and not temporal:
        chart_type = "bar"

    if temporal and len(datasets) > 1 and _series_names_look_like_metrics([item["name"] for item in datasets]):
        return None

    metric_name = _metric_name_from_title(title, datasets[0]["name"])

    if temporal and len(datasets) == 1:
        verdict = _build_single_series_temporal_verdict(metric_name, x_labels, datasets[0]["data"])
        highlight = f"{x_labels[0]}-{x_labels[-1]}"
    elif temporal:
        verdict = _build_multi_company_temporal_verdict(metric_name, x_labels, datasets)
        highlight = f"{x_labels[0]}-{x_labels[-1]}"
    elif len(datasets) == 1:
        verdict = _build_category_comparison_verdict(metric_name, x_labels, datasets[0]["data"])
        highlight = "横向对比"
    else:
        latest_values = [dataset["data"][-1] for dataset in datasets]
        verdict = _build_category_comparison_verdict(metric_name, [dataset["name"] for dataset in datasets], latest_values)
        highlight = "横向对比"

    if any(pattern.search(verdict) for pattern in BANNED_VERDICT_PATTERNS):
        verdict = ""

    return _build_chart(
        title=title,
        x_labels=x_labels,
        datasets=datasets,
        analyst_verdict=verdict,
        chart_type=chart_type,
        strategic_highlight=highlight,
    )


def _normalize_explicit_chart(chart: ChartPayload) -> List[ChartPayload]:
    sanitized = _sanitize_chart(chart)
    if sanitized is not None:
        return [sanitized]

    x_labels = [_localize_text(str(label)) for label in (chart.get("x_labels") or []) if str(label).strip()]
    raw_datasets = chart.get("datasets") or chart.get("series") or []
    if not isinstance(raw_datasets, list):
        return []

    datasets: List[Dict[str, Any]] = []
    for item in raw_datasets:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_dataset(item)
        if normalized is None:
            continue
        if x_labels and len(normalized["data"]) != len(x_labels):
            continue
        datasets.append(normalized)

    if len(x_labels) < 2 or len(datasets) < 2:
        return []

    temporal = _looks_temporal_axis(x_labels)
    if not temporal:
        return []

    if not _series_names_look_like_metrics([item["name"] for item in datasets]):
        return []

    split_charts: List[ChartPayload] = []
    for dataset in datasets:
        metric_name = _metric_name_from_title(dataset["name"], dataset["name"])
        split_charts.append(
            _build_chart(
                title=f"{metric_name}趋势图",
                x_labels=x_labels,
                datasets=[dataset],
                analyst_verdict=_build_single_series_temporal_verdict(metric_name, x_labels, dataset["data"]),
                chart_type="line",
                strategic_highlight=f"{x_labels[0]}-{x_labels[-1]}",
            )
        )

    return split_charts


def _split_plain_row(line: str) -> List[str]:
    if "\t" in line:
        return [cell.strip() for cell in re.split(r"\t+", line) if cell.strip()]
    return [cell.strip() for cell in re.split(r"\s{2,}", line) if cell.strip()]


def _table_rows_from_markdown(text: str) -> Optional[Tuple[List[str], List[List[str]]]]:
    lines = [line.strip() for line in text.splitlines() if "|" in line]
    if len(lines) < 3:
        return None

    header = [cell.strip() for cell in lines[0].split("|") if cell.strip()]
    if len(header) < 2:
        return None

    rows: List[List[str]] = []
    for line in lines[2:]:
        cells = [cell.strip() for cell in line.split("|") if cell.strip()]
        if len(cells) == len(header):
            rows.append(cells)

    if not rows:
        return None

    return header, rows


def _table_rows_from_plain_text(text: str) -> Optional[Tuple[List[str], List[List[str]]]]:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        return None

    for index, line in enumerate(lines[:-1]):
        header = _split_plain_row(line)
        if len(header) < 3:
            continue

        rows: List[List[str]] = []
        cursor = index + 1
        while cursor < len(lines):
            current = lines[cursor].strip()
            if current.startswith(("1.", "2.", "3.", "4.", "5.", "-", "*")):
                break
            row = _split_plain_row(current)
            if len(row) != len(header):
                break
            rows.append(row)
            cursor += 1

        if rows:
            return header, rows

    return None


def _chart_signature(chart: ChartPayload) -> str:
    normalized = {
        "title": chart.get("title") or chart.get("chart_name") or "",
        "chart_type": chart.get("chart_type") or "",
        "x_labels": chart.get("x_labels") or [],
        "datasets": [
            {"name": item.get("name"), "data": item.get("data")}
            for item in chart.get("datasets", [])
            if isinstance(item, dict)
        ],
    }
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True)


def _dedupe_charts(charts: List[ChartPayload]) -> List[ChartPayload]:
    seen = set()
    deduped: List[ChartPayload] = []
    for chart in charts:
        signature = _chart_signature(chart)
        if signature in seen:
            continue
        seen.add(signature)
        deduped.append(chart)
    return deduped


def _parse_company_year_header(header: str) -> Optional[Tuple[str, str]]:
    match = re.match(r"^(.*?)(\d{4})$", header.strip())
    if not match:
        return None
    company = match.group(1).strip()
    year = match.group(2)
    if not company:
        return None
    return company, year


def _is_company_year_matrix(headers: List[str]) -> bool:
    parsed = [_parse_company_year_header(header) for header in headers[1:]]
    return len([item for item in parsed if item is not None]) >= 4


def _build_company_year_matrix_charts(headers: List[str], rows: List[List[str]]) -> List[ChartPayload]:
    parsed_headers: List[Tuple[int, str, str]] = []
    for index, header in enumerate(headers[1:], start=1):
        parsed = _parse_company_year_header(header)
        if parsed is None:
            continue
        company, year = parsed
        parsed_headers.append((index, company, year))

    if len(parsed_headers) < 4:
        return []

    company_order: List[str] = []
    year_order: List[str] = []
    for _, company, year in parsed_headers:
        if company not in company_order:
            company_order.append(company)
        if year not in year_order:
            year_order.append(year)
    year_order.sort()

    charts: List[ChartPayload] = []
    for row in rows[:8]:
        metric_name = row[0].strip()
        datasets: List[Dict[str, Any]] = []

        for company in company_order:
            values: List[float] = []
            is_complete = True
            for year in year_order:
                target_index = next(
                    (
                        index
                        for index, company_name, year_value in parsed_headers
                        if company_name == company and year_value == year
                    ),
                    None,
                )
                if target_index is None or target_index >= len(row):
                    is_complete = False
                    break
                parsed_value = _parse_float(row[target_index])
                if parsed_value is None:
                    is_complete = False
                    break
                values.append(parsed_value)

            if is_complete and len(values) >= 2:
                datasets.append({"name": company, "data": values})

        if not datasets:
            continue

        charts.append(
            _build_chart(
                title=f"{metric_name}趋势对比",
                x_labels=year_order,
                datasets=datasets,
                analyst_verdict=_build_multi_company_temporal_verdict(metric_name, year_order, datasets)
                if len(datasets) > 1
                else _build_single_series_temporal_verdict(metric_name, year_order, datasets[0]["data"]),
                chart_type="line",
                strategic_highlight=f"{year_order[0]}-{year_order[-1]}",
            )
        )

    return charts


def _build_standard_table_charts(headers: List[str], rows: List[List[str]]) -> List[ChartPayload]:
    if len(headers) < 2 or not rows:
        return []

    row_labels = [row[0].strip() for row in rows if row and row[0].strip()]
    if len(row_labels) != len(rows):
        return []

    numeric_columns: List[int] = []
    for column_index in range(1, len(headers)):
        parsed_values = [
            _parse_float(row[column_index])
            for row in rows
            if column_index < len(row)
        ]
        numeric_count = len([value for value in parsed_values if value is not None])
        if numeric_count >= max(1, min(2, len(rows))):
            numeric_columns.append(column_index)

    if not numeric_columns:
        return []

    is_temporal = _looks_temporal_axis(row_labels)
    charts: List[ChartPayload] = []

    if len(rows) == 1 and len(numeric_columns) >= 2:
        entity_name = rows[0][0].strip()
        metric_labels: List[str] = []
        values: List[float] = []
        for column_index in numeric_columns[:8]:
            parsed_value = _parse_float(rows[0][column_index])
            if parsed_value is None:
                continue
            metric_labels.append(_localize_text(headers[column_index]))
            values.append(parsed_value)

        if len(values) >= 2:
            charts.append(
                _build_chart(
                    title=f"{entity_name}核心指标对比",
                    x_labels=metric_labels,
                    datasets=[{"name": entity_name, "data": values}],
                    analyst_verdict=_build_single_entity_metric_snapshot_verdict(entity_name, metric_labels, values),
                    chart_type="bar",
                    strategic_highlight="横向对比",
                )
            )
        return charts

    for column_index in numeric_columns[:8]:
        metric_name = _localize_text(headers[column_index])
        values: List[float] = []
        for row in rows:
            if column_index >= len(row):
                values = []
                break
            parsed_value = _parse_float(row[column_index])
            if parsed_value is None:
                values = []
                break
            values.append(parsed_value)

        if len(values) < 2:
            continue

        if is_temporal:
            charts.append(
                _build_chart(
                    title=f"{metric_name}趋势图",
                    x_labels=row_labels,
                    datasets=[{"name": metric_name, "data": values}],
                    analyst_verdict=_build_single_series_temporal_verdict(metric_name, row_labels, values),
                    chart_type="line" if len(values) >= 3 else "bar",
                    strategic_highlight=f"{row_labels[0]}-{row_labels[-1]}",
                )
            )
        else:
            charts.append(
                _build_chart(
                    title=f"{metric_name}对比图",
                    x_labels=row_labels,
                    datasets=[{"name": metric_name, "data": values}],
                    analyst_verdict=_build_category_comparison_verdict(metric_name, row_labels, values),
                    chart_type="bar",
                    strategic_highlight="横向对比",
                )
            )

    return charts


def _auto_visualize_table_charts(text: str) -> List[ChartPayload]:
    parsed = _table_rows_from_markdown(text)
    if not parsed:
        parsed = _table_rows_from_plain_text(text)
    if not parsed:
        return []

    headers, rows = parsed
    if _is_company_year_matrix(headers):
        return _build_company_year_matrix_charts(headers, rows)
    return _build_standard_table_charts(headers, rows)


def build_response_payload_from_text(text: str, source: str = "unknown") -> Dict[str, Any]:
    raw_text = str(text or "").strip()
    charts, body_text = _extract_chart_json_blocks(raw_text)
    sources = _extract_source_lines(raw_text)

    normalized_explicit_charts: List[ChartPayload] = []
    for chart in charts:
        normalized_explicit_charts.extend(_normalize_explicit_chart(chart))
    charts = normalized_explicit_charts

    if not charts:
        charts.extend(_auto_visualize_table_charts(body_text))

    charts = _dedupe_charts(charts)

    return {
        "version": "1.0",
        "source": source,
        "raw_text": raw_text,
        "summary": "",
        "body": body_text,
        "sections": [],
        "sources": sources,
        "chart": charts[0] if charts else None,
        "charts": charts,
    }
