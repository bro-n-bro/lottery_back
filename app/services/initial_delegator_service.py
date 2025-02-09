import logging

from sqlalchemy.orm import Session

from app.db import models
from app.db.models import InitialDelegator
from app.services.general import get_delegators_from_cosmos


def participate(db: Session, address: str):
    delegator = db.query(InitialDelegator).filter_by(address=address).first()

    if delegator:
        delegator.is_participate = True
    else:
        delegator = InitialDelegator(address=address, amount=0, is_participate=True)
        db.add(delegator)

    db.commit()
    db.refresh(delegator)

    return delegator


def fetch_delegators_data(db: Session):
    delegators = get_delegators_from_cosmos()

    for delegation in delegators:
        delegator_address = delegation.delegation.delegator_address
        amount = int(delegation.balance.amount) / 1_000_000  # Преобразуем uatom в ATOM

        existing_delegator = db.query(models.InitialDelegator).filter(
            models.InitialDelegator.address == delegator_address).first()

        if not existing_delegator:
            logging.info("Creating new init delegator")
            new_delegator = models.InitialDelegator(
                address=delegator_address,
                amount=amount,
                is_participate=False
            )
            db.add(new_delegator)
            db.commit()
            db.refresh(new_delegator)
        else:
            logging.info(f"Delegator {delegator_address} already in db ")
            existing_delegator.amount = amount
            db.commit()