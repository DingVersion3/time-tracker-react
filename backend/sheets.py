import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os, json

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def get_gc():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        raise RuntimeError("GOOGLE_CREDENTIALS environment variable not set")
    creds_dict = json.loads(creds_json)
    creds      = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def format_time_12h(t):
    try:
        dt   = datetime.strptime(str(t), "%H:%M:%S")
        hour = dt.hour % 12 or 12
        return f"{hour}:{dt.strftime('%M')}{'pm' if dt.hour >= 12 else 'am'}"
    except Exception:
        return str(t)


def generate_invoice_sheet(user, entries, invoice_num, due_days=14):
    """
    Duplicates the user's invoice template tab and fills in the data.
    Returns the URL to the new tab.
    """
    from collections import defaultdict
    from datetime import timedelta

    gc           = get_gc()
    today        = datetime.now().strftime("%m/%d/%Y")
    due_date     = (datetime.now() + timedelta(days=due_days)).strftime("%m/%d/%Y")
    template_ss  = gc.open_by_key(user.invoice_template_id)
    template_tab = template_ss.get_worksheet_by_id(user.invoice_template_gid)

    new_ws = template_ss.duplicate_sheet(
        template_tab.id,
        new_sheet_name=f"Invoice {invoice_num}"
    )

    # Fill header fields
    new_ws.update([[ f"Submitted on {today}" ]], "B9")
    new_ws.update([[ entries[0].client_name if entries else "" ]], "B12")
    new_ws.update([[ invoice_num ]], "F12")
    new_ws.update([[ due_date ]], "F15")

    # Group by day
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
