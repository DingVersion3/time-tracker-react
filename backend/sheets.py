from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import gspread
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy.orm import Session
from database import User
import os, json
from collections import defaultdict


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

# Built-in template — users who haven't set a custom one use this
DEFAULT_TEMPLATE_ID  = "1NyEArEv_kdhgH9FmRDU6mVrS6z-4yQ7-mKL4xMgNa80"
DEFAULT_TEMPLATE_GID = 790763898


def get_user_credentials(user: User, db: Session) -> Credentials:
    """Build Google OAuth credentials from stored user tokens."""
    if not user.google_refresh_token:
        raise ValueError("Google account not connected")

    creds = Credentials(
        token         = user.google_access_token or None,
        refresh_token = user.google_refresh_token,
        token_uri     = "https://oauth2.googleapis.com/token",
        client_id     = os.environ.get("GOOGLE_CLIENT_ID"),
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET"),
        scopes        = SCOPES,
    )

    # Refresh if expired
    if not creds.valid:
        creds.refresh(Request())
        user.google_access_token = creds.token
        user.google_token_expiry = creds.expiry
        db.commit()

    return creds


def format_time_12h(t):
    try:
        dt   = datetime.strptime(str(t), "%H:%M:%S")
        hour = dt.hour % 12 or 12
        return f"{hour}:{dt.strftime('%M')}{'pm' if dt.hour >= 12 else 'am'}"
    except Exception:
        return str(t)


def generate_invoice_sheet(user: User, entries, invoice_num: str, due_days: int, db: Session) -> str:
    creds    = get_user_credentials(user, db)
    gc       = gspread.authorize(creds)
    today    = datetime.now().strftime("%m/%d/%Y")
    due_date = (datetime.now() + timedelta(days=due_days)).strftime("%m/%d/%Y")
    client_name = entries[0].client_name if entries else ""

    # Create a brand new spreadsheet in the user's Drive
    ss = gc.create(f"Invoice {invoice_num} — {client_name}")
    ws = ss.sheet1
    ws.update_title("Invoice")

    # Header info
    ws.update([[ user.business_name or "" ]], "A1")
    ws.update([[ user.business_address or "" ]], "A2")
    ws.update([[ user.business_phone or "" ]], "A3")
    ws.update([[ f"Submitted on {today}" ]], "A5")
    ws.update([[ "Invoice for" ]], "A7")
    ws.update([[ client_name ]], "A8")
    ws.update([[ "Payable to" ]], "C7")
    ws.update([[ user.payable_to or "" ]], "C8")
    ws.update([[ "Invoice #" ]], "E7")
    ws.update([[ invoice_num ]], "E8")
    ws.update([[ "Due date" ]], "E10")
    ws.update([[ due_date ]], "E11")

    # Column headers
    ws.update([[ "Description", "", "Hours", "Total" ]], "A13")

    # Group entries by day
    entries_sorted = sorted(entries, key=lambda e: (e.date, e.clock_in))
    by_day = defaultdict(list)
    for entry in entries_sorted:
        by_day[entry.date].append(entry)

    current_row = 14
    total_hours    = 0
    total_earnings = 0

    for day_date, day_entries in by_day.items():
        day_name  = datetime.strptime(str(day_date), "%Y-%m-%d").strftime("%A") + ":"
        day_lines = [day_name]
        day_hours = 0
        day_earn  = 0

        for entry in day_entries:
            time_in  = format_time_12h(str(entry.clock_in))
            time_out = format_time_12h(str(entry.clock_out))
            rate     = float(entry.hourly_rate)
            hours    = float(entry.hours_worked)
            day_hours += hours
            day_earn  += hours * rate
            day_lines.append(f"{time_in}-{time_out}(${int(rate)}/hr)")

        ws.update([[ "\n".join(day_lines) ]], f"A{current_row}")
        ws.update([[ round(day_hours, 2) ]], f"C{current_row}")
        ws.update([[ round(day_earn,  2) ]], f"D{current_row}")
        total_hours    += day_hours
        total_earnings += day_earn
        current_row += 1

    # Totals
    ws.update([[ "Subtotal", "", "", round(total_earnings, 2) ]], f"A{current_row + 1}")
    ws.update([[ "TOTAL DUE", "", "", round(total_earnings, 2) ]], f"A{current_row + 2}")

    return f"https://docs.google.com/spreadsheets/d/{ss.id}"
