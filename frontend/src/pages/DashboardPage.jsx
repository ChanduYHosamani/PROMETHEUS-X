import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Activity, AlertTriangle, BarChart3, CheckCircle2, Cpu,
  Database, Server, ShieldCheck, TrendingUp, Upload, Zap
} from 'lucide-react'
import { fetchAnalyticsOverview, fetchCategories, fetchHealth, fetchModelStatus } from '../api/client'
import { LoadingSpinner, SeverityBadge } from '../components/StatusStates'
import { useAuth } from '../context/AuthContext'

function StatCard({ label, value, sub, icon: Icon, colorClass = 'text-cyanpulse', loading }) {
  return (
    <div className="rounded-2xl border border-panelBorder bg-panel p-5 flex items-center gap-4">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center bg-slate-800/80 ${colorClass}`}>
        <Icon className="w-6 h-6" />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-slate-400 font-medium">{label}</p>
        {loading
          ? <div className="mt-1 h-6 w-16 rounded bg-slate-700 animate-pulse" />
          : <p className="text-2xl font-bold text-white">{value ?? '—'}</p>
        }
        {sub && <p className="text-xs text-slate-500 mt-0.5 truncate">{sub}</p>}
      </div>
    </div>
  )
}

function CategoryBankGrid({ categories }) {
  if (!categories?.length) return null
  return (
    <div className="rounded-2xl border border-panelBorder bg-panel p-5">
      <h2 className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2">
        <Database className="w-4 h-4 text-cyanpulse" /> MVTec AD Category Readiness
      </h2>
      <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
        {categories.map((cat) => (
          <div
            key={cat.id}
            className={`rounded-xl px-2.5 py-2 border text-center ${
              cat.memory_bank_ready
                ? 'border-emerald-500/30 bg-emerald-900/20'
                : 'border-panelBorder bg-obsidian/60'
            }`}
          >
            <p className="text-xs font-medium truncate text-slate-200">{cat.display_name}</p>
            <p className={`text-[10px] mt-0.5 ${cat.memory_bank_ready ? 'text-emerald-400' : 'text-slate-500'}`}>
              {cat.memory_bank_ready ? '✓ Ready' : '○ No Bank'}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const { isAuthenticated } = useAuth()
  const [health, setHealth] = useState(null)
  const [modelStatus, setModelStatus] = useState(null)
  const [categories, setCategories] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.allSettled([
      fetchHealth().then(setHealth),
      fetchModelStatus().then(setModelStatus),
      fetchCategories().then(setCategories),
      isAuthenticated ? fetchAnalyticsOverview().then(setAnalytics).catch(() => null) : Promise.resolve(),
    ]).finally(() => setLoading(false))
  }, [isAuthenticated])

  const totalInspections = analytics?.status === 'ok' ? analytics.data.total_inspections : null
  const anomalousCount = analytics?.status === 'ok' ? analytics.data.anomalous_count : null
  const normalCount = analytics?.status === 'ok' ? analytics.data.normal_count : null
  const readyCount = modelStatus?.ready_count ?? 0
  const totalCategories = modelStatus?.total_categories ?? 15

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-white">Industrial Inspection Dashboard</h1>
          <p className="text-sm text-slate-400 mt-1">ResNet18 + PatchCore Anomaly Detection · MVTec AD</p>
        </div>
        <Link
          to="/inspect"
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-electric to-cyanpulse text-white text-sm font-semibold hover:opacity-90 transition"
        >
          <Upload className="w-4 h-4" /> New Inspection
        </Link>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Inspections" value={totalInspections ?? (isAuthenticated ? '—' : 'Sign In')} icon={BarChart3} loading={loading} />
        <StatCard label="Anomalous" value={anomalousCount ?? '—'} icon={AlertTriangle} colorClass="text-rose-400" loading={loading} />
        <StatCard label="Normal" value={normalCount ?? '—'} icon={CheckCircle2} colorClass="text-emerald-400" loading={loading} />
        <StatCard label="Models Ready" value={`${readyCount}/${totalCategories}`} sub="Category memory banks" icon={ShieldCheck} colorClass="text-cyanpulse" loading={loading} />
      </div>

      {/* System Status + Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* System */}
        <div className="rounded-2xl border border-panelBorder bg-panel p-5 space-y-4">
          <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Server className="w-4 h-4 text-cyanpulse" /> System &amp; AI Engine
          </h2>
          {loading ? <LoadingSpinner label="Checking system status..." /> : (
            <div className="space-y-3 text-sm">
              <div className="flex justify-between items-center">
                <span className="text-slate-400">API Status</span>
                <span className={`font-medium ${health ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {health ? '● Online' : '● Offline'}
                </span>
              </div>
              {health?.gpu_name && (
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">GPU</span>
                  <span className="text-cyanpulse font-medium text-xs truncate max-w-[180px]">{health.gpu_name}</span>
                </div>
              )}
              <div className="flex justify-between items-center">
                <span className="text-slate-400">CUDA</span>
                <span className={health?.cuda_available ? 'text-emerald-400' : 'text-slate-400'}>
                  {health?.cuda_available ? 'Available' : 'CPU Mode'}
                </span>
              </div>
              {modelStatus?.vram_total_mb && (
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">VRAM</span>
                  <span className="text-cyanpulse text-xs">
                    {modelStatus.vram_allocated_mb}MB / {modelStatus.vram_total_mb}MB
                  </span>
                </div>
              )}
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Backbone Loaded</span>
                <span className={modelStatus?.backbone_loaded ? 'text-emerald-400' : 'text-slate-500'}>
                  {modelStatus?.backbone_loaded ? 'Yes' : 'On First Inference'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Supabase</span>
                <span className={health?.supabase_configured ? 'text-emerald-400' : 'text-amber-400'}>
                  {health?.supabase_configured ? 'Configured' : 'Not Configured'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Model Version</span>
                <span className="text-slate-300 text-xs">resnet18-patchcore-v1</span>
              </div>
            </div>
          )}
          {!health && !loading && (
            <p className="text-xs text-rose-300 bg-rose-950/30 border border-rose-500/20 rounded-lg p-3">
              Backend API is offline. Start the FastAPI server on port 8000.
            </p>
          )}
        </div>

        {/* Analytics */}
        <div className="rounded-2xl border border-panelBorder bg-panel p-5 space-y-4">
          <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-cyanpulse" /> Inspection Analytics
          </h2>
          {!isAuthenticated ? (
            <div className="flex flex-col items-center justify-center gap-3 py-6 text-center">
              <Activity className="w-8 h-8 text-slate-600" />
              <p className="text-sm text-slate-400">Analytics requires authentication.</p>
              <Link to="/login" className="text-xs text-cyanpulse hover:underline">Sign in →</Link>
            </div>
          ) : loading ? (
            <LoadingSpinner label="Loading analytics..." />
          ) : analytics?.status === 'ok' ? (
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Anomaly Rate</span>
                <span className="text-white font-medium">{(analytics.data.anomaly_rate * 100).toFixed(1)}%</span>
              </div>
              {Object.entries(analytics.data.by_severity || {}).map(([sev, cnt]) => (
                <div key={sev} className="flex justify-between items-center">
                  <SeverityBadge severity={sev} />
                  <span className="text-slate-300">{cnt} inspection{cnt !== 1 ? 's' : ''}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-6 text-sm text-slate-400">
              <Zap className="w-7 h-7 text-slate-600 mx-auto mb-2" />
              <p>{analytics?.message || 'No inspection data yet. Run your first inspection.'}</p>
              <Link to="/inspect" className="text-xs text-cyanpulse hover:underline mt-2 inline-block">Start inspecting →</Link>
            </div>
          )}
        </div>
      </div>

      <CategoryBankGrid categories={categories} />

      {readyCount === 0 && !loading && (
        <div className="rounded-2xl border border-amber-500/20 bg-amber-950/15 p-5 text-sm text-amber-200 space-y-1">
          <p className="font-semibold text-amber-100 flex items-center gap-2"><AlertTriangle className="w-4 h-4" /> No Category Memory Banks Available</p>
          <p className="text-amber-200/80">AI inspection is unavailable until normal feature memory banks are built for at least one MVTec AD category using the backend <code className="bg-amber-900/40 px-1 rounded">MemoryBankTrainer</code>. Set <code className="bg-amber-900/40 px-1 rounded">MVTEC_DATASET_DIR</code> in your <code className="bg-amber-900/40 px-1 rounded">.env</code> and run the training script.</p>
        </div>
      )}
    </div>
  )
}
