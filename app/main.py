# main.py
import random
from typing import List

import uvicorn
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette import status

from app.core.celery_app import celery_app
from app.core.dependencies import verify_token
from app.db import models
from app.db.database import get_db
from app.db.models import Lottery
from app.schemas.initial_delegator import ParticipateRequest
from app.schemas.lottery import LotteryCreate, LotteryResponse
from app.services.claim_prizes_service import claim_prizes, get_address_prizes
from app.services.delegator_service import get_invited_users, get_stakers_ranking
from app.services.general import validate_signature
from app.services.initial_delegator_service import participate, fetch_delegators_data, is_token_exist
from app.services.invitation_service import get_invitation_ranking
from app.services.lottery_service import create_lottery, get_lottery_info_by_address, \
    get_addresses_participating_in_lottery, draw_lottery, get_lotteries_with_winners, process_lottery

app = FastAPI()


@app.get('/')
def read_root():
    return {"message": "Started"}

@app.post("/initial-delegator/{address}/participate")
def participate_endpoint(
        address: str,
        data: ParticipateRequest,
        db: Session = Depends(get_db)
):
    if not validate_signature(data.pubkey, data.signatures, address):
        raise HTTPException(status_code=400, detail="Invalid signature")
    delegator = participate(db, address, data.referral_code)
    return {"address": delegator.address, "is_participate": delegator.is_participate}


@app.post("/create_lottery")
async def create_lottery_endpoint(lottery_data: LotteryCreate, db: Session = Depends(get_db),
                                  x_token: str = Depends(verify_token)):
    new_lottery = create_lottery(lottery_data, db)

    return {"message": "Lottery created successfully", "lottery_id": new_lottery.id}

@app.post("/populate-initial-delegators")
def populate_delegators(db: Session = Depends(get_db)):
    delegators_count = db.query(models.InitialDelegator).count()
    if delegators_count == 0:
        fetch_delegators_data(db)
        return {"message": "Delegators data populated"}
    else:
        return {"message": "Delegators table is not empty. No action taken."}

@app.get("/lottery/current/{address}/info")
async def get_lottery_info_api(address: str, db: Session = Depends(get_db)):
    try:
        lottery_info = get_lottery_info_by_address(address, db)
        return lottery_info
    except HTTPException as e:
        raise e


@app.get("/lottery/participants")
async def get_lottery_addresses(db: Session = Depends(get_db)):
    try:
        addresses = get_addresses_participating_in_lottery(db)
        return {"addresses": addresses}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/draw_lottery", response_model=dict)
async def draw_lottery_endpoint(
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    try:
        result = draw_lottery(db)
        return result

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.post("/{address}/claim-prizes")
def claim_prizes_endpoint(
    address: str,
    pubkey: str,
    signatures: str,
    db: Session = Depends(get_db)
):
    if not validate_signature(pubkey, signatures, address):
        raise HTTPException(status_code=400, detail="Invalid signature")
    return claim_prizes(db, address)

@app.get("/{address}/prizes")
def get_prizes(address: str, db: Session = Depends(get_db)):
    return get_address_prizes(db, address)

@app.get("/address/{address}/invited")
def invited_users(address: str, db: Session = Depends(get_db)):
    return get_invited_users(address, db)

@app.get("/stakers/ranking")
def stakers_ranking(db: Session = Depends(get_db)):
    return get_stakers_ranking(db)

@app.get("/inviters/ranking")
def invitation_ranking(db: Session = Depends(get_db)):
    return get_invitation_ranking(db)

@app.get("/check_referral_token/{referral_token}")
def check_referral_token(referral_token: str, db: Session = Depends(get_db)):
    return {'is_exist': is_token_exist(referral_token, db)}

@app.get("/lotteries", response_model=List[LotteryResponse])
def get_lotteries(db: Session = Depends(get_db)):
    lotteries = db.query(Lottery).all()
    return lotteries

@app.get("/lotteries/last", response_model=LotteryResponse)
def get_last_lottery(db: Session = Depends(get_db)):
    lottery = (
        db.query(Lottery)
        .filter(Lottery.is_finished == True)
        .order_by(Lottery.start_at.desc())
        .first()
    )
    if not lottery:
        raise HTTPException(status_code=404, detail="No finished lottery found")

    return process_lottery(lottery, db)


@app.get("/lotteries/current", response_model=LotteryResponse)
def get_current_lottery(db: Session = Depends(get_db)):
    lottery = db.query(Lottery).filter(Lottery.is_finished == False).first()
    if not lottery:
        raise HTTPException(status_code=404, detail="No current lottery found")

    return process_lottery(lottery, db)


@app.get("/lotteries/{lottery_id}", response_model=LotteryResponse)
def get_lottery(lottery_id: int, db: Session = Depends(get_db)):
    lottery = db.query(Lottery).filter(Lottery.id == lottery_id).first()
    if not lottery:
        raise HTTPException(status_code=404, detail="Lottery not found")

    return process_lottery(lottery, db)


async def lifespan(app: FastAPI):
    celery_app.start()
    yield


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)
