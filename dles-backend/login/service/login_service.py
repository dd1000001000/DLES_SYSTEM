# -*- coding: utf-8 -*-
import re
from datetime import timedelta

from database.database import Database
from enhance.enhance_history_tree.enhance_history_tree import EnhanceHistoryTree
from logs.log import error_log
from utils.authorization.authorization import hash_password, get_user, authenticate_user, ACCESS_TOKEN_EXPIRE_MINUTES, \
    create_access_token
from utils.mail.mail import send_verifycode
from utils.verify_code.verify_code import consume_verify_code

class LoginService:
    def __init__(self):
        pass

    def send_verify_code(self, receiver: str, send_type: str) -> bool:
        try:
            return send_verifycode(receiver, send_type)
        except Exception as e:
            error_log(f'发送验证码出现异常，原因: {e}')
            return False

    def user_login(self, username, password):
        user = authenticate_user(username, password)
        if not user:
            return None
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user['username']}, expires_delta=access_token_expires
        )
        return access_token

    def is_password_valid(self, password: str) -> bool:
        return bool(re.fullmatch(r'[A-Za-z0-9]{6,14}', password))

    def user_register(self, username: str, verify_code: str, password: str) -> bool:
        if not self.is_password_valid(password):
            raise Exception('密码不是6-14位的大小写字母和数字的组合')
        if get_user(username):
            raise Exception('该邮箱已经被注册')
        if not consume_verify_code(username, verify_code):
            raise Exception('验证码错误或者过期，请检查验证码是否正确')
        try:
            hashed_password = hash_password(password)
            enhance_history_tree = EnhanceHistoryTree(username)
            enhance_history_tree.init_history_tree()
            db = Database()
            sql = f"INSERT INTO user (username,password,user_type) VALUES ('{username}','{hashed_password}','user');"
            db.execute_update(sql)
            db.close()
            return True
        except Exception as e:
            error_log(f'用户注册失败，原因: {e}')
            return False

    def user_recover(self, username: str, verify_code: str, new_password: str) -> bool:
        if not self.is_password_valid(new_password):
            raise Exception('密码不是6-14位的大小写字母和数字的组合')
        if not consume_verify_code(username, verify_code):
            raise Exception('验证码错误或者过期，请检查验证码是否正确')
        if not get_user(username):
            raise Exception('用户还没有注册')
        try:
            hashed_password = hash_password(new_password)
            db = Database()
            sql = f"UPDATE user SET password='{hashed_password}' WHERE username='{username}';"
            db.execute_update(sql)
            return True
        except Exception as e:
            error_log(f'用户重置密码失败，原因: {e}')
            return False
