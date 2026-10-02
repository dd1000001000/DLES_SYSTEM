# -*- coding: utf-8 -*-
import copy
import csv
import json
import os
import random
import re
import shutil
import string
import threading
from typing import List, Dict

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from transformers import pipeline

from database.database import Database
from embedding.table_embedding import TableEmbedding
from enhance.LLM.key_word_extraction import KeyWordExtraction
from settings.service.llm_config_service import get_llm_config
from enhance.LLM.table_enhance_strategy_llm import TableEnhanceStrategyLLM
from enhance.enhance_history_tree.enhance_history_tree import EnhanceHistoryTree
from enhance.enhance_main.query_engine.query_engine import QueryEngine
from logs.log import error_log
from transformer.transformer import Transformer
from utils.read_config.read_config import read_config, resolve_data_path

config = read_config(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json'))

# 增强过程会占用 GPU 并写用例文件，串行执行；接口是同步函数，会在线程池中运行，不会阻塞其他请求。
# 只在向量化/检索和合并/填充两段持有；等待大模型返回（最长几分钟、不占 GPU）的时候不持有，避免其他用户排队
enhance_lock = threading.Lock()

# 一次 UNION 操作最多追加多少行；相关表可能有成千上万行，全部追加再用模型“预测填充”其余列没有意义
UNION_MAX_ROWS = 1000
# 发给大模型的样本表：每个单元格最多保留的字符数、最多保留的列数
SAMPLE_CELL_CHARS = 60
SAMPLE_MAX_COLUMNS = 40
# BERT 填充时每个样本值最多保留的字符数，保证拼出的句子不会超过 512 个 token
FILL_MASK_VALUE_CHARS = 30

JOIN_KEY_COLUMN = '__dles_join_key__'
_LEADING_ZERO = re.compile(r'^\s*[-+]?0\d')
_LONG_DIGITS = re.compile(r'\d{16,}')
_UNION_JOIN_REF = re.compile(r'\s*(\d+)\.(.+?)\s*\+\s*(\d+)\.(.+)', re.S)
_UNION_REF = re.compile(r'\s*(\d+)\.(.+)', re.S)


def infer_numeric(series: pd.Series) -> pd.Series:
    """
    文本列里的值全部能解析成数字时才转成数值列。
    邮编、编号这类带前导零的值（02134）和超过 16 位的长数字不转，否则写回 CSV 时会变成 2134 或丢失精度。
    """
    if pd.api.types.is_numeric_dtype(series):
        return series
    non_null = series.dropna()
    if non_null.empty:
        return series
    texts = non_null.astype(str)
    if texts.str.contains(_LEADING_ZERO).any() or texts.str.contains(_LONG_DIGITS).any():
        return series
    converted = pd.to_numeric(series, errors='coerce')
    if converted.notna().sum() != series.notna().sum():
        return series
    return converted


def read_table_csv(path: str) -> pd.DataFrame:
    """读取表格：先全部当文本读入，再按列判断是否是数值列（见 infer_numeric），避免 pandas 自动推断改写数据"""
    df = pd.read_csv(path, dtype=str, na_values=['.', 'NA'], encoding_errors='replace')
    for column in df.columns:
        df[column] = infer_numeric(df[column])
    return df


def join_key(series: pd.Series) -> pd.Series:
    """
    JOIN 用的连接键：去掉首尾空格；数值列里值为整数的（1.0）写成 1，这样数字列和文本列（"1"）也能连接。
    空值保持为空，调用方负责不让空键参与连接。
    """
    if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
        key = series.map(lambda v: v if pd.isna(v) else (str(int(v)) if float(v).is_integer() else repr(float(v))))
    else:
        key = series.map(lambda v: v if pd.isna(v) else str(v).strip())
    return key.astype(object).where(series.notna())


# 这个类会锁定一个用例
class EnhanceMainService:
    def __init__(self,username:str,enhance_id:int):
        self.username = username
        self.enhance_id = enhance_id
        self.history_folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../enhance_history')
        self.enhance_case_path = os.path.abspath(os.path.join(self.history_folder_path,self.get_case_path()))
        self.enhance_paras = None
        self._filler = None

    def convert_to_numeric_if_possible(self, df: pd.DataFrame, column_name: str) -> None:
        # 整列（不算空值）都能解析成数字才转换
        df[column_name] = infer_numeric(df[column_name])

    def fill_numeric_value_with_model(self, df: pd.DataFrame, target_col: str) -> None:
        if df[target_col].notna().all():
            return

        # 确保目标列是数值型
        if not pd.api.types.is_numeric_dtype(df[target_col]):
            raise ValueError(f"Target column '{target_col}' must be numeric")

        train_data = df[df[target_col].notna()].copy()
        pred_data = df[df[target_col].isna()].copy()

        if len(train_data) == 0:
            df.fillna({target_col: 0}, inplace=True)
            return

        X_train = train_data.drop(columns=[target_col])
        y_train = train_data[target_col]
        X_pred = pred_data.drop(columns=[target_col])

        encoders = {}

        for col in X_train.columns:
            if pd.api.types.is_numeric_dtype(X_train[col]):
                median_val = X_train[col].median()
                if pd.isna(median_val):  # 整列都是空的特征列
                    median_val = 0
                X_train[col] = X_train[col].fillna(median_val)
                X_pred[col] = X_pred[col].fillna(median_val)
            else:
                # UNION 之后同一列里可能同时有字符串和数字，LabelEncoder 要求类型一致，统一按文本编码
                le = LabelEncoder()
                train_text = X_train[col].astype(str)
                pred_text = X_pred[col].astype(str)
                le.fit(pd.concat([train_text, pred_text]))
                X_train[col] = le.transform(train_text)
                X_pred[col] = le.transform(pred_text)
                encoders[col] = le

        assert all(pd.api.types.is_numeric_dtype(X_train[col]) for col in X_train.columns)

        model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)
        predicted_values = model.predict(X_pred)
        df.loc[df[target_col].isna(), target_col] = predicted_values

    def fill_text_value(self,df: pd.DataFrame, target_col: str, words_cnt:int = 16) -> None:
        non_null = df[target_col].dropna()
        if len(non_null) == 0:
            df[target_col] = df[target_col].fillna("unknown")
            return
        if self._filler is None:
            self._filler = pipeline('fill-mask', model=resolve_data_path(config['bert_model_path']))
            # 万一还是超长，从左边截断，保证句尾的 [MASK] 不会被截掉
            self._filler.tokenizer.truncation_side = 'left'
        filler = self._filler
        null_indices = df[df[target_col].isnull()].index
        # 长文本列（描述、摘要等）里的值很长，拼 16 个会远超 BERT 的 512 个 token，每个值只取前面一部分
        non_null_texts = non_null.astype(str).str.slice(0, FILL_MASK_VALUE_CHARS)
        rng = np.random.RandomState(0)  # 固定随机种子，同样的输入得到同样的结果
        queries = [','.join(non_null_texts.sample(n=words_cnt, replace=True, random_state=rng).tolist() + ['[MASK]'])
                   for _ in range(len(null_indices))]
        results = filler(queries, tokenizer_kwargs={'truncation': True, 'max_length': 512})
        for idx, res in zip(null_indices, results):
            try:
                filled = 'unknown'
                # 结果按得分从高到低排列，取第一个不是标点的候选词
                for r in res:
                    if r['token_str'] not in string.punctuation:
                        filled = r['token_str']
                        break
                df.at[idx, target_col] = filled
            except (KeyError, IndexError):
                df.at[idx, target_col] = 'unknown'


    def fill_vacancy_values(self,df:pd.DataFrame,flag:str):
        for column in df.columns:
            self.convert_to_numeric_if_possible(df, column)

        # 先填充非数值类型
        for column in df.columns:
            if not pd.api.types.is_numeric_dtype(df[column]):
                self.fill_text_value(df,column)

        # 再填充数值类型
        for column in df.columns:
            if pd.api.types.is_numeric_dtype(df[column]):
                if flag == 'MODEL':
                    self.fill_numeric_value_with_model(df, column)
                else:
                    # AVERAGE / MEAN 都是用平均值填充；整列都是空的（比如 JOIN 后一行都没连上的列）没有平均值，和 MODEL 一样填 0
                    mean = df[column].mean()
                    df[column] = df[column].fillna(0 if pd.isna(mean) else mean)

    # 总的执行增强函数
    def execute_enhance(self,k:int=8):
        try:
            if self.enhance_paras is None:
                raise Exception("增强参数不存在，无法执行增强")
            # 先取模型配置：没配置就直接报错，不用白白跑完耗时的向量化和检索
            llm_config = get_llm_config(self.username)
            # 向量化和检索占用 GPU，串行执行
            with enhance_lock:
                related_tables_path = self.find_related_table_paths(k)
            query_table_info = self.read_csv_random_rows(os.path.join(self.enhance_case_path,'table.csv'))
            related_tables_info = [self.read_csv_random_rows(related_table_path) for related_table_path in related_tables_path]
            # 等大模型返回可能要几分钟，不占 GPU，不持有锁
            table_enhance_strategy_LLM = TableEnhanceStrategyLLM(llm_config)
            enhance_strategy = table_enhance_strategy_LLM.ask(query_table_info,related_tables_info,self.enhance_paras)
            if not isinstance(enhance_strategy, dict) or not any(
                    isinstance(enhance_strategy.get(key), list) for key in ('join_operations', 'union_operations')):
                raise Exception('模型没有返回有效的增强策略（缺少 join_operations / union_operations）。'
                                '请检查模型配置，或换一个更强的模型；本地 Ollama 需要把上下文长度调大（OLLAMA_CONTEXT_LENGTH=16384）')
            with enhance_lock:
                self.apply_strategy(enhance_strategy, related_tables_path)
        except Exception as e:
            error_log(f'执行增强操作失败：{self.username} {self.enhance_id}，失败原因：{e}')
            raise e

    def find_related_table_paths(self, k: int) -> List[str]:
        related_tables_path = []
        for table_id, score in self.query_tables(k):
            with Database() as db:
                sql_result = db.execute_query("SELECT * FROM table_base_info WHERE table_id=%s", (int(table_id) + 1,))
            if len(sql_result) == 0:
                raise Exception(f'id 为 {table_id+1} 的相关表格查找不到')
            related_tables_path.append(sql_result[0]['table_path'])
        return related_tables_path

    def apply_strategy(self, enhance_strategy: Dict, related_tables_path: List[str]) -> None:
        """按大模型给出的策略增强用户表并保存"""
        table_path = os.path.join(self.enhance_case_path, 'table.csv')
        df = read_table_csv(table_path)
        original_columns = list(df.columns)
        # 增强方式：只要 JOIN 就不执行 UNION，反之亦然，不管大模型有没有多给
        enhance_type = self.enhance_paras.get('type', 'BOTH')
        join_operations = enhance_strategy.get('join_operations') if enhance_type in ('JOIN', 'BOTH') else []
        union_operations = enhance_strategy.get('union_operations') if enhance_type in ('UNION', 'BOTH') else []
        # related_table 1_index
        # 先处理JOIN操作
        # 大模型的输出不可信：每一个操作都单独校验、单独容错，一个操作有问题只跳过它，不影响其他操作
        df = self.apply_join_operations(df, join_operations, related_tables_path)
        df = self.apply_union_operations(df, union_operations, related_tables_path)
        df = self.trim_columns(df, original_columns, self.enhance_paras.get('number'),
                               self.enhance_paras.get('columns') or [])

        self.fill_vacancy_values(df, self.enhance_paras['fill'])
        # 保存表格：先写临时文件再替换，写到一半出错不会把用户的表格弄坏
        temp_path = table_path + '.tmp'
        df.to_csv(temp_path, index=False)
        os.replace(temp_path, table_path)

    @staticmethod
    def trim_columns(df: pd.DataFrame, original_columns: List[str], number, focus_columns: List[str]) -> pd.DataFrame:
        """
        增强后的列数超过期望列数时，丢掉缺失最多的新增列。
        用户原来的列和用户重点关注的列不会被丢弃，所以期望列数小于原表列数时不会删用户自己的列。
        """
        if not isinstance(number, int) or number <= 0 or df.shape[1] <= number:
            return df
        protected = set(original_columns) | set(focus_columns)
        added = [c for c in df.columns if c not in protected]
        # 缺失比例从高到低，同样缺失时后面的列先丢
        order = sorted(range(len(added)), key=lambda i: (df[added[i]].isna().mean(), i), reverse=True)
        drop = [added[i] for i in order[:df.shape[1] - number]]
        return df.drop(columns=drop)

    @staticmethod
    def _is_str_list(value) -> bool:
        return isinstance(value, list) and all(isinstance(item, str) for item in value)

    def apply_join_operations(self, df: pd.DataFrame, join_operations, related_tables_path: List[str]) -> pd.DataFrame:
        """JOIN：把相关表里的列按连接列拼到用户表的右边（保留用户表的所有行）"""
        join_extra_flag = "_eCnIIm7B0TvO"
        for join_operation in (join_operations or []):
            try:
                if not self._is_str_list(join_operation) or len(join_operation) < 3:
                    raise ValueError('JOIN 操作必须是至少 3 个字符串的列表')
                column_q = join_operation[0]
                table_id, column_r = join_operation[1].split('.', 1)
                table_id = int(table_id) - 1
                keep_columns = list(dict.fromkeys(join_operation[2:] + [column_r]))  # 去重并保持顺序
                if not 0 <= table_id < len(related_tables_path):
                    raise ValueError(f'相关表编号超出范围：{table_id + 1}')
                if column_q not in df.columns:
                    raise ValueError(f'用户表中不存在列 {column_q}')
                related_table_df = read_table_csv(related_tables_path[table_id])
                if column_r not in related_table_df.columns:
                    raise ValueError(f'相关表中不存在列 {column_r}')
                # 空键不参与连接（pandas 会把空值和空值连在一起）；连接键统一成文本，数字列和文本列也能连接
                right = related_table_df.filter(items=keep_columns).dropna(subset=[column_r])
                right = right.assign(**{JOIN_KEY_COLUMN: join_key(right[column_r])}).drop_duplicates(subset=[JOIN_KEY_COLUMN])
                left = df.assign(**{JOIN_KEY_COLUMN: join_key(df[column_q])})
                df = left.merge(right, on=JOIN_KEY_COLUMN, how='left', suffixes=('', join_extra_flag))
                # 对于 JOIN 结果中额外的列做删除
                df = df.drop(columns=[JOIN_KEY_COLUMN] + [col for col in df.columns if join_extra_flag in col])
            except Exception as e:
                error_log(f'跳过无法执行的 JOIN 操作 {join_operation}：{e}')
        return df

    def apply_union_operations(self, df: pd.DataFrame, union_operations, related_tables_path: List[str]) -> pd.DataFrame:
        """UNION：把相关表（可能先内部 JOIN）按列对应关系拼成新的行，追加到用户表下面"""
        union_operations = union_operations or []
        if len(union_operations) % 2 == 1:
            error_log('联合操作的列表长度为奇数')
            union_operations = union_operations[:-1]
        # ['1.相关表列a','1.相关表列b+1.相关表列a','2.相关表列b','2.相关表列c+3.相关表列d'],['column1','column3','column2','column4']
        for i in range(0, len(union_operations), 2):
            operations, column_names = union_operations[i], union_operations[i + 1]
            try:
                if not (self._is_str_list(operations) and self._is_str_list(column_names)):
                    raise ValueError('UNION 操作必须成对给出两个字符串列表')
                if len(operations) != len(column_names) or len(operations) == 0:
                    raise ValueError('UNION 操作的两个列表长度必须相同')
                df = df.loc[:, ~df.columns.duplicated(keep='first')].reset_index(drop=True)
                union_df = self.get_join_table_df(operations, column_names, related_tables_path)
                # 目标列名必须是增强到这一步的表里已经有的列；大模型给了不存在的名字就忽略那一列，而不是凭空多出一列
                unknown = [c for c in union_df.columns if c not in df.columns]
                if unknown:
                    error_log(f'UNION 操作的目标列在表中不存在，已忽略：{unknown}')
                union_df = union_df.drop(columns=unknown).dropna(how='all').drop_duplicates()
                if union_df.shape[1] == 0 or len(union_df) == 0:
                    raise ValueError('UNION 操作没有产生可以追加的行')
                combined = pd.concat([df, union_df.reset_index(drop=True)], ignore_index=True)
                # 只对新追加的行去重（和已有行重复的新行丢掉），用户原表里的行不动
                is_new_row = combined.index >= len(df)
                new_rows = combined[is_new_row & ~combined.duplicated()]
                if len(new_rows) > UNION_MAX_ROWS:
                    new_rows = new_rows.sample(n=UNION_MAX_ROWS, random_state=0).sort_index()
                df = pd.concat([combined[~is_new_row], new_rows], ignore_index=True)
            except Exception as e:
                error_log(f'跳过无法执行的 UNION 操作 {operations}：{e}')
        return df

    def get_join_table_df(self,list_operations:List,list_column_names:List,table_paths:List):
        """
        按 UNION 操作的描述拼出“和用户表做 UNION 的那张表”。
        list_operations 里每一项是 '表号.列名'（单个相关表的一列），或 '表号.列名+表号.列名'（用两个相关表的这两列做连接，
        连接后取前一列）；list_column_names 的第 i 项是第 i 列在结果里的名字。
        用 '+' 连起来的相关表先按连接列依次 JOIN 成一张表（链式的 1+2、2+3 也能连起来）；
        没有 '+' 相连的相关表各自独立，各自的行上下堆叠起来，而不是按行号横着硬拼。
        """
        # 解析：columns[i] = [(表号, 列名), ...]（第一项是取值的那一列），edges 是连接关系
        entries, edges = [], []
        for operation, name in zip(list_operations, list_column_names):
            joined = _UNION_JOIN_REF.fullmatch(operation)
            if joined:
                ta, ca, tb, cb = int(joined.group(1)), joined.group(2).strip(), int(joined.group(3)), joined.group(4).strip()
                if ta != tb:
                    edges.append((ta, ca, tb, cb))
                entries.append((ta, ca, name))
                continue
            single = _UNION_REF.fullmatch(operation)
            if not single:
                raise ValueError(f'无法解析 UNION 的列：{operation}')
            entries.append((int(single.group(1)), single.group(2).strip(), name))

        involved = sorted({t for t, _, _ in entries} | {t for e in edges for t in (e[0], e[2])})
        # 相关表编号从 1 开始
        if involved[0] < 1 or involved[-1] > len(table_paths):
            raise ValueError('UNION 操作引用了不存在的相关表')

        frames = {}
        for table_id in involved:
            frame = read_table_csv(table_paths[table_id - 1])
            frames[table_id] = frame.loc[:, ~frame.columns.duplicated(keep='first')]

        def prefixed(table_id):
            return frames[table_id].add_prefix(f'{table_id}|')

        # 用 '+' 把相关表连成若干连通块（并查集）
        parent = {t: t for t in involved}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for ta, _, tb, _ in edges:
            parent[find(tb)] = find(ta)
        components = {}
        for table_id in involved:
            components.setdefault(find(table_id), []).append(table_id)

        stacked = []
        for members in components.values():
            member_set = set(members)
            merged = prefixed(members[0])
            joined_tables = {members[0]}
            remaining = [e for e in edges if e[0] in member_set]
            # 每次找一条一端已经连进来、另一端还没连进来的边，把另一张表 JOIN 进来
            progress = True
            while progress:
                progress = False
                for ta, ca, tb, cb in remaining:
                    if (ta in joined_tables) == (tb in joined_tables):
                        continue
                    if tb in joined_tables:  # 统一成 ta 已连入
                        ta, ca, tb, cb = tb, cb, ta, ca
                    left_key, right_key = f'{ta}|{ca}', f'{tb}|{cb}'
                    right = prefixed(tb)
                    if left_key not in merged.columns or right_key not in right.columns:
                        raise ValueError(f'连接列不存在：{ta}.{ca} + {tb}.{cb}')
                    right = right.dropna(subset=[right_key])
                    right = right.assign(**{JOIN_KEY_COLUMN: join_key(right[right_key])}).drop_duplicates(subset=[JOIN_KEY_COLUMN])
                    merged = merged.assign(**{JOIN_KEY_COLUMN: join_key(merged[left_key])}).merge(
                        right, on=JOIN_KEY_COLUMN, how='inner').drop(columns=[JOIN_KEY_COLUMN])
                    joined_tables.add(tb)
                    progress = True
            if joined_tables != member_set:
                raise ValueError('UNION 操作中相关表之间的连接关系无法连通')

            columns = {}
            for table_id, column, name in entries:
                if table_id in member_set and name not in columns:
                    if f'{table_id}|{column}' not in merged.columns:
                        error_log(f'UNION 引用的列在相关表 {table_id} 中不存在，已忽略：{column}')
                        continue
                    columns[name] = merged[f'{table_id}|{column}']
            if columns:
                stacked.append(pd.DataFrame(columns))

        if not stacked:
            raise ValueError('UNION 操作引用的列在相关表中都不存在')
        return pd.concat(stacked, ignore_index=True)

    def trans_table_list_to_json(self,table_list, columns=None):
        cols = table_list[0]
        rows = table_list[1:]
        if columns is None:
            columns_to_keep = cols
        else:
            columns_to_keep = [col for col in columns if col in cols]
        json_result = {}
        for col in columns_to_keep:
            col_idx = cols.index(col)
            json_result[col] = [row[col_idx] for row in rows]
        return json_result

    def set_enhance_paras(self,enhance_paras:Dict):
        if enhance_paras is None:
            raise Exception("增强参数必须存在")
        self.enhance_paras = enhance_paras

    def get_case_path(self):
        enhance_history_tree = EnhanceHistoryTree(self.username)
        full_path = enhance_history_tree.get_path_by_id(self.enhance_id, enhance_history_tree.get_user_tree())[0]
        if full_path is None:
            raise Exception('当前查找的用例不存在')
        return full_path

    def extraction_dialogue(self,chat_history:List[Dict],user_input:str):
        try:
            # 在最后写入json
            extraction_engine = KeyWordExtraction(get_llm_config(self.username))
            history = copy.deepcopy(chat_history)
            history = history[:-1]
            user_pure_input = user_input.replace("开始增强","").strip()
            if user_pure_input != "":
                history = extraction_engine.trans_front_to_back(history)
                history = extraction_engine.query(history,user_input,os.path.join(self.enhance_case_path,'table.csv'))
                history2 = extraction_engine.trans_back_to_front(history)
            else:
                history2 = history
                history2.append({"role":"user","content":user_input})
                find_extraction = False
                for history in history2:
                    if history["role"]=="assistant" and "提取的关键词如下：" in history["content"]:
                        find_extraction = True
                if find_extraction:
                    history2.append({"role":"assistant","content":"提取的关键词和上次一致。"})
                else:
                    history2.append({"role":"assistant","content":"您似乎没有输入增强要求，请输入表格增强要求。"})
            with open(os.path.join(self.enhance_case_path,'dialogue.json'), mode='w', encoding='utf-8') as file:
                json.dump(history2, file,indent=2, ensure_ascii=False)
            return extraction_engine.trans_front_to_back(history2)
        except Exception as e:
            raise e

    def read_csv_random_rows(self, table_path, max_rows=10):
        # 读取CSV文件并提取数据，作为样本发给大模型：宽表、长文本会撑爆上下文，所以限制列数并截断单元格
        with open(table_path, 'r', encoding='utf-8', errors='replace', newline='') as file:
            reader = csv.reader(file)
            headers = next(reader, None)
            if headers is None:
                raise ValueError(f'表格文件是空的：{os.path.basename(table_path)}')
            data_rows = list(reader)
        selected_rows = random.sample(data_rows,k=min(max_rows, len(data_rows)))

        def shorten(cell: str) -> str:
            return cell if len(cell) <= SAMPLE_CELL_CHARS else cell[:SAMPLE_CELL_CHARS] + '…'

        n_columns = min(len(headers), SAMPLE_MAX_COLUMNS)
        result = [[shorten(h) for h in headers[:n_columns]]]
        for row in selected_rows:
            row = row[:n_columns] + [''] * (n_columns - len(row))  # 有的行列数不够，补齐
            result.append([shorten(cell) for cell in row])
        return result

    # 先处理表格的 embedding
    def get_embedding_before(self):
        try:
            table_embedding = TableEmbedding(True)
            table_embedding.embedding_one(os.path.join(self.enhance_case_path, 'table.csv'),self.enhance_case_path,add_time_timestamp=False)
            shutil.move(os.path.join(self.enhance_case_path, 'table.npy'), os.path.join(self.enhance_case_path, 'pure_embedding.npy'))
        except Exception as e:
            raise e

    def processed_embedding(self):
        try:
            transformer = Transformer(True)
            transformer.process_and_save_embedding(os.path.join(self.enhance_case_path, 'pure_embedding.npy'),os.path.join(self.enhance_case_path, 'processed_embedding.npy'))
        except Exception as e:
            raise e

    def query(self,k:int):
        table_embedding = TableEmbedding(False)
        table_embedding = table_embedding.read_embeddings(os.path.join(self.enhance_case_path, 'processed_embedding.npy'))
        q = QueryEngine()
        return q.query(table_embedding,k)

    def query_tables(self,k:int):
        self.get_embedding_before()
        self.processed_embedding()
        return self.query(k)

    def query_brute_force(self,k:int):
        self.get_embedding_before()
        self.processed_embedding()
        table_embedding = TableEmbedding(False)
        table_embedding = table_embedding.read_embeddings(os.path.join(self.enhance_case_path, 'processed_embedding.npy'))
        q = QueryEngine()
        return q.query_brute_force(table_embedding,k)

    def extract_enhance_paras_from_history(self,history:List[Dict]):
        length = len(history)
        for i in range(length-1,-1,-1):
            one_history = history[i]
            if one_history["role"]=="assistant" and isinstance(one_history["content"],Dict):
                return one_history["content"]
        return None

