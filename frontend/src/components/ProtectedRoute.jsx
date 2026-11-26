import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Lock } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, supabaseConfigured } = useAuth()
  const location = useLocation()

  if (isAuthenticated) {
    return children
  }

  return (
    <div className="max-w-xl mx-auto mt-12 rounded-2xl border border-panelBorder bg-panel p-8 text-center space-y-4">
      <div className="w-12 h-12 rounded-full bg-electric/15 border border-electric/30 text-cyanpulse flex items-center justify-center mx-auto">
        <Lock className="w-6 h-6" />
      </div>
      <h2 className="text-xl font-semibold text-slate-100">Authentication Required</h2>
      <p className="text-sm text-slate-400">
        {supabaseConfigured
          ? 'Sign in with your Supabase operator account to access private inspection records, reviews, analytics, and reports.'
          : 'This section is protected by Supabase Authentication. Configure VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in your frontend .env to enable sign-in.'}
      </p>
      <div className="flex items-center justify-center gap-3 pt-2">
        <Link
          to="/login"
          state={{ from: location.pathname }}
          className="px-4 py-2 rounded-lg bg-electric hover:bg-blue-500 text-white text-sm font-medium transition"
        >
          Go to Sign In
        </Link>
        <Link
          to="/"
          className="px-4 py-2 rounded-lg border border-slate-700 hover:bg-slate-800 text-slate-300 text-sm transition"
        >
          Back to Dashboard
        </Link>
      </div>
    </div>
  )
}
