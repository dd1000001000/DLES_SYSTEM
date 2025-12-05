# -*- coding: utf-8 -*-
import math

import numpy as np
from numpy.typing import NDArray


class Similarity:
    def __init__(self, table1: NDArray, table2: NDArray):
        self.n = len(table1)
        self.m = len(table2)
        self.table1 = table1
        self.table2 = table2
        self.threshold = 0
        self.similarity_matrix = self.cosine_similarity_matrix(self.table1, self.table2)

    def cosine_similarity_matrix(self, table1: np.ndarray, table2: np.ndarray):
        # 计算 L2 范数，避免除零
        norm1 = np.linalg.norm(table1, axis=1, keepdims=True)  # (m1, 1)
        norm2 = np.linalg.norm(table2, axis=1, keepdims=True)  # (m2, 1)
        # 计算余弦相似度
        similarity_matrix = np.dot(table1, table2.T) / (norm1 @ norm2.T)
        similarity_matrix[similarity_matrix < self.threshold] = 1e-9
        return similarity_matrix

    def sinkhorn_knopp(self, similarity_matrix, num_iter=10):
        """Sinkhorn-Knopp 算法用于近似双随机矩阵"""
        for _ in range(num_iter):
            similarity_matrix = similarity_matrix / similarity_matrix.sum(axis=1, keepdims=True)  # 行归一化
            similarity_matrix = similarity_matrix / similarity_matrix.sum(axis=0, keepdims=True)  # 列归一化
        return similarity_matrix

    def select_matches(self, matched_matrix):
        """
        从双随机矩阵中选择 min(n, m) 对匹配关系
        :param matched_matrix: 双随机矩阵
        :return: 匹配关系列表 [(i, j)]
        """
        n, m = matched_matrix.shape
        k = min(n, m)
        matches = []
        matrix = matched_matrix.copy()  # 防止修改原矩阵
        for _ in range(k):
            max_idx = np.argmax(matrix)  # 找到矩阵中最大值的索引
            i = max_idx // m  # 计算行索引
            j = max_idx % m  # 计算列索引
            matches.append((i, j))
            # 将选中的行和列置零，保证每个点只能匹配一次
            matrix[i, :] = 0
            matrix[:, j] = 0

        return matches

    def calc_distance(self) -> float:
        normalized_matrix = self.sinkhorn_knopp(self.similarity_matrix)
        matches = self.select_matches(normalized_matrix)
        # 加速最大流的计算
        total_weight = sum(self.similarity_matrix[i, j] for i, j in matches)
        if total_weight <= 0:
            total_weight = 1e-9
        return max(self.n, self.m) / total_weight
