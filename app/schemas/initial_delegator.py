from pydantic import BaseModel

class InitialDelegatorCreate(BaseModel):
    address: str
    amount: int
    is_participate: bool
