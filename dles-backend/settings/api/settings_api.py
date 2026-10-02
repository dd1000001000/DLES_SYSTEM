# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Response, UploadFile
from starlette import status
from starlette.responses import JSONResponse

from login.service.login_service import LoginService
from settings.model.models import ChangePassword, LLMConfigForm
from settings.service import llm_config_service
from enhance.LLM.llm_client import LLMError
from utils.rate_limit import RateLimiter
from utils.authorization.authorization import get_current_user, set_auth_cookie
from utils.authorization.models import User, Token
from ..service.settings_service import SettingsService

settings_router = APIRouter()

# 测试连接会让服务器向用户填写的地址发请求，限制频率
test_llm_limiter = RateLimiter(max_events=10, window_seconds=600)


@settings_router.get('/llm_config')
def get_llm_config(current_user: Annotated[User, Depends(get_current_user)]):
    try:
        return llm_config_service.get_llm_config_view(current_user['username'])
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message": f"读取模型配置失败: {e}"})


@settings_router.post('/llm_config')
def save_llm_config(form: LLMConfigForm, current_user: Annotated[User, Depends(get_current_user)]):
    try:
        username = current_user['username']
        config = llm_config_service.build_config(username, form.base_url, form.api_key, form.chat_model,
                                                 form.strategy_model, form.code_model)
        llm_config_service.save_llm_config(username, config)
        return llm_config_service.get_llm_config_view(username)
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message": f"保存模型配置失败: {e}"})


@settings_router.post('/llm_config/test')
def test_llm_config(form: LLMConfigForm, current_user: Annotated[User, Depends(get_current_user)]):
    username = current_user['username']
    if test_llm_limiter.is_blocked(username):
        return JSONResponse(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            content={"message": "测试过于频繁，请稍后再试"})
    test_llm_limiter.record(username)
    try:
        config = llm_config_service.build_config(username, form.base_url, form.api_key, form.chat_model,
                                                 form.strategy_model, form.code_model)
        reply = llm_config_service.test_llm_config(config)
        return {"reply": reply}
    except (ValueError, LLMError, RuntimeError) as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message": f"测试失败: {e}"})


@settings_router.post('/change_password')
def user_change_password(change_password_form: ChangePassword, response: Response,
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
        set_auth_cookie(response, login_result)
        return Token(access_token=login_result, token_type="bearer")
    except Exception as e:
        return JSONResponse(
            content={"message": f"重置密码失败: {e}"},
            status_code=status.HTTP_400_BAD_REQUEST
        )


@settings_router.post('/upload_avatar')
def upload_avatar(avatar: UploadFile, current_user: Annotated[User, Depends(get_current_user)]):
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