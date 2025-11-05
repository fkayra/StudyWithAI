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
  const [loading, setLoading] = useState(true)

  const refreshUser = async (retryCount = 0) => {
    try {
      const response = await apiClient.get('/me')
      setUser(response.data)
    } catch (error: any) {
      // Check if it's a network error (CORS, connection failed, etc.)
      const isNetworkError = !error.response || error.message?.includes('Network Error') || error.code === 'ERR_NETWORK'
      
      // Retry once on network errors (could be CORS preflight issue on first load)
      if (isNetworkError && retryCount < 1) {
        // Wait a bit and retry
        await new Promise(resolve => setTimeout(resolve, 1000))
        return refreshUser(retryCount + 1)
      }
      
      // If it's a 401 or other auth error, clear tokens
      if (error.response?.status === 401 || !isNetworkError) {
        if (typeof window !== 'undefined') {
          localStorage.removeItem('accessToken')
          localStorage.removeItem('refreshToken')
        }
        setUser(null)
      }
      // For other network errors after retry, keep tokens but don't set user
      // (user might still be able to login later when network is stable)
    }
  }

  useEffect(() => {
    // Check if user is logged in
    const checkAuth = async () => {
      if (typeof window !== 'undefined') {
        const token = localStorage.getItem('accessToken')
        if (token) {
          await refreshUser()
        }
      }
      setLoading(false)
    }
    
    checkAuth()
  }, []) // Empty dependency array is fine here

  const login = async (email: string, password: string) => {
    try {
      const response = await apiClient.post('/auth/login', { email, password })
      if (typeof window !== 'undefined') {
        localStorage.setItem('accessToken', response.data.access_token)
        localStorage.setItem('refreshToken', response.data.refresh_token)
      }
      await refreshUser()
    } catch (error) {
      // Re-throw the error so it can be caught by the login page
      throw error
    }
  }

  const register = async (email: string, password: string) => {
    await apiClient.post('/auth/register', { email, password })
    await login(email, password)
  }

  const logout = () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('accessToken')
      localStorage.removeItem('refreshToken')
    }
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
