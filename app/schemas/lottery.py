from app.schemas.winner import WinnerResponse
from pydantic import BaseModel
from typing import List
from datetime import datetime

class LotteryCreate(BaseModel):
    github_link: str
    start_at: datetime

    class Config:
        orm_mode = True


class LotteryResponse(BaseModel):
    id: int
    winners_count: int
    start_at: datetime
    created_at: datetime
    is_finished: bool
    winners: List[WinnerResponse]

    class Config:
        orm_mode = True
