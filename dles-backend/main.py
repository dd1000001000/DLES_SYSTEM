import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse

from login.api.login_api import login_router
from settings.api.settings_api import settings_router
from enhance import enhance_router
from train import train_router
from transformer.model import TransformerEncoder, TableContrastiveModel


app = FastAPI()

origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router=login_router, prefix='/login', tags=['用户登录'])
app.include_router(router=settings_router, prefix='/settings', tags=['用户设置'])
app.include_router(router=enhance_router, prefix='/enhance', tags=['表格增强'])
app.include_router(router=train_router,prefix='/train',tags=['模型训练'])

@app.get("/avatars/{avatar_path}")
async def get_avatar(avatar_path: str):
    avatar_folder = os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'user_avatar'))
    file_path = os.path.join(avatar_folder, avatar_path)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"message": "Avatar not found"}


if __name__ == '__main__':
    uvicorn.run('main:app', port=8080, reload=False)
