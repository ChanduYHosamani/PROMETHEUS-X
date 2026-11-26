import React, { useEffect, useState } from 'react'
import { BarChart3, TrendingUp, Zap } from 'lucide-react'
import { fetchAnalyticsOverview, fetchDistributionShift } from '../api/client'
import { LoadingSpinner, SeverityBadge } from '../components/StatusStates'
import ProtectedRoute from '../components/ProtectedRoute'

function SimpleBarChart({ data, label }) {
  if (!data || Object.keys(data).length === 0) return null
  const max = Math.max(...Object.values(data), 1)
  return (
    <div className="space-y-2">
      {Object.entries(data).map(([key, val]) => (
        <div key={key} className="flex items-center gap-3 text-xs">
          <span className="text-slate-400 w-28 truncate capitalize">{key.replace('_', ' ')}</span>
          <div className="flex-1 h-2 rounded-full bg-slate-800">
            <div
              className="h-2 rounded-full bg-gradient-to-r from-electric to-cyanpulse"
              style={{ width: `${(val / max) * 100}%` }}
            />
          </div>
          <span className="text-slate-300 w-6 text-right">{val}</span>
        </div>
      ))}
    </div>
  )
}

function AnalyticsContent() {
  const [overview, setOverview] = useState(null)
  const [shift, setShift] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.allSettled([
      fetchAnalyticsOverview().then(setOverview),
      fetchDistributionShift().then(setShift),
    ]).finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Analytics</h1>
        <p className="text-sm text-slate-400 mt-1">Inspection statistics and distribution-shift monitoring computed from real stored records.</p>
      </div>

      {loading ? <LoadingSpinner label="Loading analytics..." /> : (
        <div className="space-y-5">
          {/* Overview */}
          <div className="rounded-2xl border border-panelBorder bg-panel p-5 space-y-4">
            <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2"><BarChart3 className="w-4 h-4 text-cyanpulse" /> Inspection Overview</h2>
            {overview?.status === 'ok' ? (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div className="rounded-xl bg-obsidian/60 p-3 border border-panelBorder text-center">
                    <p className="text-xs text-slate-400 mb-1">Total</p>
                    <p className="text-2xl font-bold text-white">{overview.data.total_inspections}</p>
                  </div>
                  <div className="rounded-xl bg-obsidian/60 p-3 border border-panelBorder text-center">
                    <p className="text-xs text-slate-400 mb-1">Anomalous</p>
                    <p className="text-2xl font-bold text-rose-400">{overview.data.anomalous_count}</p>
                  </div>
                  <div className="rounded-xl bg-obsidian/60 p-3 border border-panelBorder text-center">
                    <p className="text-xs text-slate-400 mb-1">Normal</p>
                    <p className="text-2xl font-bold text-emerald-400">{overview.data.normal_count}</p>
                  </div>
                  <div className="rounded-xl bg-obsidian/60 p-3 border border-panelBorder text-center">
                    <p className="text-xs text-slate-400 mb-1">Anomaly Rate</p>
                    <p className="text-2xl font-bold text-cyanpulse">{(overview.data.anomaly_rate * 100).toFixed(1)}%</p>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-2">
                  <div>
                    <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">By Severity</h3>
                    <SimpleBarChart data={overview.data.by_severity} />
                  </div>
                  <div>
                    <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">By Category</h3>
                    <SimpleBarChart data={overview.data.by_category} />
                  </div>
                </div>
              </>
            ) : (
              <div className="text-center py-8 space-y-2">
                <Zap className="w-7 h-7 text-slate-600 mx-auto" />
                <p className="text-sm text-slate-400">{overview?.message || 'No overview data available.'}</p>
              </div>
            )}
          </div>

          {/* Distribution Shift */}
          <div className="rounded-2xl border border-panelBorder bg-panel p-5 space-y-4">
            <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2"><TrendingUp className="w-4 h-4 text-cyanpulse" /> Distribution Shift Monitoring</h2>
            {shift?.status === 'ok' ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="border-b border-panelBorder text-slate-400">
                      <th className="pb-2 font-medium">Category</th>
                      <th className="pb-2 font-medium text-right">Count</th>
                      <th className="pb-2 font-medium text-right">Mean Score</th>
                      <th className="pb-2 font-medium text-right">Max Score</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-panelBorder/60">
                    {Object.entries(shift.data.categories || {}).map(([cat, stats]) => (
                      <tr key={cat} className="text-slate-300">
                        <td className="py-2 capitalize">{cat.replace('_', ' ')}</td>
                        <td className="py-2 text-right">{stats.count}</td>
                        <td className="py-2 text-right font-mono">{stats.mean_anomaly_score?.toFixed(4)}</td>
                        <td className="py-2 text-right font-mono">{stats.max_anomaly_score?.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-8 space-y-2">
                <TrendingUp className="w-7 h-7 text-slate-600 mx-auto" />
                <p className="text-sm text-slate-400">{shift?.message || 'Insufficient data for distribution-shift monitoring.'}</p>
                <p className="text-xs text-slate-500">At least 5 completed inspections are required.</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default function AnalyticsPage() {
  return <ProtectedRoute><AnalyticsContent /></ProtectedRoute>
}
