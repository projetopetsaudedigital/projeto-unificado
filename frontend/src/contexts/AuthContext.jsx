import { createContext, useContext, useState, useEffect } from 'react'

const AuthContext = createContext(null)

const API_BASE = '/api/v1'

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem('token'))
  const [carregando, setCarregando] = useState(true)

  // Ao montar, verifica se o token salvo ainda é válido
  useEffect(() => {
    if (!token) {
      setCarregando(false)
      return
    }
    fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => {
        if (!r.ok) throw new Error('Token inválido')
        return r.json()
      })
      .then(u => {
        setUsuario(u)
        setCarregando(false)
      })
      .catch(() => {
        localStorage.removeItem('token')
        setToken(null)
        setUsuario(null)
        setCarregando(false)
      })
  }, [token])

  async function login(email, senha) {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, senha }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Erro ao fazer login')
    }
    const data = await res.json()
    localStorage.setItem('token', data.access_token)
    setToken(data.access_token)
    setUsuario(data.usuario)
    return data.usuario
  }

  function logout() {
    localStorage.removeItem('token')
    setToken(null)
    setUsuario(null)
  }

  return (
    <AuthContext.Provider value={{ usuario, token, carregando, login, logout, autenticado: !!usuario }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth deve ser usado dentro de <AuthProvider>')
  return ctx
}
