import numpy as np
import pandas as pd

def entropy_weight(data: pd.DataFrame):
    """
    计算熵权
    data: DataFrame, 行是个体 (企业), 列是指标
    """
    # 归一化 (极差法)
    normalized_data = (data - data.min()) / (data.max() - data.min())
    # 稍微加一个小值防止 log(0)
    p = normalized_data / normalized_data.sum(axis=0)
    p = p.replace(0, 1e-12)
    
    # 计算信息熵
    e = - (np.sum(p * np.log(p), axis=0) / np.log(len(data)))
    # 计算冗余度
    d = 1 - e
    # 计算权重
    weights = d / d.sum()
    return weights

def calculate_topsis(data: pd.DataFrame, is_positive: list = None):
    """
    TOPSIS (逼近理想解排序法)
    data: 指标矩阵
    is_positive: 指标是否为正向指标 (1 正向, 0 负向)
    """
    if data is None or data.empty:
        return data

    # 1. 极佳与极差正向化处理 (略过，假设输入已分类)
    # 2. 归一化 (向量归一化)
    norm_data = data / np.sqrt(np.sum(data**2, axis=0))
    
    # 3. 确定权重 (使用熵权法)
    weights = entropy_weight(data)
    
    # 4. 加权归一化
    weighted_norm_data = norm_data * weights
    
    # 5. 确定正、负理想解
    positive_ideal = weighted_norm_data.max() # 正
    negative_ideal = weighted_norm_data.min() # 负
    
    # 如果有负向指标，需要反转该列的理想解
    if is_positive:
        for idx, pos in enumerate(is_positive):
            if not pos:
                col = weighted_norm_data.columns[idx]
                positive_ideal[col] = weighted_norm_data[col].min()
                negative_ideal[col] = weighted_norm_data[col].max()

    # 6. 计算到理想解的欧式距离
    d_plus = np.sqrt(np.sum((weighted_norm_data - positive_ideal)**2, axis=1))
    d_minus = np.sqrt(np.sum((weighted_norm_data - negative_ideal)**2, axis=1))
    
    # 7. 计算相对接近度 C (分数)
    score = d_minus / (d_plus + d_minus)
    
    # 保存结果
    result = data.copy()
    result["综合评分"] = score
    result = result.sort_values(by="综合评分", ascending=False)
    
    return result

if __name__ == "__main__":
    # 测试
    test_data = pd.DataFrame({
        "净资产收益率": [15, 20, 10, 25],
        "销售净利率": [12, 18, 8, 22],
        "资产负债率": [40, 50, 30, 60] # 对于负债率，通常越低越好 (负向指标)
    }, index=["企业A", "企业B", "企业C", "企业D"])
    
    res = calculate_topsis(test_data, is_positive=[1, 1, 0])
    print(res)
