import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, ChevronDown, ImagePlus, Loader2, ScanSearch, Upload, X } from 'lucide-react'
import { fetchCategories, runInspection } from '../api/client'
import { ErrorBanner, LoadingSpinner } from '../components/StatusStates'

const ACCEPT = 'image/png,image/jpeg,image/webp,image/bmp,image/tiff'
const MAX_MB = 15

export default function InspectPage() {
  const navigate = useNavigate()
  const fileInputRef = useRef(null)
  const dropRef = useRef(null)

  const [categories, setCategories] = useState([])
  const [catLoading, setCatLoading] = useState(true)
  const [categoryId, setCategoryId] = useState('')
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [validationError, setValidationError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [apiError, setApiError] = useState('')

  useEffect(() => {
    fetchCategories()
      .then((cats) => { setCategories(cats); setCatLoading(false) })
      .catch(() => setCatLoading(false))
  }, [])

  const validateAndSetFile = (f) => {
    setValidationError('')
    setApiError('')
    if (!f) return
    if (!f.type.startsWith('image/')) {
      setValidationError('Only image files (PNG, JPEG, WEBP, BMP, TIFF) are accepted.')
      return
    }
    if (f.size > MAX_MB * 1024 * 1024) {
      setValidationError(`File is too large. Maximum allowed size is ${MAX_MB} MB.`)
      return
    }
    setFile(f)
    const url = URL.createObjectURL(f)
    setPreview(url)
  }

  const handleFileChange = (e) => validateAndSetFile(e.target.files?.[0])
  const clearFile = () => { setFile(null); setPreview(null); setValidationError('') }

  const onDragOver = useCallback((e) => { e.preventDefault(); setDragging(true) }, [])
  const onDragLeave = useCallback(() => setDragging(false), [])
  const onDrop = useCallback((e) => {
    e.preventDefault()
    setDragging(false)
    validateAndSetFile(e.dataTransfer.files?.[0])
  }, [])

  const selectedCategory = categories.find((c) => c.id === categoryId)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) { setValidationError('Please select an image file.'); return }
    if (!categoryId) { setValidationError('Please select a product category.'); return }
    setApiError('')
    setSubmitting(true)
    try {
      const result = await runInspection({ categoryId, sourceType: 'upload', file })
      navigate('/results', { state: { result, originalFile: preview } })
    } catch (err) {
      const detail = err?.response?.data?.detail || err.message || 'Inspection failed.'
      const isModelMissing = err?.response?.status === 409
      setApiError(isModelMissing
        ? `Model memory bank unavailable: ${detail} — Train and save the "${selectedCategory?.display_name || categoryId}" memory bank first.`
        : detail)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Image Inspection</h1>
        <p className="text-sm text-slate-400 mt-1">Upload an industrial product image and select its category to run PatchCore anomaly detection.</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Category Select */}
        <div className="rounded-2xl border border-panelBorder bg-panel p-5 space-y-3">
          <label className="text-sm font-semibold text-slate-200">Product Category</label>
          {catLoading ? <LoadingSpinner label="Loading categories..." /> : (
            <div className="relative">
              <select
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
                className="w-full appearance-none rounded-xl bg-obsidian border border-panelBorder px-4 py-3 pr-10 text-sm text-white focus:outline-none focus:border-cyanpulse"
              >
                <option value="">— Select MVTec AD Category —</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.display_name} ({cat.domain_type})
                    {cat.memory_bank_ready ? ' ✓ Ready' : ' ○ No Bank'}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            </div>
          )}
          {categoryId && selectedCategory && !selectedCategory.memory_bank_ready && (
            <div className="flex items-start gap-2 text-xs text-amber-200 bg-amber-950/30 border border-amber-500/20 rounded-lg p-3">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <span>
                The <strong>{selectedCategory.display_name}</strong> memory bank has not been built yet. AI inference will be unavailable for this category until its normal feature bank is trained and saved.
              </span>
            </div>
          )}
        </div>

        {/* Drop Zone */}
        <div
          ref={dropRef}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={() => !file && fileInputRef.current?.click()}
          className={`rounded-2xl border-2 border-dashed transition cursor-pointer ${
            dragging ? 'border-cyanpulse bg-cyanpulse/10' : 'border-panelBorder bg-panel hover:border-slate-600'
          } ${file ? 'cursor-default' : ''} p-6`}
        >
          <input ref={fileInputRef} type="file" accept={ACCEPT} className="hidden" onChange={handleFileChange} />
          {!file ? (
            <div className="flex flex-col items-center gap-3 text-center py-4">
              <div className="w-14 h-14 rounded-2xl bg-slate-800 flex items-center justify-center">
                <ImagePlus className="w-7 h-7 text-cyanpulse" />
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-200">Drag &amp; drop an image here</p>
                <p className="text-xs text-slate-400 mt-1">or click to browse — PNG, JPEG, WEBP, BMP, TIFF · Max {MAX_MB} MB</p>
              </div>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click() }}
                className="px-4 py-2 rounded-xl bg-slate-800 border border-panelBorder text-xs font-medium text-slate-200 hover:bg-slate-700 transition"
              >
                Browse File
              </button>
            </div>
          ) : (
            <div className="flex items-start gap-4">
              <img
                src={preview}
                alt="Preview"
                className="w-28 h-28 rounded-xl object-cover border border-panelBorder bg-obsidian shrink-0"
              />
              <div className="flex-1 min-w-0 space-y-1">
                <p className="text-sm font-semibold text-slate-100 truncate">{file.name}</p>
                <p className="text-xs text-slate-400">{(file.size / 1024 / 1024).toFixed(2)} MB · {file.type}</p>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); clearFile() }}
                  className="mt-2 inline-flex items-center gap-1.5 text-xs text-rose-400 hover:text-rose-300 transition"
                >
                  <X className="w-3.5 h-3.5" /> Remove
                </button>
              </div>
            </div>
          )}
        </div>

        {validationError && (
          <ErrorBanner title="Validation Error" message={validationError} />
        )}
        {apiError && (
          <ErrorBanner title={apiError.includes('memory bank') ? 'Model Not Ready' : 'Inspection Failed'} message={apiError} />
        )}

        <button
          type="submit"
          disabled={submitting || !file || !categoryId}
          className="w-full py-3.5 rounded-2xl bg-gradient-to-r from-electric to-cyanpulse hover:opacity-90 disabled:opacity-40 text-white text-sm font-bold flex items-center justify-center gap-2.5 transition"
        >
          {submitting ? (
            <><Loader2 className="w-4 h-4 animate-spin" /> Running Inspection...</>
          ) : (
            <><ScanSearch className="w-4 h-4" /> Start Inspection</>
          )}
        </button>
      </form>
    </div>
  )
}
