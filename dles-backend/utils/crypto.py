# -*- coding: utf-8 -*-
import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken

from utils.read_config.read_config import get_env


def _get_fernet() -> Fernet:
    # 优先使用专门配置的加密密钥；没有配置时由 JWT 密钥派生（此时更换 JWT 密钥会让已保存的 API Key 无法解密）
    key = os.getenv('DLES_ENCRYPTION_KEY')
    if not key:
        digest = hashlib.sha256(b'dles-encryption-key:' + get_env('DLES_JWT_SECRET_KEY').encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key)


def encrypt_text(plain: str) -> str:
    return _get_fernet().encrypt(plain.encode('utf-8')).decode('ascii')


def decrypt_text(token: str) -> str:
    try:
        return _get_fernet().decrypt(token.encode('ascii')).decode('utf-8')
    except InvalidToken:
        raise RuntimeError('无法解密已保存的 API Key（加密密钥已更换），请在设置里重新填写')
