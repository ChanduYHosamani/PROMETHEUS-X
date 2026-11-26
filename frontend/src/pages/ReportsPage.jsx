import React, { useEffect, useState } from 'react'
import { Download, FileText, Loader2, Printer } from 'lucide-react'
import { fetchInspections } from '../api/client'
import { EmptyState, ErrorBanner, SeverityBadge } from '../components/StatusStates'
import ProtectedRoute from '../components/ProtectedRoute'

function formatDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleString('en-IN', { dateStyle: 'long', timeStyle: 'short' })
}

function ReportCard({ row }) {
  const res = row.inspection_results?.[0] || row.inspection_results

  const download = () => {
    const content = `PROMETHEUS-X INSPECTION REPORT
==============================
Generated: ${new Date().toLocaleString()}

INSPECTION DETAILS
------------------
ID:              ${row.id}
Date:            ${formatDate(row.created_at)}
Category:        ${(row.category_id || '').replace('_', ' ')}
Source:          ${row.source_type}
Status:          ${row.status}

AI DETECTION RESULT
-------------------
Verdict:         ${res ? (res.is_anomalous ? 'ANOMALY DETECTED' : 'NORMAL — No Defect') : 'No result recorded'}
Severity:        ${res?.severity || '—'}
Anomaly Score:   ${res?.anomaly_score?.toFixed(6) || '—'}
Confidence:      ${res?.calibrated_confidence ? (res.calibrated_confidence * 100).toFixed(2) + '%' : '—'}
Inference Time:  ${res?.inference_time_ms?.toFixed(1) || '—'} ms
Model Version:   resnet18-patchcore-v1

STORAGE
-------
Image:    ${row.image_storage_path || 'Not persisted'}
Heatmap:  ${res?.heatmap_storage_path || 'Not persisted'}

NOTE: This report was generated from stored Supabase records.
AI results are produced by the ResNet18 + PatchCore anomaly detection engine.
No predictions in this report were fabricated or simulated.
`
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `prometheus-x-report-${row.id.slice(0, 8)}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="rounded-2xl border border-panelBorder bg-panel p-5 space-y-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="space-y-1">
          <p className="text-sm font-semibold text-slate-100 capitalize">{(row.category_id || '').replace('_', ' ')} Inspection</p>
          <p className="text-xs text-slate-400">{formatDate(row.created_at)}</p>
          <p className="text-xs font-mono text-slate-500">{row.id}</p>
        </div>
        <div className="flex items-center gap-2">
          {res && <SeverityBadge severity={res.severity} />}
          {res && (
            <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${res.is_anomalous ? 'border-rose-500/30 bg-rose-900/20 text-rose-300' : 'border-emerald-500/30 bg-emerald-900/20 text-emerald-300'}`}>
              {res.is_anomalous ? 'Anomalous' : 'Normal'}
            </span>
          )}
        </div>
      </div>

      {res && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          <div className="bg-obsidian/60 rounded-xl p-2.5 border border-panelBorder">
            <p className="text-slate-400">Score</p>
            <p className="font-mono text-slate-200 mt-0.5">{res.anomaly_score?.toFixed(6)}</p>
          </div>
          <div className="bg-obsidian/60 rounded-xl p-2.5 border border-panelBorder">
            <p className="text-slate-400">Confidence</p>
            <p className="text-slate-200 mt-0.5">{(res.calibrated_confidence * 100).toFixed(1)}%</p>
          </div>
          <div className="bg-obsidian/60 rounded-xl p-2.5 border border-panelBorder">
            <p className="text-slate-400">Latency</p>
            <p className="text-slate-200 mt-0.5">{res.inference_time_ms?.toFixed(1)} ms</p>
          </div>
          <div className="bg-obsidian/60 rounded-xl p-2.5 border border-panelBorder">
            <p className="text-slate-400">Model</p>
            <p className="text-slate-200 mt-0.5 truncate">resnet18-v1</p>
          </div>
        </div>
      )}

      <div className="flex items-center gap-2 pt-1">
        <button
          onClick={download}
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-electric/15 border border-electric/30 text-cyanpulse text-xs font-medium hover:bg-electric/25 transition"
        >
          <Download className="w-3.5 h-3.5" /> Download Report (.txt)
        </button>
        <button
          onClick={() => window.print()}
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800 border border-panelBorder text-slate-300 text-xs hover:bg-slate-700 transition"
        >
          <Printer className="w-3.5 h-3.5" /> Print
        </button>
      </div>
    </div>
  )
}

function ReportsContent() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchInspections({ limit: 50 })
      .then((data) => { setItems(data?.items ?? []); setLoading(false) })
      .catch((err) => { setError(err?.response?.data?.detail || err.message || 'Failed to load reports.'); setLoading(false) })
  }, [])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Inspection Reports</h1>
        <p className="text-sm text-slate-400 mt-1">Download text-format inspection reports containing real AI detection results from your stored inspections.</p>
      </div>

      <ErrorBanner title="Failed to Load Reports" message={error} />

      {loading ? (
        <div className="flex items-center justify-center py-16 gap-3 text-slate-400">
          <Loader2 className="w-5 h-5 animate-spin text-cyanpulse" />
          <span className="text-sm">Loading reports…</span>
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          title="No Inspection Records"
          description="Complete an inspection to generate a downloadable report. Reports are generated from real stored Supabase records."
        />
      ) : (
        <div className="space-y-4">
          {items.map((row) => <ReportCard key={row.id} row={row} />)}
        </div>
      )}
    </div>
  )
}

export default function ReportsPage() {
  return <ProtectedRoute><ReportsContent /></ProtectedRoute>
}
