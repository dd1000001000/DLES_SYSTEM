# -*- coding: utf-8 -*-
# 这个文件不应该依赖于其他任何文件
import os
from datetime import datetime

LOG_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../log.log'))


def info_log(text: str):
    now = datetime.now()
    with open(LOG_PATH, 'a', encoding='utf-8') as file:
        file.write(f'INFO {text} {now}\n')


def error_log(text: str):
    now = datetime.now()
    with open(LOG_PATH, 'a', encoding='utf-8') as file:
        file.write(f'ERROR {text} {now}\n')


def clear_log():
    with open(LOG_PATH, 'w', encoding='utf-8') as file:
        pass
