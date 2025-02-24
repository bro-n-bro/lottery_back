import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db import models
from app.db.models import InitialDelegator, Invitation, Delegator
from app.services.general import get_delegators_from_cosmos
from app.services.lottery_service import get_invitations_dict, get_tickets_per_address


def get_invitation_ranking(db: Session):
    invitations_dict = get_invitations_dict(db)
    tickets_per_address = get_tickets_per_address(db)

    result = {}

    for address, invitations in invitations_dict.items():
        tickets = 0
        for invitation in invitations:
            tickets += tickets_per_address.get(invitation, 0)
        result[address] = tickets
    sorted_items = sorted(result.items(), key=lambda item: item[1], reverse=True)
    return [
        {"position": index + 1, "address": address, "tickets": tickets}
        for index, (address, tickets) in enumerate(sorted_items)
    ]
