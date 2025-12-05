import os
import shutil
from collections import defaultdict
from pathlib import Path
from typing import List
import pandas.api.types as ptypes
import pandas as pd
from fastapi import UploadFile


class CsvFileManager:
    def __init__(self):
        self.history_folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../temp_csv_files')

    def delete_folder(self,folder_name:str):
        shutil.rmtree(os.path.join(self.history_folder_path,folder_name))

    def create_folder(self,folder_name:str):
        full_path = os.path.join(self.history_folder_path,folder_name)
        if not os.path.exists(full_path):
            os.mkdir(full_path)

    def get_file_names(self,folder_name:str) -> List[str]:
        full_path = os.path.join(os.path.join(self.history_folder_path,folder_name))
        if not os.path.exists(full_path):
            os.mkdir(full_path)
        result_list = []
        for filename in os.listdir(full_path):
            if os.path.isfile(os.path.join(full_path,filename)) and filename.endswith('.csv'):
                name = Path(filename).stem
                result_list.append(name+'.csv')
        return result_list

    def delete_one_file(self,folder_name:str,file_name:str):
        path = os.path.join(self.history_folder_path,folder_name,file_name)
        path = os.path.abspath(path)
        os.remove(path)

    @staticmethod
    def convert_to_numeric__possible(df: pd.DataFrame, column_name: str) -> None:
        # 尝试转换整个列为数字（无效值转为 NaN）
        converted_series = pd.to_numeric(df[column_name], errors="coerce")
        if not converted_series.isna().any():
            df[column_name] = converted_series

    def save_csv(self,folder_name:str,csvFile:UploadFile):
        filename = csvFile.filename
        if not filename.endswith('.csv'):
            raise Exception('上传的不是csv文件')
        full_path = os.path.join(self.history_folder_path,folder_name,filename)
        if os.path.exists(full_path):
            raise Exception('文件名称和已有文件重复')
        with open(full_path,'wb') as file:
            shutil.copyfileobj(csvFile.file, file)

    def get_predict_column_names(self,folder_name:str) -> List[str]:
        full_path = os.path.join(self.history_folder_path,folder_name)
        file_count = 0
        counter_dict = defaultdict(int)
        for filename in os.listdir(full_path):
            if os.path.isfile(os.path.join(full_path,filename)) and filename.endswith('.csv'):
                df = pd.read_csv(os.path.join(full_path,filename))
                file_count += 1
                for column_name in df.columns:
                    self.convert_to_numeric__possible(df,column_name)
                    counter_dict[(column_name,ptypes.is_numeric_dtype(df[column_name]))] += 1

        result = list()
        for k,v in counter_dict.items():
            if v>=file_count:
                result.append(k[0])
        return list(set(result))