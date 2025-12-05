# -*- coding: utf-8 -*-
import copy
import csv
import json
import os
import random
import shutil
import string
from typing import List, Dict

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from transformers import pipeline

from database.database import Database
from embedding.jina_embedding import JinaEmbedding
from enhance.LLM.key_word_extraction import KeyWordExtraction
from enhance.LLM.table_enhance_strategy_llm import TableEnhanceStrategyLLM
from enhance.enhance_history_tree.enhance_history_tree import EnhanceHistoryTree
from enhance.enhance_main.query_engine.query_engine import QueryEngine
from logs.log import error_log
# 强制导入，禁止删除
from transformer.model import TableContrastiveModel, TransformerEncoder
from transformer.transformer import Transformer
from utils.read_config.read_config import read_config

config = read_config(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json'))

# 这个类会锁定一个用例
class EnhanceMainService:
    def __init__(self,username:str,enhance_id:int):
        self.username = username
        self.enhance_id = enhance_id
        self.history_folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../enhance_history')
        self.enhance_case_path = os.path.abspath(os.path.join(self.history_folder_path,self.get_case_path()))
        self.enhance_paras = None

    def convert_to_numeric_if_possible(self, df: pd.DataFrame, column_name: str) -> None:
        # 尝试转换整个列为数字（无效值转为 NaN）
        converted_series = pd.to_numeric(df[column_name], errors="coerce")
        if not converted_series.isna().any():
            df[column_name] = converted_series

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
                X_train[col].fillna(median_val, inplace=True)
                X_pred[col].fillna(median_val, inplace=True)
            else:
                le = LabelEncoder()
                combined = pd.concat([X_train[col], X_pred[col]])
                le.fit(combined)
                X_train[col] = le.transform(X_train[col])
                X_pred[col] = le.transform(X_pred[col])
                encoders[col] = le

        assert all(pd.api.types.is_numeric_dtype(X_train[col]) for col in X_train.columns)

        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        predicted_values = model.predict(X_pred)
        df.loc[df[target_col].isna(), target_col] = predicted_values

    def fill_text_value(self,df: pd.DataFrame, target_col: str, words_cnt:int = 16) -> None:
        non_null = df[target_col].dropna()
        if len(non_null) == 0:
            df[target_col].fillna("unknown", inplace=True)
            return
        filler = pipeline('fill-mask', model=config['bert_model_path'])
        null_indices = df[df[target_col].isnull()].index
        non_null_texts = non_null.astype(str)
        queries = [','.join(non_null_texts.sample(n=words_cnt, replace=True).tolist() + ['[MASK]']) for _ in
                   range(len(null_indices))]
        results = filler(queries)
        for idx, res in zip(null_indices, results):
            try:
                filled = 'unknown'
                for r in res:
                    if r['token_str'] not in string.punctuation:
                        filled = r['token_str']
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
                elif flag == 'MEAN':
                    mode_val = df[column].mode()[0]
                    df[column].fillna(mode_val, inplace=True)
                else:
                    median_val = df[column].median()
                    df[column].fillna(median_val, inplace=True)

    # 总的执行增强函数
    def execute_enhance(self,k:int=8):
        try:
            if self.enhance_paras is None:
                raise Exception("增强参数不存在，无法执行增强")
            related_tables = self.query_tables(k)
            related_tables_path = []
            for table_id,score in related_tables:
                select_sql = f"SELECT * FROM table_base_info WHERE table_id={table_id+1}"
                db=Database()
                sql_result = db.execute_query(select_sql)
                db.close()
                if len(sql_result) == 0:
                    raise Exception(f'id 为 {table_id+1} 的相关表格查找不到')
                related_tables_path.append(sql_result[0]['table_path'])

            query_table_info = self.read_csv_random_rows(os.path.join(self.enhance_case_path,'table.csv'))
            related_tables_info = [self.read_csv_random_rows(related_table_path) for related_table_path in related_tables_path]
            table_enhance_strategy_LLM = TableEnhanceStrategyLLM()
            enhance_strategy = table_enhance_strategy_LLM.ask(query_table_info,related_tables_info,self.enhance_paras)
            user_query_table_df = pd.read_csv(os.path.join(self.enhance_case_path,'table.csv'), na_values = ['.', 'NA'])
            # related_table 1_index
            # 先处理JOIN操作
            join_extra_flag = "_eCnIIm7B0TvO"
            join_operations = enhance_strategy['join_operations']
            for join_operation in join_operations:
                if len(join_operation) < 3:
                    error_log(f'JOIN 操作的信息小于 3 列，无法执行：{str(join_operation)}')
                    continue
                column_q = join_operation[0]
                table_id, column_r = join_operation[1].split('.', 1)
                keep_columns = list(set(join_operation[2:] + [column_r]))
                table_id = int(table_id) - 1
                if table_id < len(related_tables_path):
                    related_table_df = pd.read_csv(related_tables_path[table_id],na_values = ['.', 'NA'])
                    related_table_df = related_table_df.filter(items=keep_columns)
                    related_table_df = related_table_df.drop_duplicates(subset=[column_r])
                    user_query_table_df = pd.merge(user_query_table_df,related_table_df,left_on=column_q,right_on=column_r,how='outer',suffixes=('', join_extra_flag))
                    # 对于 JOIN 结果中额外的列做删除
                    drop_cols = [col for col in user_query_table_df.columns if "_eCnIIm7B0TvO" in col]
                    user_query_table_df = user_query_table_df.drop(columns=drop_cols)
            # 再处理union操作
            union_operations = enhance_strategy['union_operations']
            if len(union_operations)%2 == 1:
                error_log(f'联合操作的列表长度为奇数')
                union_operations.pop()
            # 对于每一个增强拼接成一个新的表格，然后concat到当前的表格下
            # ['1.相关表列a','1.相关表列b+1.相关表列a','2.相关表列b','2.相关表列c+3.相关表列d'],['column1','column3','column2','column4']
            # 这里需要有一个顺序进行 JOIN 操作，为了避免神秘的情况出现
            for i in range(0,len(union_operations),2):
                operations = union_operations[i]
                column_names = union_operations[i+1]
                if len(operations)!=len(column_names):
                    error_log(f'union 操作的操作长度不一致')
                    continue
                union_df = self.get_join_table_df(operations,column_names,related_tables_path)
                if union_df is None:
                    continue
                user_query_table_df = user_query_table_df.loc[:, ~ user_query_table_df.columns.duplicated(keep='first')]
                user_query_table_df = user_query_table_df.reset_index(drop=True)
                union_df = union_df.reset_index(drop=True)
                user_query_table_df = pd.concat([user_query_table_df,union_df],ignore_index=True).drop_duplicates()

            self.fill_vacancy_values(user_query_table_df,self.enhance_paras['fill'])
            print(user_query_table_df)
            # 保存表格
            user_query_table_df.to_csv(os.path.join(self.enhance_case_path,'table.csv'),index=False)
        except Exception as e:
            error_log(f'执行增强操作失败：{self.username} {self.enhance_id}，失败原因：{e}')
            raise e

    def get_join_table_df(self,list_operations:List,list_column_names:List,table_paths:List):
        def rename_and_filter_columns(df, column_mapping:Dict):
            existing_columns = [col for col in df.columns if col in column_mapping]
            df = df[existing_columns].rename(columns=column_mapping)
            return df

        # 就只有8个表格 1. 2. 3. 4.
        table_had = list()
        for index,operation in enumerate(list_operations):
            if '+' in operation:
                column_a , column_b = operation.split('+')
                table_ida, table_column = column_a.split('.',1)
                table_had.append(int(table_ida))
                table_idb, table_column = column_b.split('.',1)
                table_had.append(int(table_idb))
            else:
                table_id,table_column = operation.split('.',1)
                table_had.append(int(table_id))
        table_had = list(set(table_had))
        if max(table_had)>len(table_paths):
            return None
        join_map = [[] for _ in range(max(table_had) + 1)]
        for operation in list_operations:
            if '+' in operation:
                column_a, column_b = operation.split('+')
                table_ida, table_column = column_a.split('.', 1)
                table_idb, table_column = column_b.split('.', 1)
                table_ida = int(table_ida)
                table_idb = int(table_idb)
                join_map[table_idb].append(table_ida)
                join_map[table_ida].append(table_idb)
        for i in range(len(join_map)):
            join_map[i] = list(set(join_map[i]))

        tables_df = [None] * (max(table_had) + 1)
        for have in table_had:
            index = int(have)-1
            tables_df[have] = pd.read_csv(table_paths[index], na_values = ['.', 'NA'])

        for x in table_had:
            change_name_dict = {}
            for index,operation in enumerate(list_operations):
                if '+' in operation:
                    column_a, column_b = operation.split('+')
                    table_ida, table_column1 = column_a.split('.', 1)
                    table_idb, table_column2 = column_b.split('.', 1)
                    table_ida = int(table_ida)
                    table_idb = int(table_idb)
                    if x == table_ida:
                        change_name_dict[table_column1] = list_column_names[index]
                    if x == table_idb:
                        change_name_dict[table_column2] = list_column_names[index]
                else:
                    table_id, table_column = operation.split('.', 1)
                    table_id = int(table_id)
                    if x == table_id:
                        change_name_dict[table_column] = list_column_names[index]
            tables_df[x] =  tables_df[x].loc[:, ~ tables_df[x].columns.duplicated(keep='first')]
            tables_df[x] = rename_and_filter_columns(tables_df[x],change_name_dict)

        result = None
        visited = [False] * (max(table_had)+1)
        for x in table_had:
            if visited[x]:
                continue
            visited[x] = True
            if result is None:
                result = tables_df[x]
            else:
                result = pd.concat([result, tables_df[x]], axis=1)
            for y in join_map[x]:
                if visited[y]:
                    continue
                visited[y] = True
                result = pd.merge(result,tables_df[y])
        if result is None:
            raise Exception('部分表格 union 的结果出现 None')
        result = result.loc[:, ~ result.columns.duplicated(keep='first')]
        return result

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
            extraction_engine = KeyWordExtraction()
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
        # 读取CSV文件并提取数据
        with open(table_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            headers = next(reader)
            data_rows = list(reader)
        selected_rows = random.sample(data_rows,k=min(max_rows, len(data_rows)))
        result = [headers] + selected_rows
        return result

    # 先处理表格的 embedding
    def get_embedding_before(self):
        try:
            jina_embedding = JinaEmbedding(True)
            jina_embedding.embedding_one(os.path.join(self.enhance_case_path, 'table.csv'),self.enhance_case_path,add_time_timestamp=False)
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
        jina_embedding = JinaEmbedding(False)
        table_embedding = jina_embedding.read_embeddings(os.path.join(self.enhance_case_path, 'processed_embedding.npy'))
        q = QueryEngine()
        return q.query(table_embedding,k)

    def query_tables(self,k:int):
        self.get_embedding_before()
        self.processed_embedding()
        return self.query(k)

    def query_brute_force(self,k:int):
        self.get_embedding_before()
        self.processed_embedding()
        jina_embedding = JinaEmbedding(False)
        table_embedding = jina_embedding.read_embeddings(os.path.join(self.enhance_case_path, 'processed_embedding.npy'))
        q = QueryEngine()
        return q.query_brute_force(table_embedding,k)

    def extract_enhance_paras_from_history(self,history:List[Dict]):
        length = len(history)
        for i in range(length-1,-1,-1):
            one_history = history[i]
            if one_history["role"]=="assistant" and isinstance(one_history["content"],Dict):
                return one_history["content"]
        return None


if __name__ == '__main__':
    obj = EnhanceMainService("1228280263@qq.com",2)