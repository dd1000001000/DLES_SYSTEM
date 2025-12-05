import os
from typing import List

import pandas as pd
from fastapi import UploadFile
from sklearn.model_selection import train_test_split

from train.enhance_comparation.csvfile_manager import CsvFileManager
from train.enhance_comparation.model.models import EvaluateParas
from train.enhance_comparation.prediction_evaluator import PredictionEvaluator
from train.enhance_comparation.smart_table_predictor import SmartTablePredictor


class TempFileService:
    @staticmethod
    def get_file_names(folder_name:str) -> List[str]:
        csv_file_manager = CsvFileManager()
        return csv_file_manager.get_file_names(folder_name)

    @staticmethod
    def delete_folder(folder_name:str) -> None:
        csv_file_manager = CsvFileManager()
        csv_file_manager.delete_folder(folder_name)

    @staticmethod
    def get_columns(folder_name:str) -> List[str]:
        csv_file_manager = CsvFileManager()
        return csv_file_manager.get_predict_column_names(folder_name)

    @staticmethod
    def delete_file(folder_name:str,file_name:str) -> None:
        csv_file_manager = CsvFileManager()
        csv_file_manager.delete_one_file(folder_name,file_name)

    @staticmethod
    def add_file(folder_name:str,csv_file:UploadFile) -> None:
        csv_file_manager = CsvFileManager()
        csv_file_manager.save_csv(folder_name,csv_file)

    @staticmethod
    def get_evaluate_result(folder_name:str,evaluate_form:EvaluateParas):
        csv_file_manager = CsvFileManager()
        file_names = csv_file_manager.get_file_names(folder_name)
        file_name_list = list()
        path = csv_file_manager.history_folder_path
        for file_name in file_names:
            file_name_list.append(os.path.join(path,folder_name,file_name))
        dfs = [pd.read_csv(file_name) for file_name in file_name_list]
        drop_column = evaluate_form.predict_column
        is_text_column = None
        score = list()
        for df in dfs:
            model = SmartTablePredictor(text_features_max=evaluate_form.text_features_max,
                                        target_text_keywords=evaluate_form.target_text_keywords)
            df = df.dropna()
            X = df.drop(columns=[drop_column])
            y = df[drop_column]
            for col in X.columns:
                X[col] = model.try_convert_to_numeric(X[col])
            y = model.try_convert_to_numeric(y)
            X_train, X_test, y_train, y_test = train_test_split(X,y,test_size=1.0-evaluate_form.training_set_percentage)
            model.fit(X_train,y_train)
            if is_text_column is None:
                is_text_column = model.is_text_target
            result = model.predict(X_test)
            evaluator = PredictionEvaluator()
            if is_text_column:
                score.append(evaluator.calc_F1(result,y_test))
            else:
                score.append(evaluator.calc_RMSE(result,y_test))
        return score, "string" if is_text_column else "number"

