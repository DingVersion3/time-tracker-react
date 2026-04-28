from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Time, ForeignKey, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Render's postgres URLs start with postgres:// but SQLAlchemy needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine         = create_engine(DATABASE_URL)
SessionLocal   = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base           = declarative_base()


# ── Models ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id                  = Column(Integer, primary_key=True, index=True)
    email               = Column(String, unique=True, index=True, nullable=False)
    hashed_password     = Column(String, nullable=False)
    business_name       = Column(String, default="")
    business_address    = Column(String, default="")
    business_phone      = Column(String, default="")
    payable_to          = Column(String, default="")

    # Stripe
    stripe_customer_id  = Column(String, default="")
    subscription_status = Column(String, default="trialing")  # trialing, active, canceled
    trial_ends_at       = Column(DateTime, nullable=True)

    # Google Sheets
    invoice_template_id = Column(String, default="")
    invoice_template_gid= Column(Integer, default=0)
    invoice_folder_id   = Column(String, default="")

    created_at          = Column(DateTime, default=datetime.utcnow)

    entries = relationship("TimeEntry", back_populates="user", cascade="all, delete")
    rates   = relationship("Rate",      back_populates="user", cascade="all, delete")


class TimeEntry(Base):
    __tablename__ = "time_entries"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    date         = Column(String, nullable=False)
    clock_in     = Column(String, nullable=False)
    clock_out    = Column(String, default="")
    num_children = Column(Integer, default=1)
    hourly_rate  = Column(Float, default=0.0)
    hours_worked = Column(Float, default=0.0)
    client_name  = Column(String, default="")
    notes        = Column(String, default="")

    user = relationship("User", back_populates="entries")


class Rate(Base):
    __tablename__ = "rates"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    num_children = Column(Integer, nullable=False)
    hourly_rate  = Column(Float, nullable=False)

    user = relationship("User", back_populates="rates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)
