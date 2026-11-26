import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, Camera, CameraOff, ChevronDown, Loader2, ScanSearch, StopCircle } from 'lucide-react'
import { fetchCategories, runInspection } from '../api/client'
import { ErrorBanner } from '../components/StatusStates'

export default function LiveCameraPage() {
  const navigate = useNavigate()
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const streamRef = useRef(null)

  const [stream, setStream] = useState(null)
  const [cameraError, setCameraError] = useState('')
  const [capturedBlob, setCapturedBlob] = useState(null)
  const [capturedPreview, setCapturedPreview] = useState(null)
  const [categories, setCategories] = useState([])
  const [categoryId, setCategoryId] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [apiError, setApiError] = useState('')

  useEffect(() => {
    fetchCategories().then(setCategories).catch(() => null)
    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }
  }, [])

  const startCamera = useCallback(async () => {
    setCameraError('')
    setCapturedBlob(null)
    setCapturedPreview(null)
    try {
      const s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment', width: { ideal: 1280 } } })
      streamRef.current = s
      setStream(s)
      if (videoRef.current) {
        videoRef.current.srcObject = s
        videoRef.current.play()
      }
    } catch (err) {
      setCameraError(`Camera access denied or unavailable: ${err.message}`)
    }
  }, [])

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    setStream(null)
    if (videoRef.current) videoRef.current.srcObject = null
  }, [])

  const captureFrame = useCallback(() => {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas) return
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext('2d').drawImage(video, 0, 0)
    canvas.toBlob((blob) => {
      setCapturedBlob(blob)
      setCapturedPreview(canvas.toDataURL('image/png'))
    }, 'image/png')
    stopCamera()
  }, [stopCamera])

  const retake = () => { setCapturedBlob(null); setCapturedPreview(null); startCamera() }

  const handleInspect = async () => {
    if (!capturedBlob || !categoryId) return
    setApiError('')
    setSubmitting(true)
    try {
      const file = new File([capturedBlob], 'camera_capture.png', { type: 'image/png' })
      const result = await runInspection({ categoryId, sourceType: 'camera', file })
      navigate('/results', { state: { result, originalFile: capturedPreview } })
    } catch (err) {
      const detail = err?.response?.data?.detail || err.message || 'Inspection failed.'
      const isModelMissing = err?.response?.status === 409
      setApiError(isModelMissing ? `Model memory bank unavailable: ${detail}` : detail)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Live Camera Inspection</h1>
        <p className="text-sm text-slate-400 mt-1">Capture a frame from your camera and run it through the PatchCore inspection pipeline. Single-frame capture only — continuous inference is not implemented.</p>
      </div>

      {cameraError && <ErrorBanner title="Camera Error" message={cameraError} />}
      {apiError && <ErrorBanner title="Inspection Error" message={apiError} />}

      <div className="rounded-2xl border border-panelBorder bg-panel overflow-hidden">
        <div className="relative bg-obsidian min-h-64 flex items-center justify-center">
          {!stream && !capturedPreview && (
            <div className="text-center p-8 space-y-3">
              <CameraOff className="w-12 h-12 text-slate-600 mx-auto" />
              <p className="text-sm text-slate-400">Camera is not active. Click "Start Camera" to begin.</p>
            </div>
          )}
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className={`w-full max-h-96 object-contain ${!stream ? 'hidden' : ''}`}
          />
          {capturedPreview && !stream && (
            <img src={capturedPreview} alt="Captured" className="w-full max-h-96 object-contain" />
          )}
        </div>

        <canvas ref={canvasRef} className="hidden" />

        <div className="p-4 flex items-center gap-3 flex-wrap border-t border-panelBorder">
          {!stream && !capturedPreview && (
            <button
              onClick={startCamera}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-cyanpulse/15 border border-cyanpulse/30 text-cyanpulse text-sm font-medium hover:bg-cyanpulse/25 transition"
            >
              <Camera className="w-4 h-4" /> Start Camera
            </button>
          )}
          {stream && (
            <>
              <button
                onClick={captureFrame}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-electric to-cyanpulse text-white text-sm font-semibold hover:opacity-90 transition"
              >
                <Camera className="w-4 h-4" /> Capture Frame
              </button>
              <button
                onClick={stopCamera}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 border border-panelBorder text-slate-300 text-sm hover:bg-slate-700 transition"
              >
                <StopCircle className="w-4 h-4" /> Stop
              </button>
            </>
          )}
          {capturedPreview && !stream && (
            <button
              onClick={retake}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 border border-panelBorder text-slate-300 text-sm hover:bg-slate-700 transition"
            >
              <Camera className="w-4 h-4" /> Retake
            </button>
          )}
        </div>
      </div>

      {capturedPreview && (
        <div className="rounded-2xl border border-panelBorder bg-panel p-5 space-y-4">
          <h2 className="text-sm font-semibold text-slate-200">Select Category &amp; Run Inspection</h2>
          <div className="relative">
            <select
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
              className="w-full appearance-none rounded-xl bg-obsidian border border-panelBorder px-4 py-3 pr-10 text-sm text-white focus:outline-none focus:border-cyanpulse"
            >
              <option value="">— Select MVTec AD Category —</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.display_name}{cat.memory_bank_ready ? ' ✓ Ready' : ' ○ No Bank'}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>
          <button
            onClick={handleInspect}
            disabled={!capturedBlob || !categoryId || submitting}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-electric to-cyanpulse hover:opacity-90 disabled:opacity-40 text-white text-sm font-bold flex items-center justify-center gap-2 transition"
          >
            {submitting ? <><Loader2 className="w-4 h-4 animate-spin" /> Inspecting…</> : <><ScanSearch className="w-4 h-4" /> Run Inspection</>}
          </button>
          <div className="flex items-start gap-2 text-xs text-slate-400 bg-slate-800/50 rounded-lg p-3">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
            <span>This performs single-frame capture inspection. Continuous live-stream inference is not currently implemented.</span>
          </div>
        </div>
      )}
    </div>
  )
}
