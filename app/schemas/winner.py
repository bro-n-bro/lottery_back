from pydantic import BaseModel

class WinnerResponse(BaseModel):
    address: str
    is_main: bool

    class Config:
        orm_mode = True
