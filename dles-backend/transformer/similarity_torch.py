# -*- coding: utf-8 -*-
"""
表格相似度的 PyTorch 批量实现，和 enhance/.../similarity.py（numpy 版）的定义一致：
  1. 列与列之间算余弦相似度，小于阈值（0）的记为 1e-9；
  2. 用 Sinkhorn-Knopp 迭代把相似度矩阵近似成双随机矩阵；
  3. 在归一化后的矩阵上贪心地选出 min(n, m) 对列匹配；
  4. 表格相似度 = 被选中的匹配对的原始余弦相似度之和 / max(n, m)（论文公式 3.4）。
训练时用它构造对比损失（匹配的选择不求导，梯度通过被选中的余弦相似度回传），评估时用它批量排序。
"""
import torch
import torch.nn.functional as F


def pad_tables(tables, max_cols: int = None, device='cpu', pad_to: int = None):
    """把列数不同的表格（每个是 (n_i, D) 的张量）补齐成 (b, N, D)，并返回 (b, N) 的有效列掩码"""
    n_max = pad_to or max(t.shape[0] for t in tables)
    if max_cols is not None:
        n_max = min(n_max, max_cols)
    dim = tables[0].shape[1]
    x = torch.zeros(len(tables), n_max, dim, device=device)
    mask = torch.zeros(len(tables), n_max, dtype=torch.bool, device=device)
    for i, t in enumerate(tables):
        n = min(t.shape[0], n_max)
        x[i, :n] = t[:n]
        mask[i, :n] = True
    return x, mask


def table_similarity(a, mask_a, b, mask_b, sinkhorn_iters: int = 10, threshold: float = 0.0):
    """
    a: (A, N, D)，mask_a: (A, N)；b: (B, M, D)，mask_b: (B, M)
    返回 (A, B)：a 中每张表和 b 中每张表的相似度
    """
    a = F.normalize(a, dim=-1)
    b = F.normalize(b, dim=-1)
    cos = torch.einsum('and,bmd->abnm', a, b)  # (A, B, N, M)
    valid = (mask_a[:, None, :, None] & mask_b[None, :, None, :])  # (A, B, N, M)
    sim = torch.where(cos < threshold, torch.full_like(cos, 1e-9), cos)
    sim = sim * valid

    # Sinkhorn-Knopp：交替做行归一化和列归一化（只用来决定匹配，不参与求导）
    with torch.no_grad():
        p = sim.clone()
        for _ in range(sinkhorn_iters):
            p = p / (p.sum(dim=-1, keepdim=True) + 1e-12)
            p = p / (p.sum(dim=-2, keepdim=True) + 1e-12)
            p = p * valid

        n_a = mask_a.sum(-1)  # (A,)
        n_b = mask_b.sum(-1)  # (B,)
        k = torch.minimum(n_a[:, None], n_b[None, :])  # (A, B) 每对表格要选出的匹配数
        n_cols, m_cols = sim.shape[-2], sim.shape[-1]
        flat = p.reshape(p.shape[0], p.shape[1], n_cols * m_cols)
        rows = torch.arange(n_cols, device=sim.device)[:, None].expand(n_cols, m_cols).reshape(-1)
        cols = torch.arange(m_cols, device=sim.device)[None, :].expand(n_cols, m_cols).reshape(-1)
        chosen = []  # 每一轮选中的位置 (A, B) 和这一轮是否有效 (A, B)
        for step in range(min(n_cols, m_cols)):
            idx = flat.argmax(dim=-1)  # (A, B)
            chosen.append((idx, step < k))
            # 选中的行和列都清零，保证每一列只匹配一次
            row_i, col_j = rows[idx], cols[idx]
            flat = flat.masked_fill((rows[None, None, :] == row_i[..., None]) | (cols[None, None, :] == col_j[..., None]), 0.0)

    flat_sim = sim.reshape(sim.shape[0], sim.shape[1], n_cols * m_cols)
    total = torch.zeros(sim.shape[0], sim.shape[1], device=sim.device)
    for idx, is_valid in chosen:
        total = total + flat_sim.gather(-1, idx[..., None]).squeeze(-1) * is_valid
    return total / torch.maximum(n_a[:, None], n_b[None, :]).clamp(min=1)


def nt_xent_loss(view1, mask1, view2, mask2, temperature: float = 0.1, raw_views=None, fn_alpha: float = None):
    """
    论文公式 (3.1)(3.2) 的 NT-Xent：同一张表的两个视图是正样本，批次里其他表格的所有视图都是负样本。
    view1/view2: (b, N, D)，是 Transformer 的输出。

    数据湖里常有大量互相相关的表（比如同一张原表切出来的很多张表），把它们全当成负样本会把相关表推开（假负样本）。
    传入 raw_views=(原始向量1, 原始向量2) 和 fn_alpha 时启用假负样本消除：
    如果某个“负样本”和锚点在原始嵌入空间里的相似度已经达到正样本相似度的 fn_alpha 倍以上，
    就认为它很可能是相关表，不再把它当作负样本推开。这一步不需要任何标注。
    """
    b = view1.shape[0]
    x = torch.cat([view1, view2], dim=0)
    mask = torch.cat([mask1, mask2], dim=0)
    sim = table_similarity(x, mask, x, mask) / temperature  # (2b, 2b)
    eye = torch.eye(2 * b, dtype=torch.bool, device=sim.device)
    target = torch.cat([torch.arange(b, 2 * b), torch.arange(0, b)]).to(sim.device)
    if raw_views is not None and fn_alpha is not None:
        with torch.no_grad():
            raw = torch.cat(raw_views, dim=0)
            raw_sim = table_similarity(raw, mask, raw, mask)
            positive_sim = raw_sim.gather(1, target[:, None])  # (2b, 1)
            is_positive = torch.zeros_like(eye)
            is_positive[torch.arange(2 * b, device=sim.device), target] = True
            false_negative = (raw_sim > fn_alpha * positive_sim) & ~is_positive & ~eye
        sim = sim.masked_fill(false_negative, float('-inf'))
    sim = sim.masked_fill(eye, float('-inf'))
    return F.cross_entropy(sim, target)


@torch.no_grad()
def pairwise_distance_matrix(tables, device='cpu', max_cols: int = 64, chunk: int = 8):
    """
    数据湖里所有表格两两之间的距离矩阵（numpy 版 Similarity.calc_distance 的批量 GPU 实现），
    距离 = max(n, m) / 匹配相似度之和 = 1 / 表格相似度。
    """
    import numpy as np
    x, mask = pad_tables([torch.as_tensor(t, dtype=torch.float32) for t in tables], max_cols=max_cols, device=device)
    size = x.shape[0]
    distance = np.zeros((size, size), dtype=np.float64)
    for start in range(0, size, chunk):
        sims = table_similarity(x[start:start + chunk], mask[start:start + chunk], x, mask)
        distance[start:start + chunk] = (1.0 / sims.clamp(min=1e-9)).double().cpu().numpy()
    distance = np.minimum(distance, distance.T)  # 数值误差下保持对称
    np.fill_diagonal(distance, 0.0)
    return distance
