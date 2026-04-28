import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { signup, setToken } from '../api'

export default function SignupPage() {
  const [email,        setEmail]        = useState('')
  const [password,     setPassword]     = useState('')
  const [confirm,      setConfirm]      = useState('')
  const [businessName, setBusinessName] = useState('')
  const [payableTo,    setPayableTo]    = useState('')
  const [loading,      setLoading]      = useState(false)
  const [error,        setError]        = useState('')
  const navigate = useNavigate()

  async function handleSignup() {
    if (!email || !password || !confirm) { setError('Please fill in all fields'); return }
    if (password !== confirm)            { setError('Passwords do not match'); return }
    if (password.length < 8)             { setError('Password must be at least 8 characters'); return }

    setError('')
    setLoading(true)
    try {
      const data = await signup(email, password, businessName, payableTo)
      setToken(data.access_token)
      navigate('/')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
      <div style={{ width: '100%', maxWidth: 400 }}>
        <div style={{ marginBottom: 32, textAlign: 'center' }}>
          <div style={{ fontFamily: 'var(--font-head)', fontSize: '2rem', fontWeight: 800, letterSpacing: '-0.03em' }}>
            ⏱️ Time Tracker
          </div>
          <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 6 }}>
            Start your 14-day free trial
          </div>
        </div>

        <div className="card" style={{ margin: 0 }}>
          <div className="field">
            <label>Email</label>
            <input className="input" type="email" placeholder="you@example.com"
              value={email} onChange={e => setEmail(e.target.value)} />
          </div>
          <div className="field">
            <label>Password</label>
            <input className="input" type="password" placeholder="Min. 8 characters"
              value={password} onChange={e => setPassword(e.target.value)} />
          </div>
          <div className="field">
            <label>Confirm Password</label>
            <input className="input" type="password" placeholder="••••••••"
              value={confirm} onChange={e => setConfirm(e.target.value)} />
          </div>

          <div className="divider" />

          <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            Business Info (optional — can set later)
          </div>

          <div className="field">
            <label>Business Name</label>
            <input className="input" placeholder="e.g. Janelle's Care Services"
              value={businessName} onChange={e => setBusinessName(e.target.value)} />
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>Your Name (Payable To)</label>
            <input className="input" placeholder="e.g. Janelle Wilkinson"
              value={payableTo} onChange={e => setPayableTo(e.target.value)} />
          </div>

          {error && <div className="error-msg" style={{ marginTop: 10 }}>{error}</div>}
        </div>

        <div style={{ padding: '12px 0' }}>
          <button className="btn btn-primary" onClick={handleSignup} disabled={loading}>
            {loading ? 'Creating account...' : 'Create Account — Free Trial'}
          </button>
        </div>

        <div style={{ textAlign: 'center', fontSize: 13, color: 'var(--muted)' }}>
          Already have an account?{' '}
          <Link to="/login" style={{ color: 'var(--accent)', textDecoration: 'none' }}>
            Sign in
          </Link>
        </div>
      </div>
    </div>
  )
}
