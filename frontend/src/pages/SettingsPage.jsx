import { useState, useEffect } from 'react'
import { getRates, updateRates } from '../api'

export default function SettingsPage() {
  const [rates,   setRates]   = useState([])
  const [loading, setLoading] = useState(true)
  const [saving,  setSaving]  = useState(false)
  const [saved,   setSaved]   = useState(false)
  const [error,   setError]   = useState('')

  useEffect(() => {
    getRates().then(data => {
      setRates(data.sort((a, b) => a.num_children - b.num_children))
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  function updateRate(index, field, value) {
    setRates(prev => prev.map((r, i) => i === index ? { ...r, [field]: value } : r))
    setSaved(false)
  }

  function addRow() {
    const maxChildren = rates.length ? Math.max(...rates.map(r => r.num_children)) : 0
    setRates(prev => [...prev, { num_children: maxChildren + 1, hourly_rate: 0 }])
    setSaved(false)
  }

  function removeRow(index) {
    setRates(prev => prev.filter((_, i) => i !== index))
    setSaved(false)
  }

  async function handleSave() {
    setError('')
    setSaving(true)
    try {
      const payload = rates.map(r => ({
        num_children: Number(r.num_children),
        hourly_rate:  Number(r.hourly_rate),
      }))
      await updateRates(payload)
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <div className="page-title">Settings</div>
        <div className="page-subtitle">Hourly rates by child count</div>
      </div>

      <div className="card">
        <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 16, lineHeight: 1.6 }}>
          Set the hourly rate charged for each number of children in care.
          These rates are applied automatically when you clock in.
        </p>

        {loading ? (
          <div style={{ color: 'var(--muted)', fontSize: 13 }}>Loading...</div>
        ) : (
          <>
            {/* Header row */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 40px', gap: 8, marginBottom: 8 }}>
              <label style={{ margin: 0 }}># Children</label>
              <label style={{ margin: 0 }}>Rate / hr</label>
              <span />
            </div>

            {/* Rate rows */}
            {rates.map((r, i) => (
              <div key={i} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 40px', gap: 8, marginBottom: 8, alignItems: 'center' }}>
                <input
                  className="input"
                  type="number"
                  min="1"
                  value={r.num_children}
                  onChange={e => updateRate(i, 'num_children', e.target.value)}
                />
                <div style={{ position: 'relative' }}>
                  <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--muted)', fontSize: 14 }}>$</span>
                  <input
                    className="input"
                    type="number"
                    min="0"
                    step="0.01"
                    value={r.hourly_rate}
                    style={{ paddingLeft: 24 }}
                    onChange={e => updateRate(i, 'hourly_rate', e.target.value)}
                  />
                </div>
                <button
                  className="btn btn-ghost btn-sm"
                  style={{ color: 'var(--red)', borderColor: 'transparent', padding: '8px' }}
                  onClick={() => removeRow(i)}
                >
                  ✕
                </button>
              </div>
            ))}

            <button
              className="btn btn-ghost"
              style={{ marginTop: 4 }}
              onClick={addRow}
            >
              + Add rate tier
            </button>
          </>
        )}

        {error && <div className="error-msg" style={{ marginTop: 10 }}>{error}</div>}
      </div>

      <div style={{ padding: '0 16px' }}>
        <button className="btn btn-primary" onClick={handleSave} disabled={saving || loading}>
          {saving ? 'Saving...' : saved ? '✓ Saved!' : 'Save Rates'}
        </button>
      </div>

      <div style={{ margin: '24px 24px 0', padding: '20px', background: 'var(--surface)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
        <div style={{ fontFamily: 'var(--font-head)', fontWeight: 700, marginBottom: 6 }}>About</div>
        <div style={{ fontSize: 12, color: 'var(--muted)', lineHeight: 1.7 }}>
          Time Tracker for childcare.<br />
          Built with React + FastAPI.
        </div>
      </div>
    </div>
  )
}
