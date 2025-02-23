import random
import string

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from .database import Base


class Delegator(Base):
    __tablename__ = "delegators"

    id = Column(Integer, primary_key=True, index=True)
    address = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)
    timestamp = Column(DateTime, server_default=func.now())

class Lottery(Base):
    __tablename__ = "lotteries"

    id = Column(Integer, primary_key=True, index=True)
    winners_count = Column(Integer, nullable=False)
    start_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    is_finished = Column(Boolean, default=False)
    github_link = Column(String, nullable=True)

    winners = relationship("Winner", back_populates="lottery")

class Winner(Base):
    __tablename__ = "winners"

    id = Column(Integer, primary_key=True, index=True)
    lottery_id = Column(Integer, ForeignKey("lotteries.id"), nullable=False)
    initial_delegator_id = Column(Integer, ForeignKey("initial_delegators.id"), nullable=False)
    is_main = Column(Boolean, default=False)
    is_claim_prize = Column(Boolean, default=False)

    lottery = relationship("Lottery", back_populates="winners")
    initial_delegator = relationship("InitialDelegator")


class InitialDelegator(Base):
    __tablename__ = "initial_delegators"

    id = Column(Integer, primary_key=True, index=True)
    address = Column(String, unique=True, nullable=False)
    amount = Column(Integer, nullable=False)
    is_participate = Column(Boolean, default=False)
    referral_token = Column(String, unique=True, nullable=True, index=True)
    winners = relationship("Winner", back_populates="initial_delegator")

    invited_by = relationship("Invitation", back_populates="inviter", foreign_keys="[Invitation.inviter_id]")
    invited_users = relationship("Invitation", back_populates="invitee", foreign_keys="[Invitation.invitee_id]")

    @staticmethod
    def generate_referral_token():
        return "".join(random.choices(string.ascii_letters + string.digits, k=6))


class Invitation(Base):
    __tablename__ = "invitations"

    id = Column(Integer, primary_key=True, index=True)
    inviter_id = Column(Integer, ForeignKey("initial_delegators.id"), nullable=False)
    invitee_id = Column(Integer, ForeignKey("initial_delegators.id"), nullable=False)

    inviter = relationship("InitialDelegator", back_populates="invited_by", foreign_keys=[inviter_id])
    invitee = relationship("InitialDelegator", back_populates="invited_users", foreign_keys=[invitee_id])
