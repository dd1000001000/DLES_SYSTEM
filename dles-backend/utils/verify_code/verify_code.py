# -*- coding: utf-8 -*-
# 单例
import hmac
import os
import time

from utils.read_config.read_config import read_config

verify_code_dict = dict()
# 同一邮箱两次发送验证码的最小间隔（秒）、验证码最多允许输错的次数
SEND_INTERVAL = 60
MAX_ATTEMPTS = 5
send_time_dict = dict()
attempts_dict = dict()

config = read_config(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json'))
VERIFY_CODE_EXPIRY_TIME = config['VERIFY_CODE_EXPIRE_TIME']


def can_send_verify_code(email: str) -> bool:
    last_time = send_time_dict.get(email)
    return last_time is None or time.time() - last_time >= SEND_INTERVAL


def add_or_update_verify_code(email: str, code: str):
    now = time.time()
    # 顺便清理所有已过期的验证码，避免字典无限增长
    for key in [k for k, (_, t) in verify_code_dict.items() if now - t > VERIFY_CODE_EXPIRY_TIME]:
        verify_code_dict.pop(key, None)
        send_time_dict.pop(key, None)
        attempts_dict.pop(key, None)
    verify_code_dict[email] = (code, now)
    send_time_dict[email] = now
    attempts_dict[email] = 0


def get_verify_code(email: str):
    data = verify_code_dict.get(email)
    if data:
        code, timestamp = data
        if time.time() - timestamp <= VERIFY_CODE_EXPIRY_TIME:
            return code
        else:
            verify_code_dict.pop(email)
    return None


def consume_verify_code(email: str, code: str) -> bool:
    data = verify_code_dict.get(email)
    if not data:
        return False
    stored_code, timestamp = data
    if time.time() - timestamp > VERIFY_CODE_EXPIRY_TIME:
        verify_code_dict.pop(email)
        return False
    if hmac.compare_digest(stored_code, code):
        verify_code_dict.pop(email)
        attempts_dict.pop(email, None)
        return True
    attempts_dict[email] = attempts_dict.get(email, 0) + 1
    if attempts_dict[email] >= MAX_ATTEMPTS:
        verify_code_dict.pop(email, None)
        attempts_dict.pop(email, None)
    return False
