import math
import random
from typing import List

import numpy as np
from numpy.typing import NDArray
from tqdm import tqdm

from enhance.enhance_main.query_engine.engine_utils.similarity import Similarity


class DSU:
    def __init__(self, size):
        self.parent = list(range(size))  # 父节点数组

    def find(self, x):
        if x==self.parent[x]:
            return x
        else:
            self.parent[x] = self.find(self.parent[x])
            return self.parent[x]

    def union(self, x, y):
        x_root = self.find(x)
        y_root = self.find(y)
        if x_root == y_root:
            return False
        self.parent[y_root] = x_root
        return True

class Graph2:
    def __init__(self,  tables: List[NDArray], max_layers = 5,edge_short = 0.145,edge_long = 0.005):
        self.tables = tables
        self.n = len(self.tables)
        self.ml = 1.0 / math.log(self.n)
        self.max_layers = max_layers
        self.edge_short = edge_short
        self.edge_long = edge_long

        self.layer = [0]*self.n
        self.layer_nodes = [[] for _ in range(self.max_layers)]
        self.assign_layers()

        self.e = [[[] for i in range(self.n)] for _ in range(self.max_layers)]

        self.distance = self.get_distance()
        self.build_graph()

    def assign_layers(self):
        for i in range(self.n):
            possibility = random.random()
            for j in range(self.max_layers-1, -1, -1):
                if possibility <= math.pow(self.ml,j):
                    self.layer[i] = self.max_layers - 1 - j
                    break
        if 0 not in self.layer:
            x = random.randint(0, self.n - 1)
            self.layer[x] = 0

        for i in range(self.n):
            self.layer_nodes[self.layer[i]].append(i)

        for i in range(self.max_layers):
            print(i,len(self.layer_nodes[i]))

    def get_distance(self):
        distance = np.zeros((self.n, self.n))
        for i in tqdm(range(self.n),position=0, leave=True):
            for j in range(i + 1, self.n):
                simi = Similarity(self.tables[i], self.tables[j])
                distance[i, j] = distance[j, i] = simi.calc_distance()
        distance = distance.astype(np.float64)
        return distance

    def build_graph(self):
        for k in range(self.max_layers):
            nodes = self._get_layer_nodes_less_than(k)
            edges = []
            for i in nodes:
                for j in nodes:
                    if i == j:
                        continue
                    edges.append((i, j, self.distance[i, j]))
            edges.sort(key=lambda x: x[2])
            dsu = DSU(self.n)
            remaining_edges = []
            for edge in edges:
                i, j, d = edge
                if dsu.union(i, j):
                    self.e[k][i].append(j)
                    self.e[k][j].append(i)
                else:
                    remaining_edges.append(edge)
            edges = remaining_edges
            len_short = math.ceil(len(edges)*self.edge_short)
            len_long = math.ceil(len(edges)*self.edge_long)
            for index in range(len_short):
                i,j,d = edges[index]
                self.e[k][i].append(j)
                self.e[k][j].append(i)

            for index in range(len(edges)-1,len(edges)-1-len_long,-1):
                i,j,d = edges[index]
                self.e[k][i].append(j)
                self.e[k][j].append(i)

            for i in range(self.n):
                self.e[k][i] = list(set(self.e[k][i]))

    def _get_layer_nodes_less_than(self, layer):
        return [i for i in range(self.n) if self.layer[i] <= layer]

    def query_top_k(self, q_table:NDArray, k:int = 1):
        assert k<=self.n
        distance = [float('inf')] * self.n
        start = random.choice(self.layer_nodes[0])
        simi = Similarity(q_table, self.tables[start])
        distance[start] = simi.calc_distance()

        def SA(current_node,layer,steps=None):
            if steps is None:
                steps = math.ceil(len(self.layer_nodes[layer])//5)
            while steps > 0:
                min_dis = float('inf')
                next_node = -1
                for v in self.e[layer][current_node]:
                    if distance[v] == float('inf'):
                        simi = Similarity(q_table,self.tables[v])
                        distance[v] = simi.calc_distance()
                    if distance[v] < min_dis:
                        min_dis = distance[v]
                        next_node = v
                current_node = next_node
                steps -= 1

        for _ in range(self.max_layers):
            SA(start,_)
            start = min(range(len(distance)), key=lambda i: distance[i])

        result = list(enumerate(distance))
        result.sort(key=lambda item: item[1])
        assert len(result) >= k
        return result[:k]

    def query_top_k_brute_force(self, q_table: NDArray, k: int = 1):
        distance = [float('inf')] * self.n
        for i in range(self.n):
            simi = Similarity(q_table, self.tables[i])
            distance[i] = simi.calc_distance()
        result = list(enumerate(distance))
        result.sort(key=lambda item: item[1])
        return result[:k]

