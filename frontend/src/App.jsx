import React from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import Layout from './components/Layout'
import DashboardPage from './pages/DashboardPage'
import InspectPage from './pages/InspectPage'
import ResultsPage from './pages/ResultsPage'
import LiveCameraPage from './pages/LiveCameraPage'
import HistoryPage from './pages/HistoryPage'
import HistoryDetailPage from './pages/HistoryDetailPage'
import ReviewPage from './pages/ReviewPage'
import AnalyticsPage from './pages/AnalyticsPage'
import ReportsPage from './pages/ReportsPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/inspect" element={<InspectPage />} />
            <Route path="/results" element={<ResultsPage />} />
            <Route path="/camera" element={<LiveCameraPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/history/:id" element={<HistoryDetailPage />} />
            <Route path="/review" element={<ReviewPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
