import axios from 'axios'

// In production, use the backend URL directly
// In development, use the proxy via /api
const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE || '/api'

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
apiClient.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('accessToken')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

// Handle token refresh on 401
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    
    // Don't handle token refresh for auth endpoints (login/register) - let them handle their own errors
    const isAuthEndpoint = originalRequest?.url?.includes('/auth/login') || 
                          originalRequest?.url?.includes('/auth/register')
    
    if (error.response?.status === 401 && !originalRequest._retry && typeof window !== 'undefined' && !isAuthEndpoint) {
      originalRequest._retry = true
      
      const refreshToken = localStorage.getItem('refreshToken')
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE}/auth/refresh`, { refresh_token: refreshToken })
          localStorage.setItem('accessToken', response.data.access_token)
          localStorage.setItem('refreshToken', response.data.refresh_token)
          
          originalRequest.headers.Authorization = `Bearer ${response.data.access_token}`
          return apiClient(originalRequest)
        } catch (refreshError) {
          localStorage.removeItem('accessToken')
          localStorage.removeItem('refreshToken')
          if (typeof window !== 'undefined') {
            window.location.href = '/login'
          }
        }
      } else {
        // No refresh token, redirect to login (but not if we're already on login/register)
        if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
          window.location.href = '/login'
        }
      }
    }
    
    return Promise.reject(error)
  }
)

// History API helpers
export const historyAPI = {
  // Save history item (if user is logged in, saves to backend; otherwise localStorage)
  // Returns the ID of the saved item (number for backend, string for localStorage)
  async save(item: { type: string; title: string; data: any; score?: any }): Promise<number | string | null> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('accessToken') : null
    
    if (token) {
      // User is logged in, save to backend
      try {
        const response = await apiClient.post('/history', item)
        return response.data.id // Return backend ID
      } catch (error) {
        console.error('Failed to save history to backend:', error)
        // Fallback to localStorage
        return this.saveToLocalStorage(item)
      }
    } else {
      // Anonymous user, save to localStorage
      return this.saveToLocalStorage(item)
    }
  },

  saveToLocalStorage(item: { type: string; title: string; data: any; score?: any }): string {
    if (typeof window === 'undefined') return ''
    
    const itemId = Date.now().toString()
    const historyItem = {
      id: itemId,
      type: item.type,
      title: item.title,
      data: item.data,
      score: item.score,
      timestamp: Date.now()
    }
    const existingHistory = JSON.parse(localStorage.getItem('studyHistory') || '[]')
    localStorage.setItem('studyHistory', JSON.stringify([historyItem, ...existingHistory]))
    return itemId
  },

  // Get all history items
  async getAll() {
    const token = typeof window !== 'undefined' ? localStorage.getItem('accessToken') : null
    
    if (token) {
      // User is logged in, fetch from backend
      try {
        const response = await apiClient.get('/history')
        return response.data
      } catch (error) {
        console.error('Failed to fetch history from backend:', error)
        // Fallback to localStorage
        return this.getFromLocalStorage()
      }
    } else {
      // Anonymous user, read from localStorage
      return this.getFromLocalStorage()
    }
  },

  getFromLocalStorage() {
    if (typeof window === 'undefined') return []
    return JSON.parse(localStorage.getItem('studyHistory') || '[]')
  },

  // Delete specific item
  async delete(id: string | number) {
    const token = typeof window !== 'undefined' ? localStorage.getItem('accessToken') : null
    
    if (token && typeof id === 'number') {
      // Backend ID, delete from backend
      try {
        await apiClient.delete(`/history/${id}`)
      } catch (error) {
        console.error('Failed to delete from backend:', error)
      }
    } else {
      // localStorage ID, delete from localStorage
      if (typeof window === 'undefined') return
      const history = JSON.parse(localStorage.getItem('studyHistory') || '[]')
      const newHistory = history.filter((item: any) => item.id !== id)
      localStorage.setItem('studyHistory', JSON.stringify(newHistory))
    }
  },

  // Update history item (for adding scores after completion)
  async update(id: string | number, updates: { title?: string; data?: any; score?: any }) {
    const token = typeof window !== 'undefined' ? localStorage.getItem('accessToken') : null
    
    if (token && typeof id === 'number') {
      // Backend ID, update on backend
      try {
        await apiClient.put(`/history/${id}`, updates)
      } catch (error) {
        console.error('Failed to update history on backend:', error)
      }
    }
    
    // Also update localStorage for consistency
    if (typeof window !== 'undefined') {
      const history = JSON.parse(localStorage.getItem('studyHistory') || '[]')
      const index = history.findIndex((item: any) => item.id === id)
      if (index !== -1) {
        if (updates.title) history[index].title = updates.title
        if (updates.data) history[index].data = updates.data
        if (updates.score) history[index].score = updates.score
        localStorage.setItem('studyHistory', JSON.stringify(history))
      }
    }
  },

  // Clear all history
  async clearAll() {
    const token = typeof window !== 'undefined' ? localStorage.getItem('accessToken') : null
    
    if (token) {
      // User is logged in, clear from backend
      try {
        await apiClient.delete('/history')
      } catch (error) {
        console.error('Failed to clear history from backend:', error)
      }
    }
    // Also clear localStorage
    if (typeof window !== 'undefined') {
      localStorage.removeItem('studyHistory')
    }
  }
}
