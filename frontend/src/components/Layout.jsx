import React, { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import {
  Activity,
  BarChart3,
  Camera,
  CheckSquare,
  Cpu,
  FileText,
  History,
  LayoutDashboard,
  LogIn,
  LogOut,
  Menu,
  ScanSearch,
  ShieldCheck,
  Upload,
  X,
} from 'lucide-react'
import { fetchHealth } from '../api/client'
import { useAuth } from '../context/AuthContext'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/inspect', label: 'Image Inspection', icon: Upload },
  { to: '/results', label: 'Inspection Results', icon: ScanSearch },
  { to: '/camera', label: 'Live Camera', icon: Camera },
  { to: '/history', label: 'Inspection History', icon: History, private: true },
  { to: '/review', label: 'False Positive Review', icon: CheckSquare, private: true },
  { to: '/analytics', label: 'Analytics', icon: BarChart3, private: true },
  { to: '/reports', label: 'Reports', icon: FileText, private: true },
]

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [health, setHealth] = useState(null)
  const { user, isAuthenticated, logout } = useAuth()

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => setHealth(null))
  }, [])

  const navLinkClass = ({ isActive }) =>
    `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition ${
      isActive
        ? 'bg-gradient-to-r from-electric/20 to-cyanpulse/15 text-cyanpulse border border-cyanpulse/30 shadow-sm'
        : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60 border border-transparent'
    }`

  return (
    <div className="min-h-screen bg-obsidian text-slate-100 flex">
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={`fixed lg:static inset-y-0 left-0 z-40 w-68 bg-navybase border-r border-panelBorder flex flex-col transition-transform duration-200 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div className="p-5 border-b border-panelBorder flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-electric to-cyanpulse flex items-center justify-center shadow-lg shadow-cyanpulse/20">
              <ShieldCheck className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-bold tracking-tight text-white">PROMETHEUS-X</h1>
              <p className="text-[11px] text-cyanpulse tracking-wide">Industrial AI Vision</p>
            </div>
          </div>
          <button
            className="lg:hidden text-slate-400 hover:text-white"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close sidebar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={navLinkClass}
                onClick={() => setSidebarOpen(false)}
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span className="flex-1">{item.label}</span>
                {item.private && !isAuthenticated && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                    Auth
                  </span>
                )}
              </NavLink>
            )
          })}
        </nav>

        <div className="p-4 border-t border-panelBorder space-y-3">
          {isAuthenticated ? (
            <div className="flex items-center justify-between gap-2 bg-panel rounded-xl p-2.5 border border-panelBorder">
              <div className="min-w-0">
                <p className="text-xs font-medium text-slate-200 truncate">{user?.email || 'Operator'}</p>
                <p className="text-[10px] text-emerald-400">Authenticated Session</p>
              </div>
              <button
                onClick={logout}
                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition"
                title="Sign Out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <NavLink
              to="/login"
              className="flex items-center justify-center gap-2 w-full py-2 rounded-xl bg-electric/15 hover:bg-electric/25 text-cyanpulse border border-electric/30 text-xs font-semibold transition"
              onClick={() => setSidebarOpen(false)}
            >
              <LogIn className="w-4 h-4" />
              <span>Operator Sign In</span>
            </NavLink>
          )}
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 bg-navybase/80 backdrop-blur border-b border-panelBorder px-4 lg:px-8 flex items-center justify-between sticky top-0 z-20">
          <div className="flex items-center gap-3">
            <button
              className="lg:hidden p-2 rounded-lg border border-panelBorder text-slate-300 hover:bg-slate-800"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open sidebar"
            >
              <Menu className="w-5 h-5" />
            </button>
            <span className="text-xs text-slate-400 hidden sm:inline">
              See Beyond the Expected. Detect the Unknown.
            </span>
          </div>

          <div className="flex items-center gap-3 text-xs">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-panel border border-panelBorder">
              <Activity className={`w-3.5 h-3.5 ${health ? 'text-emerald-400 animate-pulse-slow' : 'text-rose-400'}`} />
              <span className="text-slate-300">
                {health ? 'API Online' : 'API Offline'}
              </span>
            </div>
            {health?.gpu_name && (
              <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full bg-panel border border-panelBorder text-cyanpulse">
                <Cpu className="w-3.5 h-3.5" />
                <span>{health.gpu_name}</span>
              </div>
            )}
          </div>
        </header>

        <main className="flex-1 p-4 lg:p-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
