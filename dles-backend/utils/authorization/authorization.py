# -*- coding: utf-8 -*-
import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext

from database.database import Database
from utils.rate_limit import RateLimiter, TooManyAttemptsError
from utils.read_config.read_config import get_env, read_config

config = read_config(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json'))
SECRET_KEY = get_env('DLES_JWT_SECRET_KEY')
ALGORITHM = config['ALGORITHM']
ACCESS_TOKEN_EXPIRE_MINUTES = config['ACCESS_TOKEN_EXPIRE_MINUTES']

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# auto_error=False：没有 Authorization 头时，继续尝试从 Cookie 里取 Token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login/login", auto_error=False)

# Token 放在 httpOnly Cookie 里，前端 JS（包括 XSS）读不到
COOKIE_NAME = 'dles_token'
COOKIE_SECURE = os.getenv('DLES_COOKIE_SECURE', '0') == '1'  # 部署在 HTTPS 下时设为 1

# 登录限流：同一账号+IP 15 分钟内最多失败 5 次；同一 IP 15 分钟内最多失败 30 次
LOGIN_WINDOW_SECONDS = 15 * 60
user_login_limiter = RateLimiter(max_events=5, window_seconds=LOGIN_WINDOW_SECONDS)
ip_login_limiter = RateLimiter(max_events=30, window_seconds=LOGIN_WINDOW_SECONDS)


def hash_password(password: str):
    return hashlib.sha3_512(password.encode()).hexdigest()


def get_user(username: str):
    with Database() as db:
        sql = "SELECT * FROM user WHERE username=%s;"
        user = db.execute_query(sql, (username,))
    if len(user) == 0:
        return None
    return user[0]


def password_fingerprint(stored_password: str) -> str:
    """写进 Token 里的密码指纹：用户改密码后指纹变化，旧 Token 随之失效"""
    return hashlib.sha256(stored_password.encode()).hexdigest()[:16]


def authenticate_user(username: str, password: str, ip: str = ''):
    user_key = f'{username}|{ip}'
    if user_login_limiter.is_blocked(user_key) or (ip and ip_login_limiter.is_blocked(ip)):
        raise TooManyAttemptsError('密码错误次数过多，请 15 分钟后再试')
    user = get_user(username)
    if not user or hash_password(password) != user['password']:
        user_login_limiter.record(user_key)
        if ip:
            ip_login_limiter.record(ip)
        return None
    user_login_limiter.reset(user_key)
    return user


def set_auth_cookie(response: Response, token: str):
    response.set_cookie(
        COOKIE_NAME, token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True, samesite='lax', secure=COOKIE_SECURE, path='/',
    )


def clear_auth_cookie(response: Response):
    response.delete_cookie(COOKIE_NAME, path='/', httponly=True, samesite='lax', secure=COOKIE_SECURE)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(request: Request, bearer_token: Annotated[str | None, Depends(oauth2_scheme)]):
    token = bearer_token or request.cookies.get(COOKIE_NAME)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(username)
    if user is None:
        raise credentials_exception
    # 密码改过之后，旧 Token 里的指纹对不上，视为失效
    if payload.get("pwd") != password_fingerprint(user['password']):
        raise credentials_exception
    return user


def ensure_same_user(username: str, current_user: dict):
    """路径中的 username 必须是当前登录用户，防止越权访问他人数据"""
    if username != current_user['username']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问其他用户的数据")
