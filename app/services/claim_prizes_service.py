from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.db.models import InitialDelegator, Winner

def claim_prizes(db: Session, address: str):
    delegator = db.query(InitialDelegator).filter_by(address=address).first()
    if not delegator:
        raise HTTPException(status_code=404, detail="Address not found")

    unclaimed_winners = (
        db.query(Winner)
        .filter_by(initial_delegator_id=delegator.id, is_claim_prize=False)
        .all()
    )

    if not unclaimed_winners:
        raise HTTPException(status_code=400, detail="You have no unclaimed prizes")

    for winner in unclaimed_winners:
        winner.is_claim_prize = True

    db.commit()

    return {"message": "Prizes successfully claimed"}