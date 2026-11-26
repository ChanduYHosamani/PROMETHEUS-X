import React from 'react'
import { useLocation, Link } from 'react-router-dom'
import {
  AlertTriangle, ArrowLeft, CheckCircle2, Clock,
  Eye, MapPin, Scan, TrendingUp, Upload
} from 'lucide-react'
import { SeverityBadge } from '../components/StatusStates'

function ScoreBar({ label, value, colorClass = 'bg-cyanpulse' }) {
  const pct = Math.round((value ?? 0) * 100)
  return (
    <div>
      <div className="flex justify-between text-xs mb-1.5">
        <span className="text-slate-400">{label}</span>
        <span className="text-slate-200 font-medium">{(value ?? 0).toFixed(4)}</span>
      </div>
      <div className="h-2 rounded-full bg-slate-800">
        <div className={`h-2 rounded-full transition-all ${colorClass}`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
    </div>
  )
}

export default function ResultsPage() {
  const location = useLocation()
  const { result, originalFile } = location.state || {}

  if (!result) {
    return (
      <div className="max-w-xl mx-auto mt-12 rounded-2xl border border-panelBorder bg-panel p-10 text-center space-y-4">
        <Scan className="w-10 h-10 text-slate-600 mx-auto" />
        <h2 className="text-lg font-semibold text-slate-200">No Inspection Result</h2>
        <p className="text-sm text-slate-400">Navigate here after submitting an image inspection.</p>
        <Link to="/inspect" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-electric text-white text-sm font-medium hover:bg-blue-500 transition">
          <Upload className="w-4 h-4" /> Go to Inspection
        </Link>
      </div>
    )
  }

  const severityColorMap = { low: 'bg-cyan-500', medium: 'bg-amber-500', high: 'bg-orange-500', critical: 'bg-rose-500' }
  const heatmapSrc = result.heatmap_base64 ? `data:image/png;base64,${result.heatmap_base64}` : null

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-4 flex-wrap">
        <Link to="/inspect" className="flex items-center gap-2 text-sm text-slate-400 hover:text-cyanpulse transition">
          <ArrowLeft className="w-4 h-4" /> New Inspection
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-white">Inspection Result</h1>
          <p className="text-xs text-slate-400 mt-0.5">Category: <span className="text-cyanpulse capitalize">{result.category_id}</span> · ID: <span className="font-mono text-slate-300">{result.inspection_id?.slice(0, 16)}…</span></p>
        </div>
      </div>

      {/* Verdict Banner */}
      <div className={`rounded-2xl p-5 border ${
        result.is_anomalous
          ? 'border-rose-500/40 bg-rose-950/30'
          : 'border-emerald-500/30 bg-emerald-950/20'
      } flex items-center gap-4`}>
        {result.is_anomalous
          ? <AlertTriangle className="w-8 h-8 text-rose-400 shrink-0" />
          : <CheckCircle2 className="w-8 h-8 text-emerald-400 shrink-0" />
        }
        <div>
          <p className="text-lg font-bold text-white">{result.is_anomalous ? 'Anomaly Detected' : 'Normal — No Defect'}</p>
          <div className="flex items-center gap-3 mt-1 flex-wrap">
            <SeverityBadge severity={result.severity} />
            <span className="text-xs text-slate-400">Confidence: <span className="text-slate-200 font-medium">{(result.calibrated_confidence * 100).toFixed(1)}%</span></span>
            <span className="flex items-center gap-1 text-xs text-slate-400">
              <Clock className="w-3 h-3" /> {result.inference_time_ms?.toFixed(1)} ms
            </span>
          </div>
        </div>
      </div>

      {/* Scores */}
      <div className="rounded-2xl border border-panelBorder bg-panel p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2"><TrendingUp className="w-4 h-4 text-cyanpulse" /> Detection Scores</h2>
        <ScoreBar label="Raw Anomaly Score" value={result.anomaly_score} colorClass={result.is_anomalous ? 'bg-rose-500' : 'bg-emerald-500'} />
        <ScoreBar label="Calibrated Confidence" value={result.calibrated_confidence} colorClass="bg-cyanpulse" />
      </div>

      {/* Images */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-2xl border border-panelBorder bg-panel p-4 space-y-3">
          <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2"><Eye className="w-4 h-4 text-cyanpulse" /> Original Image</h2>
          {originalFile
            ? <img src={originalFile} alt="Original" className="rounded-xl w-full object-contain max-h-72 bg-obsidian" />
            : <div className="flex items-center justify-center h-40 rounded-xl bg-obsidian text-slate-500 text-xs">Image preview not available</div>
          }
        </div>
        <div className="rounded-2xl border border-panelBorder bg-panel p-4 space-y-3">
          <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Scan className="w-4 h-4 text-cyanpulse" /> Anomaly Heatmap Overlay
          </h2>
          {heatmapSrc
            ? <img src={heatmapSrc} alt="Heatmap" className="rounded-xl w-full object-contain max-h-72 bg-obsidian" />
            : <div className="flex items-center justify-center h-40 rounded-xl bg-obsidian text-slate-500 text-xs text-center px-4">
                Heatmap not returned — this occurs when no memory bank is loaded for this category.
              </div>
          }
          {result.image_size && (
            <p className="text-xs text-slate-500 text-center">{result.image_size.width} × {result.image_size.height} px</p>
          )}
        </div>
      </div>

      {/* Defect Regions */}
      {result.detections?.length > 0 && (
        <div className="rounded-2xl border border-panelBorder bg-panel p-5 space-y-3">
          <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <MapPin className="w-4 h-4 text-rose-400" /> Detected Defect Regions ({result.detections.length})
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-panelBorder text-slate-400">
                  <th className="pb-2 font-medium">#</th>
                  <th className="pb-2 font-medium">Position (x, y)</th>
                  <th className="pb-2 font-medium">Size (w × h)</th>
                  <th className="pb-2 font-medium">Area %</th>
                  <th className="pb-2 font-medium">Peak Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-panelBorder">
                {result.detections.map((d, i) => (
                  <tr key={i} className="text-slate-300">
                    <td className="py-2">{i + 1}</td>
                    <td className="py-2">{(d.bbox_x * 100).toFixed(1)}%, {(d.bbox_y * 100).toFixed(1)}%</td>
                    <td className="py-2">{(d.bbox_w * 100).toFixed(1)}% × {(d.bbox_h * 100).toFixed(1)}%</td>
                    <td className="py-2">{(d.area_ratio * 100).toFixed(2)}%</td>
                    <td className="py-2 text-rose-300 font-medium">{d.peak_score?.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Persistence */}
      {result.persisted_to_supabase && (
        <p className="text-xs text-emerald-400 text-center">✓ Inspection persisted to Supabase · <Link to="/history" className="underline hover:text-emerald-300">View History</Link></p>
      )}
    </div>
  )
}
