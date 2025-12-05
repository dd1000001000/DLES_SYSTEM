# -*- coding: utf-8 -*-
from typing import List

from fastapi import UploadFile

from enhance.enhance_history_tree.enhance_history_tree import EnhanceHistoryTree
from logs.log import error_log


class EnhanceHistoryTreeService:
    def __init__(self, username:str):
        self.username = username

    def get_user_tree(self):
        try:
            enhance_history_tree  = EnhanceHistoryTree(self.username)
            history_tree = enhance_history_tree.get_user_tree()
            if history_tree is None:
                raise Exception(f'用户 {self.username} 增强历史记录树不存在')
            return history_tree
        except Exception as e:
            error_log(f'获取用户历史记录树失败，原因：{e}')
            raise e

    def get_folder_or_file_info(self,node_id:int):
        try:
            enhance_history_tree = EnhanceHistoryTree(self.username)
            return enhance_history_tree.get_folder_info(node_id)
        except Exception as e:
            error_log(f'获取文件或文件夹详细信息失败，原因：{e}')
            raise e
    def add_folder(self, fa_node_id:int, node_name:str):
        try:
            enhance_history_tree = EnhanceHistoryTree(self.username)
            enhance_history_tree.add_folder(fa_node_id, node_name)
        except Exception as e:
            error_log(f'新增文件夹失败，原因：{e}')
            raise e

    def change_folder_name(self, node_id:int, new_node_name:str):
        try:
            enhance_history_tree = EnhanceHistoryTree(self.username)
            enhance_history_tree.change_folder_name(node_id, new_node_name)
        except Exception as e:
            error_log(f'新增文件夹失败，原因：{e}')
            raise e

    def delete_folders(self,delete_ids:List[int]):
        try:
            enhance_history_tree = EnhanceHistoryTree(self.username)
            enhance_history_tree.delete_folders(delete_ids)
        except Exception as e:
            error_log(f'删除文件夹失败，原因：{e}')
            raise e

    def init_case(self,fa_node_id:int,csv_file: UploadFile):
        try:
            enhance_history_tree = EnhanceHistoryTree(self.username)
            return enhance_history_tree.add_file(fa_node_id,csv_file)
        except Exception as e:
            error_log(f'初始化增强用例失败，原因：{e}')
            raise e

    def get_path_by_id(self,node_id:int):
        try:
            enhance_history_tree = EnhanceHistoryTree(self.username)
            full_path = enhance_history_tree.get_path_by_id(node_id,enhance_history_tree.get_user_tree())[0]
            if full_path is None:
                raise Exception('当前查找的用例不存在')
            return full_path
        except Exception as e:
            raise e