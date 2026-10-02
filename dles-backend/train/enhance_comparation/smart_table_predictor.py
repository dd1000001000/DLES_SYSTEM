# -*- coding: utf-8 -*-
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.multioutput import MultiOutputRegressor
from sklearn.preprocessing import LabelEncoder


class SmartTablePredictor(BaseEstimator):
    """
    预测表格中的某一列。特征列里的数值列直接使用，文本列做 TF-IDF。

    目标列是数值：LightGBM 回归，输出数值。
    目标列是文本：输出的一定是目标列里出现过的完整取值（而不是单个关键词），这样才能和真实值逐条比较。
      - 取值种类不多（<= max_classes，例如国家、类别）：当作分类问题，LightGBM 分类器直接预测取值。
      - 取值种类很多（例如名称、描述）：先回归出目标文本的 TF-IDF 向量，
        再在训练集出现过的取值里找余弦相似度最高的那一个作为预测结果。
    """

    def __init__(self, text_features_max=100, target_text_keywords=50, max_classes=30):
        self.text_features_max = text_features_max
        self.target_text_keywords = target_text_keywords
        self.max_classes = max_classes
        self.is_text_target = None
        self.target_mode = None  # 'classify' | 'retrieve' | 'constant'
        self.text_vectorizers = {}
        self.target_vectorizer = None
        self.label_encoder = None
        self.constant_label = None
        self.candidate_labels = None
        self.candidate_vectors = None
        self.model = None
        self.feature_order = []
        self.feature_names = []

    @staticmethod
    def try_convert_to_numeric(series):
        """
        尝试将Series转换为数值类型：
        1. 如果是object类型，先尝试清理字符串
        2. 尝试转换为数值
        3. 如果转换失败，保持原样
        """
        if series.dtype == object:
            original_series = series.copy()
            try:
                cleaned = series.astype(str).str.replace(",", "").str.replace("$", "").str.replace(" ", "")
                numeric_series = pd.to_numeric(cleaned, errors="raise")
                if (numeric_series % 1 == 0).all() and not numeric_series.isna().any():
                    return numeric_series.astype(int)
                return numeric_series
            except (ValueError, TypeError):
                return original_series
        return series

    @staticmethod
    def _detect_type(y):
        return not pd.api.types.is_numeric_dtype(y)

    def _fit_features(self, X):
        numeric_cols = X.select_dtypes(include=np.number).columns.tolist()
        text_cols = [col for col in X.columns if col not in numeric_cols]
        self.feature_order = numeric_cols + text_cols

        numeric_features = X[numeric_cols].values if numeric_cols else np.zeros((len(X), 0))

        text_features_list = []
        for col in text_cols:
            vec = TfidfVectorizer(max_features=self.text_features_max)
            try:
                transformed = vec.fit_transform(X[col].astype(str)).toarray()
            except ValueError:
                # 整列都是停用词/标点，词表为空，这一列没有可用信息
                continue
            self.text_vectorizers[col] = vec
            text_features_list.append(transformed)

        if text_features_list:
            return np.hstack([numeric_features] + text_features_list).astype(float)
        return numeric_features.astype(float)

    def _transform_features(self, X):
        numeric_cols = [col for col in self.feature_order if col in X.select_dtypes(include=np.number).columns]
        text_cols = [col for col in self.feature_order if col not in numeric_cols]

        numeric_features = X[numeric_cols].values if numeric_cols else np.zeros((len(X), 0))

        text_features_list = []
        for col in text_cols:
            vec = self.text_vectorizers.get(col)
            if vec:
                text_features_list.append(vec.transform(X[col].astype(str)).toarray())

        if text_features_list:
            return np.hstack([numeric_features] + text_features_list).astype(float)
        return numeric_features.astype(float)

    @staticmethod
    def _to_frame(matrix):
        # LightGBM 不允许特征名里有 JSON 特殊字符，而列名/词语里什么都可能出现，所以统一用编号命名
        return pd.DataFrame(matrix, columns=[f'f{i}' for i in range(matrix.shape[1])])

    def _fit_text_target(self, X_frame, y):
        y_text = y.astype(str).reset_index(drop=True)
        labels = sorted(y_text.unique())

        if len(labels) == 1:
            self.target_mode = 'constant'
            self.constant_label = labels[0]
            return

        if len(labels) <= self.max_classes:
            self.target_mode = 'classify'
            self.label_encoder = LabelEncoder().fit(y_text)
            self.model = lgb.LGBMClassifier(verbose=-1)
            self.model.fit(X_frame, self.label_encoder.transform(y_text))
            return

        self.target_mode = 'retrieve'
        self.target_vectorizer = TfidfVectorizer(max_features=self.target_text_keywords)
        try:
            y_vectors = self.target_vectorizer.fit_transform(y_text).toarray()
        except ValueError:
            # 目标文本里提取不出任何词，退化为总是预测出现最多的取值
            self.target_mode = 'constant'
            self.constant_label = y_text.value_counts().idxmax()
            return
        self.candidate_labels = np.array(labels)
        self.candidate_vectors = self.target_vectorizer.transform(self.candidate_labels).toarray()
        self.model = MultiOutputRegressor(lgb.LGBMRegressor(verbose=-1))
        self.model.fit(X_frame, y_vectors)

    def fit(self, X, y):
        X = X.copy()
        for col in X.columns:
            X[col] = self.try_convert_to_numeric(X[col])
        y = self.try_convert_to_numeric(y)
        self.is_text_target = self._detect_type(y)
        X_frame = self._to_frame(self._fit_features(X))

        if self.is_text_target:
            self._fit_text_target(X_frame, y)
        else:
            self.target_mode = 'regress'
            self.model = lgb.LGBMRegressor(verbose=-1)
            self.model.fit(X_frame, y)
        return self

    def predict(self, X):
        X = X.copy()
        for col in X.columns:
            X[col] = self.try_convert_to_numeric(X[col])
        X_frame = self._to_frame(self._transform_features(X))

        if not self.is_text_target:
            return self.model.predict(X_frame)
        if self.target_mode == 'constant':
            return [self.constant_label] * len(X_frame)
        if self.target_mode == 'classify':
            return list(self.label_encoder.inverse_transform(self.model.predict(X_frame)))

        predicted_vectors = self.model.predict(X_frame)
        norm_pred = np.maximum(np.linalg.norm(predicted_vectors, axis=1, keepdims=True), 1e-12)
        norm_cand = np.maximum(np.linalg.norm(self.candidate_vectors, axis=1, keepdims=True), 1e-12)
        similarity = (predicted_vectors / norm_pred) @ (self.candidate_vectors / norm_cand).T
        return list(self.candidate_labels[similarity.argmax(axis=1)])
