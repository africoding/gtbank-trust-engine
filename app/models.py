from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    full_name = Column(String)
    phone = Column(String, unique=True)
    email = Column(String, unique=True, nullable=True)
    bvn = Column(String, unique=True, nullable=True)
    nin = Column(String, unique=True, nullable=True)
    pin_hash = Column(String)
    balance = Column(Float, default=0.0)
    kyc_tier = Column(String, default="tier1")
    created_at = Column(DateTime)

class Transaction(Base):
    __tablename__ = "transactions"
    transaction_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    recipient = Column(String)
    amount = Column(Float)
    timestamp = Column(DateTime)
    status = Column(String)
    reference = Column(String)
    message = Column(String)
