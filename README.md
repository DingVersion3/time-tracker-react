# ⏱️ Time Tracker — React + FastAPI

A mobile-friendly time tracking app for childcare businesses with variable hourly rates.

---

## Project Structure

```
time-tracker-react/
├── backend/
│   ├── main.py           # FastAPI app — all API endpoints
│   ├── requirements.txt
│   ├── time_entries.csv  # auto-created on first clock-in
│   └── rates.csv         # hourly rate tiers
└── frontend/
    ├── src/
    │   ├── api/index.js  # ALL fetch() calls live here
    │   ├── pages/        # ClockPage, LogPage, InvoicePage, SettingsPage
    │   ├── App.jsx       # routing + nav
    │   └── main.jsx      # entry point
    ├── index.html
    ├── package.json
    └── vite.config.js    # proxies /api → localhost:8000 in dev
```

---

## Running Locally

### Backend
```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload
```
Backend runs at: http://localhost:8000
API docs at:     http://localhost:8000/docs

### Frontend (new terminal)
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at: http://localhost:5173

---

## How the Frontend Talks to the Backend

All API calls are in `frontend/src/api/index.js`.
In development, Vite proxies `/api` → `http://localhost:8000` automatically.
Example: `fetch('/api/entries')` → hits `http://localhost:8000/entries`

---

## Deploying

### Backend → Render (free)
1. Push to GitHub
2. Go to render.com → New Web Service
3. Connect your repo, set root directory to `backend`
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Copy the deployed URL (e.g. https://your-app.onrender.com)

### Frontend → Vercel (free)
1. Go to vercel.com → New Project → connect your repo
2. Set root directory to `frontend`
3. Add environment variable: `VITE_API_URL` = your Render URL (e.g. `https://your-app.onrender.com`)
4. Deploy

---

## ⚠️ Persistent Storage Note

The backend currently uses CSV files. On Render's free tier, the filesystem resets on redeploy.
To persist data, the next step is switching to Google Sheets storage using `gspread`.
Ask for the Google Sheets upgrade when ready — it's a self-contained change to `main.py`.
