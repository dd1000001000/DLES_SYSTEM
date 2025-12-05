# -*- coding: utf-8 -*-
from typing import Literal, List

from pydantic import BaseModel, Field


class EnhanceParas(BaseModel):
    type: Literal["JOIN", "UNION", "BOTH"] = Field(
        ...,
        description="表格增强方式：JOIN（连接）、UNION（合并）、BOTH（同时执行 JOIN 和 UNION），默认为BOTH"
    )
    columns: List[str] = Field(
        ...,
        description="要增强表格列名列表，例如 ['col1', 'col2']，默认为空列表"
    )
    number: int = Field(
        ...,
        description="表格增强后的列的目标数量，默认为6"
    )
    fill: Literal["AVERAGE", "MEAN", "MODEL"] = Field(
        ...,
        description="填充缺失值的方式：AVERAGE（平均值）、MEAN（均值）、MODEL（使用模型预测填充），默认为 MODEL"
    )