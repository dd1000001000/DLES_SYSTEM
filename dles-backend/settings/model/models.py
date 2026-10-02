# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field


class ChangePassword(BaseModel):
    old_password: str
    new_password: str


class LLMConfigForm(BaseModel):
    base_url: str = Field(max_length=512)
    api_key: str = Field(default='', max_length=512)  # 留空表示不修改已保存的 Key
    chat_model: str = Field(max_length=255)
    strategy_model: str = Field(default='', max_length=255)  # 留空则使用 chat_model
    code_model: str = Field(default='', max_length=255)  # 留空则使用 chat_model
