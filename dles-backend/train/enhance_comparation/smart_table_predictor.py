# -*- coding: utf-8 -*-
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputRegressor


class SmartTablePredictor(BaseEstimator):
    def __init__(self, text_features_max=100, target_text_keywords=50):
        self.text_features_max = text_features_max
        self.target_text_keywords = target_text_keywords
        self.is_text_target = None
        self.text_vectorizers = {}
        self.target_vectorizer = None
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

    def _detect_type(self, y):
        return isinstance(y.iloc[0], str) if hasattr(y, 'iloc') else isinstance(y[0], str)

    def _fit_features(self, X):
        numeric_cols = X.select_dtypes(include=np.number).columns.tolist()
        text_cols = [col for col in X.columns if col not in numeric_cols]
        self.feature_order = numeric_cols + text_cols

        numeric_features = X[numeric_cols].values if numeric_cols else np.zeros((len(X), 0))

        numeric_feature_names = numeric_cols.copy()

        text_features_list = []
        text_feature_names = []
        for col in text_cols:
            vec = TfidfVectorizer(max_features=self.text_features_max)
            self.text_vectorizers[col] = vec
            transformed = vec.fit_transform(X[col].astype(str)).toarray()
            text_features_list.append(transformed)

            if self.text_features_max == 1:
                text_feature_names.append(f"{col}_{vec.get_feature_names_out()[0]}")
            else:
                text_feature_names.extend([f"{col}_{word}" for word in vec.get_feature_names_out()])

        if text_features_list:
            text_features = np.hstack(text_features_list)
            self.feature_names = numeric_feature_names + text_feature_names
            return np.hstack([numeric_features, text_features])
        else:
            self.feature_names = numeric_feature_names
            return numeric_features

    def _transform_features(self, X):
        numeric_cols = [col for col in self.feature_order if col in X.select_dtypes(include=np.number).columns]
        text_cols = [col for col in self.feature_order if col not in numeric_cols]

        numeric_features = X[numeric_cols].values if numeric_cols else np.zeros((len(X), 0))

        text_features_list = []
        for col in text_cols:
            vec = self.text_vectorizers.get(col)
            if vec:
                transformed = vec.transform(X[col].astype(str)).toarray()
                text_features_list.append(transformed)

        if text_features_list:
            text_features = np.hstack(text_features_list)
            return np.hstack([numeric_features, text_features])
        else:
            return numeric_features

    def _process_text_target(self, y):
        self.target_vectorizer = TfidfVectorizer(max_features=self.target_text_keywords)
        return self.target_vectorizer.fit_transform(y).toarray()

    def fit(self, X, y):
        for col in X.columns:
            X[col] = self.try_convert_to_numeric(X[col])
        y = self.try_convert_to_numeric(y)
        self.is_text_target = self._detect_type(y)
        X_processed = self._fit_features(X)

        if self.is_text_target:
            y_processed = self._process_text_target(y)
            self.model = MultiOutputRegressor(lgb.LGBMRegressor())
        else:
            y_processed = y
            self.model = lgb.LGBMRegressor()

        if len(self.feature_names) == X_processed.shape[1]:
            X_processed = pd.DataFrame(X_processed, columns=self.feature_names)

        self.model.fit(X_processed, y_processed)
        return self

    def predict(self, X):
        X_processed = self._transform_features(X)

        if len(self.feature_names) == X_processed.shape[1]:
            X_processed = pd.DataFrame(X_processed, columns=self.feature_names)

        if self.is_text_target:
            pred = self.model.predict(X_processed)
            keywords = self.target_vectorizer.get_feature_names_out()
            return [keywords[row.argmax()] for row in pred]
        else:
            return self.model.predict(X_processed)


# 示例使用
if __name__ == "__main__":
    predict_column = "Amount"
    df = pd.read_csv("E:/DLES_System/dles-backend/train/temp_csv_files/84d8c4cd-353c-4cf5-9e10-c487a4d9ac28/01_April_28201829.csv")
    X = df.drop(columns=[predict_column])
    y = df[predict_column]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    print("=== 数值预测 ===")
    model = SmartTablePredictor()
    model.fit(X_train, y_train)
    print(model.predict(X_test))


