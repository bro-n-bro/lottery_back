from fastapi import HTTPException
from sqlalchemy.orm import Session, aliased

from app.db.models import InitialDelegator, Invitation, Delegator
from app.services.lottery_service import get_address_tickets
from sqlalchemy import func

def get_invited_users(address: str, db: Session):
    delegator = db.query(InitialDelegator).filter_by(address=address).first()
    if not delegator:
        raise HTTPException(status_code=404, detail="Address not found")

    invited_users = db.query(Invitation).filter_by(inviter_id=delegator.id).all()

    result = []
    for invitation in invited_users:
        invitee = db.query(InitialDelegator).filter_by(id=invitation.invitee_id).first()
        if invitee:
            tickets = get_address_tickets(invitee.address, db)
            result.append({"address": invitee.address, "tickets": tickets})
    return result


def get_stakers_ranking(db: Session):
    delegators_alias = aliased(Delegator)
    initial_delegators_alias = aliased(InitialDelegator)

    ticket_expr = (delegators_alias.amount - initial_delegators_alias.amount) // 10

    ranking_query = (
        db.query(
            delegators_alias.address,
            func.coalesce(ticket_expr, 0).label("tickets")
        )
        .join(
            initial_delegators_alias,
            delegators_alias.address == initial_delegators_alias.address
        )
        .filter(initial_delegators_alias.is_participate == True)
        .filter(delegators_alias.amount - initial_delegators_alias.amount >= 0)
        .order_by(func.coalesce(ticket_expr, 0).desc())
    ).all()

    return [{"position": index + 1, "address": row.address, "tickets": row.tickets} for index, row in
            enumerate(ranking_query)]

