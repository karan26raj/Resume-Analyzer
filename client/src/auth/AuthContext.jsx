import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { getToken, setToken, setUnauthorizedHandler } from '../api/client'
import { authApi } from '../api/services'
import { getTokenExpiry, isTokenExpired } from '../utils/jwt'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setTokenState] = useState(() => {
    const stored = getToken()
    return stored && !isTokenExpired(stored) ? stored : null
  })
  const [user, setUser] = useState(null)
  const [status, setStatus] = useState(token ? 'loading' : 'anonymous')
  const [sessionExpired, setSessionExpired] = useState(false)
  const [attempt, setAttempt] = useState(0)

  const logout = useCallback((reason) => {
    setToken(null)
    setTokenState(null)
    setUser(null)
    setStatus('anonymous')
    setSessionExpired(reason === 'expired')
  }, [])

  // Any 401 from the API means the token is no longer valid.
  useEffect(() => {
    setUnauthorizedHandler(() => logout('expired'))
    return () => setUnauthorizedHandler(null)
  }, [logout])

  // Load the current user whenever we have a token.
  useEffect(() => {
    if (!token) return undefined
    const controller = new AbortController()
    setStatus('loading')
    authApi
      .me({ signal: controller.signal })
      .then((me) => {
        setUser(me)
        setStatus('authenticated')
      })
      .catch((error) => {
        if (error.name === 'AbortError') return
        if (error.status === 401) logout('expired')
        else setStatus('error')
      })
    return () => controller.abort()
  }, [token, attempt, logout])

  // End the session exactly when the JWT expires.
  useEffect(() => {
    const expiry = getTokenExpiry(token)
    if (!expiry) return undefined
    const timeout = setTimeout(() => logout('expired'), Math.max(0, expiry.getTime() - Date.now()))
    return () => clearTimeout(timeout)
  }, [token, logout])

  const login = useCallback(async (email, password) => {
    const { access_token: accessToken } = await authApi.login(email, password)
    setToken(accessToken)
    setSessionExpired(false)
    setTokenState(accessToken)
  }, [])

  const register = useCallback(
    async (email, password) => {
      await authApi.register(email, password)
      await login(email, password)
    },
    [login],
  )

  const value = useMemo(
    () => ({
      token,
      user,
      status,
      sessionExpired,
      expiresAt: getTokenExpiry(token),
      login,
      register,
      logout,
      retry: () => setAttempt((count) => count + 1),
    }),
    [token, user, status, sessionExpired, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>')
  return context
}
