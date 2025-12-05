# -*- coding: utf-8 -*-
import json

from logs.log import error_log


def read_config(file_path: str):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        error_log(f'文件 {file_path} 未找到')
    except json.JSONDecodeError:
        error_log(f'无法解析 {file_path}，请检查 JSON 格式')
    return None
