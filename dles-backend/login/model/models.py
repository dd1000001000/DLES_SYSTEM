# -*- coding: utf-8 -*-
from typing import Literal

from pydantic import BaseModel, EmailStr


class SendEmail(BaseModel):
    email: EmailStr
    type: Literal['register', 'recover']


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    verify_code: str


class UserRecover(BaseModel):
    email: EmailStr
    new_password: str
    verify_code: str
