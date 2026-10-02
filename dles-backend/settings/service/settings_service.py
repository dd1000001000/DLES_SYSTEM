# -*- coding: utf-8 -*-
import os
import re
import shutil

from fastapi import UploadFile

from database.database import Database
from logs.log import error_log
from utils.authorization.authorization import authenticate_user, hash_password


class SettingsService:
    def __init__(self, username: str):
        self.username = username
        self.avatar_folder = os.path.abspath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../user_avatar'))

    def is_password_valid(self, password: str) -> bool:
        return bool(re.fullmatch(r'[A-Za-z0-9]{6,14}', password))

    def change_password(self, old_password: str, new_password: str) -> bool:
        if not authenticate_user(self.username, old_password):
            raise Exception('旧密码错误，如果忘记密码，请使用找回密码功能')
        if not self.is_password_valid(new_password):
            raise Exception('新密码不是6-14位的大小写字母和数字的组合')
        try:
            hashed_password = hash_password(new_password)
            db = Database()
            sql = "UPDATE user SET password=%s WHERE username=%s;"
            db.execute_update(sql, (hashed_password, self.username))
            db.close()
            return True
        except Exception as e:
            error_log(f'用户修改密码失败，原因: {e}')
            return False

    def save_avatar(self, user_avatar: UploadFile):
        try:
            db = Database()
            sql = "SELECT avatar_path FROM user WHERE username=%s;"
            result = db.execute_query(sql, (self.username,))
            db.close()
            if len(result) > 0 and result[0]['avatar_path'] is not None:
                file_path = os.path.join(self.avatar_folder, result[0]['avatar_path'])
                if os.path.exists(file_path):
                    os.remove(file_path)
        except Exception as e:
            error_log(f'删除用户旧头像失败，原因：{e}')
            return None
        try:
            safe_filename = os.path.basename((user_avatar.filename or '').replace('\\', '/'))
            file_name = f'{self.username}_{safe_filename}'
            with open(os.path.join(self.avatar_folder, file_name), "wb") as file:
                shutil.copyfileobj(user_avatar.file, file)
            if os.path.exists(os.path.join(self.avatar_folder, file_name)):
                db = Database()
                sql = "UPDATE user SET avatar_path=%s WHERE username=%s;"
                db.execute_update(sql, (file_name, self.username))
                db.close()
                return file_name
            else:
                return None
        except Exception as e:
            error_log(f'保存用户新头像失败，原因：{e}')
            return None
