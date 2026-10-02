# -*- coding: utf-8 -*-
"""
端到端冒烟测试：通过 HTTP 接口走一遍 登录 -> 配置模型 -> 上传表格 -> 提取增强参数 -> 开始增强。
需要后端已经启动、.env 里有 scripts/create_user.py --generate 生成的测试用户，并且模型端点可用。

用法（在 dles-backend 目录下）：
  python -m scripts.smoke_test <模型名> <要增强的 csv 路径>
默认使用本机 Ollama（http://localhost:11434/v1）。
"""
import json
import os
import sys
import time

import httpx
from dotenv import dotenv_values

env = dotenv_values(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
EMAIL, PASSWORD = env['DLES_TEST_USER_EMAIL'], env['DLES_TEST_USER_PASSWORD']
MODEL = sys.argv[1] if len(sys.argv) > 1 else 'qwen3:30b'
TABLE = sys.argv[2]

c = httpx.Client(base_url='http://localhost:8080', timeout=1800)

r = c.post('/login/login', data={'username': EMAIL, 'password': PASSWORD})
print('login', r.status_code, 'cookie set:', 'dles_token' in c.cookies)
r = c.post('/login/user/me')
print('me', r.status_code, r.json()['email'])

r = c.post('/settings/llm_config', json={'base_url': 'http://localhost:11434/v1', 'api_key': 'ollama', 'chat_model': MODEL})
print('save llm config', r.status_code, {k: v for k, v in r.json().items() if k != 'api_key_masked'})
t = time.time()
r = c.post('/settings/llm_config/test', json={'base_url': 'http://localhost:11434/v1', 'api_key': '', 'chat_model': MODEL})
print('test llm', r.status_code, r.text[:200], f'{time.time() - t:.0f}s')

r = c.get(f'/enhance/enhance_history/{EMAIL}')
print('history tree', r.status_code)
name = os.path.basename(TABLE)
with open(TABLE, 'rb') as f:
    r = c.post(f'/enhance/enhance_history/{EMAIL}/init/0', files={'csvFile': (name, f, 'text/csv')})
print('upload', r.status_code, r.text[:200])
case_id = r.json()['node_id']

dialogues = [{'role': 'assistant', 'content': '你好，让我来帮你增强表格吧。'},
             {'role': 'user', 'content': '请用连接和联合两种方式增强这张表，增强后大约 10 列，缺失值用平均值填充。'}]
t = time.time()
r = c.post(f'/enhance/enhance_main/{EMAIL}/{case_id}', json=dialogues)
print('extract keywords', r.status_code, r.text[:300], f'{time.time() - t:.0f}s')
r = c.get(f'/enhance/enhance_history/{EMAIL}/{case_id}')
dialogue = r.json()['dialogue']
print('dialogue now:', json.dumps(dialogue, ensure_ascii=False)[:400])
before_cols = len(r.json()['table'][0]) if r.json()['table'] else 0
before_rows = len(r.json()['table'])

dialogues = dialogue + [{'role': 'user', 'content': '开始增强'}]
t = time.time()
r = c.post(f'/enhance/enhance_main/{EMAIL}/{case_id}', json=dialogues)
print('enhance', r.status_code, r.text[:300], f'{time.time() - t:.0f}s')
r = c.get(f'/enhance/enhance_history/{EMAIL}/{case_id}')
table = r.json()['table']
print(f'table before: {before_rows} rows x {before_cols} cols; after: {len(table)} rows x {len(table[0]) if table else 0} cols')
print('columns after:', list(table[0].keys()) if table else None)
