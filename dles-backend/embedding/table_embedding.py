# -*- coding: utf-8 -*-
import csv
import hashlib
import json
import math
import os
import string
import sys
import threading
from collections import defaultdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from tqdm import tqdm
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

from database.database import Database
from logs.log import error_log
from utils.read_config.read_config import read_config, resolve_data_path

# 表格里可能有很长的单元格，提高 csv 模块的字段长度上限
csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

config = read_config(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json'))
model_path = resolve_data_path(config['model_path'])
device = 'cuda' if torch.cuda.is_available() else 'cpu'

_PUNCTUATION_TABLE = str.maketrans('', '', string.punctuation)


@lru_cache(maxsize=2_000_000)
def clean_and_split(text) -> tuple:
    """去掉标点、转小写后按空白切词。表格里的取值大量重复，缓存后能省下大部分时间"""
    return tuple(str(text).translate(_PUNCTUATION_TABLE).lower().split())


class TableEmbedding:
    """把表格的每一列变成一个语义向量（先用 TF-IDF 截断列内容，再用文本嵌入模型编码）"""
    # 静态变量：IDF、模型和分词器都只加载一次，避免每次请求都重新载入
    words_IDF = None
    _model = None
    _tokenizer = None
    _tokenizer_lock = threading.Lock()

    def __init__(self, use_embedding=True):
        self.max_token_length = config['max_token_length']
        self.pure_table_path = resolve_data_path(config['pure_table_path'])
        self.pure_embedding_path = resolve_data_path(config['pure_embedding_path'])
        self.embedding_length = config['embedding_length']
        self.batch_sz = config['batch_sz']
        if use_embedding:
            if TableEmbedding._model is None:
                # Qwen3-Embedding：取最后一个 token 的隐藏状态作为句向量，所以分词器要在左侧补齐
                TableEmbedding._tokenizer = AutoTokenizer.from_pretrained(model_path, padding_side='left')
                dtype = torch.float16 if device == 'cuda' else torch.float32
                TableEmbedding._model = AutoModel.from_pretrained(model_path, dtype=dtype).to(device).eval()
            self.model = TableEmbedding._model
            self.tokenizer = TableEmbedding._tokenizer
            if TableEmbedding.words_IDF is None:
                TableEmbedding.words_IDF = self._load_or_build_idf()
            self._count_tokens = lru_cache(maxsize=2_000_000)(self._count_tokens_uncached)
            # 分词器会自动在末尾加的特殊 token 数（Qwen3 是 1 个结束符）
            self._special_tokens = len(self.tokenizer.encode(''))
        else:
            self.model = None
            self.tokenizer = None

    # ---------- 全局 IDF ----------
    def _lake_files(self) -> list:
        return sorted(f for f in os.listdir(self.pure_table_path)
                      if os.path.isfile(os.path.join(self.pure_table_path, f)))

    def _lake_signature(self, files: list) -> str:
        digest = hashlib.md5()
        for name in files:
            digest.update(f'{name}:{os.path.getsize(os.path.join(self.pure_table_path, name))};'.encode('utf-8'))
        return digest.hexdigest()

    def _load_or_build_idf(self):
        # 扫描整个数据湖算 IDF 很慢，结果按数据湖内容缓存到磁盘，数据湖没变就直接读取
        files = self._lake_files()
        signature = self._lake_signature(files)
        cache_path = os.path.join(self.pure_embedding_path, 'idf.json')
        if os.path.isfile(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as cache:
                cached = json.load(cache)
            if cached.get('signature') == signature:
                idf = defaultdict(float)
                idf.update(cached['idf'])
                return idf
        idf = self._get_IDF(files)
        os.makedirs(self.pure_embedding_path, exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as cache:
            json.dump({'signature': signature, 'idf': idf}, cache, ensure_ascii=False)
        result = defaultdict(float)
        result.update(idf)
        return result

    def _get_IDF(self, files: list) -> dict:
        words_count = defaultdict(int)
        file_count = 0
        for name in tqdm(files, desc='计算全局 IDF', position=0, leave=True):
            try:
                df = pd.read_csv(os.path.join(self.pure_table_path, name), low_memory=False,
                                 encoding_errors='replace', on_bad_lines='skip')
            except Exception as e:
                error_log(f'计算 IDF 时读取表格失败: {name}, {e}')
                continue
            file_count += 1
            word_counted = set()
            for column in df.columns:
                word_counted.update(clean_and_split(column))
                # 每个词在一张表里只统计一次，所以只需要看不重复的取值
                for cell in df[column].dropna().unique():
                    word_counted.update(clean_and_split(cell))
            for word in word_counted:
                words_count[word] += 1
        return {word: math.log(file_count / (count + 1)) + 1 for word, count in words_count.items()}

    # ---------- 表格列的文本表示（论文算法 1：基于 TF-IDF 的内容截断） ----------
    def _count_tokens_uncached(self, text: str) -> int:
        # Rust 实现的分词器不能同时被多个线程使用（会报 Already borrowed）
        with TableEmbedding._tokenizer_lock:
            return len(self.tokenizer.encode(text, add_special_tokens=False))

    def get_table_columns_from_rows(self, headers: list, rows: list) -> list:
        """
        把表格转成每一列一段文本，每段文本不超过 max_token_length 个 token。
        每一行的得分是其中所有词的 TF-IDF 之和，按得分从高到低整行加入，直到有一列超出长度上限为止。
        """
        word_count = defaultdict(int)
        word_cnt = 0
        for text in list(headers) + [cell for row in rows for cell in row]:
            for word in clean_and_split(text):
                word_count[word] += 1
                word_cnt += 1
        if word_cnt == 0:
            return [str(header) for header in headers]
        idf = TableEmbedding.words_IDF
        word_score = {word: cnt / word_cnt * idf[word] for word, cnt in word_count.items()}

        scored_rows = []
        for row in rows:
            score = sum(word_score[word] for cell in row for word in clean_and_split(cell))
            scored_rows.append((score, row))
        scored_rows.sort(key=lambda item: item[0], reverse=True)

        n_cols = len(headers)
        # token 数是可以累加的（分词是先按空白和标点切开再分别处理），不用每加一行就把整列重新编码一遍
        token_counts = [self._special_tokens + self._count_tokens(str(header)) for header in headers]
        columns = [[] for _ in range(n_cols)]
        for _, row in scored_rows:
            new_counts = list(token_counts)
            for i in range(min(len(row), n_cols)):
                new_counts[i] += self._count_tokens(str(row[i]))
            if max(new_counts) > self.max_token_length:
                break
            token_counts = new_counts
            for i in range(min(len(row), n_cols)):
                columns[i].append(row[i])
        return [' '.join([str(header)] + [str(v) for v in values]) for header, values in zip(headers, columns)]

    def get_table_columns(self, table_path: str) -> list:
        with open(table_path, mode='r', newline='', encoding='utf-8', errors='replace') as table:
            reader = csv.reader(table)
            headers = next(reader)
            rows = list(reader)
        return self.get_table_columns_from_rows(headers, rows)

    # ---------- 向量化 ----------
    @torch.no_grad()
    def get_text_embeddings(self, texts: list) -> np.ndarray:
        if len(texts) == 0:
            return np.zeros((0, self.embedding_length), dtype=np.float32)
        # 按长度排序再分批，减少补齐浪费；最后还原成原来的顺序
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
        result = np.zeros((len(texts), self.embedding_length), dtype=np.float32)
        # 令牌累加是近似值，给截断留一点余量
        max_length = self.max_token_length + 32
        for start in range(0, len(order), self.batch_sz):
            index = order[start:start + self.batch_sz]
            with TableEmbedding._tokenizer_lock:
                batch = self.tokenizer([texts[i] for i in index], padding=True, truncation=True, max_length=max_length,
                                       return_tensors='pt')
            batch = batch.to(device)
            hidden = self.model(**batch).last_hidden_state
            embeddings = F.normalize(hidden[:, -1].float(), dim=-1)
            result[index] = embeddings.cpu().numpy()
        return result

    def save_embeddings(self, save_path, embeddings: list | np.ndarray):
        np.save(save_path, np.array(embeddings))

    def embedding_one(self, table_path: str, save_folder: str, add_time_timestamp=True) -> str:
        if not os.path.isfile(table_path):
            raise Exception('表格不存在')
        columns = self.get_table_columns(table_path)
        embeddings = self.get_text_embeddings(columns)
        timestamp = str(int(datetime.now().timestamp()))
        name = Path(table_path).stem
        save_name = os.path.join(save_folder, name + (('_' + timestamp) if add_time_timestamp else '') + '.npy')
        self.save_embeddings(save_name, embeddings)
        return save_name

    def pre_all(self, reset=False):
        """
        把数据湖里的每张表向量化，保存到 pure_embedding_path，并登记到 table_base_info 表。
        reset=True 会清空 table_base_info 重新开始（table_id 从 1 开始连续，检索时依赖这一点）；
        否则已经登记过的表会被跳过。
        """
        os.makedirs(self.pure_embedding_path, exist_ok=True)
        with Database() as db:
            if reset:
                db.execute_update('TRUNCATE TABLE table_base_info;')
            done = {row['table_path'] for row in db.execute_query('SELECT table_path FROM table_base_info;')}
        failed = []
        for name in tqdm(self._lake_files(), desc='向量化数据湖', position=0, leave=True):
            table_path = Path(os.path.join(self.pure_table_path, name)).as_posix()
            if table_path in done:
                continue
            try:
                save_name = Path(self.embedding_one(os.path.join(self.pure_table_path, name),
                                                    self.pure_embedding_path, add_time_timestamp=False)).as_posix()
                with Database() as db:
                    db.execute_update("INSERT INTO table_base_info (table_path, pure_embedding_path) VALUES (%s, %s);",
                                      (table_path, save_name))
            except Exception as e:
                failed.append(name)
                error_log(f'初始化表格向量错误: {name},{e}')
        print(f'向量化完成，失败 {len(failed)} 张：{failed[:10]}')

    def read_embeddings(self, save_path: str) -> np.ndarray:
        return np.load(save_path)


if __name__ == '__main__':
    TableEmbedding().pre_all(reset='--reset' in sys.argv)
