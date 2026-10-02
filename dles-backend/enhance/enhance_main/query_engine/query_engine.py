import random
import threading
import time

import numpy as np
import torch
from numpy.typing import NDArray
from tqdm import tqdm

from database.database import Database
from embedding.table_embedding import TableEmbedding
from enhance.enhance_main.query_engine.engine_utils.graph2 import Graph2
from transformer.similarity_torch import pairwise_distance_matrix


class QueryEngine:
    # 静态变量
    graph = None
    _build_lock = threading.Lock()

    def __init__(self):
        if QueryEngine.graph is None:
            with QueryEngine._build_lock:
                if QueryEngine.graph is None:
                    self.build_graph()


    def load_embeddings(self):
        with Database() as db:
            sql = 'SELECT * FROM table_base_info;'
            tables_info = db.execute_query(sql)
        tables = [None] * len(tables_info)
        embedder = TableEmbedding(False)
        for table_info in tables_info:
            save_path = table_info['processed_embedding_path']
            if save_path is None or not 1 <= table_info['table_id'] <= len(tables_info):
                raise Exception(f"table_base_info 数据不完整（table_id={table_info['table_id']}），"
                                "table_id 必须从 1 开始连续，且每张表都要有 processed_embedding_path")
            embedding = embedder.read_embeddings(save_path)
            tables[table_info['table_id'] - 1] = embedding
        return tables

    def build_graph(self):
        tables = self.load_embeddings()
        # 用 GPU 批量计算所有表格两两之间的距离，比逐对调用 numpy 版 Similarity 快几个数量级
        distance = pairwise_distance_matrix(tables, device='cuda' if torch.cuda.is_available() else 'cpu')
        QueryEngine.graph = Graph2(tables, distance=distance)

    def query(self,embedding:NDArray,k:int=1):
        return QueryEngine.graph.query_top_k(embedding,k)

    def query_brute_force(self,embedding:NDArray,k:int=1):
        return QueryEngine.graph.query_top_k_brute_force(embedding,k)


if __name__ == '__main__':
    q = QueryEngine()


    def get_precision(pans, jans):
        count = 0
        ans = [a for (a, b) in jans]
        for a, b in pans:
            if a in ans:
                count += 1
        return count / len(ans)

    k = 10
    batch = 100
    precision = [0]*k
    timec = 0
    timeb = 0
    for t in tqdm(range(batch),position=0, leave=True):
        dim = random.randint(2, 10)
        random_vector = np.random.rand(dim, 768)
        for i in range(k):
            tim = time.time()
            resultc = q.query(random_vector,i+1)
            timec += time.time()-tim
            tim = time.time()
            resultb = q.query_brute_force(random_vector,i+1)
            timeb += time.time()-tim
            precision[i] += get_precision(resultc,resultb)

    print(f'k = {k}, batch = {batch}')
    print(f'time brute: {timeb}, time cluster: {timec}, percentage: {timec/timeb}')
    for i in range(k):
        print(f'k = {i+1} precision: {precision[i]/batch}')




