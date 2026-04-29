from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import gspread
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy.orm import Session
from database import User
import os, json, requests as req

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


def get_user_credentials(user: User, db: Session) -> Credentials:
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


def hex_to_rgb(hex_color):
    """Convert hex color to Google Sheets RGB dict (0-1 range)."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return {"red": r/255, "green": g/255, "blue": b/255}


def generate_invoice_sheet(user: User, entries, invoice_num: str, due_days: int, db: Session) -> str:
    """
    Creates a formatted invoice spreadsheet from scratch in the user's Google Drive.
    No template copying needed — built entirely via the Sheets API.
    """
    creds       = get_user_credentials(user, db)
    gc          = gspread.authorize(creds)
    service     = build("sheets", "v4", credentials=creds)
    today       = datetime.now().strftime("%m/%d/%Y")
    due_date    = (datetime.now() + timedelta(days=due_days)).strftime("%m/%d/%Y")
    client_name = entries[0].client_name if entries else ""

    # Group entries by day
    entries_sorted = sorted(entries, key=lambda e: (e.date, e.clock_in))
    by_day = defaultdict(list)
    for entry in entries_sorted:
        by_day[entry.date].append(entry)

    # Build line item rows
    line_rows   = []
    total_hours = 0
    total_earn  = 0

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

        total_hours += day_hours
        total_earn  += day_earn
        line_rows.append({
            "description": "\n".join(day_lines),
            "hours":       round(day_hours, 2),
            "total":       round(day_earn, 2),
        })

    # ── Create spreadsheet ────────────────────────────────────────────────────
    ss = gc.create(f"Invoice {invoice_num} — {client_name}")
    ws = ss.sheet1
    sheet_id = ws.id

    # ── Write all data ────────────────────────────────────────────────────────
    business_name    = user.business_name    or "Your Business Name"
    business_address = user.business_address or ""
    business_phone   = user.business_phone   or ""
    payable_to       = user.payable_to       or ""

    # Row 1-3: Business info
    ws.update([[ business_name ]],    "B3")
    ws.update([[ business_address ]], "B4")
    ws.update([[ business_phone ]],   "B5")

    # Row 8: "Invoice" heading
    ws.update([[ "Invoice" ]], "B8")

    # Row 9: Submitted date
    ws.update([[ f"Submitted on {today}" ]], "B9")

    # Row 11: Column labels
    ws.update([[ "Invoice for", "", "Payable to", "", "Invoice #" ]], "B11")

    # Row 12: Values
    ws.update([[ client_name, "", payable_to, "", invoice_num ]], "B12")

    # Row 14: Due date label
    ws.update([[ "", "", "", "", "Due date" ]], "B14")

    # Row 15: Due date value
    ws.update([[ "", "", "", "", due_date ]], "B15")

    # Row 17: Divider (empty)
    # Row 18: Table headers
    ws.update([[ "Description", "", "Hours", "", "Total price" ]], "B18")

    # Line items starting row 19
    start_row   = 19
    current_row = start_row

    for row in line_rows:
        ws.update([[ row["description"], "", row["hours"], "", row["total"] ]], f"B{current_row}")
        current_row += 1

    # Totals
    subtotal_row = current_row + 1
    ws.update([[ "", "", "", "Subtotal",   round(total_earn, 2) ]], f"B{subtotal_row}")
    ws.update([[ "", "", "", "Adjustments", 0 ]],                   f"B{subtotal_row + 1}")
    ws.update([[ "", "", "", "TOTAL DUE",  round(total_earn, 2) ]], f"B{subtotal_row + 2}")

    # ── Apply formatting via batchUpdate ──────────────────────────────────────
    purple      = hex_to_rgb("4a148c")
    light_purple= hex_to_rgb("7e57c2")
    pink        = hex_to_rgb("e91e8c")
    light_gray  = hex_to_rgb("f5f5f5")
    dark_text   = hex_to_rgb("212121")
    white       = {"red": 1, "green": 1, "blue": 1}

    def cell_range(start_row_idx, start_col_idx, end_row_idx, end_col_idx):
        return {
            "sheetId":          sheet_id,
            "startRowIndex":    start_row_idx,
            "endRowIndex":      end_row_idx,
            "startColumnIndex": start_col_idx,
            "endColumnIndex":   end_col_idx,
        }

    requests = [
        # Set column widths
        {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1}, "properties": {"pixelSize": 20},  "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 4}, "properties": {"pixelSize": 150}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 4, "endIndex": 5}, "properties": {"pixelSize": 80},  "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 5, "endIndex": 6}, "properties": {"pixelSize": 100}, "fields": "pixelSize"}},

        # Business name — large purple bold
        {"repeatCell": {"range": cell_range(2, 1, 3, 5), "cell": {"userEnteredFormat": {"textFormat": {"fontSize": 18, "bold": True, "foregroundColor": purple}}}, "fields": "userEnteredFormat.textFormat"}},

        # "Invoice" heading — huge purple bold
        {"repeatCell": {"range": cell_range(7, 1, 8, 5), "cell": {"userEnteredFormat": {"textFormat": {"fontSize": 26, "bold": True, "foregroundColor": purple}}}, "fields": "userEnteredFormat.textFormat"}},

        # "Submitted on" — pink bold
        {"repeatCell": {"range": cell_range(8, 1, 9, 5), "cell": {"userEnteredFormat": {"textFormat": {"bold": True, "foregroundColor": pink}}}, "fields": "userEnteredFormat.textFormat"}},

        # Column labels row (Invoice for, Payable to, Invoice #) — bold
        {"repeatCell": {"range": cell_range(10, 1, 11, 6), "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}}, "fields": "userEnteredFormat.textFormat"}},

        # Due date label — bold
        {"repeatCell": {"range": cell_range(13, 4, 14, 6), "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}}, "fields": "userEnteredFormat.textFormat"}},

        # Table header row — purple background white text bold
        {"repeatCell": {"range": cell_range(17, 1, 18, 6), "cell": {"userEnteredFormat": {
            "backgroundColor": light_purple,
            "textFormat": {"bold": True, "foregroundColor": white},
        }}, "fields": "userEnteredFormat(backgroundColor,textFormat)"}},

        # Line item rows — alternating light gray
        {"repeatCell": {"range": cell_range(start_row - 1, 1, current_row - 1, 6), "cell": {"userEnteredFormat": {
            "backgroundColor": light_gray,
            "wrapStrategy": "WRAP",
            "verticalAlignment": "TOP",
        }}, "fields": "userEnteredFormat(backgroundColor,wrapStrategy,verticalAlignment)"}},

        # Subtotal label — right aligned bold
        {"repeatCell": {"range": cell_range(subtotal_row - 1, 1, subtotal_row + 2, 6), "cell": {"userEnteredFormat": {
            "horizontalAlignment": "RIGHT",
        }}, "fields": "userEnteredFormat.horizontalAlignment"}},

        # Total due — large pink bold
        {"repeatCell": {"range": cell_range(subtotal_row + 1, 4, subtotal_row + 2, 6), "cell": {"userEnteredFormat": {
            "textFormat": {"fontSize": 14, "bold": True, "foregroundColor": pink},
        }}, "fields": "userEnteredFormat.textFormat"}},

        # Horizontal divider above table
        {"updateBorders": {"range": cell_range(16, 1, 17, 6), "bottom": {"style": "SOLID", "width": 2, "color": light_purple}}},

        # Horizontal divider below line items
        {"updateBorders": {"range": cell_range(current_row - 1, 1, current_row, 6), "bottom": {"style": "SOLID", "width": 1, "color": light_purple}}},
    ]

    service.spreadsheets().batchUpdate(
        spreadsheetId=ss.id,
        body={"requests": requests}
    ).execute()

    return f"https://docs.google.com/spreadsheets/d/{ss.id}"