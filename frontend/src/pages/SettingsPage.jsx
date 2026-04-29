import { useState, useEffect } from 'react'
import { getRates, updateRates, getMe, updateProfile } from '../api'

const BASE_URL = import.meta.env.VITE_API_URL || "/api"

export default function SettingsPage({ onLogout }) {
  const [rates,         setRates]         = useState([])
  const [user,          setUser]          = useState(null)
  const [loading,       setLoading]       = useState(true)
  const [saving,        setSaving]        = useState(false)
  const [savingProfile, setSavingProfile] = useState(false)
  const [saved,         setSaved]         = useState(false)
  const [savedProfile,  setSavedProfile]  = useState(false)
  const [error,         setError]         = useState('')

  const [businessName,    setBusinessName]    = useState('')
  const [businessAddress, setBusinessAddress] = useState('')
  const [businessPhone,   setBusinessPhone]   = useState('')
  const [payableTo,       setPayableTo]       = useState('')

  useEffect(() => {
    Promise.all([getRates(), getMe()]).then(([r, u]) => {
      setRates(r.sort((a, b) => a.num_children - b.num_children))
      setUser(u)
      setBusinessName(u.business_name || '')
      setBusinessAddress(u.business_address || '')
      setBusinessPhone(u.business_phone || '')
      setPayableTo(u.payable_to || '')
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  function updateRate(index, field, value) {
    setRates(prev => prev.map((r, i) => i === index ? { ...r, [field]: value } : r))
    setSaved(false)
  }

  function addRow() {
    const max = rates.length ? Math.max(...rates.map(r => r.num_children)) : 0
    setRates(prev => [...prev, { num_children: max + 1, hourly_rate: 0 }])
  }

  function removeRow(index) {
    setRates(prev => prev.filter((_, i) => i !== index))
  }

  async function handleSaveRates() {
    setError('')
    setSaving(true)
    try {
      await updateRates(rates.map(r => ({ num_children: Number(r.num_children), hourly_rate: Number(r.hourly_rate) })))
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleSaveProfile() {
    setError('')
    setSavingProfile(true)
    try {
      await updateProfile({ business_name: businessName, business_address: businessAddress, business_phone: businessPhone, payable_to: payableTo })
      setSavedProfile(true)
      setTimeout(() => setSavedProfile(false), 2500)
    } catch (e) {
      setError(e.message)
    } finally {
      setSavingProfile(false)
    }
  }

  async function handleConnectGoogle() {
    const token = localStorage.getItem('token')
    const res   = await fetch(`${BASE_URL}/auth/google`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    const data = await res.json()
    window.location.href = data.url
  }

  async function handleDisconnectGoogle() {
    const token = localStorage.getItem('token')
    await fetch(`${BASE_URL}/auth/google/disconnect`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    })
    setUser(prev => ({ ...prev, google_connected: 'false' }))
  }

  const trialDays = user?.trial_ends_at
    ? Math.max(0, Math.ceil((new Date(user.trial_ends_at) - new Date()) / (1000 * 60 * 60 * 24)))
    : null

  const googleConnected = user?.google_connected === 'true'

  return (
    <div>
      <div className="page-header">
        <div className="page-title">Settings</div>
        <div className="page-subtitle">{user?.email}</div>
      </div>

      {/* Trial banner */}
      {user?.subscription_status === 'trialing' && trialDays !== null && (
        <div style={{ margin: '0 16px 12px', padding: '12px 16px', background: 'rgba(232,255,71,0.08)', border: '1px solid rgba(232,255,71,0.2)', borderRadius: 12, fontSize: 13 }}>
          ⏳ <strong>{trialDays} days</strong> left in your free trial
        </div>
      )}

      {/* Google Account */}
      <div className="section-label" style={{ marginTop: 8 }}>Google Account</div>
      <div className="card">
        <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 14, lineHeight: 1.6 }}>
          Connect your Google account to generate invoices directly in your Google Drive.
        </p>
        {googleConnected ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--green)', fontSize: 13 }}>✓ Google account connected</span>
            <button className="btn btn-ghost btn-sm" style={{ color: 'var(--red)' }} onClick={handleDisconnectGoogle}>
              Disconnect
            </button>
          </div>
        ) : (
          <button className="btn btn-primary" onClick={handleConnectGoogle}>
            🔗 Connect Google Account
          </button>
        )}
      </div>

      {/* Business Profile */}
      <div className="section-label">Business Profile</div>
      <div className="card">
        <div className="field">
          <label>Business Name</label>
          <input className="input" value={businessName} onChange={e => setBusinessName(e.target.value)} placeholder="e.g. Janelle's Care Services" />
        </div>
        <div className="field">
          <label>Address</label>
          <input className="input" value={businessAddress} onChange={e => setBusinessAddress(e.target.value)} placeholder="e.g. 325 E Oak View Ave A" />
        </div>
        <div className="field">
          <label>Phone</label>
          <input className="input" value={businessPhone} onChange={e => setBusinessPhone(e.target.value)} placeholder="e.g. (805) 258-9423" />
        </div>
        <div className="field" style={{ marginBottom: 0 }}>
          <label>Payable To</label>
          <input className="input" value={payableTo} onChange={e => setPayableTo(e.target.value)} placeholder="e.g. Janelle Wilkinson" />
        </div>
      </div>

      {error && <div className="error-msg" style={{ padding: '0 24px' }}>{error}</div>}

      <div style={{ padding: '0 16px' }}>
        <button className="btn btn-primary" onClick={handleSaveProfile} disabled={savingProfile}>
          {savingProfile ? 'Saving...' : savedProfile ? '✓ Saved!' : 'Save Profile'}
        </button>
      </div>

      {/* Rates */}
      <div className="section-label" style={{ marginTop: 20 }}>Hourly Rates</div>
      <div className="card">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 40px', gap: 8, marginBottom: 8 }}>
          <label style={{ margin: 0 }}># Children</label>
          <label style={{ margin: 0 }}>Rate / hr</label>
          <span />
        </div>
        {loading ? (
          <div style={{ color: 'var(--muted)', fontSize: 13 }}>Loading...</div>
        ) : rates.map((r, i) => (
          <div key={i} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 40px', gap: 8, marginBottom: 8, alignItems: 'center' }}>
            <input className="input" type="number" min="1" value={r.num_children} onChange={e => updateRate(i, 'num_children', e.target.value)} />
            <div style={{ position: 'relative' }}>
              <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--muted)', fontSize: 14 }}>$</span>
              <input className="input" type="number" min="0" step="0.01" value={r.hourly_rate} style={{ paddingLeft: 24 }} onChange={e => updateRate(i, 'hourly_rate', e.target.value)} />
            </div>
            <button className="btn btn-ghost btn-sm" style={{ color: 'var(--red)', borderColor: 'transparent' }} onClick={() => removeRow(i)}>✕</button>
          </div>
        ))}
        <button className="btn btn-ghost" style={{ marginTop: 4 }} onClick={addRow}>+ Add rate tier</button>
      </div>

      <div style={{ padding: '0 16px' }}>
        <button className="btn btn-primary" onClick={handleSaveRates} disabled={saving || loading}>
          {saving ? 'Saving...' : saved ? '✓ Saved!' : 'Save Rates'}
        </button>
      </div>

      {/* Logout */}
      <div style={{ padding: '20px 16px 0' }}>
        <button className="btn btn-ghost" onClick={onLogout}>Sign Out</button>
      </div>
    </div>
  )
}
