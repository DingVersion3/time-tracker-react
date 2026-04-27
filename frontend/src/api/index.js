// All API calls go through this file.
// BASE_URL points to your FastAPI backend.
// In development, Vite proxies /api → http://localhost:8000
// In production, set VITE_API_URL in your Vercel environment variables.

const BASE_URL = import.meta.env.VITE_API_URL || "/api"

async function request(method, path, body = null) {
  const options = {
    method,
    headers: { "Content-Type": "application/json" },
  }
  if (body) options.body = JSON.stringify(body)

  const res = await fetch(`${BASE_URL}${path}`, options)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }))
    throw new Error(err.detail || "Request failed")
  }
  return res.json()
}

// ── Entries ───────────────────────────────────────────────────────────────────

export const getEntries = () => request("GET", "/entries")

export const clockIn = (num_children, client_name, notes = "") =>
  request("POST", "/entries/clock-in", { num_children, client_name, notes })

export const clockOut = (entry_id) =>
  request("POST", `/entries/${entry_id}/clock-out`)

export const deleteEntry = (entry_id) =>
  request("DELETE", `/entries/${entry_id}`)

// ── Rates ─────────────────────────────────────────────────────────────────────

export const getRates = () => request("GET", "/rates")

export const updateRates = (rates) => request("PUT", "/rates", rates)

// ── Invoice ───────────────────────────────────────────────────────────────────

export const getInvoice = (client_name, start_date, end_date) =>
  request("GET", `/invoice?client_name=${encodeURIComponent(client_name)}&start_date=${start_date}&end_date=${end_date}`)
