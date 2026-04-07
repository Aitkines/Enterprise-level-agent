import re
import json
from typing import Any, Dict, List

def _auto_visualize_markdown_table(text: str) -> Dict[str, Any] | None:
    """如果检测到 Markdown 表格且含有多行数值，尝试自动转为图表。"""
    try:
        lines = [l.strip() for l in text.splitlines() if "|" in l]
        if len(lines) < 3: return None
        
        headers = [h.strip() for h in lines[0].split("|") if h.strip()]
        if len(headers) < 2: return None
        
        data_rows = []
        for l in lines[2:]:
            cols = [c.strip() for c in l.split("|") if c.strip()]
            if len(cols) == len(headers):
                data_rows.append(cols)
        
        if not data_rows: return None
        
        x_col = headers[0]
        datasets = []
        for i in range(1, len(headers)):
            col_name = headers[i]
            col_data = []
            valid_nums = 0
            for row in data_rows:
                try:
                    val = float(re.sub(r"[^0-9\.\-]", "", row[i]))
                    col_data.append(val)
                    valid_nums += 1
                except:
                    col_data.append(0)
            if valid_nums > 0:
                datasets.append({"name": col_name, "data": col_data})
        
        if not datasets: return None
        
        return {
            "title": "智能提取：指标对比图",
            "chart_type": "bar",
            "x_labels": [row[0] for row in data_rows],
            "datasets": datasets
        }
    except:
        return None

def _extract_data_from_mermaid(text: str) -> Dict[str, Any] | None:
    """万能兜底：从模型误吐的 Mermaid 线图/柱图中提取数据点。"""
    try:
        chart_type = "bar"
        if "line" in text.lower(): chart_type = "line"
        elif "pie" in text.lower(): chart_type = "pie"
        
        title_match = re.search(r"title\s+([^\n]+)", text)
        title = title_match.group(1).strip() if title_match else "智能恢复：对标看板"
        
        x_match = re.search(r"x-axis\s+[^\s]+\s+([^\n]+)", text)
        x_labels = x_match.group(1).strip().split() if x_match else []
        
        datasets = []
        data_lines = re.findall(r"(?:line|bar|pie)\s+([^\d\s\-\u4e00-\u9fa5]*[\u4e00-\u9fa5]+[^\s]*|[^\d\s]+)\s+([\d\.\s\-]+)", text)
        for name, vals in data_lines:
            val_list = [float(v) for v in vals.split() if v.strip()]
            if val_list:
                datasets.append({"name": name.strip(), "data": val_list})
        
        if datasets and x_labels:
            return {
                "title": title,
                "chart_type": chart_type,
                "x_labels": x_labels,
                "datasets": datasets,
                "analyst_verdict": "系统已自动从结构化草稿中恢复可视化决策视图。"
            }
    except:
        pass
    return None

def build_response_payload_from_text(text: str, source: str = "unknown") -> Dict[str, Any]:
    raw_text = str(text or "").strip()
    sources = []
    source_lines = re.findall(r"\[\d+\]\s+(.*)", raw_text)
    if source_lines:
        sources = [s.strip() for s in source_lines]
    
    charts = []
    body_text = raw_text
    
    # 1. 结构化识别 (多模式顺序提取)
    combined_pattern = r"\[CHART_DATA(?:[:：])?\s*({[\s\S]*?})\s*(?:\]|\[/CHART_DATA\])|```(?:json)?\s*({[\s\S]*?\"chart_type\"[\s\S]*?})\s*```"
    
    matches = list(re.finditer(combined_pattern, raw_text))
    for m in matches:
        json_str = m.group(1) or m.group(2)
        if not json_str: continue
        try:
            json_str = json_str.strip().replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
            cd = json.loads(json_str)
            if cd and isinstance(cd, dict) and "chart_type" in cd:
                charts.append(cd)
                body_text = body_text.replace(m.group(0), "")
        except:
            continue
    
    # 2. 强力噪音清理
    body_text = re.sub(r"<div style=[\s\S]*?>[\s\S]*?</div>", "", body_text)
    mermaid_blocks = re.findall(r"```mermaid[\s\S]*?```", body_text)
    if not charts and mermaid_blocks:
        md = _extract_data_from_mermaid(mermaid_blocks[0])
        if md:
            charts.append(md)
    body_text = re.sub(r"```mermaid[\s\S]*?```", "", body_text).strip()
    
    # 3. 后备方案：自动可视化表格
    if not charts:
        ad = _auto_visualize_markdown_table(body_text)
        if ad:
            charts.append(ad)

    if not body_text.strip() and charts:
        body_text = "_📊 深度分析视图已同步至右侧决策轨道。_"

    return {
        "version": "1.0",
        "source": source,
        "raw_text": raw_text,
        "summary": "",
        "body": body_text,
        "sections": [],
        "sources": sources,
        "chart": charts[0] if charts else None,
        "charts": charts
    }
