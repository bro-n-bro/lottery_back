# main.py
import random

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.dependencies import verify_token
from app.db import models
from app.db.database import get_db
from app.schemas.lottery import LotteryCreate
from app.services.initial_delegator_service import participate, fetch_delegators_data
from app.services.lottery_service import create_lottery, get_lottery_info_by_address

app = FastAPI()


@app.get('/')
def read_root():
    return {"message": "Started"}


@app.get("/address/{address_id}")
def get_address_info(address_id: str):
    return {
        "address": address_id,
        "delegated_tokens_after_snapshot": round(random.uniform(0, 1000), 2),
        "tickets_number": random.randint(0, 20),
        "win_probability": round(random.uniform(0, 100), 2)
    }

@app.get("/{lottery_id}")
def get_lottery_info(lottery_id: str):
    is_finished = random.choice([True, False])

    winners = []
    if is_finished:
        num_winners = random.randint(1, 5)
        winners = [
            {
                "address": f"0x{random.randint(10**15, 10**16 - 1):x}",
                "is_main_winner": i == 0,  # Только первый - главный победитель
                "delegated_tokens": round(random.uniform(0, 1000), 2)
            }
            for i in range(num_winners)
        ]

    return {
        "lottery": lottery_id,
        "is_finished": is_finished,
        "winners": winners
    }

@app.post("/initial-delegator/{address}/participate")
def participate_endpoint(address: str, db: Session = Depends(get_db)):
    delegator = participate(db, address)
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

async def lifespan(app: FastAPI):
    celery_app.start()
    yield