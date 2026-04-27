import { useState, useEffect, useRef } from 'react'
import { clockIn, clockOut, getRates } from '../api'

// Stores active session in localStorage so it survives page refresh
const SESSION_KEY = 'active_session'

function loadSession() {
  try { return JSON.parse(localStorage.getItem(SESSION_KEY)) } catch { return null }
}

function saveSession(s) {
  if (s) localStorage.setItem(SESSION_KEY, JSON.stringify(s))
  else    localStorage.removeItem(SESSION_KEY)
}

export default function ClockPage() {
  const [rates,       setRates]       = useState([])
  const [session,     setSession]     = useState(loadSession)   // active clock-in entry
  const [numChildren, setNumChildren] = useState(1)
  const [clientName,  setClientName]  = useState('')
  const [notes,       setNotes]       = useState('')
  const [elapsed,     setElapsed]     = useState(0)            // seconds
  const [loading,     setLoading]     = useState(false)
  const [error,       setError]       = useState('')
  const timerRef = useRef(null)

  // Load rates on mount
  useEffect(() => {
    getRates().then(setRates).catch(() => {})
  }, [])

  // Live timer while clocked in
  useEffect(() => {
    if (session) {
      const tick = () => {
        const diff = Math.floor((Date.now() - new Date(session.startedAt).getTime()) / 1000)
        setElapsed(diff)
      }
      tick()
      timerRef.current = setInterval(tick, 1000)
    }
    return () => clearInterval(timerRef.current)
  }, [session])

  const currentRate = rates.find(r => r.num_children === numChildren)?.hourly_rate || 0
  const sessionRate = session ? (rates.find(r => r.num_children === session.num_children)?.hourly_rate || 0) : 0
  const earnings    = ((elapsed / 3600) * sessionRate).toFixed(2)

  function formatElapsed(secs) {
    const h = Math.floor(secs / 3600)
    const m = Math.floor((secs % 3600) / 60)
    const s = secs % 60
    return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
  }

  async function handleClockIn() {
    if (!clientName.trim()) { setError('Client name is required'); return }
    setError('')
    setLoading(true)
    try {
      const entry = await clockIn(numChildren, clientName.trim(), notes.trim())
      const sess  = { ...entry, startedAt: new Date().toISOString() }
      setSession(sess)
      saveSession(sess)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleClockOut() {
    setLoading(true)
    try {
      await clockOut(session.id)
      setSession(null)
      saveSession(null)
      setElapsed(0)
      setClientName('')
      setNotes('')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function handleDiscard() {
    setSession(null)
    saveSession(null)
    setElapsed(0)
  }

  return (
    <div>
      <div className="page-header">
        <div className="page-title">Time Tracker</div>
        <div className="page-subtitle">Childcare hours</div>
      </div>

      {/* Status */}
      <div style={{ padding: '0 24px', marginBottom: 16 }}>
        {session ? (
          <span className="status-pill in">
            <span className="dot green" /> Clocked in
          </span>
        ) : (
          <span className="status-pill out">
            <span className="dot red" /> Clocked out
          </span>
        )}
      </div>

      {session ? (
        /* ── Active session view ─────────────────────────────────────────── */
        <>
          <div className="card">
            <div className="clock-display">{formatElapsed(elapsed)}</div>
            <div className="clock-earning">${earnings} earned</div>
            <div className="divider" />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
              <span style={{ color: 'var(--muted)' }}>Client</span>
              <span style={{ fontFamily: 'var(--font-head)', fontWeight: 600 }}>{session.client_name}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginTop: 8 }}>
              <span style={{ color: 'var(--muted)' }}>Children</span>
              <span>{session.num_children} @ ${sessionRate}/hr</span>
            </div>
            {session.notes && (
              <div style={{ marginTop: 10 }}>
                <span className="tag">{session.notes}</span>
              </div>
            )}
          </div>

          <div style={{ padding: '0 16px' }}>
            <button className="btn btn-danger" onClick={handleClockOut} disabled={loading}>
              {loading ? 'Saving...' : '⏹ Clock Out'}
            </button>
            <button
              className="btn btn-ghost"
              style={{ marginTop: 8 }}
              onClick={handleDiscard}
            >
              Discard session
            </button>
          </div>
        </>
      ) : (
        /* ── Clock-in form ───────────────────────────────────────────────── */
        <>
          <div className="card">
            <div className="field">
              <label>Number of children</label>
              <select
                className="select"
                value={numChildren}
                onChange={e => setNumChildren(Number(e.target.value))}
              >
                {rates.map(r => (
                  <option key={r.num_children} value={r.num_children}>
                    {r.num_children} {r.num_children === 1 ? 'child' : 'children'} — ${r.hourly_rate}/hr
                  </option>
                ))}
              </select>
            </div>

            <div className="field">
              <label>Client name</label>
              <input
                className="input"
                placeholder="e.g. Smith Family"
                value={clientName}
                onChange={e => setClientName(e.target.value)}
              />
            </div>

            <div className="field" style={{ marginBottom: 0 }}>
              <label>Notes (optional)</label>
              <input
                className="input"
                placeholder="e.g. field trip day"
                value={notes}
                onChange={e => setNotes(e.target.value)}
              />
            </div>

            {error && <div className="error-msg">{error}</div>}
          </div>

          <div style={{ padding: '0 16px' }}>
            <button className="btn btn-primary" onClick={handleClockIn} disabled={loading}>
              {loading ? 'Starting...' : '▶ Clock In'}
            </button>
          </div>
        </>
      )}
    </div>
  )
}
