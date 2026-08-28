from pydantic import BaseModel, ConfigDict
from typing import Optional

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    role: str
    organization_id: Optional[int] = None
    new_organization_name: Optional[str] = None

class UserOut(UserBase):
    id: int
    role: str
    organization_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class OrganizationOut(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)
