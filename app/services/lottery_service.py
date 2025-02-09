from sqlalchemy.orm import Session, aliased
from app.db import models
from fastapi import HTTPException
from sqlalchemy import func


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


def get_active_lottery(db: Session):
    active_lottery = db.query(models.Lottery).filter(models.Lottery.is_finished == False).first()
    if not active_lottery:
        raise HTTPException(status_code=404, detail="No active lottery")
    return active_lottery

def get_initial_delegator(address: str, db: Session):
    initial_delegator = db.query(models.InitialDelegator).filter(models.InitialDelegator.address == address).first()
    if not initial_delegator or not initial_delegator.is_participate:
        raise HTTPException(status_code=400, detail="You don't take part in lotteries")
    return initial_delegator

def get_latest_delegator(address: str, db: Session):
    delegator = db.query(models.Delegator).filter(models.Delegator.address == address)\
        .order_by(models.Delegator.timestamp.desc()).first()
    if not delegator:
        raise HTTPException(status_code=404, detail="Delegator not found")
    return delegator

def calculate_tickets(delegator_amount: int, initial_delegator_amount: int):
    return (delegator_amount - initial_delegator_amount) // 10


def get_total_tickets(db):
    delegators_alias = aliased(models.Delegator)
    initial_delegators_alias = aliased(models.InitialDelegator)

    subquery = (
        db.query(
            delegators_alias.address,
            (delegators_alias.amount - initial_delegators_alias.amount) // 10
        )
        .join(
            initial_delegators_alias,
            delegators_alias.address == initial_delegators_alias.address
        )
        .filter(initial_delegators_alias.is_participate == True)
        .distinct(delegators_alias.address)
        .order_by(delegators_alias.address, delegators_alias.timestamp.desc())
        .subquery()
    )

    total_tickets = (
        db.query(func.sum(subquery.c[1]))
        .scalar()
    )

    return total_tickets



def get_lottery_info_by_address(address: str, db: Session):
    get_active_lottery(db)

    initial_delegator = get_initial_delegator(address, db)

    delegator = get_latest_delegator(address, db)

    tickets = calculate_tickets(delegator.amount, initial_delegator.amount)

    total_tickets = get_total_tickets(db)

    win_probability = tickets / total_tickets if total_tickets else 0

    return {
        "address": address,
        "initial_amount": initial_delegator.amount,
        "amount": delegator.amount,
        "tickets": tickets,
        "win_probability": win_probability,
    }
