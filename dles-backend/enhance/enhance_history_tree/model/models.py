# -*- coding: utf-8 -*-
from typing import List
from pydantic import BaseModel


class HistoryTreeNode(BaseModel):
    id: int
    faid: int
    label: str
    disabled: bool
    isFile: bool
    children: List['HistoryTreeNode']

    class Config:
        arbitrary_types_allowed = True

class AddFolder(BaseModel):
    faNodeId: int
    nodeName: str

class changeForm(BaseModel):
    nodeId: int
    newNodeName: str

class Dialogue(BaseModel):
    content: str
    role: str
