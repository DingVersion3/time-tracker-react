from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os, json
from datetime import datetime, timedelta
from collections import defaultdict
import gspread
from google.oauth2.service_account import Credentials

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

# ── Google Sheets Setup ────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

TEMPLATE_SPREADSHEET_ID = "1rBbCHT8E9dCEzCorE0alX2reFc3XoK2tIRHdtFS6Q3w"
TEMPLATE_GID             = 790763898

STORAGE_SPREADSHEET_ID = "1TRrhhGVmBJZCYhEr2e8nqZEQxnBjYzZGSmnaZxegT2Y"

ENTRIES_SHEET = "time_entries"
RATES_SHEET   = "rates"

ENTRIES_COLS = ["id", "date", "clock_in", "clock_out", "num_children",
                "hourly_rate", "hours_worked", "client_name", "notes"]
RATES_COLS   = ["num_children", "hourly_rate"]


def get_gc():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        raise RuntimeError("GOOGLE_CREDENTIALS environment variable not set")
    creds_dict = json.loads(creds_json)
    creds      = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def get_storage_spreadsheet():
    """
    Opens the storage spreadsheet by its fixed ID.
    On first run sets up the required tabs and headers if they don't exist.
    """
    gc    = get_gc()
    sheet = gc.open_by_key(STORAGE_SPREADSHEET_ID)

    existing_tabs = [ws.title for ws in sheet.worksheets()]

    if ENTRIES_SHEET not in existing_tabs:
        ws = sheet.add_worksheet(title=ENTRIES_SHEET, rows=1000, cols=len(ENTRIES_COLS))
        ws.append_row(ENTRIES_COLS)

    if RATES_SHEET not in existing_tabs:
        ws = sheet.add_worksheet(title=RATES_SHEET, rows=20, cols=2)
        ws.append_row(RATES_COLS)
        for r in get_default_rates():
            ws.append_row([r["num_children"], r["hourly_rate"]])

    return sheet


def get_worksheet(tab_name):
    return get_storage_spreadsheet().worksheet(tab_name)


def sheet_to_dicts(ws):
    return [dict(r) for r in ws.get_all_records()]


def next_id(rows):
    if not rows:
        return 1
    ids = [int(r["id"]) for r in rows if str(r.get("id", "")).isdigit()]
    return max(ids) + 1 if ids else 1


def get_default_rates():
    return [
        {"num_children": 1, "hourly_rate": 20.00},
        {"num_children": 2, "hourly_rate": 30.00},
        {"num_children": 3, "hourly_rate": 38.00},
        {"num_children": 4, "hourly_rate": 45.00},
    ]


def load_rates_dict():
    rows = sheet_to_dicts(get_worksheet(RATES_SHEET))
    if not rows:
        return {r["num_children"]: r["hourly_rate"] for r in get_default_rates()}
    return {int(r["num_children"]): float(r["hourly_rate"]) for r in rows}


def format_time_12h(t):
    """Convert HH:MM:SS to 8:30am format."""
    try:
        dt = datetime.strptime(str(t), "%H:%M:%S")
        hour = dt.hour % 12 or 12
        return f"{hour}:{dt.strftime('%M')}{'pm' if dt.hour >= 12 else 'am'}"
    except Exception:
        return str(t)


# ── Models ─────────────────────────────────────────────────────────────────────

class ClockInRequest(BaseModel):
    num_children: int
    client_name: str
    notes: Optional[str] = ""

class RateUpdate(BaseModel):
    num_children: int
    hourly_rate: float

class InvoiceRequest(BaseModel):
    client_name: str
    start_date: str
    end_date: str
    invoice_number: Optional[str] = None
    due_days: Optional[int] = 14


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "Time Tracker API running"}


# ── Entries ────────────────────────────────────────────────────────────────────

@app.get("/entries")
def get_entries():
    return sheet_to_dicts(get_worksheet(ENTRIES_SHEET))


@app.post("/entries/clock-in")
def clock_in(req: ClockInRequest):
    rates    = load_rates_dict()
    rate     = rates.get(req.num_children, 0.0)
    ws       = get_worksheet(ENTRIES_SHEET)
    rows     = sheet_to_dicts(ws)
    now      = datetime.now()
    entry_id = next_id(rows)

    ws.append_row([
        entry_id,
        now.strftime("%Y-%m-%d"),
        now.strftime("%H:%M:%S"),
        "",
        req.num_children,
        rate,
        "",
        req.client_name,
        req.notes or "",
    ])

    return {
        "id": entry_id, "date": now.strftime("%Y-%m-%d"),
        "clock_in": now.strftime("%H:%M:%S"), "clock_out": "",
        "num_children": req.num_children, "hourly_rate": rate,
        "hours_worked": "", "client_name": req.client_name,
        "notes": req.notes or "",
    }


@app.post("/entries/{entry_id}/clock-out")
def clock_out(entry_id: int):
    ws      = get_worksheet(ENTRIES_SHEET)
    records = ws.get_all_records()
    now     = datetime.now()

    for i, row in enumerate(records):
        if str(row.get("id", "")).isdigit() and int(row["id"]) == entry_id:
            clock_in_dt = datetime.strptime(
                f"{row['date']} {row['clock_in']}", "%Y-%m-%d %H:%M:%S"
            )
            hours     = (now - clock_in_dt).total_seconds() / 3600
            sheet_row = i + 2
            ws.update_cell(sheet_row, 4, now.strftime("%H:%M:%S"))
            ws.update_cell(sheet_row, 7, round(hours, 4))
            return {**row, "clock_out": now.strftime("%H:%M:%S"), "hours_worked": round(hours, 4)}

    raise HTTPException(status_code=404, detail="Entry not found")


