import logging
import random
import requests

from sqlalchemy.orm import Session, aliased
from app.db import models
from fastapi import HTTPException
from sqlalchemy import func, delete

from app.db.models import Invitation, Delegator
from app.services.general import get_delegator_info


def create_lottery(lottery_data, db: Session):
    existing_lottery = db.query(models.Lottery).filter(models.Lottery.is_finished == False).first()
    if existing_lottery:
        raise HTTPException(
            status_code=400,
            detail="There is already an active lottery"
        )

    link = lottery_data.github_link
    if link:
        try:
            response = requests.get(link)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                winners_count = len(data)
            else:
                raise HTTPException(status_code=400, detail="Invalid JSON format. Expected a list.")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error fetching or parsing JSON: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail=f"Github link is required")

    new_lottery = models.Lottery(
        winners_count=winners_count,
        start_at=lottery_data.start_at,
        github_link=link,
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
    initial_delegator = db.query(models.InitialDelegator).filter(models.InitialDelegator.address == address).first()
    if not initial_delegator or not initial_delegator.is_participate:
        raise HTTPException(status_code=400, detail="You don't take part in lotteries")
    return initial_delegator

def get_latest_delegator(address: str, db: Session):
    delegator = db.query(models.Delegator).filter(models.Delegator.address == address).first()
    if not delegator:
        return models.Delegator(address=address, amount=0, timestamp=func.now())
    return delegator

def update_delegator_info(db: Session, delegator: Delegator):
    delegation_info = get_delegator_info(delegator.address)

    if not delegation_info:
        return delegator

    db.execute(delete(Delegator).where(Delegator.address == delegator.address))

    new_delegator = Delegator(
        address=delegator.address,
        amount=int(delegation_info.balance.amount) / 1_000_000,
    )

    db.add(new_delegator)
    db.commit()
    db.refresh(new_delegator)

    return new_delegator

def calculate_stacking_tickets(delegator_amount: int, initial_delegator_amount: int):
    return (max(delegator_amount - initial_delegator_amount, 0)) // 10


def get_total_stacking_tickets(db: Session):
    delegators_alias = aliased(models.Delegator)
    initial_delegators_alias = aliased(models.InitialDelegator)

    total_tickets = (
        db.query(
            func.sum((delegators_alias.amount - initial_delegators_alias.amount) // 10)
        )
        .join(
            initial_delegators_alias,
            delegators_alias.address == initial_delegators_alias.address,
            isouter=False
        )
        .filter(initial_delegators_alias.is_participate == True)
        .filter(delegators_alias.amount - initial_delegators_alias.amount > 0)
        .scalar()
    )

    return total_tickets or 0


def get_address_tickets(address: str, db: Session):
    initial_delegator = get_initial_delegator(address, db)

    delegator = get_latest_delegator(address, db)

    return calculate_stacking_tickets(delegator.amount, initial_delegator.amount)

def get_invitation_tickets(address, ticket_per_address, invitations_dict):
    result = 0
    if address_invitations := invitations_dict.get(address, None):
        for item in address_invitations:
            result += ticket_per_address.get(item, 0)
    return result


def get_total_invitation_tickets(ticket_per_address, invitations_dict):
    result = 0
    for _, invitees in invitations_dict.items():
        for address in invitees:
            result += ticket_per_address.get(address, 0)
    return result

def get_lottery_info_by_address(address: str, db: Session):
    active_lottery = get_active_lottery(db)

    initial_delegator = get_initial_delegator(address, db)

    delegator = get_latest_delegator(address, db)
    delegator = update_delegator_info(db, delegator)
    stacking_tickets = calculate_stacking_tickets(delegator.amount, initial_delegator.amount)
    total_stacking_tickets = get_total_stacking_tickets(db)

    ticket_per_address = get_tickets_per_address(db)
    invitations_dict = get_invitations_dict(db)

    invitation_tickets = get_invitation_tickets(address, ticket_per_address, invitations_dict)
    total_invitation_tickets = get_total_invitation_tickets(ticket_per_address, invitations_dict)
    total_tickets = total_invitation_tickets + total_stacking_tickets
    tickets = stacking_tickets + invitation_tickets
    win_probability = tickets / total_tickets if total_tickets else 0

    result =  {
        "address_info": {
            "address": address,
            "initial_amount": initial_delegator.amount,
            "referral_token": initial_delegator.referral_token,
            "amount": delegator.amount,
            "delegation_difference": delegator.amount - initial_delegator.amount,
            "total_tickets": tickets,
            "delegation_tickets": stacking_tickets,
            "referral_tickets": invitation_tickets,
            "win_probability": win_probability,
        }
    }
    if active_lottery:
        result["lottery_info"] = {
            "winners_count": active_lottery.winners_count,
            "start_at": active_lottery.start_at,
            "id": active_lottery.id
        }
    return result

def get_addresses_participating_in_lottery(db):
    stacking_participants = get_participants_by_stakers(db)
    invitation_participants = get_invitations_by_participants(db)
    return invitation_participants + stacking_participants

def get_invitations_by_participants(db):
    result = []
    invitations_dict = get_invitations_dict(db)
    tickets_per_address = get_tickets_per_address(db)
    for address, invitations in invitations_dict.items():
        tickets = 0
        for invitation in invitations:
            tickets += tickets_per_address.get(invitation, 0)
        if tickets > 0:
            result.extend([address] * tickets)
    return result

def get_participants_by_stakers(db):
    delegator = models.Delegator
    initial_delegator = models.InitialDelegator

    results = (
        db.query(
            delegator.address,
            ((delegator.amount - initial_delegator.amount) // 10).label("ticket_count")
        )
        .join(
            initial_delegator,
            delegator.address == initial_delegator.address
        )
        .filter(initial_delegator.is_participate == True)
        .all()
    )

    addresses = []
    for address, ticket_count in results:
        if ticket_count > 0:
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


def get_tickets_per_address(db: Session):
    delegators_alias = aliased(models.Delegator)
    initial_delegators_alias = aliased(models.InitialDelegator)

    results = (
        db.query(
            delegators_alias.address,
            ((delegators_alias.amount - initial_delegators_alias.amount) // 10).label("tickets")
        )
        .join(
            initial_delegators_alias,
            delegators_alias.address == initial_delegators_alias.address,
            isouter=False
        )
        .filter(initial_delegators_alias.is_participate == True)
        .filter(delegators_alias.amount - initial_delegators_alias.amount > 0)
        .all()
    )

    tickets_dict = {row.address: row.tickets for row in results}
    return tickets_dict


def get_invitations_dict(db: Session):
    inviter = aliased(models.InitialDelegator)
    invitee = aliased(models.InitialDelegator)

    query = (
        db.query(
            inviter.address.label("inviter_address"),
            invitee.address.label("invitee_address")
        )
        .join(Invitation, Invitation.inviter_id == inviter.id)
        .join(invitee, Invitation.invitee_id == invitee.id)
    )

    invitations_dict = {}
    for row in query.all():
        if row.inviter_address in invitations_dict:
            invitations_dict[row.inviter_address].append(row.invitee_address)
        else:
            invitations_dict[row.inviter_address] = [row.invitee_address]

    return invitations_dict