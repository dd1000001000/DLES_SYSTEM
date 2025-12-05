# -*- coding: utf-8 -*-
from fastapi import APIRouter

from train.code_generation.api.code_generation_api import code_generation_router
from train.enhance_comparation.api.temp_file_api import temp_file_api

train_router = APIRouter()

train_router.include_router(router=code_generation_router,prefix='/code_generation',tags=['代码生成'])

train_router.include_router(router=temp_file_api,prefix='/temp_file',tags=['临时文件管理'])