import axios from 'axios'

// In production, use the backend URL directly
// In development, use the proxy via /api
const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE || '/api'

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,  // Send cookies with requests
})

// No need to manually add auth tokens - cookies are sent automatically

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
      
      try {
        // Try to refresh using cookie-based refresh token
        await axios.post(`${API_BASE}/auth/refresh`, {}, { withCredentials: true })
        // Retry original request
        return apiClient(originalRequest)
      } catch (refreshError) {
        // Refresh failed, redirect to login
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
    // Try to save to backend first (cookies sent automatically)
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
