# -*- coding: utf-8 -*-
# 单例
import os
import time

from utils.read_config.read_config import read_config

verify_code_dict = dict()

config = read_config(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json'))
VERIFY_CODE_EXPIRY_TIME = config['VERIFY_CODE_EXPIRE_TIME']


def add_or_update_verify_code(email: str, code: str):
    verify_code_dict[email] = (code, time.time())


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
    if stored_code == code:
        verify_code_dict.pop(email)
        return True
    return False
