import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { getToken } from '../api'

const BASE_URL = import.meta.env.VITE_API_URL || "/api"

export default function GoogleCallbackPage() {
  const [status, setStatus]         = useState('Connecting your Google account...')
  const [error,  setError]          = useState('')
  const [params]                    = useSearchParams()
  const navigate                    = useNavigate()

  useEffect(() => {
    const code    = params.get('code')
    const state   = params.get('state')   // user_id passed via state param
    const token   = getToken()

    if (!code || !token) {
      setError('Missing authorization code. Please try again.')
      return
    }

    fetch(`${BASE_URL}/auth/google/callback`, {
      method:  'POST',
      headers: {
        'Content-Type':  'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ code, user_id: state }),
    })
      .then(res => {
        if (!res.ok) return res.json().then(e => { throw new Error(e.detail) })
        return res.json()
      })
      .then(() => {
        setStatus('Google account connected! Redirecting...')
        setTimeout(() => navigate('/settings'), 1500)
      })
      .catch(e => {
        setError(e.message || 'Failed to connect Google account')
      })
  }, [])

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
      <div style={{ textAlign: 'center', maxWidth: 400 }}>
        {error ? (
          <>
            <div style={{ fontSize: '2rem', marginBottom: 16 }}>❌</div>
            <div style={{ fontFamily: 'var(--font-head)', fontSize: '1.2rem', fontWeight: 700, marginBottom: 8 }}>Connection Failed</div>
            <div style={{ color: 'var(--red)', fontSize: 13, marginBottom: 20 }}>{error}</div>
            <button className="btn btn-ghost" onClick={() => navigate('/settings')}>
              Back to Settings
            </button>
          </>
        ) : (
          <>
            <div style={{ fontSize: '2rem', marginBottom: 16 }}>🔗</div>
            <div style={{ fontFamily: 'var(--font-head)', fontSize: '1.2rem', fontWeight: 700, marginBottom: 8 }}>
              {status}
            </div>
            <div style={{ color: 'var(--muted)', fontSize: 13 }}>Please wait...</div>
          </>
        )}
      </div>
    </div>
  )
}
