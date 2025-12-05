# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile
from starlette import status
from starlette.responses import JSONResponse

from login.service.login_service import LoginService
from settings.model.models import ChangePassword
from utils.authorization.authorization import get_current_user
from utils.authorization.models import User, Token
from ..service.settings_service import SettingsService

settings_router = APIRouter()


@settings_router.post('/change_password')
async def user_change_password(change_password_form: ChangePassword,
                               current_user: Annotated[User, Depends(get_current_user)]):
    try:
        settings_service = SettingsService(current_user['username'])
        change_result = settings_service.change_password(change_password_form.old_password,
                                                         change_password_form.new_password)
        if not change_result:
            return JSONResponse(
                content={"message": f"重置密码失败"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        login_service = LoginService()
        login_result = login_service.user_login(current_user['username'], change_password_form.new_password)
        return Token(access_token=login_result, token_type="bearer")
    except Exception as e:
        return JSONResponse(
            content={"message": f"重置密码失败: {e}"},
            status_code=status.HTTP_400_BAD_REQUEST
        )


@settings_router.post('/upload_avatar')
async def upload_avatar(avatar: UploadFile, current_user: Annotated[User, Depends(get_current_user)]):
    try:
        settings_service = SettingsService(current_user['username'])
        save_result = settings_service.save_avatar(avatar)
        if not save_result:
            return JSONResponse(
                content={"message": f"保存头像失败"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        return {"avatar_path": save_result}
    except Exception as e:
        return JSONResponse(
            content={"message": f"保存头像失败: {e}"},
            status_code=status.HTTP_400_BAD_REQUEST
        )