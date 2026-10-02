# -*- coding: utf-8 -*-
"""
在 TUS 基准上评估“相关表发现”的效果：对每个查询表，按表格相似度给整个数据湖排序，
和基准里标注的可合并（unionable）表格比较，计算 P@k 与 R@k。

用法（在 dles-backend 目录下）：
  python -m transformer.evaluate --benchmark-dir ../_downloads/tus/tus
会依次评估：不经过 Transformer 的原始嵌入向量、训练好的 Transformer 输出。
"""
import argparse
import os
import pickle

import numpy as np
import torch

from transformer.model import load_checkpoint
from transformer.similarity_torch import pad_tables, table_similarity
from utils.read_config.read_config import read_config, resolve_data_path

KS = (1, 5, 10, 20, 50)
MAX_COLS = 64  # 评估时列数超过这个值的表格只取前面这些列


def load_lake_embeddings(embedding_dir: str):
    names = sorted(f for f in os.listdir(embedding_dir) if f.endswith('.npy'))
    tables = [torch.from_numpy(np.load(os.path.join(embedding_dir, f))).float() for f in names]
    return [os.path.splitext(f)[0] + '.csv' for f in names], tables


def load_benchmark(benchmark_dir: str, names: list):
    with open(os.path.join(benchmark_dir, 'benchmark.pkl'), 'rb') as f:
        benchmark = pickle.load(f)
    index = {name: i for i, name in enumerate(names)}
    queries = sorted(q for q in os.listdir(os.path.join(benchmark_dir, 'query')) if q in index and q in benchmark)
    ground_truth = {q: {index[t] for t in benchmark[q] if t in index and t != q} for q in queries}
    return queries, ground_truth, index


def split_queries(queries: list):
    """查询表分成两半：偶数位置的作开发集（调超参数、观察训练），奇数位置的作测试集（只在最后报告）"""
    return queries[0::2], queries[1::2]


@torch.no_grad()
def rank_all(query_ids: list, x, mask, batch: int = 8):
    """返回 (Q, T) 的相似度矩阵：每个查询表和数据湖里每张表的相似度"""
    sims = []
    for start in range(0, len(query_ids), batch):
        ids = query_ids[start:start + batch]
        sims.append(table_similarity(x[ids], mask[ids], x, mask))
    return torch.cat(sims, dim=0)


def retrieval_metrics(sims: torch.Tensor, query_ids: list, ground_truth_sets: list, ks=KS):
    sims = sims.clone()
    for row, q in enumerate(query_ids):
        sims[row, q] = float('-inf')  # 查询表自己不算
    order = sims.argsort(dim=1, descending=True).cpu().numpy()
    result = {}
    for k in ks:
        precision, recall = [], []
        for row, truth in enumerate(ground_truth_sets):
            hits = len(set(order[row, :k].tolist()) & truth)
            precision.append(hits / k)
            recall.append(hits / min(k, len(truth)))  # TUS 的惯用写法：分母取 min(k, 标注数量)，k 很小时才有可能达到 1
        result[f'P@{k}'] = float(np.mean(precision))
        result[f'R@{k}'] = float(np.mean(recall))
    return result


def evaluate_embeddings(tables, query_ids, ground_truth_sets, model=None, device='cuda'):
    x, mask = pad_tables(tables, max_cols=MAX_COLS, device=device)
    if model is not None:
        model.eval()
        with torch.no_grad():
            x = torch.cat([model(x[i:i + 256], ~mask[i:i + 256]) for i in range(0, len(x), 256)])
    sims = rank_all(query_ids, x, mask)
    return retrieval_metrics(sims, query_ids, ground_truth_sets)


def format_metrics(metrics: dict) -> str:
    return '  '.join(f'{k}={v:.3f}' for k, v in metrics.items())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--benchmark-dir', required=True)
    parser.add_argument('--embedding-dir', default=None)
    parser.add_argument('--checkpoint', default=None)
    args = parser.parse_args()

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    config = read_config(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json'))
    embedding_dir = args.embedding_dir or resolve_data_path(config['pure_embedding_path'])
    checkpoint = args.checkpoint or os.path.join(os.path.dirname(os.path.abspath(__file__)), config['model_path'])

    names, tables = load_lake_embeddings(embedding_dir)
    queries, truth, index = load_benchmark(args.benchmark_dir, names)
    query_ids = [index[q] for q in queries]
    truth_sets = [truth[q] for q in queries]
    print(f'数据湖 {len(names)} 张表，查询表 {len(queries)} 个，平均每个查询有 {np.mean([len(t) for t in truth_sets]):.1f} 张相关表')

    _, test = split_queries(queries)
    for title, subset in (('测试集', test), ('全部查询', queries)):
        ids = [index[q] for q in subset]
        sets = [truth[q] for q in subset]
        print(f'[{title} {len(subset)} 个查询]')
        print('  原始嵌入向量（不经过 Transformer）:', format_metrics(evaluate_embeddings(tables, ids, sets, None, device)))
        if os.path.isfile(checkpoint):
            try:
                model = load_checkpoint(checkpoint, device)
            except Exception as e:
                print(f'  无法加载 {checkpoint}（可能是旧格式的检查点，或者向量维度和当前嵌入模型不一致），请先运行 python -m transformer.train：{type(e).__name__}')
                return
            print('  Transformer 输出:                  ', format_metrics(evaluate_embeddings(tables, ids, sets, model, device)))


if __name__ == '__main__':
    main()
