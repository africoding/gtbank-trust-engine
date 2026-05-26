from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.database import Base, engine, SessionLocal
from app.engine import process_transfer
from app.models import Transaction

# ============================================
# GTBank Trust Engine - FastAPI Gateway
# Production replacement for Flask api.py
# Receives requests. Orchestrates. Returns truth.
# ============================================

# Create all database tables on startup
Base.metadata.create_all(bind=engine)

# Initialize FastAPI
app = FastAPI(
    title="GTBank Trust Engine",
    description="Selling certainty to uncertainty in Nigerian payments",
    version="1.0.0"
)

# ============================================
# REQUEST SCHEMA
# Defines exact shape of incoming transfer request
# FastAPI validates automatically
# ============================================

class TransferRequest(BaseModel):
    sender: str
    recipient: str
    amount: float

# ============================================
# ENDPOINT 1: CREATE TRANSFER
# POST /transfer
# Emeka sends money
# ============================================

@app.post("/transfer")
def create_transfer(request: TransferRequest):
    result = process_transfer(
        sender=request.sender,
        recipient=request.recipient,
        amount=request.amount
    )
    return result

# ============================================
# ENDPOINT 2: LOOKUP TRANSFER
# GET /transfer/{reference}
# Agent looks up transaction by reference
# ============================================

@app.get("/transfer/{reference}")
def lookup_transfer(reference: str):
    db = SessionLocal()
    transaction = db.query(Transaction).filter(
        Transaction.reference == reference
    ).first()
    db.close()

    if not transaction:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found"
        )

    return {
        "transaction_id": transaction.transaction_id,
        "sender": transaction.sender,
        "recipient": transaction.recipient,
        "amount": transaction.amount,
        "timestamp": transaction.timestamp,
        "status": transaction.status,
        "reference": transaction.reference,
        "message": transaction.message
    }

# ============================================
# ENDPOINT 3: HEALTH CHECK
# GET /health
# Confirms engine is alive
# ============================================

@app.get("/health")
def health_check():
    return {
        "status": "alive",
        "engine": "GTBank Trust Engine",
        "version": "1.0.0",
        "message": "Selling certainty to uncertainty"
    }