@app.delete("/entries/{entry_id}")
def delete_entry(entry_id: int):
    ws      = get_worksheet(ENTRIES_SHEET)
    records = ws.get_all_records()

    for i, row in enumerate(records):
        if str(row.get("id", "")).isdigit() and int(row["id"]) == entry_id:
            ws.delete_rows(i + 2)
            return {"deleted": entry_id}

    raise HTTPException(status_code=404, detail="Entry not found")


# ── Rates ──────────────────────────────────────────────────────────────────────

@app.get("/rates")
def get_rates():
    rows = sheet_to_dicts(get_worksheet(RATES_SHEET))
    if not rows:
        return get_default_rates()
    return [{"num_children": int(r["num_children"]), "hourly_rate": float(r["hourly_rate"])} for r in rows]


@app.put("/rates")
def update_rates(rates: list[RateUpdate]):
    ws = get_worksheet(RATES_SHEET)
    ws.clear()
    ws.append_row(RATES_COLS)
    for r in rates:
        ws.append_row([r.num_children, r.hourly_rate])
    return {"updated": len(rates)}


# ── Invoice ────────────────────────────────────────────────────────────────────

@app.get("/invoice")
def get_invoice(client_name: str, start_date: str, end_date: str):
    """Returns invoice data as JSON for the frontend preview."""
    rows = sheet_to_dicts(get_worksheet(ENTRIES_SHEET))

    filtered = [
        r for r in rows
        if r.get("client_name") == client_name
        and r.get("clock_out")
        and start_date <= str(r.get("date", "")) <= end_date
    ]

    total_hours    = sum(float(r["hours_worked"]) for r in filtered if r.get("hours_worked"))
    total_earnings = sum(
        float(r["hours_worked"]) * float(r["hourly_rate"])
        for r in filtered if r.get("hours_worked") and r.get("hourly_rate")
    )

    return {
        "client_name":    client_name,
        "start_date":     start_date,
        "end_date":       end_date,
        "entries":        filtered,
        "total_hours":    round(total_hours, 2),
        "total_earnings": round(total_earnings, 2),
    }


@app.post("/invoice/generate")
def generate_invoice(req: InvoiceRequest):
    """
    Copies the invoice template into a new Google Sheet,
    fills in all session data grouped by day,
    and returns a shareable link to the completed invoice.
    """
    gc   = get_gc()
    rows = sheet_to_dicts(get_worksheet(ENTRIES_SHEET))

    filtered = [
        r for r in rows
        if r.get("client_name") == req.client_name
        and r.get("clock_out")
        and req.start_date <= str(r.get("date", "")) <= req.end_date
    ]

    if not filtered:
        raise HTTPException(status_code=404, detail="No entries found for this client and date range")

    invoice_num = req.invoice_number or str(
        max([int(r.get("id", 0)) for r in rows if str(r.get("id","")).isdigit()], default=1)
    )
    due_date = (datetime.now() + timedelta(days=req.due_days or 14)).strftime("%m/%d/%Y")
    today    = datetime.now().strftime("%m/%d/%Y")

    # Add a new tab to the template spreadsheet for this invoice
    template_ss  = gc.open_by_key(TEMPLATE_SPREADSHEET_ID)
    template_tab = template_ss.get_worksheet_by_id(TEMPLATE_GID)
    new_ws       = template_ss.duplicate_sheet(
        template_tab.id,
        new_sheet_name=f"{req.client_name}_{invoice_num}"
    )
    new_ss = template_ss

    # Fill header fields
    new_ws.update([[ f"Submitted on {today}" ]], "B9")
    new_ws.update([[ req.client_name ]], "B12")
    new_ws.update([[ invoice_num ]], "F12")
    new_ws.update([[ due_date ]], "F15")

    # Group entries by day and write line items starting at row 19
    filtered.sort(key=lambda r: (str(r["date"]), str(r["clock_in"])))

    by_day = defaultdict(list)
    for entry in filtered:
        by_day[str(entry["date"])].append(entry)

    current_row = 19

    for day_date, day_entries in by_day.items():
        day_name     = datetime.strptime(day_date, "%Y-%m-%d").strftime("%A") + ":"
        day_lines    = [day_name]
        day_hours    = 0
        day_earnings = 0

        for entry in day_entries:
            time_in      = format_time_12h(str(entry["clock_in"]))
            time_out     = format_time_12h(str(entry["clock_out"]))
            rate         = float(entry["hourly_rate"])
            hours        = float(entry["hours_worked"])
            day_hours    += hours
            day_earnings += hours * rate
            day_lines.append(f"{time_in}-{time_out}(${int(rate)}/hr)")

        new_ws.update([[ "\n".join(day_lines) ]], f"B{current_row}")
        new_ws.update([[ round(day_hours, 2) ]], f"E{current_row}")
        new_ws.update([[ round(day_earnings, 2) ]], f"G{current_row}")
        current_row += 1

    total_earnings = round(sum(
        float(r["hours_worked"]) * float(r["hourly_rate"])
        for r in filtered if r.get("hours_worked") and r.get("hourly_rate")
    ), 2)

    return {
        "url":            f"https://docs.google.com/spreadsheets/d/{new_ss.id}/edit#gid={new_ws.id}",
        "invoice_number": invoice_num,
        "total_earnings": total_earnings,
    }
