from pydantic import BaseModel
from datetime import datetime

class LotteryCreate(BaseModel):
    winners_count: int
    start_at: datetime

    class Config:
        orm_mode = True
