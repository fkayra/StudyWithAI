import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || '/api'

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('accessToken')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle token refresh on 401
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    
    if (error.response?.status === 401 && !originalRequest._retry) {
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
          window.location.href = '/login'
        }
      }
    }
    
    return Promise.reject(error)
  }
)
