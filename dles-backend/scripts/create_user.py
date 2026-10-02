# -*- coding: utf-8 -*-
"""
不经过邮箱验证码，直接在数据库里创建一个用户（本地开发、测试用）。

用法（在 dles-backend 目录下）：
  python -m scripts.create_user you@example.com            # 会提示输入密码
  python -m scripts.create_user you@example.com --generate  # 随机生成密码，写进 .env 的 DLES_TEST_USER_*，不打印
"""
import argparse
import getpass
import re
import secrets
import string
import sys
from pathlib import Path

from database.database import Database
from enhance.enhance_history_tree.enhance_history_tree import EnhanceHistoryTree
from utils.authorization.authorization import get_user, hash_password


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('email')
    parser.add_argument('--generate', action='store_true')
    args = parser.parse_args()

    if get_user(args.email):
        sys.exit('该用户已经存在')
    if args.generate:
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for _ in range(12))
    else:
        password = getpass.getpass('密码（6-14 位大小写字母和数字）：')
    if not re.fullmatch(r'[A-Za-z0-9]{6,14}', password):
        sys.exit('密码必须是 6-14 位的大小写字母和数字')

    EnhanceHistoryTree(args.email).init_history_tree()
    with Database() as db:
        db.execute_update("INSERT INTO user (username,password,user_type) VALUES (%s, %s, 'user');",
                          (args.email, hash_password(password)))
    if args.generate:
        env_path = Path(__file__).resolve().parents[1] / '.env'
        with open(env_path, 'a', encoding='utf-8') as env:
            env.write(f'\nDLES_TEST_USER_EMAIL={args.email}\nDLES_TEST_USER_PASSWORD={password}\n')
        print(f'已创建用户 {args.email}，密码保存在 {env_path} 的 DLES_TEST_USER_PASSWORD 里')
    else:
        print(f'已创建用户 {args.email}')


if __name__ == '__main__':
    main()
