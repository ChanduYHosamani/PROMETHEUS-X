import React from 'react'
import { AlertTriangle, CheckCircle2, Inbox, Loader2 } from 'lucide-react'

export function LoadingSpinner({ label = 'Loading...' }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-slate-400 gap-3">
      <Loader2 className="w-7 h-7 text-cyanpulse animate-spin" />
      <span className="text-sm">{label}</span>
    </div>
  )
}

export function ErrorBanner({ title = 'Action Failed', message }) {
  if (!message) return null
  return (
    <div className="rounded-xl border border-rose-500/40 bg-rose-950/30 p-4 flex items-start gap-3 text-rose-200">
      <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
      <div className="text-sm">
        <p className="font-semibold text-rose-100">{title}</p>
        <p className="text-rose-200/90 mt-0.5">{message}</p>
      </div>
    </div>
  )
}

export function SuccessBanner({ title = 'Success', message }) {
  if (!message) return null
  return (
    <div className="rounded-xl border border-emerald-500/40 bg-emerald-950/30 p-4 flex items-start gap-3 text-emerald-200">
      <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
      <div className="text-sm">
        <p className="font-semibold text-emerald-100">{title}</p>
        <p className="text-emerald-200/90 mt-0.5">{message}</p>
      </div>
    </div>
  )
}

export function EmptyState({ title, description, action }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-700 bg-panel/40 p-10 text-center flex flex-col items-center gap-3">
      <div className="p-3 rounded-full bg-slate-800/80 text-slate-400">
        <Inbox className="w-6 h-6" />
      </div>
      <div>
        <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
        <p className="text-xs text-slate-400 mt-1 max-w-md">{description}</p>
      </div>
      {action}
    </div>
  )
}

const SEVERITY_STYLES = {
  low: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30',
  medium: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  high: 'bg-orange-500/15 text-orange-300 border-orange-500/30',
  critical: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
}

export function SeverityBadge({ severity }) {
  if (!severity) return <span className="text-xs text-slate-500">—</span>
  const cls = SEVERITY_STYLES[severity] || 'bg-slate-800 text-slate-300 border-slate-700'
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border uppercase tracking-wide ${cls}`}>
      {severity}
    </span>
  )
}
