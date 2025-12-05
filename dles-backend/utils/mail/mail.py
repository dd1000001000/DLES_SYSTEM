# -*- coding: utf-8 -*-
import os
import random
import smtplib
import string
from email.mime.text import MIMEText

from logs.log import error_log, info_log
from utils.read_config.read_config import read_config
from utils.verify_code.verify_code import add_or_update_verify_code

config = read_config(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json'))

my_sender = config['mail_sender']
token = config['mail_token']


def mail(title: str, text: str, receiver: str) -> bool:
    try:
        msg = MIMEText(text, 'plain', 'utf-8')  # 填写邮件内容
        msg['From'] = my_sender
        msg['Subject'] = title  # 邮件的的标题
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(my_sender, token)
        server.sendmail(my_sender, [receiver], msg.as_string())
        server.quit()  # 关闭连接
    except Exception as e:  # 如果 try 中的语句没有执行，则会执行下面的 ret=False
        error_log(f'发送邮件给 {receiver} 失败: {e}')
        return False
    info_log(f'发送邮件给 {receiver} 成功')
    return True


def getcode(length=8) -> str:
    characters = string.ascii_lowercase + string.digits  # 小写字母 + 数字
    return ''.join(random.choices(characters, k=length))


def send_verifycode(receiver: str, send_type: str) -> bool:
    verifycode = getcode()
    title = '基于数据湖的表格增强系统验证码'
    text = f'您的邮箱验证码是 {verifycode}，请使用此验证码来' + ('注册账号。' if send_type == 'register' else '修改密码。')
    if mail(title, text, receiver):
        add_or_update_verify_code(receiver, verifycode)
        return True
    else:
        return False

# mail('验证码','123456','1228280263@qq.com')
