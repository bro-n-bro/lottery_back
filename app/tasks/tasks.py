from celery import shared_task
from sqlalchemy.orm import Session
from app.db import models
from app.db.database import SessionLocal

from app.services.general import get_delegators_from_cosmos

@shared_task
def sync_delegators():
    db: Session = SessionLocal()

    try:
        delegators = get_delegators_from_cosmos()
        db.query(models.Delegator).delete()
        for delegation in delegators:
            delegator_address = delegation.delegation.delegator_address
            amount = int(delegation.balance.amount) / 1_000_000

            new_entry = models.Delegator(
                address=delegator_address,
                amount=amount
            )
            db.add(new_entry)

        # TODO: remove before prod
        new_entry = models.Delegator(
            address='cosmos1p4hc20yrucx4hk4lf68wmuzvsa0rrxkuczh2ew',
            amount=51
        )
        db.add(new_entry)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error while getting validators: {e}")
    finally:
        db.close()

    return f"Added {len(delegators)} delegators to  Delegator."
