from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import Base, engine, SessionLocal
from app.engine import process_transfer
from app.models import Transaction, User
from app.schemas import (
    TransferRequest, TransferResponse,
    UserRegister, UserLogin, TokenResponse, UserResponse
)
from app.auth import create_token, verify_token
from datetime import datetime
import bcrypt
import uuid

# ============================================
# CREATE ALL DATABASE TABLES ON STARTUP
# ============================================
Base.metadata.create_all(bind=engine)

# ============================================
# INITIALIZE FASTAPI
# ============================================
app = FastAPI(
    title="GTBank Trust Engine",
    description="Selling certainty to uncertainty in Nigerian payments",
    version="2.0.0"
)

# ============================================
# CORS MIDDLEWARE
# ============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)

# ============================================
# SECURITY
# ============================================
security = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# ============================================
# ENDPOINT 1: HEALTH CHECK
# GET /health
# ============================================
@app.get("/health")
def health_check():
    return {
        "status": "alive",
        "engine": "GTBank Trust Engine",
        "version": "2.0.0",
        "message": "Selling certainty to uncertainty"
    }

# ============================================
# ENDPOINT 2: REGISTER
# POST /register
# ============================================
@app.post("/register")
def register(request: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.phone == request.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    pin_hash = bcrypt.hashpw(request.pin.encode(), bcrypt.gensalt()).decode()

    user = User(
        id=str(uuid.uuid4()),
        full_name=request.full_name,
        phone=request.phone,
        email=request.email,
        bvn=request.bvn,
        nin=request.nin,
        pin_hash=pin_hash,
        balance=5000.0,
        kyc_tier="tier1",
        created_at=datetime.now()
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token(user.id, user.phone)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "phone": user.phone,
            "balance": user.balance,
            "kyc_tier": user.kyc_tier
        }
    }

# ============================================
# ENDPOINT 3: LOGIN
# POST /login
# ============================================
@app.post("/login")
def login(request: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone == request.phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="Phone number not registered")

    pin_valid = bcrypt.checkpw(request.pin.encode(), user.pin_hash.encode())
    if not pin_valid:
        raise HTTPException(status_code=401, detail="Incorrect PIN")

    token = create_token(user.id, user.phone)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "phone": user.phone,
            "balance": user.balance,
            "kyc_tier": user.kyc_tier
        }
    }

# ============================================
# ENDPOINT 4: GET BALANCE
# GET /balance
# Protected - requires JWT token
# ============================================
@app.get("/balance")
def get_balance(current_user: User = Depends(get_current_user)):
    return {
        "full_name": current_user.full_name,
        "phone": current_user.phone,
        "balance": current_user.balance,
        "kyc_tier": current_user.kyc_tier
    }

# ============================================
# ENDPOINT 5: ACCOUNT LOOKUP
# GET /account/lookup/{account_number}
# FirstBank style - "Looking for account"
# ============================================
@app.get("/account/lookup/{account_number}")
def lookup_account(account_number: str, db: Session = Depends(get_db)):
    if len(account_number) != 10:
        raise HTTPException(status_code=400, detail="Account number must be 10 digits")

    user = db.query(User).filter(User.phone == account_number).first()
    if not user:
        raise HTTPException(status_code=404, detail="Account not found")

    return {
        "account_number": account_number,
        "account_name": user.full_name,
        "bank": "GTBank Trust Engine"
    }

# ============================================
# ENDPOINT 6: TRANSFER
# POST /transfer
# Protected - requires JWT token
# ============================================
@app.post("/transfer")
def create_transfer(
    request: TransferRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.balance < request.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    result = process_transfer(
        user_id=current_user.id,
        sender=current_user.full_name,
        recipient=request.recipient,
        amount=request.amount
    )

    if result["status"] == "success":
        current_user.balance -= request.amount
        db.commit()

    return result

# ============================================
# ENDPOINT 7: TRANSACTION HISTORY
# GET /transactions
# Protected - requires JWT token
# ============================================
@app.get("/transactions")
def get_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.timestamp.desc()).all()

    return [
        {
            "transaction_id": t.transaction_id,
            "recipient": t.recipient,
            "amount": t.amount,
            "status": t.status,
            "reference": t.reference,
            "message": t.message,
            "timestamp": t.timestamp
        }
        for t in transactions
    ]

# ============================================
# ENDPOINT 8: LOOKUP TRANSFER BY REFERENCE
# GET /transfer/{reference}
# ============================================
@app.get("/transfer/{reference}")
def lookup_transfer(reference: str, db: Session = Depends(get_db)):
    transaction = db.query(Transaction).filter(
        Transaction.reference == reference
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return {
        "transaction_id": transaction.transaction_id,
        "recipient": transaction.recipient,
        "amount": transaction.amount,
        "timestamp": transaction.timestamp,
        "status": transaction.status,
        "reference": transaction.reference,
        "message": transaction.message
    }
