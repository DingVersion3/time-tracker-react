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
    creds       = get_user_credentials(user, db)
    gc          = gspread.authorize(creds)
    today       = datetime.now().strftime("%m/%d/%Y")
    due_date    = (datetime.now() + timedelta(days=due_days)).strftime("%m/%d/%Y")
    client_name = entries[0].client_name if entries else ""

    template_id  = user.invoice_template_id  or DEFAULT_TEMPLATE_ID
    template_gid = user.invoice_template_gid or DEFAULT_TEMPLATE_GID

    # Copy the template into the user's own Drive using their credentials
    import requests as req
    token = creds.token
    copy_res = req.post(
        f"https://www.googleapis.com/drive/v3/files/{template_id}/copy",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": f"Invoice {invoice_num} — {client_name}"}
    )

    if not copy_res.ok:
        raise Exception(f"Failed to copy template: {copy_res.text}")

    new_file_id = copy_res.json()["id"]
    new_ss      = gc.open_by_key(new_file_id)
    new_ws      = new_ss.get_worksheet_by_id(template_gid)

    # Fill header fields
    new_ws.update([[ f"Submitted on {today}" ]], "B9")
    new_ws.update([[ client_name ]], "B12")
    new_ws.update([[ invoice_num ]], "F12")
    new_ws.update([[ due_date ]], "F15")

    # Group entries by day
    entries_sorted = sorted(entries, key=lambda e: (e.date, e.clock_in))
    by_day = defaultdict(list)
    for entry in entries_sorted:
        by_day[entry.date].append(entry)

    current_row = 19
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

        new_ws.update([[ "\n".join(day_lines) ]], f"B{current_row}")
        new_ws.update([[ round(day_hours, 2) ]], f"E{current_row}")
        new_ws.update([[ round(day_earn,  2) ]], f"G{current_row}")
        current_row += 1

    return f"https://docs.google.com/spreadsheets/d/{new_file_id}"
