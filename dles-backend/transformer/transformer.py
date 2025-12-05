# -*- coding: utf-8 -*-
import os
from pathlib import Path

import numpy as np
import torch

from database.database import Database
from embedding.jina_embedding import JinaEmbedding
from logs.log import error_log
# 这里导入模型依赖的子模型，不要删除！！！
from transformer.model import TableContrastiveModel, TransformerEncoder
# from model import TableContrastiveModel, TransformerEncoder

from utils.read_config.read_config import read_config

config = read_config(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json'))


class Transformer:
    def __init__(self, use_model = True):
        self.model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),config['model_path'])
        self.pure_embedding_path = config['pure_embedding_path']
        self.processed_embedding_path = config['processed_embedding_path']
        # 加载模型
        if use_model:
            self.model = torch.load(self.model_path,weights_only=False)
            self.model.eval()
        else:
            self.model = None
        # 这里永远不能把这个参数设置成为 True，因为 transformer 不应该承担任何 embedding 的工作
        self.jina_embedding = JinaEmbedding(use_embedding=False)
        self.device  = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    def get_processed_embedding(self,embedding:np.ndarray)->np.ndarray:
        embedding =  torch.from_numpy(embedding).to(self.device).float()
        embedding = self.model(embedding)
        return embedding.cpu().detach().numpy()

    def process_and_save_embedding(self,path_before:str,path_after:str):
        embedding_before = self.jina_embedding.read_embeddings(path_before)
        embedding_after = self.get_processed_embedding(embedding_before)
        self.jina_embedding.save_embeddings(path_after,embedding_after)

    def pre_all(self):
        for filename in os.listdir(self.pure_embedding_path):
            filename = os.path.join(self.pure_embedding_path, filename)
            if os.path.isfile(filename):
                try:
                    # a/c -> b/c
                    name = Path(filename).stem
                    save_name = os.path.join(self.processed_embedding_path, name+'.npy')
                    self.process_and_save_embedding(filename,save_name)
                    filename = Path(filename).as_posix()
                    save_name = Path(save_name).as_posix()
                    db = Database()
                    sql = f"UPDATE table_base_info SET processed_embedding_path = '{save_name}' WHERE pure_embedding_path = '{filename}';"
                    db.execute_update(sql)
                    db.close()
                    print(f'成功转化表格：{filename}')
                except Exception as e:
                    error_log(f'转化表格错误: {filename},{e}')

if __name__ == '__main__':
    t = Transformer()
    t.pre_all()