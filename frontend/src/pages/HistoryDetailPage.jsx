import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { fetchInspectionById } from '../api/client'
import { LoadingSpinner, ErrorBanner, SeverityBadge } from '../components/StatusStates'
import ProtectedRoute from '../components/ProtectedRoute'

function DetailContent() {
  const { id } = useParams()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchInspectionById(id)
      .then((d) => { setData(d); setLoading(false) })
      .catch((err) => { setError(err?.response?.data?.detail || err.message); setLoading(false) })
  }, [id])

  if (loading) return <LoadingSpinner label="Loading inspection detail..." />
  if (error) return <ErrorBanner title="Failed to Load" message={error} />

  const res = data?.inspection_results?.[0] || data?.inspection_results

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <Link to="/history" className="flex items-center gap-2 text-sm text-slate-400 hover:text-cyanpulse transition">
        <ArrowLeft className="w-4 h-4" /> Back to History
      </Link>
      <div className="rounded-2xl border border-panelBorder bg-panel p-6 space-y-4">
        <h1 className="text-xl font-bold text-white">Inspection Detail</h1>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div><p className="text-slate-400 text-xs">ID</p><p className="text-slate-200 font-mono text-xs mt-0.5">{data?.id}</p></div>
          <div><p className="text-slate-400 text-xs">Category</p><p className="text-slate-200 capitalize mt-0.5">{data?.category_id?.replace('_', ' ')}</p></div>
          <div><p className="text-slate-400 text-xs">Date</p><p className="text-slate-200 mt-0.5">{data?.created_at ? new Date(data.created_at).toLocaleString() : '—'}</p></div>
          <div><p className="text-slate-400 text-xs">Source</p><p className="text-slate-200 capitalize mt-0.5">{data?.source_type}</p></div>
          {res && <>
            <div><p className="text-slate-400 text-xs">Verdict</p><p className={`font-semibold mt-0.5 ${res.is_anomalous ? 'text-rose-400' : 'text-emerald-400'}`}>{res.is_anomalous ? 'Anomalous' : 'Normal'}</p></div>
            <div><p className="text-slate-400 text-xs">Severity</p><div className="mt-0.5"><SeverityBadge severity={res.severity} /></div></div>
            <div><p className="text-slate-400 text-xs">Anomaly Score</p><p className="text-slate-200 font-mono mt-0.5">{res.anomaly_score?.toFixed(6)}</p></div>
            <div><p className="text-slate-400 text-xs">Confidence</p><p className="text-slate-200 mt-0.5">{(res.calibrated_confidence * 100).toFixed(1)}%</p></div>
            <div><p className="text-slate-400 text-xs">Inference Time</p><p className="text-slate-200 mt-0.5">{res.inference_time_ms?.toFixed(1)} ms</p></div>
          </>}
        </div>
        {res?.heatmap_storage_path && (
          <p className="text-xs text-slate-500">Heatmap: <span className="text-slate-300 font-mono">{res.heatmap_storage_path}</span></p>
        )}
      </div>
    </div>
  )
}

export default function HistoryDetailPage() {
  return <ProtectedRoute><DetailContent /></ProtectedRoute>
}
