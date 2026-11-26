import React, { useEffect, useState } from 'react'
import { CheckSquare, Loader2, MessageSquare } from 'lucide-react'
import { fetchReviews, submitReview } from '../api/client'
import { EmptyState, ErrorBanner, SeverityBadge, SuccessBanner } from '../components/StatusStates'
import ProtectedRoute from '../components/ProtectedRoute'

const VERDICTS = [
  { value: 'confirmed_defect', label: 'Confirmed Defect' },
  { value: 'false_positive', label: 'False Positive' },
  { value: 'uncertain', label: 'Uncertain' },
]
const SEVERITIES = ['low', 'medium', 'high', 'critical']

function ReviewContent() {
  const [reviews, setReviews] = useState([])
  const [loadingReviews, setLoadingReviews] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const [inspectionId, setInspectionId] = useState('')
  const [verdict, setVerdict] = useState('')
  const [correctedSeverity, setCorrectedSeverity] = useState('')
  const [notes, setNotes] = useState('')

  useEffect(() => {
    fetchReviews({ limit: 50 })
      .then((data) => { setReviews(data?.items ?? []); setLoadingReviews(false) })
      .catch(() => setLoadingReviews(false))
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    if (!inspectionId.trim() || !verdict) {
      setError('Inspection ID and verdict are required.')
      return
    }
    setSubmitting(true)
    try {
      const created = await submitReview({ inspectionId: inspectionId.trim(), verdict, correctedSeverity: correctedSeverity || null, notes })
      setReviews((prev) => [created, ...prev])
      setSuccess('Review submitted successfully.')
      setInspectionId('')
      setVerdict('')
      setCorrectedSeverity('')
      setNotes('')
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Submission failed.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">False Positive Review</h1>
        <p className="text-sm text-slate-400 mt-1">Submit operator feedback to flag false positives, confirm defects, or mark results as uncertain.</p>
      </div>

      <div className="rounded-2xl border border-panelBorder bg-panel p-6 space-y-4">
        <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2"><CheckSquare className="w-4 h-4 text-cyanpulse" /> Submit Review</h2>
        <ErrorBanner title="Submission Error" message={error} />
        <SuccessBanner title="Review Submitted" message={success} />
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">Inspection ID <span className="text-rose-400">*</span></label>
            <input
              type="text"
              required
              value={inspectionId}
              onChange={(e) => setInspectionId(e.target.value)}
              placeholder="Paste inspection UUID from history"
              className="w-full rounded-xl bg-obsidian border border-panelBorder px-3.5 py-2.5 text-sm text-white font-mono focus:outline-none focus:border-cyanpulse"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Verdict <span className="text-rose-400">*</span></label>
              <select
                required
                value={verdict}
                onChange={(e) => setVerdict(e.target.value)}
                className="w-full rounded-xl bg-obsidian border border-panelBorder px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-cyanpulse"
              >
                <option value="">— Select Verdict —</option>
                {VERDICTS.map((v) => <option key={v.value} value={v.value}>{v.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Corrected Severity (optional)</label>
              <select
                value={correctedSeverity}
                onChange={(e) => setCorrectedSeverity(e.target.value)}
                className="w-full rounded-xl bg-obsidian border border-panelBorder px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-cyanpulse"
              >
                <option value="">— No change —</option>
                {SEVERITIES.map((s) => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">Notes (optional)</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              maxLength={1000}
              rows={3}
              placeholder="Describe the reason for this review (e.g., lighting artefact on glass surface)"
              className="w-full rounded-xl bg-obsidian border border-panelBorder px-3.5 py-2.5 text-sm text-white resize-none focus:outline-none focus:border-cyanpulse"
            />
            <p className="text-xs text-slate-500 mt-1 text-right">{notes.length}/1000</p>
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2.5 rounded-xl bg-gradient-to-r from-electric to-cyanpulse hover:opacity-90 disabled:opacity-40 text-white text-sm font-semibold flex items-center justify-center gap-2 transition"
          >
            {submitting ? <><Loader2 className="w-4 h-4 animate-spin" /> Submitting…</> : <><CheckSquare className="w-4 h-4" /> Submit Review</>}
          </button>
        </form>
      </div>

      <div className="rounded-2xl border border-panelBorder bg-panel p-5 space-y-3">
        <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2"><MessageSquare className="w-4 h-4 text-cyanpulse" /> Previous Reviews</h2>
        {loadingReviews ? (
          <div className="flex justify-center py-6"><Loader2 className="w-5 h-5 animate-spin text-cyanpulse" /></div>
        ) : reviews.length === 0 ? (
          <EmptyState title="No Reviews Yet" description="Submitted reviews will appear here." />
        ) : (
          <div className="space-y-2.5">
            {reviews.map((r) => (
              <div key={r.id} className="rounded-xl border border-panelBorder bg-obsidian/60 p-3.5 space-y-1.5">
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <span className="text-xs font-mono text-slate-400">{r.inspection_id?.slice(0, 20)}…</span>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                      r.verdict === 'false_positive' ? 'bg-amber-500/20 text-amber-300' :
                      r.verdict === 'confirmed_defect' ? 'bg-rose-500/20 text-rose-300' :
                      'bg-slate-700 text-slate-300'
                    }`}>{r.verdict?.replace('_', ' ')}</span>
                    {r.corrected_severity && <SeverityBadge severity={r.corrected_severity} />}
                  </div>
                </div>
                {r.notes && <p className="text-xs text-slate-400">{r.notes}</p>}
                <p className="text-[10px] text-slate-600">{new Date(r.created_at).toLocaleString()}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default function ReviewPage() {
  return <ProtectedRoute><ReviewContent /></ProtectedRoute>
}
