# -*- coding: utf-8 -*-
import os
from pathlib import Path
from typing import Annotated, List
from fastapi.responses import FileResponse
from fastapi import Depends, APIRouter, UploadFile
from starlette.responses import JSONResponse

from enhance.enhance_history_tree.file_reader import FileReader
from enhance.enhance_history_tree.model.models import AddFolder, changeForm
from enhance.enhance_history_tree.service.enhance_history_tree_service import EnhanceHistoryTreeService
from utils.authorization.authorization import get_current_user
from utils.authorization.models import User

enhance_history_router = APIRouter()

@enhance_history_router.get('/{username}')
async def get_enhance_history_tree(username:str, current_user: Annotated[User, Depends(get_current_user)]):
    try:
        enhance_history_tree_service = EnhanceHistoryTreeService(username)
        history_tree = enhance_history_tree_service.get_user_tree()
        return {"history_tree": history_tree}
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": f"获取用户历史记录树失败，{str(e)}"})

@enhance_history_router.get('/{username}/info/{node_id}')
async def get_folder_or_file_info(username:str, node_id:int, current_user: Annotated[User, Depends(get_current_user)]):
    try:
        enhance_history_tree_service = EnhanceHistoryTreeService(username)
        detailed_info = enhance_history_tree_service.get_folder_or_file_info(node_id)
        return {"info": detailed_info}
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": f"获取文件或文件夹详细信息失败，{str(e)}"})

@enhance_history_router.post('/{username}/add')
async def add_folder(username:str, add_form: AddFolder,current_user: Annotated[User, Depends(get_current_user)]):
    try:
        enhance_history_tree_service = EnhanceHistoryTreeService(username)
        enhance_history_tree_service.add_folder(add_form.faNodeId,add_form.nodeName)
        return {}
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": f"新增文件夹失败，{str(e)}"})

@enhance_history_router.post('/{username}/change')
async def change_folder_name(username:str, change_form:changeForm,current_user: Annotated[User, Depends(get_current_user)]):
    try:
        enhance_history_tree_service = EnhanceHistoryTreeService(username)
        enhance_history_tree_service.change_folder_name(change_form.nodeId,change_form.newNodeName)
        return {}
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": f"修改文件夹名称失败，{str(e)}"})

@enhance_history_router.post('/{username}/delete')
async def delete_folders(username:str,deleteIds:List[int],current_user: Annotated[User, Depends(get_current_user)]):
    try:
        enhance_history_tree_service = EnhanceHistoryTreeService(username)
        enhance_history_tree_service.delete_folders(deleteIds)
        return {}
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": f"删除文件夹失败，{str(e)}"})

@enhance_history_router.post('/{username}/init/{faNodeId}')
async def init_case(username:str,faNodeId: str, csvFile: UploadFile, current_user: Annotated[User, Depends(get_current_user)]):
    try:
        enhance_history_tree_service = EnhanceHistoryTreeService(username)
        result = enhance_history_tree_service.init_case(int(faNodeId),csvFile)
        return {"node_id": result}
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": f"上传csv文件失败，{str(e)}"})

@enhance_history_router.get('/{username}/{enhance_id}')
async def get_enhance_history(username:str, enhance_id:int,current_user: Annotated[User, Depends(get_current_user)]):
    try:
        enhance_history_tree_service = EnhanceHistoryTreeService(username)
        case_path = enhance_history_tree_service.get_path_by_id(enhance_id)
        reader = FileReader(username)
        json_data = reader.read_json_file(os.path.join(case_path,'dialogue.json'))
        table_data = reader.read_csv_to_json(os.path.join(case_path,'table.csv'))
        return {"table":table_data,"dialogue":json_data}
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": f"读取用例失败，{str(e)}"})

@enhance_history_router.get('/download/{username}/{enhance_id}')
async def down_csv_file(username:str,enhance_id:int,current_user: Annotated[User, Depends(get_current_user)]):
    try:
        enhance_history_tree_service = EnhanceHistoryTreeService(username)
        reader = FileReader(username)
        case_path = os.path.join(reader.history_folder_path,enhance_history_tree_service.get_path_by_id(enhance_id))
        csv_path = Path(os.path.join(case_path,'table.csv'))
        if not os.path.exists(csv_path):
            raise Exception('下载的文件不存在')
        return FileResponse(
            csv_path
        )
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": f"下载文件失败，{str(e)}"})
