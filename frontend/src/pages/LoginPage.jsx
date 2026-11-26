import React, { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { LogIn, ShieldAlert, ShieldCheck } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { ErrorBanner } from '../components/StatusStates'

export default function LoginPage() {
  const { login, supabaseConfigured, loading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const redirectTo = location.state?.from || '/'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await login(email, password)
      navigate(redirectTo, { replace: true })
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="max-w-md mx-auto mt-10 rounded-2xl border border-panelBorder bg-panel p-8 space-y-6">
      <div className="text-center space-y-2">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-electric to-cyanpulse flex items-center justify-center mx-auto">
          <ShieldCheck className="w-6 h-6 text-white" />
        </div>
        <h2 className="text-2xl font-bold text-white">Operator Sign In</h2>
        <p className="text-xs text-slate-400">PROMETHEUS-X Industrial Inspection Console</p>
      </div>

      {!supabaseConfigured && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-950/30 p-3.5 flex items-start gap-2.5 text-xs text-amber-200">
          <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <span>
            Supabase Auth is not configured in frontend env (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`). Public inspection &amp; readiness views remain accessible.
          </span>
        </div>
      )}

      <ErrorBanner title="Sign In Error" message={error} />

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="operator@factory.io"
            className="w-full rounded-xl bg-obsidian border border-panelBorder px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-cyanpulse"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">Password</label>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            className="w-full rounded-xl bg-obsidian border border-panelBorder px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-cyanpulse"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !supabaseConfigured}
          className="w-full py-2.5 rounded-xl bg-gradient-to-r from-electric to-cyanpulse hover:opacity-90 disabled:opacity-40 text-white text-sm font-semibold flex items-center justify-center gap-2 transition"
        >
          <LogIn className="w-4 h-4" />
          <span>{loading ? 'Signing In...' : 'Sign In'}</span>
        </button>
      </form>

      <p className="text-center text-xs text-slate-400">
        Need an operator account?{' '}
        <Link to="/register" className="text-cyanpulse hover:underline">
          Register
        </Link>
      </p>
    </div>
  )
}
