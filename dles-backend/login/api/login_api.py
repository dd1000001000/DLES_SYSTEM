# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from utils.authorization.authorization import get_current_user
from utils.authorization.models import Token, User
from ..model.models import SendEmail, UserRegister, UserRecover
from ..service.login_service import LoginService

login_router = APIRouter()


@login_router.post('/login')
async def user_login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    login_service = LoginService()
    login_result = login_service.user_login(form_data.username, form_data.password)
    if not login_result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=login_result, token_type="bearer")


@login_router.post('/send_verify_code')
async def send_verify_code(send_email: SendEmail):
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
async def user_register(register_form: UserRegister):
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
        return Token(access_token=login_result, token_type="bearer")
    except Exception as e:
        return JSONResponse(
            content={"message": f"注册失败: {e}"},
            status_code=status.HTTP_400_BAD_REQUEST
        )


@login_router.post('/recover')
async def user_recover(recover_form: UserRecover):
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
        return Token(access_token=login_result, token_type="bearer")
    except Exception as e:
        return JSONResponse(
            content={"message": f"重置密码失败: {e}"},
            status_code=status.HTTP_400_BAD_REQUEST
        )


@login_router.post('/user/me')
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return {"email": current_user['username'], "avatar_path": current_user['avatar_path'],"user_type":current_user['user_type']}
