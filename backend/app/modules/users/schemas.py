import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=10, max_length=256)
    roles: list[str] = Field(min_length=1)
    institution_id: uuid.UUID | None = None
    state_code: str | None = Field(default=None, max_length=8)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    email: EmailStr | None = None


class UserStatus(BaseModel):
    is_active: bool


class UserRoles(BaseModel):
    roles: list[str] = Field(min_length=1)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    username: str
    full_name: str
    is_active: bool
    state_code: str | None
    roles: list[str]
    institution_id: uuid.UUID | None = None
