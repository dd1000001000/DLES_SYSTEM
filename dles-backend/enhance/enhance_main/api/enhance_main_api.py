# -*- coding: utf-8 -*-
import traceback
from typing import Annotated, List, Dict

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse
# 强制导入，禁止删除
from transformer.model import TableContrastiveModel, TransformerEncoder
from enhance.enhance_main.service.enhance_main_service import EnhanceMainService
from utils.authorization.authorization import get_current_user
from utils.authorization.models import User

enhance_main_router = APIRouter()

@enhance_main_router.post('/{username}/{enhance_id}')
async def enhance_main_process(username:str,enhance_id:int,dialogues:List[Dict],current_user: Annotated[User, Depends(get_current_user)]):
    try:
        start_enhance_word = "开始增强"
        last_dialogue = dialogues[-1]
        if last_dialogue["role"]!="user":
            raise Exception("最后一次对话必须是用户")
        user_input = last_dialogue["content"]
        execute_enhance = start_enhance_word in user_input
        enhance_main = EnhanceMainService(username,enhance_id)
        # 提取关键词
        history = enhance_main.extraction_dialogue(dialogues,user_input)
        if execute_enhance:
            enhance_paras = enhance_main.extract_enhance_paras_from_history(history)
            if enhance_paras is None:
                raise Exception("增强参数不存在，无法增强，将在3秒后自动刷新页面")
            enhance_main.set_enhance_paras(enhance_paras)
            enhance_main.execute_enhance()
        return {}
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=400, content={"message": f"增强表格失败，{str(e)}"})