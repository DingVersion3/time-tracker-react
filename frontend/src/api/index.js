const BASE_URL = import.meta.env.VITE_API_URL || "/api"

// ── Token storage ─────────────────────────────────────────────────────────────
export const getToken  = ()      => localStorage.getItem("token")
export const setToken  = (token) => localStorage.setItem("token", token)
export const clearToken = ()     => localStorage.removeItem("token")

// ── Base request ──────────────────────────────────────────────────────────────
async function request(method, path, body = null) {
  const headers = { "Content-Type": "application/json" }
  const token   = getToken()
  if (token) headers["Authorization"] = `Bearer ${token}`

  const options = { method, headers }
  if (body) options.body = JSON.stringify(body)

  const res = await fetch(`${BASE_URL}${path}`, options)

  if (res.status === 401) {
    clearToken()
    window.location.href = "/login"
    return
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }))
    throw new Error(err.detail || "Request failed")
  }

  return res.json()
}

// ── Auth ──────────────────────────────────────────────────────────────────────
export const signup = (email, password, business_name, payable_to) =>
  request("POST", "/auth/signup", { email, password, business_name, payable_to })

export const login = async (email, password) => {
  const form = new URLSearchParams()
  form.append("username", email)
  form.append("password", password)

  const res = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    body: form,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Login failed" }))
    throw new Error(err.detail)
  }
  return res.json()
}

export const getMe = () => request("GET", "/auth/me")

export const updateProfile = (data) => request("PUT", "/user/profile", data)

// ── Entries ───────────────────────────────────────────────────────────────────
export const getEntries = () => request("GET", "/entries")

export const clockIn = (num_children, client_name, notes = "") =>
  request("POST", "/entries/clock-in", { num_children, client_name, notes })

export const clockOut = (entry_id) =>
  request("POST", `/entries/${entry_id}/clock-out`)

export const deleteEntry = (entry_id) =>
  request("DELETE", `/entries/${entry_id}`)

// ── Rates ─────────────────────────────────────────────────────────────────────
export const getRates   = ()      => request("GET", "/rates")
export const updateRates = (rates) => request("PUT", "/rates", rates)

// ── Invoice ───────────────────────────────────────────────────────────────────
export const getInvoice = (client_name, start_date, end_date) =>
  request("GET", `/invoice?client_name=${encodeURIComponent(client_name)}&start_date=${start_date}&end_date=${end_date}`)

export const generateInvoice = (client_name, start_date, end_date, due_days = 14) =>
  request("POST", "/invoice/generate", { client_name, start_date, end_date, due_days })
