import axios from 'axios'

// In production, use the backend URL directly
// In development, use the proxy via /api
const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE || '/api'

// Log API base URL in development or if it's using the default
if (typeof window !== 'undefined' && (process.env.NODE_ENV === 'development' || API_BASE === '/api')) {
  console.log('[API] Using API_BASE:', API_BASE)
  if (API_BASE === '/api' && process.env.NODE_ENV === 'production') {
    console.warn('[API] WARNING: Using default /api endpoint in production. Set NEXT_PUBLIC_API_URL environment variable!')
  }
}

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,  // Still send cookies for backward compatibility
  timeout: 180000,  // 3 minute timeout (AI now generates more comprehensive content)
})

// Add Authorization header to all requests
apiClient.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token')
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
    
    // Don't handle token refresh for auth endpoints
    const isAuthEndpoint = originalRequest?.url?.includes('/auth/login') || 
                          originalRequest?.url?.includes('/auth/register')
    
    if (error.response?.status === 401 && !originalRequest._retry && typeof window !== 'undefined' && !isAuthEndpoint) {
      originalRequest._retry = true
      
      try {
        const refreshToken = localStorage.getItem('refresh_token')
        if (!refreshToken) {
          throw new Error('No refresh token')
        }
        
        // Try to refresh token
        const response = await axios.post(`${API_BASE}/auth/refresh`, 
          { refresh_token: refreshToken },
          { withCredentials: true }
        )
        
        const { access_token, refresh_token } = response.data
        localStorage.setItem('access_token', access_token)
        localStorage.setItem('refresh_token', refresh_token)
        
        // Retry original request with new token
        originalRequest.headers.Authorization = `Bearer ${access_token}`
        return apiClient(originalRequest)
      } catch (refreshError) {
        // Refresh failed, clear tokens and redirect to login
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        
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
    // Try to save to backend first (tokens sent automatically via interceptor)
    try {
      const response = await apiClient.post('/history', item)
      return response.data.id // Return backend ID
    } catch (error: any) {
      // If 401 (not logged in), save to localStorage
      if (error.response?.status === 401) {
        return this.saveToLocalStorage(item)
      }
      console.error('Failed to save history:', error)
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
    try {
      const response = await apiClient.get('/history')
      return response.data
    } catch (error: any) {
      // If 401 (not logged in), use localStorage
      if (error.response?.status === 401) {
        return this.getFromLocalStorage()
      }
      console.error('Failed to fetch history:', error)
      return this.getFromLocalStorage()
    }
  },

  getFromLocalStorage() {
    if (typeof window === 'undefined') return []
    return JSON.parse(localStorage.getItem('studyHistory') || '[]')
  },

  // Delete specific item
  async delete(id: string | number) {
    if (typeof id === 'number') {
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

  // Update history item (for adding scores after completion or moving to folder)
  async update(id: string | number, updates: { title?: string; data?: any; score?: any; folder_id?: number | null }) {
    if (typeof id === 'number') {
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
        if (updates.folder_id !== undefined) history[index].folder_id = updates.folder_id
        localStorage.setItem('studyHistory', JSON.stringify(history))
      }
    }
  },

  // Clear all history
  async clearAll() {
    try {
      await apiClient.delete('/history')
    } catch (error) {
      console.error('Failed to clear history:', error)
    }
    // Also clear localStorage
    if (typeof window !== 'undefined') {
      localStorage.removeItem('studyHistory')
    }
  },

  // Get history filtered by folder
  async getByFolder(folderId?: number) {
    try {
      const params = folderId !== undefined ? { folder_id: folderId } : {}
      const response = await apiClient.get('/history', { params })
      return response.data
    } catch (error: any) {
      // If 401 (not logged in), use localStorage
      if (error.response?.status === 401 && typeof window !== 'undefined') {
        const allHistory = JSON.parse(localStorage.getItem('studyHistory') || '[]')
        if (folderId === undefined) return allHistory
        if (folderId === 0) return allHistory.filter((item: any) => !item.folder_id)
        return allHistory.filter((item: any) => item.folder_id === folderId)
      }
      console.error('Failed to get history:', error)
      return []
    }
  }
}

// Admin API
export const adminAPI = {
  // Get all users
  async getUsers(skip: number = 0, limit: number = 100) {
    const response = await apiClient.get('/admin/users', { params: { skip, limit } })
    return response.data
  },

  // Get user by ID
  async getUser(userId: number) {
    const response = await apiClient.get(`/admin/users/${userId}`)
    return response.data
  },

  // Update user
  async updateUser(userId: number, updates: { name?: string; surname?: string; tier?: string; is_admin?: boolean }) {
    const response = await apiClient.put(`/admin/users/${userId}`, updates)
    return response.data
  },

  // Delete user
  async deleteUser(userId: number) {
    const response = await apiClient.delete(`/admin/users/${userId}`)
    return response.data
  },

  // Get admin statistics
  async getStats() {
    const response = await apiClient.get('/admin/stats')
    return response.data
  },

  // Clear cache
  async clearCache() {
    const response = await apiClient.delete('/admin/clear-cache')
    return response.data
  },

  // Get transactions
  async getTransactions(skip: number = 0, limit: number = 100, userId?: number) {
    const params: any = { skip, limit }
    if (userId) params.user_id = userId
    const response = await apiClient.get('/admin/transactions', { params })
    return response.data
  },

  // Get token usage
  async getTokenUsage(skip: number = 0, limit: number = 100, userId?: number, endpoint?: string) {
    const params: any = { skip, limit }
    if (userId) params.user_id = userId
    if (endpoint) params.endpoint = endpoint
    const response = await apiClient.get('/admin/token-usage', { params })
    return response.data
  },

  // Get revenue statistics
  async getRevenueStats(days: number = 30) {
    const response = await apiClient.get('/admin/revenue', { params: { days } })
    return response.data
  },

  // Get user detailed info
  async getUserDetails(userId: number) {
    const response = await apiClient.get(`/admin/users/${userId}/details`)
    return response.data
  }
}

// Folder API
export const folderAPI = {
  // Get all folders
  async getAll() {
    const response = await apiClient.get('/folders')
    return response.data
  },

  // Create a new folder
  async create(folder: { name: string; color?: string; icon?: string }) {
    const response = await apiClient.post('/folders', folder)
    return response.data
  },

  // Update a folder
  async update(id: number, updates: { name?: string; color?: string; icon?: string }) {
    const response = await apiClient.put(`/folders/${id}`, updates)
    return response.data
  },

  // Delete a folder
  async delete(id: number) {
    await apiClient.delete(`/folders/${id}`)
  }
}
