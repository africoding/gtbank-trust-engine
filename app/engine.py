import uuid
import time
import random
from datetime import datetime
from app.database import SessionLocal
from app.models import Transaction

def process_transfer(user_id, sender, recipient, amount):

    # ============================================
    # SECTION 1: TRANSACTION RECORD SCHEMA
    # Five fields frozen forever. Status evolves.
    # ============================================

    transaction_id = uuid.uuid4()
    timestamp = datetime.now()
    reference = f"GTB-{timestamp.strftime('%y%m%d')}-{random.randint(1000,9999)}"
    status = "initiating"

    print(f"\n--- GTBank Trust Engine ---")
    print(f"Transaction ID: {transaction_id}")
    print(f"Sender: {sender}")
    print(f"Recipient: {recipient}")
    print(f"Amount: ₦{amount}")
    print(f"Timestamp: {timestamp}")

    # ============================================
    # SECTION 2: NIBSS STATE ORCHESTRATION
    # Geometric progression backoff + jitter
    # Protects NIBSS infrastructure from DoS
    # Tracks three things: attempt, wait_time, status
    # ============================================

    print("\n--- Contacting NIBSS ---")
    attempt = 1
    max_attempts = 5

    while attempt <= max_attempts:
        status = random.choice([
            "processing",
            "stuck",
            "delay_finality",
            "reconciliation_required",
            "success",
            "failed",
            "reversed"
        ])

        base_wait = 2 ** attempt
        jitter = random.uniform(0, 1)
        wait_time = base_wait + jitter

        print(f"Attempt {attempt} of {max_attempts} | NIBSS says: {status}")

        if status in ["success", "failed", "reversed", "reconciliation_required"]:
            break

        print(f"⏳ Retrying in {wait_time:.1f} seconds... Your money is safe")
        time.sleep(wait_time)
        attempt += 1

    # ============================================
    # SECTION 3: DASHBOARD REALITY FOR HUMAN
    # Save once. Return once. No repetition.
    # ============================================

    if status == "success":
        message = f"✅ ₦{amount} has landed in {recipient}'s account. Transaction confirmed by NIBSS."
    elif status == "failed":
        message = f"❌ ₦{amount} was not sent. Your money is safe. Try again later."
    elif status == "reversed":
        message = f"↩️ ₦{amount} returned to your account. Nothing was deducted."
    elif status == "stuck":
        message = f"⚠️ ₦{amount} is being investigated. You will be notified within 24 hours."
    elif status == "delay_finality":
        message = f"⏳ ₦{amount} confirmed but waiting for settlement. Usually resolves in 1-2 hours."
    elif status == "reconciliation_required":
        message = f"🔍 ₦{amount} needs manual verification. GTBank officer will resolve within 24 hours."
    else:
        message = "⚠️ Something unexpected happened. Your money is safe. Contact GTBank."

    db = SessionLocal()
    transaction = Transaction(
        transaction_id=str(transaction_id),
        user_id=user_id,
        recipient=recipient,
        amount=amount,
        timestamp=timestamp,
        status=status,
        reference=reference,
        message=message
    )
    db.add(transaction)
    db.commit()
    db.close()

    return {
        "reference": reference,
        "status": status,
        "message": message
    }
