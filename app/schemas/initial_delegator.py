from pydantic import BaseModel

class InitialDelegatorCreate(BaseModel):
    address: str
    amount: int
    is_participate: bool

class ParticipateRequest(BaseModel):
    pubkey: str
    signatures: str
    referral_code: str = None