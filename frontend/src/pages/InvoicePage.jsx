import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getEntries, getInvoice, getMe, generateInvoice } from '../api'


export default function InvoicePage() {
  const [clients,         setClients]         = useState([])
  const [client,          setClient]          = useState('')
  const [startDate,       setStartDate]       = useState('')
  const [endDate,         setEndDate]         = useState('')
  const [invoice,         setInvoice]         = useState(null)
  const [loading,         setLoading]         = useState(false)
  const [generating,      setGenerating]      = useState(false)
  const [sheetUrl,        setSheetUrl]        = useState('')
  const [error,           setError]           = useState('')
  const [googleConnected, setGoogleConnected] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    getMe().then(u => setGoogleConnected(u.google_connected === 'true')).catch(() => {})
    getEntries().then(data => {
      const completed = data.filter(e => e.clock_out)
      const unique    = [...new Set(completed.map(e => e.client_name).filter(Boolean))]
      setClients(unique)
      if (unique.length) setClient(unique[0])

      const now   = new Date()
      const first = new Date(now.getFullYear(), now.getMonth(), 1)
      setStartDate(first.toISOString().split('T')[0])
      setEndDate(now.toISOString().split('T')[0])
    }).catch(() => {})
  }, [])

  async function handlePreview() {
    if (!client || !startDate || !endDate) { setError('Fill in all fields'); return }
    setError('')
    setSheetUrl('')
    setLoading(true)
    try {
      const data = await getInvoice(client, startDate, endDate)
      setInvoice(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleGenerate() {
    setError('')
    setGenerating(true)
    try {
      const data = await generateInvoice(client, startDate, endDate, 14)
      setSheetUrl(data.url)
    } catch (e) {
      setError(e.message)
    } finally {
      setGenerating(false)
    }
  }

  function handleDownloadCSV() {
    if (!invoice) return
    const headers = ['Date','Clock In','Clock Out','Children','Rate','Hours','Amount','Notes']
    const rows = invoice.entries.map(e => [
      e.date, e.clock_in, e.clock_out, e.num_children,
      e.hourly_rate, Number(e.hours_worked).toFixed(2),
      (Number(e.hours_worked) * Number(e.hourly_rate)).toFixed(2),
      e.notes || ''
    ])
    const csv  = [headers, ...rows].map(r => r.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = `invoice_${client.replace(/\s+/g,'_')}_${startDate}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  function formatDate(d) {
    if (!d) return ''
    return new Date(d + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  function formatTime(t) {
    if (!t) return '—'
    const [h, m] = t.split(':')
    const hr = Number(h)
    return `${hr > 12 ? hr - 12 : hr || 12}:${m}${hr >= 12 ? 'pm' : 'am'}`
  }

  return (
    <div>
      <div className="page-header">
        <div className="page-title">Invoice</div>
        <div className="page-subtitle">Generate by client & period</div>
      </div>

      <div className="card">
        {clients.length === 0 ? (
          <div style={{ color: 'var(--muted)', fontSize: 13 }}>No completed sessions yet.</div>
        ) : (
          <>
            <div className="field">
              <label>Client</label>
              <select className="select" value={client} onChange={e => { setClient(e.target.value); setInvoice(null); setSheetUrl('') }}>
                {clients.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <div className="field" style={{ marginBottom: 0 }}>
                <label>From</label>
                <input type="date" className="input" value={startDate} onChange={e => { setStartDate(e.target.value); setInvoice(null); setSheetUrl('') }} />
              </div>
              <div className="field" style={{ marginBottom: 0 }}>
                <label>To</label>
                <input type="date" className="input" value={endDate} onChange={e => { setEndDate(e.target.value); setInvoice(null); setSheetUrl('') }} />
              </div>
            </div>

            {error && <div className="error-msg" style={{ marginTop: 10 }}>{error}</div>}
          </>
        )}
      </div>

      {clients.length > 0 && (
        <div style={{ padding: '0 16px' }}>
          <button className="btn btn-primary" onClick={handlePreview} disabled={loading}>
            {loading ? 'Loading...' : 'Preview Invoice'}
          </button>
        </div>
      )}

      {invoice && invoice.entries.length > 0 && (
        <>
          {/* Summary */}
          <div style={{ padding: '20px 24px 0' }}>
            <div style={{ fontFamily: 'var(--font-head)', fontSize: '1.1rem', fontWeight: 700, marginBottom: 4 }}>
              {invoice.client_name}
            </div>
            <div style={{ color: 'var(--muted)', fontSize: 12 }}>
              {formatDate(invoice.start_date)} — {formatDate(invoice.end_date)}
            </div>
          </div>

          <div className="metrics" style={{ marginTop: 12 }}>
            <div className="metric">
              <div className="metric-label">Total Hours</div>
              <div className="metric-value accent">{invoice.total_hours}</div>
            </div>
            <div className="metric">
              <div className="metric-label">Amount Due</div>
              <div className="metric-value green">${invoice.total_earnings.toFixed(2)}</div>
            </div>
          </div>

          {/* Line items */}
          <div className="section-label">Sessions</div>
          <div className="entry-list">
            {invoice.entries.map(e => {
              const amt = (Number(e.hours_worked) * Number(e.hourly_rate)).toFixed(2)
              return (
                <div key={e.id} className="entry-row">
                  <div className="entry-left">
                    <div className="entry-date">{formatDate(e.date)}</div>
                    <div className="entry-meta">
                      {formatTime(e.clock_in)} → {formatTime(e.clock_out)}
                      {' · '}{e.num_children} {Number(e.num_children) === 1 ? 'child' : 'children'} @ ${e.hourly_rate}/hr
                    </div>
                    {e.notes && <span className="tag" style={{ marginTop: 4 }}>{e.notes}</span>}
                  </div>
                  <div className="entry-right">
                    <div className="entry-earnings">${amt}</div>
                    <div className="entry-hours">{Number(e.hours_worked).toFixed(2)} hrs</div>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Actions */}
          <div style={{ padding: '8px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>

            {/* Generate to Google Sheets */}
            {sheetUrl ? (
              <a
                href={sheetUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-primary"
                style={{ textDecoration: 'none', textAlign: 'center' }}
              >
                📄 Open Invoice in Google Sheets ↗
              </a>
            ) : (
              <button className="btn btn-primary" onClick={handleGenerate} disabled={generating}>
                {generating ? 'Generating...' : '📄 Generate Google Sheets Invoice'}
              </button>
            )}

            <button className="btn btn-ghost" onClick={handleDownloadCSV}>
              ⬇ Download CSV
            </button>
          </div>
        </>
      )}

      {invoice && invoice.entries.length === 0 && (
        <div className="empty-state">No sessions found for this period.</div>
      )}
    </div>
  )
}
