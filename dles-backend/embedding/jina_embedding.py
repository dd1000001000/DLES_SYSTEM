# -*- coding: utf-8 -*-
import csv
import math
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import string
import numpy as np
import pandas as pd
from transformers import AutoModel, AutoTokenizer
from tqdm import tqdm
from database.database import Database
from logs.log import error_log
from utils.read_config.read_config import read_config


config = read_config(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json'))
model_path = config['model_path']
device = 'cuda'

class JinaEmbedding:
    # 静态变量
    words_IDF = None
    def __init__(self,use_embedding=True):
        self.max_token_length = config['max_token_length']
        self.pure_table_path = config['pure_table_path']
        self.pure_embedding_path = config['pure_embedding_path']
        if use_embedding:
            self.model = AutoModel.from_pretrained(model_path, trust_remote_code=True).to(device)
            self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
            if JinaEmbedding.words_IDF is None:
                JinaEmbedding.words_IDF = self._get_IDF()
        else:
            self.model = None
            self.tokenizer = None
        self.embedding_length = config['embedding_length']
        self.batch_sz = config['batch_sz']
        self.keep_lines = config['max_token_length']

    @staticmethod
    def clean_and_split(text):
        text = str(text)  # 确保是字符串
        translator = str.maketrans('', '', string.punctuation)
        clean_text = text.translate(translator).lower()
        return clean_text.split()

    def _get_IDF(self):
        words_count = defaultdict(int)
        file_count = 0
        for filename in tqdm(os.listdir(self.pure_table_path),position=0, leave=True):
            filename = os.path.join(self.pure_table_path, filename)
            if not os.path.isfile(filename):
                continue
            file_count += 1
            word_counted = set()
            df = pd.read_csv(filename,low_memory=False)
            for column in df.columns:
                words = self.clean_and_split(column)
                for word in words:
                    if word not in word_counted:
                        words_count[word] += 1
                        word_counted.add(word)

            for column in df.columns:
                for cell in df[column]:
                    words = self.clean_and_split(cell)
                    for word in words:
                        if word not in word_counted:
                            words_count[word] += 1
                            word_counted.add(word)

        words_IDF = defaultdict(float)
        for k,v in words_count.items():
            score = math.log(file_count/(v+1)) + 1
            words_IDF[k] = score
        return words_IDF

    def get_table_columns(self,table_path:str)->list[str]:
        with open(table_path,mode='r',newline='',encoding='utf-8') as table:
            reader = csv.reader(table)
            headers = next(reader)
            rows = list(reader)
            word_count = defaultdict(int)
            word_cnt = 0
            for header in headers:
                words = self.clean_and_split(header)
                for word in words:
                    word_count[word] += 1
                    word_cnt += 1
            for row in rows:
                for cell in row:
                    words = self.clean_and_split(cell)
                    for word in words:
                        word_count[word] += 1
                        word_cnt += 1
            # 计算每个文本的得分
            word_score = defaultdict(float)
            for word, cnt in word_count.items():
                word_score[word] = cnt / word_cnt * JinaEmbedding.words_IDF[word]
            # 按照行的方式计算每行的保留得分
            line_score = []
            for row in rows:
                score = 0.0
                for cell in row:
                    words = self.clean_and_split(cell)
                    for word in words:
                        score += word_score[word]
                line_score.append((row,score))
            # IN-TDF
            line_score = sorted(line_score, key=lambda x:x[1], reverse=True)
            lines = [row for row,score in line_score]
            columns = defaultdict(list)
            for row in lines:
                for i, value in enumerate(row):
                    columns[headers[i]].append(value)
                is_exceeded = False
                for k,v in columns.items():
                    text = ' '.join([k]+v)
                    if len(self.tokenizer.encode(text)) > self.max_token_length:
                        is_exceeded = True
                        break
                if is_exceeded:
                    for i,value in enumerate(row):
                        columns[headers[i]].pop()
                    break
            result = list()
            for header in headers:
                result.append(' '.join([header]+columns[header]))
            return result

    def get_text_embeddings(self,texts:list[str])->list:
        embeddings = []
        for text in texts:
            input_ids = self.tokenizer.encode(text)
            tokens_len = len(input_ids)
            assert tokens_len<=self.max_token_length
            if tokens_len<=self.max_token_length:
                embedding = self.model.encode([text],device=device)
                embeddings.append(embedding[0])
            else:
                block_sz = self.max_token_length
                divisor = (tokens_len+block_sz-1)//block_sz
                embedding = np.zeros(self.embedding_length)
                text_list = []
                for i in range(0,tokens_len,block_sz):
                    text=self.tokenizer.decode(input_ids[i:min(i+block_sz,tokens_len)])
                    text_list.append(text)
                    if len(text_list)>=self.batch_sz or i+block_sz>=tokens_len:
                        one_embeddings = self.model.encode(text_list,device=device)
                        for one_embedding in one_embeddings:
                            embedding+=one_embedding
                        text_list.clear()
                # 直接取平均值
                embedding//=divisor
                embeddings.append(embedding)

        return embeddings

    def save_embeddings(self,save_path,embeddings:list|np.ndarray):
        embeddings = np.array(embeddings)
        np.save(save_path,embeddings)

    def embedding_one(self, table_path:str, save_folder:str, add_time_timestamp=True)->str:
        if not os.path.isfile(table_path):
            raise Exception('表格不存在')
        columns = self.get_table_columns(table_path)
        embeddings = self.get_text_embeddings(columns)
        timestamp = str(int(datetime.now().timestamp()))
        name = Path(table_path).stem
        save_name = os.path.join(save_folder, name + (('_' + timestamp) if add_time_timestamp else '') + '.npy')
        self.save_embeddings(save_name, embeddings)
        return save_name

    def pre_all(self):
        for filename in tqdm(os.listdir(self.pure_table_path),position=0,leave=True):
            filename = os.path.join(self.pure_table_path,filename)
            if os.path.isfile(filename):
                try:
                    save_name = self.embedding_one(filename,self.pure_embedding_path)
                    filename = Path(filename).as_posix()
                    save_name = Path(save_name).as_posix()
                    db=Database()
                    sql = f"INSERT INTO table_base_info (table_path, pure_embedding_path) VALUES ('{filename}','{save_name}');"
                    db.execute_update(sql)
                    db.close()
                    print(f'成功向量化表格: {filename}')
                except Exception as e:
                    error_log(f'初始化表格向量错误: {filename},{e}')

    def read_embeddings(self, save_path: str)->np.ndarray:
        embeddings = np.load(save_path)
        return embeddings

if __name__=='__main__':
    jina_embedding = JinaEmbedding()
    jina_embedding.pre_all()