from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile
from starlette.responses import JSONResponse

from train.enhance_comparation.model.models import DeleteForm, EvaluateParas
from train.enhance_comparation.service.temp_file_sevice import TempFileService
from utils.authorization.authorization import get_current_user
from utils.authorization.models import User

temp_file_api = APIRouter()

@temp_file_api.post("/clear_case/{uuid}")
async def clear_case(uuid:str,current_user: Annotated[User, Depends(get_current_user)]):
    try:
        temp_file_service = TempFileService()
        temp_file_service.delete_folder(uuid)
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": f"清空用例失败：{str(e)}"})

@temp_file_api.get("/{uuid}")
async def get_info(uuid:str,current_user: Annotated[User, Depends(get_current_user)]):
    try:
        temp_file_service = TempFileService()
        filenames = temp_file_service.get_file_names(uuid)
        columns = temp_file_service.get_columns(uuid)
        return {"filenames":filenames,"columns":columns}
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": f"获取文件名称失败：{str(e)}"})

@temp_file_api.post("/delete_csv")
async def delete_file(deleteForm:DeleteForm, current_user: Annotated[User, Depends(get_current_user)]):
    try:
        temp_file_service = TempFileService()
        temp_file_service.delete_file(deleteForm.folderName,deleteForm.fileName)
        return {}
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": f"删除单个文件失败：{str(e)}"})

@temp_file_api.post("/upload_csv/{uuid}")
async def upload_csv(uuid:str,csvFile:UploadFile,current_user: Annotated[User, Depends(get_current_user)]):
    try:
        temp_file_service = TempFileService()
        temp_file_service.add_file(uuid,csvFile)
        return {}
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": f"上传文件失败：{str(e)}"})

@temp_file_api.post("/evaluate/{uuid}")
async def evaluate_train(uuid:str,evaluate_form:EvaluateParas,current_user: Annotated[User, Depends(get_current_user)]):
    try:
        temp_file_service = TempFileService()
        score,predict_type = temp_file_service.get_evaluate_result(uuid,evaluate_form)
        return {"score":score,"type":predict_type}
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": f"评估失败：{str(e)}"})