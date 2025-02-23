from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class LotteryCreate(BaseModel):
    github_link: str
    start_at: datetime

    class Config:
        orm_mode = True


class InitialDelegatorResponse(BaseModel):
    id: int
    address: str
    amount: int
    is_participate: bool
    referral_token: Optional[str] = None

    class Config:
        orm_mode = True

class WinnerResponse(BaseModel):
    id: int
    lottery_id: int
    initial_delegator_id: int
    is_main: bool
    is_claim_prize: bool
    initial_delegator: InitialDelegatorResponse

    class Config:
        orm_mode = True

class LotteryResponse(BaseModel):
    id: int
    winners_count: int
    start_at: datetime
    created_at: datetime
    is_finished: bool
    github_link: Optional[str] = None
    winners: List[WinnerResponse] = []

    class Config:
        orm_mode = True