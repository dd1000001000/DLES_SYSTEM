from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from train.code_generation.model.models import GeneCode
from train.code_generation.service.code_generation_service import CodeGenerationService
from utils.authorization.authorization import get_current_user
from utils.authorization.models import User

code_generation_router = APIRouter()

@code_generation_router.post("/generate")
async def code_generation( user_input:GeneCode, current_user: Annotated[User, Depends(get_current_user)]):
    try:
        codeGenerationService = CodeGenerationService()
        result = codeGenerationService.ask(user_input.userCode,user_input.userInput)
        return {"code":result}
    except Exception as e:
        return JSONResponse(status_code=400,content={"message":f"代码生成失败：{e}"})