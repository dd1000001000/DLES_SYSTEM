# -*- coding: utf-8 -*-
"""
训练列上下文 Transformer（论文 3.3.2.3 / 算法 3），自监督，不需要标注：
  1. 数据湖里每张表已经由嵌入模型得到列向量（datalake_embedding_before/*.npy）；
  2. 对每张表做 K 次数据增强（算法 2：交换单元格 + 数值列加噪声），重新向量化，得到增强后的列向量；
  3. 每个批次里，同一张表的原始/增强视图是正样本，其他表格是负样本，用 NT-Xent 损失训练。
     表格之间的相似度用论文的 Sinkhorn 匹配相似度（transformer/similarity_torch.py）；
  4. 额外使用两个比论文更新的训练技巧：随机丢弃部分列（TUS 的相关表本来就是对原表随机投影出来的）、
     学习率 warmup + 余弦衰减。

用法（在 dles-backend 目录下）：
  python -m transformer.train --benchmark-dir ../_downloads/tus/tus
"""
import argparse
import math
import os
import time
import zlib
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import torch
from tqdm import tqdm

from embedding.table_embedding import TableEmbedding
from transformer import evaluate as ev
from transformer.augmentation import augment_table, read_table
from transformer.model import build_model, save_checkpoint
from transformer.similarity_torch import nt_xent_loss, pad_tables
from utils.read_config.read_config import read_config, resolve_data_path

device = 'cuda' if torch.cuda.is_available() else 'cpu'
HERE = os.path.dirname(os.path.abspath(__file__))


def build_augmented_embeddings(embedder: TableEmbedding, lake_dir: str, aug_dir: str, names: list, copies: int,
                               seed: int, swap_ratio: float, noise_level: float):
    """为每张表生成 copies 份增强后的列向量，保存到 aug_dir（已经存在的会跳过，可以中断后继续）"""
    os.makedirs(aug_dir, exist_ok=True)
    tasks = [(name, k) for name in names for k in range(copies)
             if not os.path.isfile(os.path.join(aug_dir, f'{os.path.splitext(name)[0]}__{k}.npy'))]
    if not tasks:
        return

    def prepare(task):
        name, k = task
        rng = np.random.default_rng([seed, k, zlib.crc32(name.encode('utf-8'))])
        try:
            headers, rows = augment_table(read_table(os.path.join(lake_dir, name)), rng, swap_ratio, noise_level)
            return task, embedder.get_table_columns_from_rows(headers, rows)
        except Exception as e:
            print(f'增强失败 {name}: {e}')
            return task, None

    # CPU 上做增强和文本截断，GPU 上做向量化，用线程池让两边重叠
    with ThreadPoolExecutor(max_workers=6) as pool:
        for (name, k), texts in tqdm(pool.map(prepare, tasks), total=len(tasks), desc='生成增强表格的向量'):
            if texts:
                np.save(os.path.join(aug_dir, f'{os.path.splitext(name)[0]}__{k}.npy'), embedder.get_text_embeddings(texts))


def random_columns(table: torch.Tensor, drop_prob: float, max_cols: int, generator: torch.Generator):
    """随机丢弃一部分列（至少保留一列），列数太多时随机取 max_cols 列"""
    n = table.shape[0]
    keep = torch.rand(n, generator=generator, device='cpu') >= drop_prob
    if not keep.any():
        keep[torch.randint(0, n, (1,), generator=generator)] = True
    index = keep.nonzero().squeeze(1)
    if len(index) > max_cols:
        index = index[torch.randperm(len(index), generator=generator)[:max_cols]]
    return table[index.to(table.device)]


