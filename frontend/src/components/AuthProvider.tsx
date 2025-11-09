'use client'

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { apiClient } from '@/lib/api'

interface User {
  id: number
  email: string
  name: string
  surname: string
  tier: 'free' | 'premium' | 'standard' | 'pro'
  is_admin?: boolean
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
  register: (email: string, password: string, name: string, surname: string) => Promise<void>
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
      
      // If it's a 401, clear user (not authenticated)
      if (error.response?.status === 401) {
        setUser(null)
      }
      // If it's a 500, log the error details for debugging but don't clear cookies
      // (might be a temporary backend issue)
      else if (error.response?.status === 500) {
        console.error('Server error while fetching user:', error.response?.data?.detail || error.message)
        // Retry once on 500 errors (might be temporary)
        if (retryCount < 1) {
          await new Promise(resolve => setTimeout(resolve, 2000))
          return refreshUser(retryCount + 1)
        }
        // After retry, clear user to be safe
        setUser(null)
      }
      // For other errors, clear user
      else if (!isNetworkError) {
        setUser(null)
      }
      // For network errors after retry, keep cookies but don't set user
      // (user might still be able to login later when network is stable)
    }
  }

  useEffect(() => {
    // Check if user is logged in (cookies are sent automatically)
    const checkAuth = async () => {
      await refreshUser()
      setLoading(false)
    }
    
    checkAuth()
  }, []) // Empty dependency array is fine here

  const login = async (email: string, password: string) => {
    try {
      console.log('[AUTH] Attempting login for:', email)
      // Login and get tokens
      const response = await apiClient.post('/auth/login', { email, password })
      console.log('[AUTH] Login successful:', response.data)
      
      // Save tokens to localStorage for Authorization header
      if (response.data.access_token) {
        localStorage.setItem('access_token', response.data.access_token)
      }
      if (response.data.refresh_token) {
        localStorage.setItem('refresh_token', response.data.refresh_token)
      }
      
      // Set user data from login response if available
      if (response.data.user) {
        setUser(response.data.user)
      }
      
      // Try to refresh user data, but don't fail if it errors
      try {
        await refreshUser()
      } catch (refreshError) {
        console.warn('Failed to refresh user after login, but login was successful:', refreshError)
        // Don't throw - login was successful, we just couldn't refresh user data
      }
    } catch (error: any) {
      // Log the error for debugging
      console.error('[AUTH] Login error:', error)
      console.error('[AUTH] Error code:', error?.code)
      console.error('[AUTH] Error message:', error?.message)
      console.error('[AUTH] Error response:', error.response?.data)
      console.error('[AUTH] Error response status:', error.response?.status)
      console.error('[AUTH] Request URL:', error.config?.url)
      console.error('[AUTH] Request baseURL:', error.config?.baseURL)
      
      // Re-throw the error so it can be caught by the login page
      throw error
    }
  }

  const register = async (email: string, password: string, name: string, surname: string) => {
    await apiClient.post('/auth/register', { email, password, name, surname })
    await login(email, password)
  }

  const logout = async () => {
    try {
      // Call backend to clear cookies
      await apiClient.post('/auth/logout')
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      // Clear tokens from localStorage
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      setUser(null)
    }
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
