import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('prometheus_access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export function extractErrorMessage(err, fallback = 'Request failed') {
  if (err?.response?.data?.detail) {
    return typeof err.response.data.detail === 'string'
      ? err.response.data.detail
      : JSON.stringify(err.response.data.detail)
  }
  if (err?.message) return err.message
  return fallback
}

// Health & Models
export async function fetchHealth() {
  const { data } = await apiClient.get('/health')
  return data
}

export async function fetchCategories() {
  const { data } = await apiClient.get('/categories')
  return data
}

export async function fetchCategory(categoryId) {
  const { data } = await apiClient.get(`/categories/${categoryId}`)
  return data
}

export async function fetchModelStatus() {
  const { data } = await apiClient.get('/models/status')
  return data
}

export async function loadCategoryModel(categoryId) {
  const { data } = await apiClient.post(`/models/${categoryId}/load`)
  return data
}

// Inspections
export async function runInspection({ categoryId, sourceType = 'upload', file }) {
  const formData = new FormData()
  formData.append('category_id', categoryId)
  formData.append('source_type', sourceType)
  formData.append('file', file)
  const { data } = await apiClient.post('/inspections', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function fetchInspections({ categoryId, limit = 50, offset = 0 } = {}) {
  const params = { limit, offset }
  if (categoryId) params.category_id = categoryId
  const { data } = await apiClient.get('/inspections', { params })
  return data
}

export async function fetchInspectionById(inspectionId) {
  const { data } = await apiClient.get(`/inspections/${inspectionId}`)
  return data
}

export async function deleteInspection(inspectionId) {
  const { data } = await apiClient.delete(`/inspections/${inspectionId}`)
  return data
}

// Reviews
export async function submitReview({ inspectionId, verdict, correctedSeverity, notes }) {
  const payload = {
    inspection_id: inspectionId,
    verdict,
    corrected_severity: correctedSeverity || null,
    notes: notes || null,
  }
  const { data } = await apiClient.post('/reviews', payload)
  return data
}

export async function fetchReviews({ inspectionId, limit = 50 } = {}) {
  const params = { limit }
  if (inspectionId) params.inspection_id = inspectionId
  const { data } = await apiClient.get('/reviews', { params })
  return data
}

// Analytics
export async function fetchAnalyticsOverview() {
  const { data } = await apiClient.get('/analytics/overview')
  return data
}

export async function fetchDistributionShift() {
  const { data } = await apiClient.get('/analytics/distribution-shift')
  return data
}
