import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Clock, Eye, Loader2, Trash2 } from 'lucide-react'
import { deleteInspection, fetchInspections } from '../api/client'
import { EmptyState, ErrorBanner, SeverityBadge } from '../components/StatusStates'
import ProtectedRoute from '../components/ProtectedRoute'

function HistoryContent() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deleting, setDeleting] = useState(null)

  const load = () => {
    setLoading(true)
    setError('')
    fetchInspections({ limit: 50 })
      .then((data) => { setItems(data?.items ?? []); setLoading(false) })
      .catch((err) => { setError(err?.response?.data?.detail || err.message); setLoading(false) })
  }

  useEffect(load, [])

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this inspection record?')) return
    setDeleting(id)
    try {
      await deleteInspection(id)
      setItems((prev) => prev.filter((r) => r.id !== id))
    } catch (err) {
      setError(err?.response?.data?.detail || 'Delete failed.')
    } finally {
      setDeleting(null)
    }
  }

  const getResult = (row) => {
    const r = row.inspection_results
    if (!r) return null
    return Array.isArray(r) ? r[0] : r
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Inspection History</h1>
        <p className="text-sm text-slate-400 mt-1">All persisted inspection records from Supabase.</p>
      </div>

      <ErrorBanner title="Failed to Load History" message={error} />

      {loading ? (
        <div className="flex items-center justify-center py-16 gap-3 text-slate-400">
          <Loader2 className="w-5 h-5 animate-spin text-cyanpulse" />
          <span className="text-sm">Loading inspection history…</span>
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          title="No Inspection Records"
          description="Run an image inspection. Records will appear here after they are persisted to Supabase."
          action={<Link to="/inspect" className="px-4 py-2 rounded-xl bg-electric text-white text-xs font-medium hover:bg-blue-500 transition">Start Inspection</Link>}
        />
      ) : (
        <div className="rounded-2xl border border-panelBorder bg-panel overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-panelBorder text-xs text-slate-400 uppercase tracking-wider">
                <th className="text-left px-5 py-3.5 font-medium">Date</th>
                <th className="text-left px-5 py-3.5 font-medium">Category</th>
                <th className="text-left px-5 py-3.5 font-medium hidden md:table-cell">Source</th>
                <th className="text-left px-5 py-3.5 font-medium">Verdict</th>
                <th className="text-left px-5 py-3.5 font-medium hidden sm:table-cell">Severity</th>
                <th className="text-right px-5 py-3.5 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-panelBorder/60">
              {items.map((row) => {
                const res = getResult(row)
                return (
                  <tr key={row.id} className="hover:bg-slate-800/30 transition">
                    <td className="px-5 py-3.5 text-xs text-slate-400">
                      <span className="flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5" />
                        {new Date(row.created_at).toLocaleDateString()}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 capitalize text-slate-200">{row.category_id?.replace('_', ' ')}</td>
                    <td className="px-5 py-3.5 capitalize text-slate-400 hidden md:table-cell">{row.source_type}</td>
                    <td className="px-5 py-3.5">
                      {res ? (
                        <span className={`text-xs font-semibold ${res.is_anomalous ? 'text-rose-400' : 'text-emerald-400'}`}>
                          {res.is_anomalous ? 'Anomalous' : 'Normal'}
                        </span>
                      ) : <span className="text-xs text-slate-500">—</span>}
                    </td>
                    <td className="px-5 py-3.5 hidden sm:table-cell">
                      <SeverityBadge severity={res?.severity} />
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <Link
                          to={`/history/${row.id}`}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-cyanpulse hover:bg-slate-800 transition"
                          title="View Details"
                        >
                          <Eye className="w-4 h-4" />
                        </Link>
                        <button
                          onClick={() => handleDelete(row.id)}
                          disabled={deleting === row.id}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition disabled:opacity-40"
                          title="Delete"
                        >
                          {deleting === row.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default function HistoryPage() {
  return <ProtectedRoute><HistoryContent /></ProtectedRoute>
}
