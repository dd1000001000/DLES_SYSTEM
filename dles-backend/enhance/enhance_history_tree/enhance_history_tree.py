# -*- coding: utf-8 -*-
import json
import os
import shutil
import time
from pathlib import Path

from fastapi import UploadFile

from database.database import Database
from enhance.enhance_history_tree.model.models import HistoryTreeNode
from logs.log import error_log
from utils.upload import safe_filename, save_upload

CSV_MAX_BYTES = 50 * 1024 * 1024


class EnhanceHistoryTree:
    def __init__(self, username: str):
        self.username = username
        self.history_folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../enhance_history')
        os.makedirs(self.history_folder_path, exist_ok=True)

    def is_valid_filename(self,filename):
        # 不论部署在哪个系统，都按最严格的规则校验，避免路径穿越和跨平台问题
        if not filename or filename in ('.', '..') or len(filename) > 100:
            return False
        if filename != filename.rstrip(' .'):
            return False
        invalid_chars = '<>:"/\\|?*\x00'
        if any(char in filename for char in invalid_chars):
            return False
        reserved_names = {"CON", "PRN", "AUX", "NUL",
                          "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
                          "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"}
        if filename.upper().split(".")[0] in reserved_names:
            return False
        return True

    # 初始化用户的树
    def init_history_tree(self):
        history_tree = HistoryTreeNode(id=0, faid=-1, label=self.username, disabled=True, isFile=False, children=[])
        try:
            os.makedirs(os.path.join(self.history_folder_path, self.username), exist_ok=True)
            with Database() as db:
                sql = "INSERT INTO enhance_history (username, history_tree) VALUES (%s, %s);"
                db.execute_update(sql, (self.username, history_tree.model_dump_json()))
        except Exception as e:
            error_log(f"初始化用户增强记录树失败，原因: {e}")
            raise e

    def get_user_tree(self):
        try:
            with Database() as db:
                sql = "SELECT history_tree FROM enhance_history WHERE username=%s;"
                tree = db.execute_query(sql, (self.username,))
            if len(tree) == 0:
                return None
            tree = HistoryTreeNode.model_validate(json.loads(tree[0]['history_tree']))
            return tree
        except Exception as e:
            raise e

    def update_history_tree_to_db(self, history_tree: HistoryTreeNode):
        try:
            with Database() as db:
                sql = "UPDATE enhance_history SET history_tree=%s WHERE username=%s;"
                db.execute_update(sql, (history_tree.model_dump_json(), self.username))
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
            folder_path = os.path.join(self.history_folder_path, full_path, node_name)
            os.mkdir(folder_path)
            try:
                self.update_history_tree_to_db(tree)
            except Exception:
                shutil.rmtree(folder_path, ignore_errors=True)
                raise
        except Exception as e:
            error_log(f'历史记录树新增节点失败，原因: {e}')
            raise e

    def add_file(self,fa_node_id: int, csv_file: UploadFile):
        file_name = safe_filename(csv_file.filename)
        if not file_name.lower().endswith(".csv"):
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
            folder_path = os.path.join(self.history_folder_path, full_path, node_name)
            os.mkdir(folder_path)
            try:
                # 创建 table.csv 和 dialogue.json 文件
                save_upload(csv_file, os.path.join(folder_path, 'table.csv'), CSV_MAX_BYTES)
                dialogue = [{'role':'assistant','content':'你好，让我来帮你增强表格吧。'}]
                with open(os.path.join(folder_path,'dialogue.json'), mode='w', encoding='utf-8') as file:
                    json.dump(dialogue, file,indent=2, ensure_ascii=False)
                self.update_history_tree_to_db(tree)
            except Exception:
                shutil.rmtree(folder_path, ignore_errors=True)
                raise
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
            if node_id == tree.id:
                raise Exception('不能修改根目录的名称')
            full_path, max_id = self.get_path_by_id(node_id, tree)
            if full_path is None:
                raise Exception('需要修改名称的文件夹不存在')
            self.change_folder_name_dfs(node_id, tree, new_node_name)
            old_path = os.path.abspath(os.path.join(self.history_folder_path, full_path))
            new_path = os.path.join(os.path.dirname(old_path), new_node_name)
            os.rename(old_path, new_path)
            try:
                self.update_history_tree_to_db(tree)
            except Exception:
                os.rename(new_path, old_path)
                raise
        except Exception as e:
            error_log(f'历史记录树修改节点名称失败，原因: {e}')
            raise e

    def delete_folder_dfs(self, delete_ids:list,current_history_tree:HistoryTreeNode,current_path:str,paths_to_remove:list):
        new_path = current_path+current_history_tree.label+'/'
        for child in current_history_tree.children:
            if child.id in delete_ids:
                paths_to_remove.append(os.path.abspath(os.path.join(self.history_folder_path ,new_path, child.label)))
        current_history_tree.children = [child for child in current_history_tree.children if child.id not in delete_ids]
        for child in current_history_tree.children:
            self.delete_folder_dfs(delete_ids, child, new_path, paths_to_remove)

    def delete_folders(self, delete_ids: list):
        try:
            tree = self.get_user_tree()
            if tree is None:
                raise Exception('用户历史记录树不存在')
            paths_to_remove = []
            self.delete_folder_dfs(delete_ids,tree,'',paths_to_remove)
            # 先更新数据库再删文件：即使删文件失败，也只是残留无用目录，不会出现树里有节点但目录不存在
            self.update_history_tree_to_db(tree)
            for path in paths_to_remove:
                shutil.rmtree(path, ignore_errors=True)
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
