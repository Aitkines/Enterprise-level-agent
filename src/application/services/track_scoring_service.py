import pandas as pd
from utils.eval_tools import calculate_topsis, entropy_weight

class TrackScoringService:
    def score_snapshots(self, snapshots, track_template):
        """
        基于 entropy_weight + calculate_topsis 的实时量化评分
        """
        if not snapshots or not track_template:
            return {"ok": False, "reason": "样本数据不足，无法计算评分"}
            
        try:
            df = pd.DataFrame(snapshots)
            if "名称" not in df.columns:
                return {"ok": False, "reason": "无效的数据结构"}
                
            df.set_index("名称", inplace=True)
            
            # 锁定计算所用的指标列
            metric_keys = [m.key for m in track_template.metrics]
            is_positive_flags = [1 if m.is_positive else 0 for m in track_template.metrics]
            
            # 清理数据：只保留我们需要的指标，并确保是数值型
            calc_df = df[metric_keys].apply(pd.to_numeric, errors='coerce').fillna(0)
            
            # 1. 计算各项指标的客观熵权 (展示用)
            weights = entropy_weight(calc_df)
            weight_df = pd.DataFrame({
                "指标": [m.display_name for m in track_template.metrics],
                "客观权重": [f"{w*100:.2f}%" for w in weights.values]
            })
            
            # 2. 执行 TOPSIS 综合评分
            ranked_df = calculate_topsis(calc_df, is_positive=is_positive_flags)
            
            # 3. 结果整理
            display_ranking = ranked_df.reset_index()[["名称", "综合评分"]]
            display_ranking["综合评分"] = display_ranking["综合评分"].map(lambda x: round(float(x), 4))
            display_ranking.sort_values(by="综合评分", ascending=False, inplace=True)
            
            return {
                "ok": True,
                "ranking_df": display_ranking,
                "weight_df": weight_df
            }
        except Exception as e:
            return {"ok": False, "reason": f"评分模型计算异常: {str(e)}"}
