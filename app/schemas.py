from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# ============================================
# GTBank Trust Engine - Schemas
# Defines exact shapes of requests and responses
# FastAPI validates automatically
# Protects engine from bad/missing data
# ============================================


# ============================================
# REQUEST SCHEMAS
# What the API expects to RECEIVE
# ============================================

class TransferRequest(BaseModel):
    sender: str = Field(..., example="Emeka")
    recipient: str = Field(..., example="Kosi")
    amount: float = Field(..., example=50000)

    class Config:
        json_schema_extra = {
            "example": {
                "sender": "Emeka",
                "recipient": "Kosi",
                "amount": 50000
            }
        }


# ============================================
# RESPONSE SCHEMAS
# What the API sends BACK
# ============================================

class TransferResponse(BaseModel):
    reference: str = Field(..., example="GTB-260524-4870")
    status: str = Field(..., example="success")
    message: str = Field(..., example="✅ ₦50000 has landed in Kosi's account.")

    class Config:
        json_schema_extra = {
            "example": {
                "reference": "GTB-260524-4870",
                "status": "success",
                "message": "✅ ₦50000 has landed in Kosi's account."
            }
        }


class TransactionDetail(BaseModel):
    transaction_id: str
    sender: str
    recipient: str
    amount: float
    timestamp: datetime
    status: str
    reference: str
    message: str

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    status: str
    engine: str
    version: str
    message: str


# ============================================
# ERROR SCHEMA
# What the API returns when something goes wrong
# ============================================

class ErrorResponse(BaseModel):
    detail: str = Field(..., example="Transaction not found")

    