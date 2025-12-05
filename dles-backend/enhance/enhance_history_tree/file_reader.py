import csv
import json
import os


class FileReader:
    def __init__(self,username:str):
        self.username = username
        self.history_folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../enhance_history')

    def read_csv_to_json(self,csv_path:str):
        if self.username not in csv_path:
            raise Exception('用户只能读取自己的文件')
        with open(os.path.join(self.history_folder_path,csv_path), mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            return list(reader)

    def read_json_file(self,json_path:str):
        if self.username not in json_path:
            raise Exception('用户只能读取自己的文件')
        with open(os.path.join(self.history_folder_path,json_path), mode='r', encoding='utf-8') as file:
            json_data = json.load(file)
            return json_data