from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import csv, os, json
from datetime import datetime, date

app = FastAPI(title="Time Tracker API")

# ── CORS ── Allow React frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your Vercel URL
    allow_methods=["*"],
    allow_headers=["*"],
)

ENTRIES_FILE = "time_entries.csv"
RATES_FILE   = "rates.csv"

ENTRIES_COLS = ["id", "date", "clock_in", "clock_out", "num_children",
                "hourly_rate", "hours_worked", "client_name", "notes"]
RATES_COLS   = ["num_children", "hourly_rate"]

# ── CSV Helpers ────────────────────────────────────────────────────────────────

def init_csv(path, columns):
    if not os.path.exists(path):
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()

def read_csv(path, columns):
    init_csv(path, columns)
    rows = []
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

def write_csv(path, columns, rows):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

def next_id(rows):
    if not rows:
        return 1
    ids = [int(r["id"]) for r in rows if r.get("id", "").isdigit()]
    return max(ids) + 1 if ids else 1

def get_default_rates():
    return [
        {"num_children": "1", "hourly_rate": "20.00"},
        {"num_children": "2", "hourly_rate": "30.00"},
        {"num_children": "3", "hourly_rate": "38.00"},
        {"num_children": "4", "hourly_rate": "45.00"},
    ]

def load_rates():
    rows = read_csv(RATES_FILE, RATES_COLS)
    if not rows:
        rows = get_default_rates()
        write_csv(RATES_FILE, RATES_COLS, rows)
    return {int(r["num_children"]): float(r["hourly_rate"]) for r in rows}

# ── Models ─────────────────────────────────────────────────────────────────────

class ClockInRequest(BaseModel):
    num_children: int
    client_name: str
    notes: Optional[str] = ""

class ClockOutRequest(BaseModel):
    entry_id: int
    clock_out: str  # ISO datetime string

class RateUpdate(BaseModel):
    num_children: int
    hourly_rate: float

class EntryUpdate(BaseModel):
    client_name: Optional[str] = None
    notes: Optional[str] = None

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "Time Tracker API running"}

# -- Entries --

@app.get("/entries")
def get_entries():
    rows = read_csv(ENTRIES_FILE, ENTRIES_COLS)
    return rows

@app.post("/entries/clock-in")
def clock_in(req: ClockInRequest):
    rates = load_rates()
    rate  = rates.get(req.num_children, 0.0)
    rows  = read_csv(ENTRIES_FILE, ENTRIES_COLS)
    now   = datetime.now()
    new_entry = {
        "id":           next_id(rows),
        "date":         now.strftime("%Y-%m-%d"),
        "clock_in":     now.strftime("%H:%M:%S"),
        "clock_out":    "",
        "num_children": req.num_children,
        "hourly_rate":  rate,
        "hours_worked": "",
        "client_name":  req.client_name,
        "notes":        req.notes or "",
    }
    rows.append(new_entry)
    write_csv(ENTRIES_FILE, ENTRIES_COLS, rows)
    return new_entry

@app.post("/entries/{entry_id}/clock-out")
def clock_out(entry_id: int):
    rows = read_csv(ENTRIES_FILE, ENTRIES_COLS)
    now  = datetime.now()
    for row in rows:
        if int(row["id"]) == entry_id:
            clock_in_dt   = datetime.strptime(f"{row['date']} {row['clock_in']}", "%Y-%m-%d %H:%M:%S")
            hours         = (now - clock_in_dt).total_seconds() / 3600
            row["clock_out"]    = now.strftime("%H:%M:%S")
            row["hours_worked"] = round(hours, 4)
            write_csv(ENTRIES_FILE, ENTRIES_COLS, rows)
            return row
    raise HTTPException(status_code=404, detail="Entry not found")

@app.delete("/entries/{entry_id}")
def delete_entry(entry_id: int):
    rows = read_csv(ENTRIES_FILE, ENTRIES_COLS)
    new_rows = [r for r in rows if int(r.get("id", -1)) != entry_id]
    if len(new_rows) == len(rows):
        raise HTTPException(status_code=404, detail="Entry not found")
    write_csv(ENTRIES_FILE, ENTRIES_COLS, new_rows)
    return {"deleted": entry_id}

# -- Rates --

@app.get("/rates")
def get_rates():
    rows = read_csv(RATES_FILE, RATES_COLS)
    if not rows:
        rows = get_default_rates()
        write_csv(RATES_FILE, RATES_COLS, rows)
    return [{"num_children": int(r["num_children"]), "hourly_rate": float(r["hourly_rate"])} for r in rows]

@app.put("/rates")
def update_rates(rates: list[RateUpdate]):
    rows = [{"num_children": str(r.num_children), "hourly_rate": str(r.hourly_rate)} for r in rates]
    write_csv(RATES_FILE, RATES_COLS, rows)
    return {"updated": len(rows)}

# -- Invoice --

@app.get("/invoice")
def get_invoice(client_name: str, start_date: str, end_date: str):
    rows = read_csv(ENTRIES_FILE, ENTRIES_COLS)
    filtered = []
    for row in rows:
        if row.get("client_name") != client_name:
            continue
        if not row.get("clock_out"):
            continue
        row_date = row.get("date", "")
        if start_date <= row_date <= end_date:
            filtered.append(row)

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
