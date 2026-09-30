import { createContext, useContext, useEffect, useState } from 'react'
import { api, type User } from '@/api/client'

interface JwtPayload {
  sub: string
  role: 'student' | 'teacher'
  org_id: number
  user_id: number
  exp?: number
}

function parseJwt(token: string): JwtPayload | null {
  try {
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      window
        .atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )
    return JSON.parse(jsonPayload)
  } catch {
    return null
  }
}

interface AuthContextType {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  register: (data: {
    username: string
    password: string
    role: 'student' | 'teacher'
    organization_id?: number
    new_organization_name?: string
  }) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('access_token'))
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)

  useEffect(() => {
    if (token) {
      const payload = parseJwt(token)
      if (payload && payload.sub) {
        setUser({
          id: payload.user_id,
          username: payload.sub,
          role: payload.role,
          organization_id: payload.org_id,
        })
      } else {
        localStorage.removeItem('access_token')
        setToken(null)
        setUser(null)
      }
    } else {
      setUser(null)
    }
    setIsLoading(false)
  }, [token])

  const login = async (username: string, password: string) => {
    const res = await api.login(username, password)
    setToken(res.access_token)
    const payload = parseJwt(res.access_token)
    if (payload) {
      setUser({
        id: payload.user_id,
        username: payload.sub,
        role: payload.role,
        organization_id: payload.org_id,
      })
    }
  }

  const register = async (data: {
    username: string
    password: string
    role: 'student' | 'teacher'
    organization_id?: number
    new_organization_name?: string
  }) => {
    await api.register(data)
    await login(data.username, data.password)
  }

  const logout = () => {
    api.logout()
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoading,
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
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
