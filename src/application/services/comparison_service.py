from __future__ import annotations

from dataclasses import dataclass, field
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
        [Metric("净资产收益率(%)", "ROE"), Metric("销售净利率(%)", "净利率"), Metric("资产负债率(%)", "负债率")]
    ),
    "银行业": TrackTemplate(
        "金融机构经营效能",
        "资产质量与报酬水平对标",
        [Metric("净资产收益率(%)", "ROE"), Metric("基本每股收益(元)", "EPS"), Metric("总资产周转率(次)", "周转率")]
    ),
    "零售业": TrackTemplate(
        "现代零售与供应链效率",
        "周转能力与营运利润对标",
        [Metric("净资产收益率(%)", "ROE"), Metric("销售净利率(%)", "净利率"), Metric("资产负债率(%)", "负债率")]
    ),
    "互联网": TrackTemplate(
        "数智化成长与盈收力",
        "边际效益与研发密度",
        [Metric("净资产收益率(%)", "ROE"), Metric("销售净利率(%)", "盈收比"), Metric("资产负债率(%)", "负债率")]
    ),
    "白酒": TrackTemplate(
        "消费品品牌力与现金流",
        "品牌溢价与渠道回款对标",
        [Metric("净资产收益率(%)", "ROE"), Metric("销售毛利率(%)", "毛利率"), Metric("销售净利率(%)", "净利率")]
    ),
    "汽车": TrackTemplate(
        "先进制造与规模效应",
        "产能利用与边际成本对标",
        [Metric("净资产收益率(%)", "ROE"), Metric("存货周转天数(天)", "周转天数"), Metric("资产负债率(%)", "负债率")]
    ),
    "电力": TrackTemplate(
        "公用事业稳定性",
        "负债结构与现金流稳定性对标",
        [Metric("资产负债率(%)", "负债率"), Metric("销售净利率(%)", "净利率"), Metric("净资产收益率(%)", "ROE")]
    )
}


class ComparisonService:
    FALLBACK_PEER_MAP = {
        "300750": [
            ("300750", "宁德时代"),
            ("002594", "比亚迪"),
            ("300014", "亿纬锂能"),
            ("300207", "欣旺达"),
            ("002074", "国轩高科"),
            ("688567", "孚能科技"),
        ],
        "300760": [
            ("300760", "迈瑞医疗"),
            ("002223", "鱼跃医疗"),
            ("300003", "乐普医疗"),
            ("688271", "联影医疗"),
            ("300347", "泰格医药"),
        ],
        "002415": [
            ("002415", "海康威视"),
            ("002236", "大华股份"),
            ("688475", "萤石网络"),
            ("300496", "中科创达"),
        ],
    }

    def __init__(self):
        self.agent = DoubaoAgent()

    def get_peer_snapshots_for_symbol(self, symbol, limit=10):
        df = get_industry_peers_data(symbol, limit=limit)
        if df.empty:
            fallback_rows = self._build_fallback_snapshots(symbol, limit=limit)
            return fallback_rows
        return df.to_dict("records")

    def _build_fallback_snapshots(self, symbol: str, limit: int = 10):
        peer_candidates = self.FALLBACK_PEER_MAP.get(symbol, [])[:limit]
        snapshots: list[dict[str, Any]] = []
        for peer_code, peer_name in peer_candidates:
            try:
                indicators = ak.stock_financial_analysis_indicator_em(symbol=peer_code)
                latest = indicators.iloc[0]
                snapshots.append(
                    {
                        "名称": peer_name,
                        "代码": peer_code,
                        "净资产收益率(%)": float(latest.get("摊薄净资产收益率(%)", 0) or 0),
                        "销售净利率(%)": float(latest.get("销售净利率(%)", 0) or 0),
                        "资产负债率(%)": float(latest.get("资产负债率(%)", 0) or 0),
                    }
                )
            except Exception:
                continue
        return snapshots

    def get_track_template_for_symbol(self, symbol):
        try:
            info = ak.stock_individual_info_em(symbol=symbol)
            # 获取行业属性，支持模糊匹配模板键
            industry = "默认"
            if "行业" in info["item"].values:
                industry_val = info[info["item"] == "行业"]["value"].values[0]
                industry = str(industry_val)
            
            # 优先匹配具体行业关键词
            for key, template in INDUSTRY_TEMPLATES.items():
                if key != "默认" and key in industry:
                    return template
            return INDUSTRY_TEMPLATES["默认"]
        except:
            return INDUSTRY_TEMPLATES["默认"]

    def build_track_chart_specs(self, symbol, limit=10, max_metrics=4):
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
            values = pd.to_numeric(frame[metric.key], errors="coerce").fillna(0.0)
            if values.empty:
                continue

            leader_index = values.idxmax() if metric.is_positive else values.idxmin()
            leader_name = str(frame.loc[leader_index, "名称"])
            leader_value = float(values.loc[leader_index])
            direction = "最高" if metric.is_positive else "最低"

            chart_specs.append(
                {
                    "title": f"{metric.display_name} 行业对标",
                    "chart_type": "bar",
                    "x_labels": x_labels,
                    "datasets": [
                        {
                            "name": metric.display_name,
                            "data": [round(float(value), 2) for value in values.tolist()],
                        }
                    ],
                    "analyst_verdict": (
                        f"{leader_name} 在 {metric.display_name} 维度处于样本中{direction}位，"
                        f"当前值约为 {leader_value:.2f}。"
                    ),
                    "strategic_highlight": f"样本数 {len(x_labels)} | 核心指标对标",
                }
            )

        return chart_specs

    def snapshots_to_focused_dataframe(self, snapshots, track_template):
        if not snapshots:
            return pd.DataFrame()
        frame = pd.DataFrame(snapshots)
        if track_template is None or frame.empty:
            return frame
        desired_columns = ["名称", "代码"] + [metric.key for metric in track_template.metrics]
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
