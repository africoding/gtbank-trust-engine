from jose import JWTError, jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

# ============================================
# CREATE JWT TOKEN
# Called after successful login/register
# ============================================
def create_token(user_id: str, phone: str) -> str:
    payload = {
        "user_id": user_id,
        "phone": phone,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# ============================================
# VERIFY JWT TOKEN
# Called on every protected request
# ============================================
def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# ============================================
# VERIFY JWT TOKEN — ALLOW RECENTLY EXPIRED
# Used only by /refresh, so a dead session
# can still renew itself within a grace period
# ============================================
def verify_token_allow_expired(token: str, grace_days: int = 7) -> dict:
    try:
        payload = jwt.decode(
            token, SECRET_KEY, algorithms=[ALGORITHM],
            options={"verify_exp": False}
        )
        exp_time = datetime.utcfromtimestamp(payload["exp"])
        if datetime.utcnow() - exp_time > timedelta(days=grace_days):
            return None
        return payload
    except JWTError:
        return None
