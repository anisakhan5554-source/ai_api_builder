from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role:str


class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role:str

    model_config = {
        "from_attributes": True
    }
class UserUpdate(BaseModel):
    name: str
    email: str
