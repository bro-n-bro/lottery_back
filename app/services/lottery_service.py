from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.db import models


def create_lottery(lottery_data, db: Session):
    existing_lottery = db.query(models.Lottery).filter(models.Lottery.is_finished == False).first()
    if existing_lottery:
        raise HTTPException(
            status_code=400,
            detail="There is already an active lottery"
        )

    new_lottery = models.Lottery(
        winners_count=lottery_data.winners_count,
        start_at=lottery_data.start_at,
        is_finished=False
    )

    db.add(new_lottery)
    db.commit()
    db.refresh(new_lottery)

    return new_lottery
