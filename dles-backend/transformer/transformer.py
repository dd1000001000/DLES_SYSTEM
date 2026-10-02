# -*- coding: utf-8 -*-
import os
from pathlib import Path

import numpy as np
import torch
from tqdm import tqdm

from database.database import Database
from embedding.table_embedding import TableEmbedding
from logs.log import error_log
from transformer.model import load_checkpoint
from utils.read_config.read_config import read_config, resolve_data_path

config = read_config(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json'))
device = 'cuda' if torch.cuda.is_available() else 'cpu'


class Transformer:
    # 模型只加载一次
    _model = None

    def __init__(self, use_model = True):
        self.model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),config['model_path'])
        self.pure_embedding_path = resolve_data_path(config['pure_embedding_path'])
        self.processed_embedding_path = resolve_data_path(config['processed_embedding_path'])
        # 加载模型
        if use_model:
            if Transformer._model is None:
                Transformer._model = load_checkpoint(self.model_path, device)
            self.model = Transformer._model
        else:
            self.model = None
        # 这里永远不能把这个参数设置成为 True，因为 transformer 不应该承担任何 embedding 的工作
        self.table_embedding = TableEmbedding(use_embedding=False)
        self.device = device

    def get_processed_embedding(self,embedding:np.ndarray)->np.ndarray:
        embedding =  torch.from_numpy(embedding).to(self.device).float()
        with torch.no_grad():
            embedding = self.model(embedding)
        return embedding.cpu().numpy()

    def process_and_save_embedding(self,path_before:str,path_after:str):
        embedding_before = self.table_embedding.read_embeddings(path_before)
        embedding_after = self.get_processed_embedding(embedding_before)
        self.table_embedding.save_embeddings(path_after,embedding_after)

    def pre_all(self):
        """用训练好的模型处理数据湖里所有表格的向量，保存到 processed_embedding_path，并更新 table_base_info"""
        os.makedirs(self.processed_embedding_path, exist_ok=True)
        names = sorted(f for f in os.listdir(self.pure_embedding_path) if f.endswith('.npy'))
        failed = []
        for name in tqdm(names, desc='Transformer 处理向量', position=0, leave=True):
            filename = os.path.join(self.pure_embedding_path, name)
            try:
                # a/c -> b/c
                save_name = os.path.join(self.processed_embedding_path, Path(filename).stem + '.npy')
                self.process_and_save_embedding(filename, save_name)
                with Database() as db:
                    sql = "UPDATE table_base_info SET processed_embedding_path = %s WHERE pure_embedding_path = %s;"
                    db.execute_update(sql, (Path(save_name).as_posix(), Path(filename).as_posix()))
            except Exception as e:
                failed.append(name)
                error_log(f'转化表格错误: {filename},{e}')
        print(f'处理完成，失败 {len(failed)} 张：{failed[:10]}')

if __name__ == '__main__':
    Transformer().pre_all()
