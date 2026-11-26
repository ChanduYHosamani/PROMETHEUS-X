import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ShieldAlert, UserPlus } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { ErrorBanner, SuccessBanner } from '../components/StatusStates'

export default function RegisterPage() {
  const { register, supabaseConfigured, loading } = useAuth()
  const navigate = useNavigate()

  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    try {
      const data = await register(email, password, fullName)
      if (data?.access_token) {
        navigate('/', { replace: true })
      } else {
        setSuccess('Registration submitted. Check your email to confirm your Supabase account.')
      }
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="max-w-md mx-auto mt-10 rounded-2xl border border-panelBorder bg-panel p-8 space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-white">Create Operator Account</h2>
        <p className="text-xs text-slate-400">Register with Supabase Authentication</p>
      </div>

      {!supabaseConfigured && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-950/30 p-3.5 flex items-start gap-2.5 text-xs text-amber-200">
          <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <span>
            Supabase Auth is not configured in frontend env (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`).
          </span>
        </div>
      )}

      <ErrorBanner title="Registration Error" message={error} />
      <SuccessBanner title="Account Created" message={success} />

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">Full Name</label>
          <input
            type="text"
            required
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Alex Rivera"
            className="w-full rounded-xl bg-obsidian border border-panelBorder px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-cyanpulse"
          />
        </div>
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
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Minimum 6 characters"
            className="w-full rounded-xl bg-obsidian border border-panelBorder px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-cyanpulse"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !supabaseConfigured}
          className="w-full py-2.5 rounded-xl bg-gradient-to-r from-electric to-cyanpulse hover:opacity-90 disabled:opacity-40 text-white text-sm font-semibold flex items-center justify-center gap-2 transition"
        >
          <UserPlus className="w-4 h-4" />
          <span>{loading ? 'Creating Account...' : 'Create Account'}</span>
        </button>
      </form>

      <p className="text-center text-xs text-slate-400">
        Already registered?{' '}
        <Link to="/login" className="text-cyanpulse hover:underline">
          Sign In
        </Link>
      </p>
    </div>
  )
}
