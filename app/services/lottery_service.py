import logging
import random

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
    return active_lottery

def get_initial_delegator(address: str, db: Session):
    print("aaaaaaaa")
    print(address)
    initial_delegator = db.query(models.InitialDelegator).filter(models.InitialDelegator.address == address).first()
    if not initial_delegator or not initial_delegator.is_participate:
        raise HTTPException(status_code=400, detail="You don't take part in lotteries")
    return initial_delegator

def get_latest_delegator(address: str, db: Session):
    delegator = db.query(models.Delegator).filter(models.Delegator.address == address)\
        .order_by(models.Delegator.timestamp.desc()).first()
    if not delegator:
        return models.Delegator(address=address, amount=0, timestamp=func.now())
    return delegator

def calculate_tickets(delegator_amount: int, initial_delegator_amount: int):
    return (min(delegator_amount - initial_delegator_amount, 0)) // 10


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


def get_address_tickets(address: str, db: Session):
    initial_delegator = get_initial_delegator(address, db)

    delegator = get_latest_delegator(address, db)

    return calculate_tickets(delegator.amount, initial_delegator.amount)


def get_lottery_info_by_address(address: str, db: Session):
    active_lottery = get_active_lottery(db)

    initial_delegator = get_initial_delegator(address, db)

    delegator = get_latest_delegator(address, db)

    tickets = calculate_tickets(delegator.amount, initial_delegator.amount)

    total_tickets = get_total_tickets(db)

    win_probability = tickets / total_tickets if total_tickets else 0

    result =  {
        "address_info": {
            "address": address,
            "initial_amount": initial_delegator.amount,
            "amount": delegator.amount,
            "delegation_difference": delegator.amount - initial_delegator.amount,
            "total_tickets": tickets,
            "delegation_tickets": tickets,
            "referral_tickets": 0,
            "win_probability": win_probability,
        }
    }
    if active_lottery:
        result["lottery_info"] = {
            "winners_count": active_lottery.winners_count,
            "start_at": active_lottery.start_at
        }
    return result

def get_addresses_participating_in_lottery(db):
    delegators_alias = aliased(models.Delegator)
    initial_delegators_alias = aliased(models.InitialDelegator)

    subquery = (
        db.query(
            delegators_alias.address,
            ((delegators_alias.amount - initial_delegators_alias.amount) // 10).label('ticket_count')
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

    result = db.query(subquery.c.address, subquery.c.ticket_count).all()

    addresses = []
    for address, ticket_count in result:
        addresses.extend([address] * ticket_count)

    return addresses


def draw_lottery(db):
    addresses = get_addresses_participating_in_lottery(db)

    lottery = db.query(models.Lottery).filter(models.Lottery.is_finished == False).first()
    if not lottery:
        raise ValueError("No active lottery.")

    winners_count = min(lottery.winners_count,len(set(addresses)))

    weighted_addresses = []
    for address in addresses:
        weighted_addresses.append(address)
    random.shuffle(weighted_addresses)
    main_winner = weighted_addresses[0]
    winners = []
    seen = set()
    for address in weighted_addresses:
        if address not in seen:
            winners.append(address)
            seen.add(address)
        if len(winners) == winners_count:
            break

    lottery.is_finished = True
    db.commit()

    winners_objects = []
    for i, address in enumerate(winners):
        initial_delegator = db.query(models.InitialDelegator).filter(models.InitialDelegator.address == address).first()
        is_main = (address == main_winner)
        winner = models.Winner(
            lottery_id=lottery.id,
            initial_delegator_id=initial_delegator.id,
            is_main=is_main
        )
        winners_objects.append(winner)

    db.add_all(winners_objects)
    db.commit()

    result = {
        "lottery_id": lottery.id,
        "is_finished": lottery.is_finished,
        "winners": [
            {"address": winner.initial_delegator.address, "is_main": winner.is_main}
            for winner in winners_objects
        ]
    }

    return result


def get_lotteries_with_winners(db: Session):
    try:
        lotteries = db.query(models.Lottery).all()

        lottery_with_winners = []
        for lottery in lotteries:
            winners = (
                db.query(models.Winner, models.InitialDelegator.address)
                .join(models.InitialDelegator, models.Winner.initial_delegator_id == models.InitialDelegator.id)
                .filter(models.Winner.lottery_id == lottery.id)
                .all()
            )

            winners_response = []
            for winner, address in winners:
                winner_data = {
                    "address": address,
                    "is_main": winner.is_main,
                }
                winners_response.append(winner_data)

            lottery_data = {
                "id": lottery.id,
                "winners_count": lottery.winners_count,
                "start_at": lottery.start_at,
                "created_at": lottery.created_at,
                "is_finished": lottery.is_finished,
                "winners": winners_response,
            }
            lottery_with_winners.append(lottery_data)
        return lottery_with_winners

    except Exception as e:
        raise Exception(f"Error: {str(e)}")