def lr_at(step: int, total: int, base_lr: float, warmup: float = 0.05):
    warmup_steps = max(1, int(total * warmup))
    if step < warmup_steps:
        return base_lr * (step + 1) / warmup_steps
    progress = (step - warmup_steps) / max(1, total - warmup_steps)
    return base_lr * 0.5 * (1 + math.cos(math.pi * progress))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--benchmark-dir', default=None, help='提供的话，训练过程中会定期用 TUS 基准评估检索效果（只用来观察，不参与训练）')
    parser.add_argument('--epochs', type=int, default=30)
    parser.add_argument('--batch-size', type=int, default=32)   # 论文：32
    parser.add_argument('--lr', type=float, default=5e-5)       # 论文：5e-5
    parser.add_argument('--temperature', type=float, default=0.1)
    parser.add_argument('--fn-alpha', type=float, default=0.5, help='假负样本消除的阈值系数，见 nt_xent_loss；设为 0 以下的值不会生效，要关闭请不要使用此脚本的默认值')
    parser.add_argument('--copies', type=int, default=3, help='每张表生成几份增强版本')
    parser.add_argument('--swap-ratio', type=float, default=0.3)
    parser.add_argument('--noise-level', type=float, default=0.1)
    parser.add_argument('--col-drop', type=float, default=0.15)
    parser.add_argument('--max-cols', type=int, default=32)
    parser.add_argument('--eval-every', type=int, default=10)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--out', default=None)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    generator = torch.Generator().manual_seed(args.seed)

    emb_config = read_config(os.path.join(HERE, '..', 'embedding', 'config.json'))
    tf_config = read_config(os.path.join(HERE, 'config.json'))
    lake_dir = resolve_data_path(emb_config['pure_table_path'])
    before_dir = resolve_data_path(emb_config['pure_embedding_path'])
    aug_dir = os.path.join(os.path.dirname(before_dir), 'datalake_embedding_aug')
    out_path = args.out or os.path.join(HERE, tf_config['model_path'])

    names, originals = ev.load_lake_embeddings(before_dir)
    print(f'数据湖里有 {len(names)} 张表的原始向量')
    embedder = TableEmbedding(True)
    build_augmented_embeddings(embedder, lake_dir, aug_dir, names, args.copies, args.seed, args.swap_ratio, args.noise_level)
    del embedder
    torch.cuda.empty_cache()

    # 取出每张表的增强向量；增强失败的表只能用原表
    originals = [t.to(device) for t in originals]
    augmented = []
    for name in names:
        stem = os.path.splitext(name)[0]
        versions = [torch.from_numpy(np.load(os.path.join(aug_dir, f'{stem}__{k}.npy'))).float().to(device)
                    for k in range(args.copies) if os.path.isfile(os.path.join(aug_dir, f'{stem}__{k}.npy'))]
        augmented.append(versions)
    usable = [i for i, v in enumerate(augmented) if v]
    print(f'可用于训练的表格：{len(usable)} 张')

    dim = originals[0].shape[1]
    model = build_model({'input_dim': dim}).to(device)
    print(f'模型参数量 {sum(p.numel() for p in model.parameters()) / 1e6:.1f}M，向量维度 {dim}')
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    steps_per_epoch = len(usable) // args.batch_size
    total_steps = steps_per_epoch * args.epochs

    eval_data = None
    if args.benchmark_dir:
        queries, truth, index = ev.load_benchmark(args.benchmark_dir, names)
        queries, _ = ev.split_queries(queries)  # 训练过程中只看开发集，另一半留作最终测试
        eval_data = ([index[q] for q in queries], [truth[q] for q in queries])
        base = ev.evaluate_embeddings([t.cpu() for t in originals], *eval_data, None, device)
        print('训练前（原始嵌入向量）:', ev.format_metrics(base))

    step = 0
    start = time.time()
    last_loss = float('nan')
    for epoch in range(1, args.epochs + 1):
        model.train()
        order = torch.randperm(len(usable), generator=generator).tolist()
        losses = []
        for b in range(steps_per_epoch):
            ids = [usable[i] for i in order[b * args.batch_size:(b + 1) * args.batch_size]]
            view1 = [random_columns(originals[i], args.col_drop, args.max_cols, generator) for i in ids]
            view2 = [random_columns(augmented[i][int(torch.randint(len(augmented[i]), (1,), generator=generator))],
                                    args.col_drop, args.max_cols, generator) for i in ids]
            n_pad = max(t.shape[0] for t in view1 + view2)  # 两个视图补齐到同样的列数，才能拼在一起算相似度
            x1, m1 = pad_tables(view1, device=device, pad_to=n_pad)
            x2, m2 = pad_tables(view2, device=device, pad_to=n_pad)
            for group in optimizer.param_groups:
                group['lr'] = lr_at(step, total_steps, args.lr)
            z1, z2 = model(x1, ~m1), model(x2, ~m2)
            loss = nt_xent_loss(z1, m1, z2, m2, args.temperature, raw_views=(x1, x2), fn_alpha=args.fn_alpha)
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            losses.append(loss.item())
            step += 1
        last_loss = float(np.mean(losses))
        print(f'epoch {epoch}/{args.epochs}  loss={last_loss:.4f}  lr={lr_at(step - 1, total_steps, args.lr):.2e}  '
              f'用时 {time.time() - start:.0f}s', flush=True)
        if eval_data and (epoch % args.eval_every == 0 or epoch == args.epochs):
            metrics = ev.evaluate_embeddings([t.cpu() for t in originals], *eval_data, model, device)
            print('  检索评估:', ev.format_metrics(metrics), flush=True)
            model.train()

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    save_checkpoint(model, {'input_dim': dim}, out_path, extra={
        'embedding_model': os.path.basename(emb_config['model_path']), 'epochs': args.epochs,
        'final_loss': last_loss, 'hparams': vars(args)})
    print(f'已保存到 {out_path}')


if __name__ == '__main__':
    main()
