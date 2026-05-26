from sqlalchemy import Column, String, Float, DateTime
from app.database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String, primary_key=True)
    sender = Column(String)
    recipient = Column(String)
    amount = Column(Float)
    timestamp = Column(DateTime)
    status = Column(String)
    reference = Column(String)
    message = Column(String)

