import csv
import json
import os


class FileReader:
    def __init__(self,username:str):
        self.username = username
        self.history_folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../enhance_history')

    def _resolve_user_path(self, relative_path: str) -> str:
        user_root = os.path.abspath(os.path.join(self.history_folder_path, self.username))
        full_path = os.path.abspath(os.path.join(self.history_folder_path, relative_path))
        if os.path.commonpath([user_root, full_path]) != user_root:
            raise Exception('用户只能读取自己的文件')
        return full_path

    def read_csv_to_json(self,csv_path:str):
        with open(self._resolve_user_path(csv_path), mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            return list(reader)

    def read_json_file(self,json_path:str):
        with open(self._resolve_user_path(json_path), mode='r', encoding='utf-8') as file:
            json_data = json.load(file)
            return json_data