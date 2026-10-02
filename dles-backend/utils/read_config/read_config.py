# -*- coding: utf-8 -*-
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from logs.log import error_log

# 从 dles-backend/.env 读取密钥等敏感配置（不会提交到仓库）
load_dotenv(Path(__file__).resolve().parents[2] / '.env')


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


def get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f'缺少环境变量 {name}，请参考 .env.example 在 dles-backend/.env 中配置')
    return value
