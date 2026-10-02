# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from utils.authorization.authorization import get_current_user, set_auth_cookie, clear_auth_cookie
from utils.rate_limit import RateLimiter, TooManyAttemptsError
from utils.authorization.models import Token, User
from ..model.models import SendEmail, UserRegister, UserRecover
from ..service.login_service import LoginService

login_router = APIRouter()

# 每个 IP 每小时最多请求 10 次验证码，防止被用来轰炸别人的邮箱
send_code_limiter = RateLimiter(max_events=10, window_seconds=3600)


def client_ip(request: Request) -> str:
    # 如果前面有反向代理，需要在代理层处理 X-Forwarded-For，这里只信任直连的地址
    return request.client.host if request.client else ''


@login_router.post('/login')
def user_login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], request: Request,
               response: Response) -> Token:
    login_service = LoginService()
    try:
        login_result = login_service.user_login(form_data.username, form_data.password, client_ip(request))
    except TooManyAttemptsError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e),
                            headers={"Retry-After": "900"})
    if not login_result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    set_auth_cookie(response, login_result)
    return Token(access_token=login_result, token_type="bearer")


@login_router.post('/logout')
def user_logout(response: Response):
    clear_auth_cookie(response)
    return {}


@login_router.post('/send_verify_code')
def send_verify_code(send_email: SendEmail, request: Request):
    ip = client_ip(request)
    if send_code_limiter.is_blocked(ip):
        return JSONResponse(content={"message": "请求验证码过于频繁，请稍后再试"},
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS)
    send_code_limiter.record(ip)
    try:
        login_service = LoginService()
        send_result = login_service.send_verify_code(send_email.email, send_email.type)
        if not send_result:
            return JSONResponse(
                content={"message": "发送验证码失败"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    except Exception as e:
        return JSONResponse(
            content={"message": f"发送验证码失败: {e}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    return {"message": "Verification code sent successfully"}


@login_router.post('/register')
def user_register(register_form: UserRegister, response: Response):
    try:
        login_service = LoginService()
        register_result = login_service.user_register(
            register_form.email, register_form.verify_code, register_form.password
        )
        if not register_result:
            return JSONResponse(
                content={"message": f"注册失败"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        login_result = login_service.user_login(register_form.email, register_form.password)
        set_auth_cookie(response, login_result)
        return Token(access_token=login_result, token_type="bearer")
    except Exception as e:
        return JSONResponse(
            content={"message": f"注册失败: {e}"},
            status_code=status.HTTP_400_BAD_REQUEST
        )


@login_router.post('/recover')
def user_recover(recover_form: UserRecover, response: Response):
    try:
        login_service = LoginService()
        recover_result = login_service.user_recover(
            recover_form.email, recover_form.verify_code, recover_form.new_password
        )
        if not recover_result:
            return JSONResponse(
                content={"message": f"重置密码失败"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        login_result = login_service.user_login(recover_form.email, recover_form.new_password)
        set_auth_cookie(response, login_result)
        return Token(access_token=login_result, token_type="bearer")
    except Exception as e:
        return JSONResponse(
            content={"message": f"重置密码失败: {e}"},
            status_code=status.HTTP_400_BAD_REQUEST
        )


@login_router.post('/user/me')
def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return {"email": current_user['username'], "avatar_path": current_user['avatar_path'],"user_type":current_user['user_type']}
