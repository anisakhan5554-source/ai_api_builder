from pydantic import BaseModel, EmailStr, field_validator

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "user"

    @field_validator("password")
    def password_strength(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v 

    @field_validator("name")
    def name_not_empty(cls, v):
        if len(v.strip()) == 0:
            raise ValueError("Name cannot be empty")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    name: str
    email: EmailStr
