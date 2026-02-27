from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import declarative_base
from datetime import datetime
from pydantic import BaseModel

Base = declarative_base()


# =========================
# DATABASE MODELS
# =========================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)


class Auction(Base):
    __tablename__ = "auctions"

    id = Column(Integer, primary_key=True)
    product_name = Column(String, nullable=False)
    current_price = Column(Float, default=0)
    status = Column(String, default="CREATED", index=True)
    end_time = Column(DateTime)

    __table_args__ = (
        Index("idx_auction_status", "status"),
    )


class Bid(Base):
    __tablename__ = "bids"

    id = Column(Integer, primary_key=True)
    auction_id = Column(Integer, ForeignKey("auctions.id"), index=True)
    dealer_id = Column(Integer, ForeignKey("users.id"), index=True)
    amount = Column(Float, nullable=False)
    idempotency_key = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("idempotency_key"),
        Index("idx_bid_auction_created", "auction_id", "created_at"),
    )


# =========================
# PYDANTIC SCHEMAS
# =========================

class UserCreate(BaseModel):
    email: str
    password: str
    role: str


class UserLogin(BaseModel):
    email: str
    password: str


class AuctionCreate(BaseModel):
    product_name: str
    current_price: float
    end_time: datetime


class BidCreate(BaseModel):
    auction_id: int
    amount: float
    idempotency_key: str