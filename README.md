# GTBank Trust Engine

A FastAPI banking backend built around a specific failure mode in Nigerian payments: **the sender is debited, the recipient isn't credited, and nobody can say what happened to the money.**

Most demo banking APIs model transfers as binary — success or failure. Real interbank transfers through NIBSS are not binary. They get stuck, they settle late, they need reconciliation, and they occasionally reverse hours later. This service is built to represent that honestly rather than pretend it away.

---

## The problem

When a Nigerian bank transfer stalls, the customer sees a debit and no credit. The app usually shows a spinner or a generic error. The money isn't lost, but the customer has no way to know that — so trust in digital banking erodes with every stuck transfer.

The engineering problem underneath: **a transfer has more than two outcomes, and the intermediate ones need to be first-class states, not error handling.**

---

## Transaction state model

Every transfer moves through an explicit lifecycle. The status field is the source of truth and is persisted with the transaction record.

| State | Meaning | Terminal? |
|---|---|---|
| `initiating` | Record created, not yet sent to NIBSS | No |
| `processing` | NIBSS has the request, no outcome yet | No |
| `stuck` | No response within expected window — retry | No |
| `delay_finality` | Accepted but not yet settled | No |
| `reconciliation_required` | Outcome genuinely unknown; needs manual reconciliation | Yes |
| `success` | Funds confirmed landed | Yes |
| `failed` | Rejected, no debit stands | Yes |
| `reversed` | Debited then returned | Yes |

The key design decision: `reconciliation_required` is a **terminal state, not an error**. An uncertain outcome is a real outcome and gets recorded as one, rather than being retried forever or collapsed into `failed`.

```
initiating
    │
    ▼
processing ──────► success
    │
    ├──► stuck ──────┐
    │                │ retry w/ backoff
    ├──► delay_finality
    │                │
    │                ▼
    ├──► reconciliation_required   (terminal — needs human)
    ├──► failed                    (terminal)
    └──► reversed                  (terminal)
```

---

## Retry strategy

Non-terminal states are retried; terminal states break the loop immediately.

- **Bounded attempts** — a maximum of 3, so a stuck transfer never loops indefinitely.
- **Increasing backoff with jitter** — wait time grows per attempt, plus a random component. The jitter matters: without it, every client retrying a NIBSS outage retries in lockstep and hammers the upstream at exactly the same moment. Jitter spreads the load.
- **Terminal states exit immediately** — no point retrying a `reversed` transaction.

The transaction is written **once**, after the loop resolves. One record per transfer, no duplicate rows from retries.

---

## Stack

- **FastAPI** — API layer, automatic OpenAPI docs
- **PostgreSQL** + **SQLAlchemy** — persistence and relational modelling
- **Alembic** — schema migrations (versioned, in `alembic/versions/`)
- **Pydantic** — request/response validation
- **python-jose** — JWT authentication
- **bcrypt** — PIN hashing
- **Cloudinary** — profile photo storage
- **Paystack** — account funding via webhook

---

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Service + database health check |
| `POST` | `/register` | Create account, returns JWT |
| `POST` | `/login` | Authenticate, returns JWT |
| `POST` | `/refresh` | Refresh an expiring token |
| `GET` | `/balance` | Authenticated balance lookup |
| `GET` | `/account/lookup/{account_number}` | Resolve account to name before transfer |
| `POST` | `/transfer` | Initiate a transfer through the state engine |
| `GET` | `/transactions` | Authenticated transaction history |
| `GET` | `/transfer/{reference}` | Look up a single transfer by reference |
| `POST` | `/fund-account` | Initiate deposit |
| `POST` | `/webhook/paystack` | Payment provider callback |
| `POST` | `/upload-photo` | Profile photo upload |
| `GET` | `/profile-photo` | Retrieve profile photo |

Interactive docs at `/docs` when running.

---

## Data model

**users** — `id`, `full_name`, `phone` (unique), `email` (unique), `bvn` (unique), `nin` (unique), `pin_hash`, `balance`, `kyc_tier`, `created_at`, `profile_photo`

**transactions** — `transaction_id` (PK), `user_id` (FK → users.id), `recipient`, `amount`, `timestamp`, `status`, `reference`, `message`

Every transaction carries a human-readable `reference` (`GTB-YYMMDD-NNNN`) and a plain-English `message`, so the customer is told what actually happened instead of seeing a raw status code.

---

## Security

- PINs hashed with **bcrypt** — never stored in plaintext
- **JWT** bearer tokens, 24-hour expiry, verified on every protected route
- Secrets (`DATABASE_URL`, `SECRET_KEY`) loaded from environment, not committed
- Pydantic schemas reject malformed payloads before they reach business logic
- Errors return structured responses rather than leaking internals

---

## Running locally

```bash
git clone https://github.com/africoding/gtbank-trust-engine.git
cd gtbank-trust-engine

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` in the project root:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/gtbank
SECRET_KEY=your-secret-key
```

Apply migrations and start:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

Open <http://localhost:8000/docs>.

---

## Project layout

```
app/
  main.py       # FastAPI app, routes, dependencies
  engine.py     # Transfer state orchestration + retry logic
  models.py     # SQLAlchemy models
  schemas.py    # Pydantic request/response schemas
  auth.py       # JWT creation and verification
  database.py   # Engine, session factory, Base
alembic/        # Migrations
```

---

## Current status & roadmap

This is an active portfolio project. The NIBSS interaction is currently **simulated** — it generates the realistic distribution of outcomes described above so the state machine and retry logic can be exercised without a live NIBSS connection.

Next:

- [ ] Idempotency keys on `/transfer` so a retried request returns the original transaction instead of creating a second one
- [ ] Move the transfer state machine behind an explicit interface so a real provider can be swapped in
- [ ] Wrap debit + transaction insert in a single database transaction
- [ ] Automated tests for each state transition and the retry loop
- [ ] Reconciliation worker for `reconciliation_required` transactions

---

## Licence

See [LICENSE](LICENSE).
