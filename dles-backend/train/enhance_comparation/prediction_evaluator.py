# -*- coding: utf-8 -*-
import re
from collections import Counter
from typing import List

import numpy as np

# 英文/数字按单词切分，中文按单字切分，标点和空白自然被丢掉
TOKEN_PATTERN = re.compile(r'[\u4e00-\u9fff]|[^\W_\u4e00-\u9fff]+')


class PredictionEvaluator:
    @staticmethod
    def _check_length(predictions: List, answers: List):
        if len(predictions) != len(answers):
            raise Exception('预测值数组和真实值数组必须等长')
        if len(predictions) == 0:
            raise Exception('没有可以评估的数据')

    @staticmethod
    def tokenize(text) -> List[str]:
        return TOKEN_PATTERN.findall(str(text).lower())

    @staticmethod
    def calc_accuracy(predictions: List, answers: List) -> float:
        PredictionEvaluator._check_length(predictions, answers)
        same_count = sum(1 for x, y in zip(predictions, answers) if x == y)
        return same_count / len(predictions)

    @staticmethod
    def calc_RMSE(predictions: List, answers: List) -> float:
        PredictionEvaluator._check_length(predictions, answers)
        x_true = np.array(answers, dtype=float)
        x_pred = np.array(predictions, dtype=float)
        return float(np.sqrt(np.mean((x_true - x_pred) ** 2)))

    def calc_exact_match(self, predictions: List, answers: List) -> float:
        """忽略大小写、标点和空白后，预测值和真实值完全一致的比例"""
        self._check_length(predictions, answers)
        same_count = sum(1 for x, y in zip(predictions, answers) if self.tokenize(x) == self.tokenize(y))
        return same_count / len(predictions)

    def calc_F1(self, predictions: List, answers: List) -> float:
        """
        文本预测的评分：逐条计算预测值与真实值的词级 F1，再取平均（和问答任务评测里的 F1 一样）。
        预测 "United States" 而真实值是 "United States of America" 时，能得到部分分数，
        而不是像整串比较那样直接得 0。
        """
        self._check_length(predictions, answers)
        scores = []
        for pred, true in zip(predictions, answers):
            pred_tokens = self.tokenize(pred)
            true_tokens = self.tokenize(true)
            if not pred_tokens or not true_tokens:
                # 两边都没有有效内容视为一致，只有一边没有则完全不一致
                scores.append(1.0 if pred_tokens == true_tokens else 0.0)
                continue
            common = sum((Counter(pred_tokens) & Counter(true_tokens)).values())
            if common == 0:
                scores.append(0.0)
                continue
            precision = common / len(pred_tokens)
            recall = common / len(true_tokens)
            scores.append(2 * precision * recall / (precision + recall))
        return float(np.mean(scores))
