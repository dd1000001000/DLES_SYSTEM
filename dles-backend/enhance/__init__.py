from fastapi import APIRouter

from enhance.enhance_history_tree.api.enhance_history_tree_api import enhance_history_router
from enhance.enhance_main.api.enhance_main_api import enhance_main_router

enhance_router = APIRouter()

enhance_router.include_router(router=enhance_history_router, prefix='/enhance_history', tags=['历史记录'])
enhance_router.include_router(router=enhance_main_router,prefix='/enhance_main',tags=['表格增强'])