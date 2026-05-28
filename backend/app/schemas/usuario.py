from typing import Optional

from pydantic import BaseModel, EmailStr

from app.utils.enums import RoleEnum


class UsuarioCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    papel: RoleEnum = RoleEnum.OPERADOR


class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    senha: Optional[str] = None
    papel: Optional[RoleEnum] = None
    ativo: Optional[bool] = None
