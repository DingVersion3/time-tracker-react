import { Routes, Route, useNavigate, useLocation, Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import ClockPage    from './pages/ClockPage'
import LogPage      from './pages/LogPage'
import InvoicePage  from './pages/InvoicePage'
import SettingsPage from './pages/SettingsPage'
import LoginPage          from './pages/LoginPage'
import SignupPage          from './pages/SignupPage'
import GoogleCallbackPage from './pages/GoogleCallbackPage'
import { getToken, clearToken } from './api'

const NAV = [
  { path: '/',         label: 'Clock',    icon: ClockIcon },
  { path: '/log',      label: 'Log',      icon: LogIcon },
  { path: '/invoice',  label: 'Invoice',  icon: InvoiceIcon },
  { path: '/settings', label: 'Settings', icon: SettingsIcon },
]

const AUTH_ROUTES = ['/login', '/signup', '/auth/google/callback']

function RequireAuth({ children }) {
  const token = getToken()
  if (!token) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  const navigate  = useNavigate()
  const location  = useLocation()
  const isAuthPage = AUTH_ROUTES.includes(location.pathname)

  function handleLogout() {
    clearToken()
    navigate('/login')
  }

  return (
    <div className="app">
      <Routes>
        <Route path="/login"  element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/auth/google/callback" element={<GoogleCallbackPage />} />
        <Route path="/"         element={<RequireAuth><ClockPage /></RequireAuth>} />
        <Route path="/log"      element={<RequireAuth><LogPage /></RequireAuth>} />
        <Route path="/invoice"  element={<RequireAuth><InvoicePage /></RequireAuth>} />
        <Route path="/settings" element={<RequireAuth><SettingsPage onLogout={handleLogout} /></RequireAuth>} />
      </Routes>

      {!isAuthPage && (
        <nav className="nav">
          {NAV.map(({ path, label, icon: Icon }) => (
            <button
              key={path}
              className={`nav-btn ${location.pathname === path ? 'active' : ''}`}
              onClick={() => navigate(path)}
            >
              <Icon />
              {label}
            </button>
          ))}
        </nav>
      )}
    </div>
  )
}

function ClockIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
    </svg>
  )
}

function LogIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/>
      <line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>
    </svg>
  )
}

function InvoiceIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
      <polyline points="10 9 9 9 8 9"/>
    </svg>
  )
}

function SettingsIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3"/>
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
    </svg>
  )
}
