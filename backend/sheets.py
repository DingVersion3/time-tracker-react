from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import gspread
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy.orm import Session
from database import User
import os, json

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
    """
    Duplicates the invoice template into the user's own Google Drive
    using their own OAuth credentials, fills in the data, and returns the URL.
    """
    creds       = get_user_credentials(user, db)
    gc          = gspread.authorize(creds)
    today       = datetime.now().strftime("%m/%d/%Y")
    due_date    = (datetime.now() + timedelta(days=due_days)).strftime("%m/%d/%Y")

    template_id  = user.invoice_template_id  or DEFAULT_TEMPLATE_ID
    template_gid = user.invoice_template_gid or DEFAULT_TEMPLATE_GID

    template_ss  = gc.open_by_key(template_id)
    template_tab = template_ss.get_worksheet_by_id(template_gid)

    new_ws = template_ss.duplicate_sheet(
        template_tab.id,
        new_sheet_name=f"Invoice {invoice_num} — {entries[0].client_name if entries else ''}"
    )

    # Fill header fields
    new_ws.update([[ f"Submitted on {today}" ]], "B9")
    new_ws.update([[ entries[0].client_name if entries else "" ]], "B12")
    new_ws.update([[ invoice_num ]], "F12")
    new_ws.update([[ due_date ]], "F15")

    # Group entries by day
    entries_sorted = sorted(entries, key=lambda e: (e.date, e.clock_in))
    by_day = defaultdict(list)
    for entry in entries_sorted:
        by_day[entry.date].append(entry)

    current_row = 19
    for day_date, day_entries in by_day.items():
        day_name     = datetime.strptime(str(day_date), "%Y-%m-%d").strftime("%A") + ":"
        day_lines    = [day_name]
        day_hours    = 0
        day_earnings = 0

        for entry in day_entries:
            time_in      = format_time_12h(str(entry.clock_in))
            time_out     = format_time_12h(str(entry.clock_out))
            rate         = float(entry.hourly_rate)
            hours        = float(entry.hours_worked)
            day_hours    += hours
            day_earnings += hours * rate
            day_lines.append(f"{time_in}-{time_out}(${int(rate)}/hr)")

        new_ws.update([[ "\n".join(day_lines) ]], f"B{current_row}")
        new_ws.update([[ round(day_hours, 2) ]], f"E{current_row}")
        new_ws.update([[ round(day_earnings, 2) ]], f"G{current_row}")
        current_row += 1

    return f"https://docs.google.com/spreadsheets/d/{template_ss.id}/edit#gid={new_ws.id}"
