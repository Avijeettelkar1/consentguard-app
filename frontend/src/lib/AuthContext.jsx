import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { apiLogin, apiSignup, apiMe } from '../api'

const AuthContext = createContext(null)
const TOKEN_KEY = 'cg_token'

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(!!localStorage.getItem(TOKEN_KEY))

  // Validate an existing token on load
  useEffect(() => {
    if (!token) { setLoading(false); return }
    let alive = true
    apiMe(token)
      .then((d) => { if (alive) setUser(d.user) })
      .catch(() => { if (alive) { localStorage.removeItem(TOKEN_KEY); setToken(null); setUser(null) } })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [token])

  const persist = useCallback((data) => {
    localStorage.setItem(TOKEN_KEY, data.access_token)
    setToken(data.access_token)
    setUser(data.user)
    return data.user
  }, [])

  const login = useCallback(async (email, password) => persist(await apiLogin({ email, password })), [persist])
  const signup = useCallback(async (email, password, name) => persist(await apiSignup({ email, password, name })), [persist])
  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setUser(null)
  }, [])

  const value = { token, user, loading, isAuthed: !!user, login, signup, logout }
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
