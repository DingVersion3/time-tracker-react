from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from database import get_db, create_tables, User, TimeEntry, Rate
from auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_active_subscription
)
from sheets import generate_invoice_sheet

app = FastAPI(title="Time Tracker API")

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://time-tracker-react-one.vercel.app",
        "http://localhost:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Create tables on startup ───────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    create_tables()


# ── Health check ───────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "Time Tracker API running"}


# ══════════════════════════════════════════════════════════════════════════════
# AUTH ROUTES
# ══════════════════════════════════════════════════════════════════════════════

class SignupRequest(BaseModel):
    email: str
    password: str
    business_name: Optional[str] = ""
    payable_to: Optional[str] = ""

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: int
    email: str
    business_name: str
    business_address: str
    business_phone: str
    payable_to: str
    subscription_status: str
    trial_ends_at: Optional[datetime]
    invoice_template_id: str
    invoice_template_gid: int
    invoice_folder_id: str

    class Config:
        from_attributes = True


@app.post("/auth/signup", response_model=TokenResponse)
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email.lower()).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email            = req.email.lower(),
        hashed_password  = hash_password(req.password),
        business_name    = req.business_name or "",
        payable_to       = req.payable_to or "",
        subscription_status = "trialing",
        trial_ends_at    = datetime.utcnow() + timedelta(days=14),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Add default rates for new user
    default_rates = [
        Rate(user_id=user.id, num_children=1, hourly_rate=20.0),
        Rate(user_id=user.id, num_children=2, hourly_rate=30.0),
        Rate(user_id=user.id, num_children=3, hourly_rate=38.0),
        Rate(user_id=user.id, num_children=4, hourly_rate=45.0),
    ]
    db.add_all(default_rates)
    db.commit()

    return {"access_token": create_access_token(user.id)}


@app.post("/auth/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username.lower()).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"access_token": create_access_token(user.id)}


@app.get("/auth/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


# ══════════════════════════════════════════════════════════════════════════════
# USER / SETTINGS ROUTES
# ══════════════════════════════════════════════════════════════════════════════

class UpdateProfileRequest(BaseModel):
    business_name:    Optional[str] = None
    business_address: Optional[str] = None
    business_phone:   Optional[str] = None
    payable_to:       Optional[str] = None
    invoice_template_id:  Optional[str] = None
    invoice_template_gid: Optional[int] = None
    invoice_folder_id:    Optional[str] = None


@app.put("/user/profile")
def update_profile(
    req: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    for field, value in req.dict(exclude_none=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


# ══════════════════════════════════════════════════════════════════════════════
# RATES ROUTES
# ══════════════════════════════════════════════════════════════════════════════

class RateItem(BaseModel):
    num_children: int
    hourly_rate: float


@app.get("/rates")
def get_rates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rates = db.query(Rate).filter(Rate.user_id == current_user.id).order_by(Rate.num_children).all()
    return [{"num_children": r.num_children, "hourly_rate": r.hourly_rate} for r in rates]


@app.put("/rates")
def update_rates(
    rates: List[RateItem],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db.query(Rate).filter(Rate.user_id == current_user.id).delete()
    for r in rates:
        db.add(Rate(user_id=current_user.id, num_children=r.num_children, hourly_rate=r.hourly_rate))
    db.commit()
    return {"updated": len(rates)}


# ══════════════════════════════════════════════════════════════════════════════
# TIME ENTRY ROUTES
# ══════════════════════════════════════════════════════════════════════════════

class ClockInRequest(BaseModel):
    num_children: int
    client_name: str
    notes: Optional[str] = ""


@app.get("/entries")
def get_entries(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    entries = db.query(TimeEntry).filter(TimeEntry.user_id == current_user.id).order_by(TimeEntry.date.desc(), TimeEntry.clock_in.desc()).all()
    return entries


@app.post("/entries/clock-in")
def clock_in(
    req: ClockInRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    rates = db.query(Rate).filter(Rate.user_id == current_user.id, Rate.num_children == req.num_children).first()
    rate  = rates.hourly_rate if rates else 0.0
    now   = datetime.now()

    entry = TimeEntry(
        user_id      = current_user.id,
        date         = now.strftime("%Y-%m-%d"),
        clock_in     = now.strftime("%H:%M:%S"),
        clock_out    = "",
        num_children = req.num_children,
        hourly_rate  = rate,
        hours_worked = 0.0,
        client_name  = req.client_name,
        notes        = req.notes or "",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@app.post("/entries/{entry_id}/clock-out")
def clock_out(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    entry = db.query(TimeEntry).filter(
        TimeEntry.id == entry_id,
        TimeEntry.user_id == current_user.id
    ).first()

    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    now         = datetime.now()
    clock_in_dt = datetime.strptime(f"{entry.date} {entry.clock_in}", "%Y-%m-%d %H:%M:%S")
    hours       = (now - clock_in_dt).total_seconds() / 3600

    entry.clock_out    = now.strftime("%H:%M:%S")
    entry.hours_worked = round(hours, 4)
    db.commit()
    db.refresh(entry)
    return entry


@app.delete("/entries/{entry_id}")
def delete_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    entry = db.query(TimeEntry).filter(
        TimeEntry.id == entry_id,
        TimeEntry.user_id == current_user.id
    ).first()

    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    db.delete(entry)
    db.commit()
    return {"deleted": entry_id}


# ══════════════════════════════════════════════════════════════════════════════
# INVOICE ROUTES
# ══════════════════════════════════════════════════════════════════════════════

class InvoiceRequest(BaseModel):
    client_name:    str
    start_date:     str
    end_date:       str
    invoice_number: Optional[str] = None
    due_days:       Optional[int] = 14


@app.get("/invoice")
def get_invoice(
    client_name: str,
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    entries = db.query(TimeEntry).filter(
        TimeEntry.user_id    == current_user.id,
        TimeEntry.client_name == client_name,
        TimeEntry.clock_out  != "",
        TimeEntry.date       >= start_date,
        TimeEntry.date       <= end_date,
    ).order_by(TimeEntry.date).all()

    total_hours    = sum(e.hours_worked for e in entries)
    total_earnings = sum(e.hours_worked * e.hourly_rate for e in entries)

    return {
        "client_name":    client_name,
        "start_date":     start_date,
        "end_date":       end_date,
        "entries":        entries,
        "total_hours":    round(total_hours, 2),
        "total_earnings": round(total_earnings, 2),
    }


@app.post("/invoice/generate")
def invoice_generate(
    req: InvoiceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    if not current_user.invoice_template_id:
        raise HTTPException(status_code=400, detail="No invoice template configured. Please add your Google Sheet template ID in Settings.")

    entries = db.query(TimeEntry).filter(
        TimeEntry.user_id     == current_user.id,
        TimeEntry.client_name == req.client_name,
        TimeEntry.clock_out   != "",
        TimeEntry.date        >= req.start_date,
        TimeEntry.date        <= req.end_date,
    ).order_by(TimeEntry.date).all()

    if not entries:
        raise HTTPException(status_code=404, detail="No entries found for this client and date range")

    # Auto-generate invoice number if not provided
    invoice_num = req.invoice_number or str(
        db.query(TimeEntry).filter(TimeEntry.user_id == current_user.id).count()
    )

    url = generate_invoice_sheet(current_user, entries, invoice_num, req.due_days or 14)

    total_earnings = round(sum(e.hours_worked * e.hourly_rate for e in entries), 2)

    return {
        "url":            url,
        "invoice_number": invoice_num,
        "total_earnings": total_earnings,
    }
