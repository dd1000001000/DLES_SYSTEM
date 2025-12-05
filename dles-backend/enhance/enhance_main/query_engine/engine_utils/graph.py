# -*- coding: utf-8 -*-
import math
import random
from typing import List

import numpy as np
from numpy.typing import NDArray

import hdbscan
from sklearn.cluster import AgglomerativeClustering
from tqdm import tqdm
from enhance.enhance_main.query_engine.engine_utils.similarity import Similarity


class Graph:
    def __init__(self, tables: List[NDArray], min_cluster_size=None,min_samples=None):
        self.tables = tables
        self.n = len(tables)
        if min_cluster_size is None:
            min_cluster_size = max(10,self.n//50)
        if min_samples is None:
            min_samples = 1
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        # type1
        self.e = None
        # type2
        self.g = None

        self.k = 0
        self.center_indices = None
        self.labels = None
        self.k_points = None

        self.build_graph()


    def build_graph(self):
        # 预处理表格之间的距离
        distance = np.zeros((self.n, self.n))
        for i in tqdm(range(self.n),position=0, leave=True):
            for j in range(i + 1, self.n):
                simi = Similarity(self.tables[i], self.tables[j])
                distance[i, j] = distance[j, i] = simi.calc_distance()

        # distance = np.load('./distance.npy')
        distance = distance.astype(np.float64)
        # np.save("./distance.npy", distance)

        # hdbscan 排除移除点
        hdbscan_cluster  = hdbscan.HDBSCAN(min_cluster_size=self.min_cluster_size,min_samples=self.min_samples,metric='precomputed')
        hdbscan_labels = hdbscan_cluster.fit_predict(distance)


        self.labels = [0] * self.n
        self.center_indices = []
        # 异常点一组，非异常点一组
        # 异常点
        bad_points = np.where(hdbscan_labels == -1)[0]
        be_filtered_distance = distance[bad_points][:, bad_points]
        cluster_size = len(bad_points) // 32
        self.k += cluster_size
        agg = AgglomerativeClustering(n_clusters=cluster_size, metric='precomputed',linkage='complete')
        labels = agg.fit_predict(be_filtered_distance)
        center_indices = []
        for cluster_id in np.unique(labels):
            cluster_points = np.where(labels == cluster_id)[0]
            sub_matrix = be_filtered_distance[np.ix_(cluster_points, cluster_points)]
            avg_distances = np.mean(sub_matrix, axis=1)
            center_idx = cluster_points[np.argmin(avg_distances)]
            center_indices.append(center_idx)

        for i,label in enumerate(labels):
            self.labels[bad_points[i]] = label

        for i in center_indices:
            self.center_indices.append(bad_points[i])

        label_add = max(labels) + 1

        # 非异常点
        non_noise_indices = np.where(hdbscan_labels != -1)[0]
        filtered_distance = distance[non_noise_indices][:,non_noise_indices]
        cluster_size = len(non_noise_indices) // 32
        self.k += cluster_size
        agg = AgglomerativeClustering(n_clusters=cluster_size, metric='precomputed', linkage='complete')
        labels = agg.fit_predict(filtered_distance)
        center_indices = []
        for cluster_id in np.unique(labels):
            cluster_points = np.where(labels == cluster_id)[0]
            sub_matrix = filtered_distance[np.ix_(cluster_points, cluster_points)]
            avg_distances = np.mean(sub_matrix, axis=1)
            center_idx = cluster_points[np.argmin(avg_distances)]
            center_indices.append(center_idx)

        for i, label in enumerate(labels):
            self.labels[non_noise_indices[i]] = label + label_add

        for i in center_indices:
            self.center_indices.append(non_noise_indices[i])
        # 初始化 k_points 为数组
        self.k_points = [[] for _ in range(self.k)]

        # 分配每个点到对应的簇
        for i in range(self.n):
            self.k_points[self.labels[i]].append(i)

        self.e = [[] for _ in range(self.n)]
        self.g = [[] for _ in range(self.n)]

        # 簇内的边
        for i in range(self.k):
            for x in range(len(self.k_points[i])):
                for y in range(x+1,len(self.k_points[i])):
                    u,v = self.k_points[i][x], self.k_points[i][y]
                    self.e[u].append(v)
                    self.e[v].append(u)

        # 添加不同簇之间的最短边
        for k1 in range(self.k):
            for k2 in range(k1 + 1, self.k):
                min_dis = float('inf')
                ans = -1, -1
                for u in self.k_points[k1]:
                    for v in self.k_points[k2]:
                        if distance[u, v] < min_dis:
                            min_dis = distance[u, v]
                            ans = u, v
                if ans != (-1, -1):
                    self.g[ans[0]].append(ans[1])
                    self.g[ans[1]].append(ans[0])

        # 从每个簇中选择一些点，并与其他簇中的点连接
        for k in range(self.k):
            choose_num = math.ceil(len(self.k_points[k])//2)
            points = random.sample(self.k_points[k], choose_num)
            for point in points:
                min_dis = float('inf')
                ans = -1
                for v in range(self.n):
                    if self.labels[v] == k:
                        continue
                    if distance[point, v] < min_dis:
                        min_dis = distance[point, v]
                        ans = v
                if ans != -1:
                    self.g[point].append(ans)
                    self.g[ans].append(point)

        # 长边
        for k in range(self.k):
            choose_num = math.ceil(len(self.k_points[k])//50)
            points = random.sample(self.k_points[k], choose_num)
            for point in points:
                max_dis = float('-inf')
                ans = -1
                for v in range(self.n):
                    if self.labels[v] == k:
                        continue
                    if distance[point, v] > max_dis:
                        max_dis = distance[point, v]
                        ans = v
                if ans != -1:
                    self.g[point].append(ans)
                    self.g[ans].append(point)

        # 去重
        for i in range(len(non_noise_indices)):
            self.e[i] = list(set(self.e[i]))
            self.g[i] = list(set(self.g[i]))

        for i, v in enumerate(self.k_points):
            print("cluster size:", i, len(v))

    def query_top_k(self, q_table: NDArray,  k: int = 1):
        assert k <= self.n
        min_distance = float('inf')
        start = -1
        distance = [float('inf')] * self.n
        for c in self.center_indices:
            dis = Similarity(q_table, self.tables[c]).calc_distance()
            distance[c] = dis
            if dis < min_distance:
                min_distance = dis
                start = c
        self.SA(distance, start, q_table)
        result = list(enumerate(distance))
        result.sort(key=lambda item: item[1])
        assert len(result) >= k
        return result[:k]

    def SA(self, distance_list: List[float],start: int, q_table: NDArray, t1:float=None, t2:float=None, d1: float = None, d2: float = None)->List:
        if d1 is None:
            d1 = 0.99999
        if d2 is None:
            d2 = 0.99999
        if t1 is None:
            t1 = math.pow(d1,-self.n/5)
        if t2 is None:
            t2 = math.pow(d2,-self.n/5)
        is_visited = [False] * self.n
        simi = Similarity(q_table, self.tables[start])
        distance = simi.calc_distance()
        distance_list[start] = distance
        is_visited[start] = True
        while t1 > 1.0 or t2 > 1.0:
            if t1 > 1.0 and len(self.e[start]) > 0:
                u1 = random.choice(self.e[start])
                if is_visited[u1]:
                    u1 = random.choice(self.e[start])
                is_visited[u1] = True
                if distance_list[u1] != float('inf'):
                    score = distance_list[u1]
                else:
                    simi = Similarity(q_table, self.tables[u1])
                    score = simi.calc_distance()
                    distance_list[u1] = score
                # 小于必须选择
                if score <= distance:
                    distance = score
                    start = u1
                # 否则按照概率接受
                else:
                    poss = np.random.rand()
                    if poss <= np.exp((distance - score) / t1):
                        distance = score
                        start = u1
            if t2 > 1.0 and len(self.g[start]) > 0:
                u2 = random.choice(self.g[start])
                if is_visited[u2]:
                    u2 = random.choice(self.g[start])
                is_visited[u2] = True
                if distance_list[u2] != float('inf'):
                    score = distance_list[u2]
                else:
                    simi = Similarity(q_table, self.tables[u2])
                    score = simi.calc_distance()
                    distance_list[u2] = score
                if score <= distance:
                    distance = score
                    start = u2
                else:
                    poss = np.random.rand()
                    if poss <= np.exp((distance - score) / t2):
                        distance = score
                        start = u2
            t1 *= d1
            t2 *= d2
        return distance_list

    def query_top_k_brute_force(self, q_table: NDArray, k: int = 1):
        distance = [float('inf')] * self.n
        for i in range(self.n):
            simi = Similarity(q_table, self.tables[i])
            distance[i] = simi.calc_distance()
        result = list(enumerate(distance))
        result.sort(key=lambda item: item[1])
        return result[:k]
