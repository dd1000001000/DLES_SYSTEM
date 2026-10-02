# -*- coding: utf-8 -*-
import os
import re

from fastapi import UploadFile

from database.database import Database
from logs.log import error_log
from utils.authorization.authorization import authenticate_user, hash_password
from utils.upload import safe_filename, save_upload

AVATAR_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
AVATAR_MAX_BYTES = 2 * 1024 * 1024


class SettingsService:
    def __init__(self, username: str):
        self.username = username
        self.avatar_folder = os.path.abspath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../user_avatar'))
        os.makedirs(self.avatar_folder, exist_ok=True)

    def is_password_valid(self, password: str) -> bool:
        return bool(re.fullmatch(r'[A-Za-z0-9]{6,14}', password))

    def change_password(self, old_password: str, new_password: str) -> bool:
        if not authenticate_user(self.username, old_password):
            raise Exception('旧密码错误，如果忘记密码，请使用找回密码功能')
        if not self.is_password_valid(new_password):
            raise Exception('新密码不是6-14位的大小写字母和数字的组合')
        try:
            hashed_password = hash_password(new_password)
            with Database() as db:
                sql = "UPDATE user SET password=%s WHERE username=%s;"
                db.execute_update(sql, (hashed_password, self.username))
            return True
        except Exception as e:
            error_log(f'用户修改密码失败，原因: {e}')
            return False

    def save_avatar(self, user_avatar: UploadFile):
        try:
            original_name = safe_filename(user_avatar.filename)
            if os.path.splitext(original_name)[1].lower() not in AVATAR_EXTENSIONS:
                raise Exception('头像必须是 png、jpg、gif 或 webp 图片')
            file_name = f'{self.username}_{original_name}'
            new_path = os.path.join(self.avatar_folder, file_name)
            # 先查出旧头像，新头像保存成功后再删除
            with Database() as db:
                result = db.execute_query("SELECT avatar_path FROM user WHERE username=%s;", (self.username,))
                old_avatar = result[0]['avatar_path'] if len(result) > 0 else None
                save_upload(user_avatar, new_path, AVATAR_MAX_BYTES)
                db.execute_update("UPDATE user SET avatar_path=%s WHERE username=%s;", (file_name, self.username))
            if old_avatar and old_avatar != file_name:
                old_path = os.path.join(self.avatar_folder, safe_filename(old_avatar))
                if os.path.exists(old_path):
                    os.remove(old_path)
            return file_name
        except Exception as e:
            error_log(f'保存用户新头像失败，原因：{e}')
            return None
