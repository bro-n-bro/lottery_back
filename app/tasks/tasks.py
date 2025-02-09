from celery import shared_task
from sqlalchemy.orm import Session
from app.db import models
from app.db.database import SessionLocal

from app.services.general import get_delegators_from_cosmos

@shared_task
def sync_delegators():
    """Задача, которая раз в час получает делегаторов и записывает в базу."""
    db: Session = SessionLocal()

    try:
        delegators = get_delegators_from_cosmos()
        for delegation in delegators:
            delegator_address = delegation.delegation.delegator_address
            amount = int(delegation.balance.amount) / 1_000_000

            new_entry = models.Delegator(
                address=delegator_address,
                amount=amount
            )
            db.add(new_entry)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Ошибка при обновлении делегаторов: {e}")
    finally:
        db.close()

    return f"Добавлено {len(delegators)} делегаторов в таблицу Delegator."
