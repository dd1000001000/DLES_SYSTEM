import os
import shutil
from collections import defaultdict
from pathlib import Path
from typing import List
import pandas.api.types as ptypes
import pandas as pd
import uuid
from fastapi import UploadFile

from utils.upload import safe_filename, save_upload

CSV_MAX_BYTES = 50 * 1024 * 1024


class CsvFileManager:
    def __init__(self):
        self.history_folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../temp_csv_files')
        os.makedirs(self.history_folder_path, exist_ok=True)

    @staticmethod
    def check_folder_name(folder_name: str) -> str:
        # 文件夹名必须是前端生成的 uuid，防止 .. 之类的路径穿越
        try:
            return str(uuid.UUID(folder_name))
        except ValueError:
            raise Exception('用例编号不合法')

    @staticmethod
    def check_file_name(file_name: str) -> str:
        if safe_filename(file_name) != file_name or file_name in ('', '.', '..'):
            raise Exception('文件名不合法')
        return file_name

    def delete_folder(self,folder_name:str):
        folder_name = self.check_folder_name(folder_name)
        shutil.rmtree(os.path.join(self.history_folder_path,folder_name), ignore_errors=True)

    def create_folder(self,folder_name:str):
        folder_name = self.check_folder_name(folder_name)
        os.makedirs(os.path.join(self.history_folder_path,folder_name), exist_ok=True)

    def get_file_names(self,folder_name:str) -> List[str]:
        folder_name = self.check_folder_name(folder_name)
        full_path = os.path.join(self.history_folder_path,folder_name)
        os.makedirs(full_path, exist_ok=True)
        result_list = []
        for filename in os.listdir(full_path):
            if os.path.isfile(os.path.join(full_path,filename)) and filename.endswith('.csv'):
                name = Path(filename).stem
                result_list.append(name+'.csv')
        return result_list

    def delete_one_file(self,folder_name:str,file_name:str):
        folder_name = self.check_folder_name(folder_name)
        file_name = self.check_file_name(file_name)
        path = os.path.abspath(os.path.join(self.history_folder_path,folder_name,file_name))
        os.remove(path)

    @staticmethod
    def convert_to_numeric__possible(df: pd.DataFrame, column_name: str) -> None:
        # 尝试转换整个列为数字（无效值转为 NaN）
        converted_series = pd.to_numeric(df[column_name], errors="coerce")
        if not converted_series.isna().any():
            df[column_name] = converted_series

    def save_csv(self,folder_name:str,csvFile:UploadFile):
        folder_name = self.check_folder_name(folder_name)
        filename = safe_filename(csvFile.filename)
        if not filename.lower().endswith('.csv'):
            raise Exception('上传的不是csv文件')
        os.makedirs(os.path.join(self.history_folder_path,folder_name), exist_ok=True)
        full_path = os.path.join(self.history_folder_path,folder_name,filename)
        if os.path.exists(full_path):
            raise Exception('文件名称和已有文件重复')
        save_upload(csvFile, full_path, CSV_MAX_BYTES)

    def get_predict_column_names(self,folder_name:str) -> List[str]:
        folder_name = self.check_folder_name(folder_name)
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