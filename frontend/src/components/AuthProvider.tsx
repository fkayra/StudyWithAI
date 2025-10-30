'use client'

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { apiClient } from '@/lib/api'

interface User {
  id: number
  email: string
  tier: 'free' | 'premium'
  usage?: {
    exam: number
    explain: number
    chat: number
    upload: number
  }
}

interface AuthContextType {
  user: User | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)

  useEffect(() => {
    // Check if user is logged in
    const token = localStorage.getItem('accessToken')
    if (token) {
      refreshUser()
    }
  }, [])

  const refreshUser = async () => {
    try {
      const response = await apiClient.get('/me')
      setUser(response.data)
    } catch (error) {
      localStorage.removeItem('accessToken')
      localStorage.removeItem('refreshToken')
      setUser(null)
    }
  }

  const login = async (email: string, password: string) => {
    const response = await apiClient.post('/auth/login', { email, password })
    localStorage.setItem('accessToken', response.data.access_token)
    localStorage.setItem('refreshToken', response.data.refresh_token)
    await refreshUser()
  }

  const register = async (email: string, password: string) => {
    await apiClient.post('/auth/register', { email, password })
    await login(email, password)
  }

  const logout = () => {
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
