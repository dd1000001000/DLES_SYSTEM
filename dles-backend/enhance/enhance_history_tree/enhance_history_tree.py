# -*- coding: utf-8 -*-
import json
import os
import shutil
import sys
import time
from pathlib import Path

from fastapi import UploadFile

from database.database import Database
from enhance.enhance_history_tree.model.models import HistoryTreeNode
from logs.log import error_log


class EnhanceHistoryTree:
    def __init__(self, username: str):
        self.username = username
        self.history_folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../enhance_history')

    def is_valid_filename(self,filename):
        if sys.platform.startswith("win"):
            invalid_chars = r'<>:"/\\|?*'
            reserved_names = {"CON", "PRN", "AUX", "NUL",
                              "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
                              "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"}
            if any(char in filename for char in invalid_chars):
                return False
            if filename.upper().split(".")[0] in reserved_names:
                return False
        elif "/" in filename:
            return False
        return True

    # 初始化用户的树
    def init_history_tree(self):
        history_tree = HistoryTreeNode(id=0, faid=-1, label=self.username, disabled=True, isFile=False, children=[])
        try:
            os.mkdir(os.path.join(self.history_folder_path, self.username))
            db = Database()
            sql = f"INSERT INTO enhance_history (username, history_tree) VALUES ('{self.username}', '{history_tree.model_dump_json()}');"
            db.execute_update(sql)
            db.close()
        except Exception as e:
            error_log(f"初始化用户增强记录树失败，原因: {e}")

    def get_user_tree(self):
        try:
            db = Database()
            sql = f"SELECT history_tree FROM enhance_history WHERE username='{self.username}';"
            tree = db.execute_query(sql)
            db.close()
            if len(tree) == 0:
                return None
            tree = HistoryTreeNode.model_validate(json.loads(tree[0]['history_tree']))
            return tree
        except Exception as e:
            raise e

    def update_history_tree_to_db(self, history_tree: HistoryTreeNode):
        try:
            db = Database()
            sql = f"UPDATE enhance_history SET history_tree='{history_tree.model_dump_json()}' WHERE username='{self.username}';"
            db.execute_update(sql)
            db.close()
        except Exception as e:
            raise e

    def get_path_by_id(self, node_id: int,history_tree: HistoryTreeNode):
        path = None
        max_id = -1
        def get_path_by_id_dfs(current_tree: HistoryTreeNode,current_path: str):
            nonlocal path, max_id
            max_id = max(max_id, current_tree.id)
            new_path = current_path+current_tree.label+'/'
            if current_tree.id == node_id:
                path = new_path
            for child in current_tree.children:
                get_path_by_id_dfs(child, new_path)
        get_path_by_id_dfs(history_tree, '')
        return path, max_id

    def insert_node_into_history_tree(self, fa_node_id:int,current_history_tree:HistoryTreeNode,node:HistoryTreeNode):
        if current_history_tree.id==fa_node_id:
            if any(child.label==node.label for child in current_history_tree.children):
                raise Exception('已经存在相同名称的文件夹')
            current_history_tree.children.append(node)
            return
        for child in current_history_tree.children:
            self.insert_node_into_history_tree(fa_node_id, child, node)

    def add_folder(self,fa_node_id: int, node_name: str):
        node_name = node_name.strip()
        if not self.is_valid_filename(node_name):
            raise Exception('文件夹名称不合法')
        try:
            tree = self.get_user_tree()
            if tree is None:
                raise Exception('用户历史记录树不存在')
            full_path, max_id = self.get_path_by_id(fa_node_id, tree)
            if full_path is None:
                raise Exception('增加文件夹的父节点不存在')
            new_node = HistoryTreeNode(id=max_id+1, faid=fa_node_id, label=node_name, disabled=False, isFile=False, children=[])
            self.insert_node_into_history_tree(fa_node_id,tree,new_node)
            self.update_history_tree_to_db(tree)
            os.mkdir(os.path.join(self.history_folder_path, full_path, node_name))
        except Exception as e:
            error_log(f'历史记录树新增节点失败，原因: {e}')
            raise e

    def add_file(self,fa_node_id: int, csv_file: UploadFile):
        file_name = csv_file.filename
        if not file_name.endswith(".csv"):
            raise Exception('文件必须是csv文件')
        node_name = Path(file_name).stem
        node_name = node_name.strip()
        if not self.is_valid_filename(node_name):
            raise Exception('文件名称不合法')
        try:
            tree = self.get_user_tree()
            if tree is None:
                raise Exception('用户历史记录树不存在')
            full_path, max_id = self.get_path_by_id(fa_node_id, tree)
            if full_path is None:
                raise Exception('增加文件夹的父节点不存在')
            new_node = HistoryTreeNode(id=max_id+1, faid=fa_node_id, label=node_name, disabled=False, isFile=True, children=[])
            self.insert_node_into_history_tree(fa_node_id,tree,new_node)
            self.update_history_tree_to_db(tree)
            folder_path = os.path.join(self.history_folder_path, full_path, node_name)
            os.mkdir(folder_path)
            # 创建 table.csv 和 dialogue.json 文件
            with open(os.path.join(folder_path, 'table.csv'), "wb") as file:
                shutil.copyfileobj(csv_file.file, file)
            dialogue = [{'role':'assistant','content':'你好，让我来帮你增强表格吧。'}]
            with open(os.path.join(folder_path,'dialogue.json'), mode='w', encoding='utf-8') as file:
                json.dump(dialogue, file,indent=2, ensure_ascii=False)
            return max_id + 1
        except Exception as e:
            error_log(f'历史记录树新增节点失败，原因: {e}')
            raise e


    def change_folder_name_dfs(self,node_id:int,current_history_tree:HistoryTreeNode,new_node_name:str):
        for child in current_history_tree.children:
            if child.id==node_id:
                for child2 in current_history_tree.children:
                    if child2.id==node_id:
                        continue
                    if child2.label==new_node_name:
                        raise Exception('已经有相同名称的文件夹')
                child.label = new_node_name
                return
        for child in current_history_tree.children:
            self.change_folder_name_dfs(node_id, child, new_node_name)


    def change_folder_name(self, node_id:int,new_node_name:str):
        new_node_name = new_node_name.strip()
        if not self.is_valid_filename(new_node_name):
            raise Exception('文件夹名称不合法')
        try:
            tree = self.get_user_tree()
            if tree is None:
                raise Exception('用户历史记录树不存在')
            full_path, max_id = self.get_path_by_id(node_id, tree)
            if full_path is None:
                raise Exception('需要修改名称的文件夹不存在')
            self.change_folder_name_dfs(node_id, tree, new_node_name)
            self.update_history_tree_to_db(tree)
            old_path = os.path.abspath(os.path.join(self.history_folder_path, full_path))
            new_path = os.path.join(os.path.dirname(old_path), new_node_name)
            os.rename(old_path, new_path)
        except Exception as e:
            error_log(f'历史记录树修改节点名称失败，原因: {e}')
            raise e

    def delete_folder_dfs(self, delete_ids:list,current_history_tree:HistoryTreeNode,current_path:str):
        try:
            new_path = current_path+current_history_tree.label+'/'
            for child in current_history_tree.children:
                if child.id in delete_ids:
                    path = os.path.abspath(os.path.join(self.history_folder_path ,new_path, child.label))
                    shutil.rmtree(path)
            current_history_tree.children = [child for child in current_history_tree.children if child.id not in delete_ids]
            for child in current_history_tree.children:
                self.delete_folder_dfs(delete_ids, child, new_path)
        except Exception as e:
            raise e

    def delete_folders(self, delete_ids: list):
        try:
            tree = self.get_user_tree()
            if tree is None:
                raise Exception('用户历史记录树不存在')
            self.delete_folder_dfs(delete_ids,tree,'')
            self.update_history_tree_to_db(tree)
        except Exception as e:
            error_log(f'批量删除文件夹失败，原因: {e}')
            raise e

    def get_folder_info(self, node_id:int):
        try:
            tree = self.get_user_tree()
            if tree is None:
                raise Exception('用户历史记录树不存在')
            full_path, max_id = self.get_path_by_id(node_id, tree)
            if full_path is None:
                raise Exception('找不到需要查找的节点信息')
            folder_info = os.stat(os.path.abspath(os.path.join(self.history_folder_path, full_path)))
            return {'createTime':time.strftime('%Y年%m月%d日，%H:%M:%S', time.localtime(folder_info.st_ctime)),
                    'lastEditTime':time.strftime('%Y年%m月%d日，%H:%M:%S', time.localtime(folder_info.st_mtime))}
        except Exception as e:
            error_log(f'查询文件夹信息失败，原因: {e}')
            raise e

    def get_user_folder(self):
        return self.get_user_tree().model_dump_json()
