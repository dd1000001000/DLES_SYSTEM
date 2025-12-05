import random
import time

import numpy as np
from numpy.typing import NDArray
from tqdm import tqdm

from database.database import Database
from embedding.jina_embedding import JinaEmbedding
from enhance.enhance_main.query_engine.engine_utils.graph import Graph
from enhance.enhance_main.query_engine.engine_utils.graph2 import Graph2


class QueryEngine:
    # 静态变量
    graph = None
    def __init__(self):
        if QueryEngine.graph is None:
            self.build_graph()


    def load_embeddings(self):
        db = Database()
        sql = 'SELECT * FROM table_base_info;'
        tables_info = db.execute_query(sql)
        db.close()
        tables = [None] * len(tables_info)
        jina = JinaEmbedding(False)
        for table_info in tables_info:
            save_path = table_info['processed_embedding_path']
            embedding = jina.read_embeddings(save_path)
            tables[table_info['table_id'] - 1] = embedding
        return tables

    def build_graph(self):
        tables = self.load_embeddings()
        QueryEngine.graph = Graph2(tables)

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




