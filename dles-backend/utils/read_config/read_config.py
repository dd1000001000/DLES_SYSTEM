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


# 项目根目录（dles-backend 的上一级）。数据湖、预训练模型、向量文件默认放在这里，也可以用 DLES_DATA_DIR 指定别处
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def resolve_data_path(path: str) -> str:
    """配置文件里的相对路径按数据目录（默认是项目根目录）解析，绝对路径原样使用"""
    if os.path.isabs(path):
        return path
    base = os.getenv('DLES_DATA_DIR') or str(PROJECT_ROOT)
    return os.path.normpath(os.path.join(base, path))


def get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f'缺少环境变量 {name}，请参考 .env.example 在 dles-backend/.env 中配置')
    return value
