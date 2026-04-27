import { useState, useEffect } from 'react'
import { getEntries, deleteEntry } from '../api'

export default function LogPage() {
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter,  setFilter]  = useState('all')

  useEffect(() => { fetchEntries() }, [])

  async function fetchEntries() {
    setLoading(true)
    try {
      const data = await getEntries()
      // Sort newest first, only completed entries
      const complete = data
        .filter(e => e.clock_out)
        .sort((a, b) => new Date(b.date + 'T' + b.clock_in) - new Date(a.date + 'T' + a.clock_in))
      setEntries(complete)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(id) {
    if (!confirm('Delete this entry?')) return
    try {
      await deleteEntry(id)
      setEntries(prev => prev.filter(e => String(e.id) !== String(id)))
    } catch (e) {
      alert(e.message)
    }
  }

  // Get unique clients for filter
  const clients  = ['all', ...new Set(entries.map(e => e.client_name).filter(Boolean))]
  const filtered = filter === 'all' ? entries : entries.filter(e => e.client_name === filter)

  // Summary totals
  const totalHours    = filtered.reduce((sum, e) => sum + Number(e.hours_worked || 0), 0)
  const totalEarnings = filtered.reduce((sum, e) => sum + Number(e.hours_worked || 0) * Number(e.hourly_rate || 0), 0)

  function formatTime(t) {
    if (!t) return '—'
    const [h, m] = t.split(':')
    const hr = Number(h)
    return `${hr > 12 ? hr - 12 : hr || 12}:${m} ${hr >= 12 ? 'PM' : 'AM'}`
  }

  function formatDate(d) {
    if (!d) return ''
    const dt = new Date(d + 'T12:00:00')
    return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  return (
    <div>
      <div className="page-header">
        <div className="page-title">Time Log</div>
        <div className="page-subtitle">{entries.length} sessions recorded</div>
      </div>

      {/* Summary metrics */}
      <div className="metrics">
        <div className="metric">
          <div className="metric-label">Total Hours</div>
          <div className="metric-value accent">{totalHours.toFixed(1)}</div>
        </div>
        <div className="metric">
          <div className="metric-label">Total Earned</div>
          <div className="metric-value green">${totalEarnings.toFixed(2)}</div>
        </div>
      </div>

      {/* Client filter */}
      {clients.length > 2 && (
        <div style={{ padding: '0 16px', marginBottom: 12, display: 'flex', gap: 8, overflowX: 'auto' }}>
          {clients.map(c => (
            <button
              key={c}
              className={`btn btn-ghost btn-sm`}
              style={{ whiteSpace: 'nowrap', color: filter === c ? 'var(--accent)' : undefined, borderColor: filter === c ? 'var(--accent)' : undefined }}
              onClick={() => setFilter(c)}
            >
              {c === 'all' ? 'All clients' : c}
            </button>
          ))}
        </div>
      )}

      {/* Entry list */}
      {loading ? (
        <div className="empty-state">Loading...</div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">No entries yet.<br />Clock in to get started.</div>
      ) : (
        <div className="entry-list">
          {filtered.map(entry => {
            const earned = (Number(entry.hours_worked) * Number(entry.hourly_rate)).toFixed(2)
            return (
              <div key={entry.id} className="entry-row">
                <div className="entry-left">
                  <div className="entry-date">{formatDate(entry.date)}</div>
                  <div className="entry-client">{entry.client_name || 'Unknown'}</div>
                  <div className="entry-meta">
                    {formatTime(entry.clock_in)} → {formatTime(entry.clock_out)}
                    {' · '}{entry.num_children} {Number(entry.num_children) === 1 ? 'child' : 'children'}
                  </div>
                  {entry.notes && (
                    <div style={{ marginTop: 4 }}>
                      <span className="tag">{entry.notes}</span>
                    </div>
                  )}
                </div>
                <div className="entry-right">
                  <div className="entry-earnings">${earned}</div>
                  <div className="entry-hours">{Number(entry.hours_worked).toFixed(2)} hrs</div>
                  <button
                    className="btn btn-ghost btn-sm"
                    style={{ marginTop: 8, color: 'var(--red)', borderColor: 'var(--red)', fontSize: 11 }}
                    onClick={() => handleDelete(entry.id)}
                  >
                    Delete
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
