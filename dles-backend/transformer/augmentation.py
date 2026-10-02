# -*- coding: utf-8 -*-
"""论文算法 2：对数据湖里的一张表做数据增强，得到对比学习的正样本"""
import numpy as np
import pandas as pd


def read_table(path: str) -> pd.DataFrame:
    # 全部按字符串读取，保证增强后写出的文本和原表一致
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding_errors='replace',
                       on_bad_lines='skip', low_memory=False)


def augment_table(df: pd.DataFrame, rng: np.random.Generator, swap_ratio: float = 0.3, noise_level: float = 0.1):
    """
    1. 交换单元格：随机选一列，交换这一列里的两个单元格，重复 swap_ratio × 行数 次（只打乱行的组合，不改变列的取值分布）；
    2. 数值列注入噪声：加上均值 0、标准差为 noise_level × 该列标准差的高斯噪声。
    返回 (表头列表, 行列表)
    """
    headers = [str(c) for c in df.columns]
    values = df.to_numpy(dtype=object, copy=True)
    n_rows, n_cols = values.shape
    if n_rows == 0 or n_cols == 0:
        return headers, values.tolist()

    n_swaps = int(swap_ratio * n_rows)
    swap_cols = rng.integers(0, n_cols, n_swaps)
    rows_a = rng.integers(0, n_rows, n_swaps)
    rows_b = rng.integers(0, n_rows, n_swaps)
    for c, a, b in zip(swap_cols, rows_a, rows_b):
        values[a, c], values[b, c] = values[b, c], values[a, c]

    for c in range(n_cols):
        numeric = pd.to_numeric(pd.Series(values[:, c]).replace('', np.nan), errors='coerce')
        non_empty = (values[:, c] != '').sum()
        if non_empty == 0 or numeric.notna().sum() < 0.9 * non_empty:
            continue  # 不是数值列
        noisy = numeric + rng.normal(0.0, noise_level * (numeric.std() or 0.0), len(numeric))
        is_integer = bool((numeric.dropna() % 1 == 0).all())
        formatted = noisy.round(0).astype('Int64').astype(str) if is_integer else noisy.round(4).astype(str)
        mask = numeric.notna().to_numpy()
        values[mask, c] = formatted.to_numpy()[mask]
    return headers, values.tolist()
