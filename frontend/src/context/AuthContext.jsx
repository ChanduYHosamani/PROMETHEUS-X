import React, { createContext, useContext, useEffect, useState } from 'react'
import axios from 'axios'

const SUPABASE_URL = (import.meta.env.VITE_SUPABASE_URL || '').replace(/\/+$/, '')
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || ''

const TOKEN_KEY = 'prometheus_access_token'
const USER_KEY = 'prometheus_user'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const supabaseConfigured = Boolean(SUPABASE_URL && SUPABASE_ANON_KEY)
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem(TOKEN_KEY) || '')
  const [user, setUser] = useState(() => {
    try {
      const raw = localStorage.getItem(USER_KEY)
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!supabaseConfigured || !accessToken) return
    let active = true
    axios
      .get(`${SUPABASE_URL}/auth/v1/user`, {
        headers: {
          apikey: SUPABASE_ANON_KEY,
          Authorization: `Bearer ${accessToken}`,
        },
      })
      .then((res) => {
        if (!active) return
        setUser(res.data)
        localStorage.setItem(USER_KEY, JSON.stringify(res.data))
      })
      .catch(() => {
        if (!active) return
        logout()
      })
    return () => {
      active = false
    }
  }, [supabaseConfigured, accessToken])

  const login = async (email, password) => {
    if (!supabaseConfigured) {
      throw new Error('Supabase authentication is not configured in frontend environment variables.')
    }
    setLoading(true)
    try {
      const { data } = await axios.post(
        `${SUPABASE_URL}/auth/v1/token?grant_type=password`,
        { email, password },
        { headers: { apikey: SUPABASE_ANON_KEY, 'Content-Type': 'application/json' } }
      )
      localStorage.setItem(TOKEN_KEY, data.access_token)
      localStorage.setItem(USER_KEY, JSON.stringify(data.user))
      setAccessToken(data.access_token)
      setUser(data.user)
      return data
    } catch (err) {
      const msg = err?.response?.data?.error_description || err?.response?.data?.msg || err.message
      throw new Error(msg || 'Sign in failed.')
    } finally {
      setLoading(false)
    }
  }

  const register = async (email, password, fullName) => {
    if (!supabaseConfigured) {
      throw new Error('Supabase authentication is not configured in frontend environment variables.')
    }
    setLoading(true)
    try {
      const { data } = await axios.post(
        `${SUPABASE_URL}/auth/v1/signup`,
        { email, password, data: { full_name: fullName } },
        { headers: { apikey: SUPABASE_ANON_KEY, 'Content-Type': 'application/json' } }
      )
      if (data.access_token) {
        localStorage.setItem(TOKEN_KEY, data.access_token)
        localStorage.setItem(USER_KEY, JSON.stringify(data.user))
        setAccessToken(data.access_token)
        setUser(data.user)
      }
      return data
    } catch (err) {
      const msg = err?.response?.data?.error_description || err?.response?.data?.msg || err.message
      throw new Error(msg || 'Registration failed.')
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setAccessToken('')
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        accessToken,
        isAuthenticated: Boolean(accessToken && user),
        supabaseConfigured,
        loading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
