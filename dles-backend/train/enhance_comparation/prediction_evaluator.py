# -*- coding: utf-8 -*-
import re
import string
from typing import List
from sklearn.metrics import f1_score
import numpy as np


class PredictionEvaluator:
    def __init__(self):
        self.punctuations  = string.punctuation + "！？｡＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～、。「」《》【】 "
        self.pattern = f"[{re.escape(self.punctuations)}]"

    @staticmethod
    def calc_accuracy(predictions:List,answers:List) -> float:
        if len(predictions) != len(answers):
            raise Exception('预测值数组和真实值数组必须等长')
        same_count = 0
        for x,y in zip(predictions,answers):
            if x==y:
                same_count += 1
        return same_count / len(predictions)

    @staticmethod
    def calc_RMSE(predictions:List,answers:List) -> float:
        if len(predictions) != len(answers):
            raise Exception('预测值数组和真实值数组必须等长')
        x_true = np.array(answers)
        x_pred = np.array(predictions)
        rmse = np.sqrt(np.mean((x_true - x_pred)**2))
        return rmse

    def calc_F1(self,predictions:List,answers:List) -> float:
        if len(predictions) != len(answers):
            raise Exception('预测值数组和真实值数组必须等长')
        x_pred = [re.sub(self.pattern,"",text.lower()) for text in predictions]
        x_true = [re.sub(self.pattern,"",text.lower()) for text in answers]
        score = f1_score(x_true,x_pred,average='micro')
        return score

if __name__ == '__main__':
    predictor = PredictionEvaluator()
    y_true = ["体育", "科!!!技", "政 治", "体育", "娱乐"]
    y_pred = ["体育", "科技", "娱乐", "体育", "财经"]
    print(predictor.calc_accuracy(y_pred,y_true))