'use client'

import { useAuth } from '@/components/AuthProvider'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { adminAPI } from '@/lib/api'

interface User {
  id: number
  email: string
  name: string | null
  surname: string | null
  tier: string
  is_admin: boolean
  created_at: string
  usage?: {
    exam: number
    explain: number
    chat: number
    upload: number
  }
  history_count?: number
  uploads_count?: number
}

interface Stats {
  users: {
    total: number
    free: number
    premium: number
    admin: number
  }
  usage_today: Record<string, number>
  content: {
    total_history: number
    total_uploads: number
  }
  recent_registrations_7d: number
}

interface Transaction {
  id: number
  user_id: number
  user_email: string | null
  stripe_session_id: string
  stripe_customer_id: string | null
  stripe_subscription_id: string | null
  amount: number
  currency: string
  status: string
  tier: string
  event_type: string
  created_at: string
}

interface TokenUsage {
  id: number
  user_id: number | null
  user_email: string | null
  endpoint: string
  model: string
  input_tokens: number
  output_tokens: number
  total_tokens: number
  estimated_cost: number
  created_at: string
}

interface RevenueStats {
  period_days: number
  total_revenue: number
  total_transactions: number
  failed_transactions: number
  daily_revenue: Array<{ date: string; revenue: number }>
  revenue_by_tier: Record<string, number>
  total_token_cost: number
  token_usage_by_endpoint: Record<string, { total_tokens: number; total_cost: number }>
  top_users_by_token_cost: Array<{ user_id: number; user_email: string | null; total_tokens: number; total_cost: number }>
  net_revenue: number
}

interface Activity {
  id: number
  user_id: number
  user_email: string
  user_name: string | null
  user_tier: string
  type: string  // "summary", "flashcards", "truefalse", "exam"
  title: string
  created_at: string
  folder_id: number | null
}

type Tab = 'overview' | 'users' | 'transactions' | 'tokens' | 'revenue' | 'activity'

export default function AdminPage() {
  const { user } = useAuth()
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<Tab>('overview')
  const [users, setUsers] = useState<User[]>([])
  const [filteredUsers, setFilteredUsers] = useState<User[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [stats, setStats] = useState<Stats | null>(null)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [tokenUsage, setTokenUsage] = useState<TokenUsage[]>([])
  const [revenueStats, setRevenueStats] = useState<RevenueStats | null>(null)
  const [activities, setActivities] = useState<Activity[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [editMode, setEditMode] = useState(false)
  const [editForm, setEditForm] = useState({
    name: '',
    surname: '',
    tier: 'free',
    is_admin: false
  })
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null)
  const [userDetails, setUserDetails] = useState<any>(null)

  useEffect(() => {
    if (!user) {
      router.push('/login')
      return
    }
    if (!user.is_admin) {
      router.push('/dashboard')
      return
    }

    loadData()
  }, [user, router])

  useEffect(() => {
    if (searchTerm) {
      const filtered = users.filter(u => 
        u.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
        u.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        u.surname?.toLowerCase().includes(searchTerm.toLowerCase())
      )
      setFilteredUsers(filtered)
    } else {
      setFilteredUsers(users)
    }
  }, [searchTerm, users])

  const loadData = async () => {
    try {
      setLoading(true)
      const [usersData, statsData] = await Promise.all([
        adminAPI.getUsers(0, 100),
        adminAPI.getStats()
      ])
      setUsers(usersData)
      setFilteredUsers(usersData)
      setStats(statsData)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load admin data')
    } finally {
      setLoading(false)
    }
  }

  const loadTransactions = async () => {
    try {
      const data = await adminAPI.getTransactions(0, 100)
      setTransactions(data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load transactions')
    }
  }

  const loadTokenUsage = async () => {
    try {
      const data = await adminAPI.getTokenUsage(0, 100)
      setTokenUsage(data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load token usage')
    }
  }

  const loadRevenueStats = async (days: number = 30) => {
    try {
      const data = await adminAPI.getRevenueStats(days)
      setRevenueStats(data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load revenue stats')
    }
  }

  const loadUserDetails = async (userId: number) => {
    try {
      const data = await adminAPI.getUserDetails(userId)
      setUserDetails(data)
      setSelectedUserId(userId)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load user details')
    }
  }

  const loadActivities = async () => {
    try {
      const data = await adminAPI.getRecentActivities(0, 100)
      setActivities(data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load activities')
    }
  }

  useEffect(() => {
    if (activeTab === 'transactions') {
      loadTransactions()
    } else if (activeTab === 'tokens') {
      loadTokenUsage()
    } else if (activeTab === 'revenue') {
      loadRevenueStats()
    } else if (activeTab === 'activity') {
      loadActivities()
    }
  }, [activeTab])

  const handleEditUser = (user: User) => {
    setSelectedUser(user)
    setEditForm({
      name: user.name || '',
      surname: user.surname || '',
      tier: user.tier,
      is_admin: user.is_admin
    })
    setEditMode(true)
  }

  const handleSaveUser = async () => {
    if (!selectedUser) return

    try {
      await adminAPI.updateUser(selectedUser.id, editForm)
      await loadData()
      setEditMode(false)
      setSelectedUser(null)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update user')
    }
  }

  const handleDeleteUser = async (userId: number) => {
    if (!confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
      return
    }

    try {
      await adminAPI.deleteUser(userId)
      await loadData()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete user')
    }
  }

  const handleClearCache = async () => {
    if (!confirm('Are you sure you want to clear the cache?')) {
      return
    }

    try {
      await adminAPI.clearCache()
      alert('Cache cleared successfully')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to clear cache')
    }
  }

  if (loading && !stats) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#0F172A] via-[#1E293B] to-[#0F172A] pt-20 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 border-4 border-teal-500/30 border-t-teal-500 rounded-full animate-spin"></div>
          <div className="text-slate-300 text-lg">Loading Admin Panel...</div>
        </div>
      </div>
    )
  }

  if (!user?.is_admin) {
    return null
  }

  const tabs = [
    { id: 'overview' as Tab, label: 'Overview', icon: '📊' },
    { id: 'users' as Tab, label: 'Users', icon: '👥' },
    { id: 'activity' as Tab, label: 'Son İşlemler', icon: '📜' },
    { id: 'transactions' as Tab, label: 'Transactions', icon: '💳' },
    { id: 'tokens' as Tab, label: 'Token Usage', icon: '🔑' },
    { id: 'revenue' as Tab, label: 'Revenue', icon: '💰' }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0F172A] via-[#1E293B] to-[#0F172A] pt-20 px-4 pb-12">
      <div className="max-w-7xl mx-auto">
        {/* Header with Gradient */}
        <div className="mb-8 relative">
          <div className="absolute inset-0 bg-gradient-to-r from-teal-500/20 via-cyan-500/20 to-blue-500/20 rounded-3xl blur-2xl"></div>
          <div className="relative backdrop-blur-xl bg-slate-900/50 border border-slate-700/50 rounded-2xl p-8">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-5xl font-bold bg-gradient-to-r from-teal-400 via-cyan-400 to-blue-400 text-transparent bg-clip-text mb-2">
                  Admin Dashboard
                </h1>
                <p className="text-slate-400 text-lg">Complete control center for StudyWithAI</p>
              </div>
              <div className="hidden md:flex items-center gap-3">
                <button
                  onClick={loadData}
                  className="px-5 py-3 bg-gradient-to-r from-teal-500 to-cyan-500 text-white rounded-xl hover:shadow-lg hover:shadow-teal-500/50 transition-all duration-300 font-medium"
                >
                  🔄 Refresh
                </button>
                <button
                  onClick={handleClearCache}
                  className="px-5 py-3 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-xl hover:shadow-lg hover:shadow-orange-500/50 transition-all duration-300 font-medium"
                >
                  🗑️ Clear Cache
                </button>
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-500/10 backdrop-blur-xl border border-red-500/50 rounded-xl text-red-400 flex items-center justify-between animate-shake">
            <span>⚠️ {error}</span>
            <button onClick={() => setError('')} className="text-red-300 hover:text-red-200 text-2xl">&times;</button>
          </div>
        )}

        {/* Tabs with Modern Design */}
        <div className="mb-8 flex gap-3 overflow-x-auto pb-2 scrollbar-thin">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-6 py-3 rounded-xl font-semibold transition-all duration-300 whitespace-nowrap ${
                activeTab === tab.id
                  ? 'bg-gradient-to-r from-teal-500 to-cyan-500 text-white shadow-lg shadow-teal-500/50 scale-105'
                  : 'bg-slate-800/50 backdrop-blur-xl text-slate-300 hover:bg-slate-700/50 border border-slate-700/50'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && stats && (
          <div className="space-y-6 animate-fadeIn">
            {/* Stats Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="group relative overflow-hidden backdrop-blur-xl bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-slate-700/50 rounded-2xl p-6 hover:scale-105 transition-transform duration-300">
                <div className="absolute inset-0 bg-gradient-to-br from-teal-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                <div className="relative">
                  <div className="text-4xl mb-2">👥</div>
                  <div className="text-3xl font-bold text-slate-100 mb-1">{stats.users.total}</div>
                  <div className="text-sm text-slate-400">Total Users</div>
                  <div className="mt-3 flex gap-2 text-xs">
                    <span className="px-2 py-1 bg-teal-500/20 text-teal-300 rounded-lg">Free: {stats.users.free}</span>
                    <span className="px-2 py-1 bg-purple-500/20 text-purple-300 rounded-lg">Premium: {stats.users.premium}</span>
                  </div>
                </div>
              </div>

              <div className="group relative overflow-hidden backdrop-blur-xl bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-slate-700/50 rounded-2xl p-6 hover:scale-105 transition-transform duration-300">
                <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                <div className="relative">
                  <div className="text-4xl mb-2">💎</div>
                  <div className="text-3xl font-bold text-purple-400 mb-1">{stats.users.premium}</div>
                  <div className="text-sm text-slate-400">Premium Users</div>
                  <div className="mt-3 w-full bg-slate-700/50 rounded-full h-2">
                    <div 
                      className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${(stats.users.premium / stats.users.total) * 100}%` }}
                    ></div>
                  </div>
                </div>
              </div>

              <div className="group relative overflow-hidden backdrop-blur-xl bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-slate-700/50 rounded-2xl p-6 hover:scale-105 transition-transform duration-300">
                <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                <div className="relative">
                  <div className="text-4xl mb-2">📚</div>
                  <div className="text-3xl font-bold text-cyan-400 mb-1">{stats.content.total_history}</div>
                  <div className="text-sm text-slate-400">Total Summaries</div>
                  <div className="mt-3 text-xs text-slate-500">
                    📤 {stats.content.total_uploads} Uploads
                  </div>
                </div>
              </div>

              <div className="group relative overflow-hidden backdrop-blur-xl bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-slate-700/50 rounded-2xl p-6 hover:scale-105 transition-transform duration-300">
                <div className="absolute inset-0 bg-gradient-to-br from-green-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                <div className="relative">
                  <div className="text-4xl mb-2">✨</div>
                  <div className="text-3xl font-bold text-green-400 mb-1">{stats.recent_registrations_7d}</div>
                  <div className="text-sm text-slate-400">New Users (7d)</div>
                  <div className="mt-3 text-xs text-green-500/70">
                    📈 {(stats.recent_registrations_7d / 7).toFixed(1)} per day
                  </div>
                </div>
              </div>
            </div>

            {/* Usage Today */}
            {Object.keys(stats.usage_today).length > 0 && (
              <div className="backdrop-blur-xl bg-slate-800/50 border border-slate-700/50 rounded-2xl p-6">
                <h3 className="text-2xl font-bold text-slate-100 mb-4 flex items-center gap-2">
                  <span>📊</span> Today's Activity
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {Object.entries(stats.usage_today).map(([key, value]) => (
                    <div key={key} className="bg-slate-900/50 rounded-xl p-4 border border-slate-700/30">
                      <div className="text-2xl font-bold text-teal-400">{value}</div>
                      <div className="text-sm text-slate-400 capitalize">{key.replace('_', ' ')}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Users Tab */}
        {activeTab === 'users' && (
          <div className="space-y-6 animate-fadeIn">
            {/* Search Bar */}
            <div className="backdrop-blur-xl bg-slate-800/50 border border-slate-700/50 rounded-2xl p-4">
              <input
                type="text"
                placeholder="🔍 Search users by email or name..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full px-6 py-3 bg-slate-900/50 border border-slate-700/50 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-500/50"
              />
            </div>

            {/* Users Table */}
            <div className="backdrop-blur-xl bg-slate-800/50 border border-slate-700/50 rounded-2xl p-6 overflow-hidden">
              <h2 className="text-2xl font-bold text-slate-100 mb-6">User Management ({filteredUsers.length})</h2>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-700">
                      <th className="text-left py-4 px-4 text-slate-300 font-semibold">ID</th>
                      <th className="text-left py-4 px-4 text-slate-300 font-semibold">Email</th>
                      <th className="text-left py-4 px-4 text-slate-300 font-semibold">Name</th>
                      <th className="text-left py-4 px-4 text-slate-300 font-semibold">Tier</th>
                      <th className="text-left py-4 px-4 text-slate-300 font-semibold">Status</th>
                      <th className="text-left py-4 px-4 text-slate-300 font-semibold">Joined</th>
                      <th className="text-left py-4 px-4 text-slate-300 font-semibold">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredUsers.map((u) => (
                      <tr key={u.id} className="border-b border-slate-800/50 hover:bg-slate-700/30 transition-colors">
                        <td className="py-4 px-4 text-slate-300 font-mono">{u.id}</td>
                        <td className="py-4 px-4 text-slate-300">{u.email}</td>
                        <td className="py-4 px-4 text-slate-300">
                          {u.name || u.surname ? `${u.name || ''} ${u.surname || ''}`.trim() : '—'}
                        </td>
                        <td className="py-4 px-4">
                          <span className={`px-3 py-1 rounded-lg text-sm font-medium ${
                            u.tier === 'premium' || u.tier === 'pro' 
                              ? 'bg-gradient-to-r from-purple-500/20 to-pink-500/20 text-purple-300 border border-purple-500/30' 
                              : 'bg-slate-700/50 text-slate-300'
                          }`}>
                            {u.tier}
                          </span>
                        </td>
                        <td className="py-4 px-4">
                          {u.is_admin ? (
                            <span className="px-3 py-1 rounded-lg text-sm font-medium bg-gradient-to-r from-red-500/20 to-orange-500/20 text-red-300 border border-red-500/30">
                              👑 Admin
                            </span>
                          ) : (
                            <span className="text-slate-500">User</span>
                          )}
                        </td>
                        <td className="py-4 px-4 text-slate-400 text-sm">
                          {new Date(u.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                        </td>
                        <td className="py-4 px-4">
                          <div className="flex gap-2">
                            <button
                              onClick={() => handleEditUser(u)}
                              className="px-3 py-1.5 bg-blue-500/20 text-blue-300 rounded-lg text-sm hover:bg-blue-500/30 transition border border-blue-500/30"
                            >
                              ✏️ Edit
                            </button>
                            <button
                              onClick={() => loadUserDetails(u.id)}
                              className="px-3 py-1.5 bg-green-500/20 text-green-300 rounded-lg text-sm hover:bg-green-500/30 transition border border-green-500/30"
                            >
                              👁️ View
                            </button>
                            {u.id !== user.id && (
                              <button
                                onClick={() => handleDeleteUser(u.id)}
                                className="px-3 py-1.5 bg-red-500/20 text-red-300 rounded-lg text-sm hover:bg-red-500/30 transition border border-red-500/30"
                              >
                                🗑️
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* User Details Modal */}
            {userDetails && selectedUserId && (
              <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fadeIn" onClick={() => { setUserDetails(null); setSelectedUserId(null) }}>
                <div className="backdrop-blur-xl bg-slate-900/95 border border-slate-700/50 rounded-2xl p-8 max-w-5xl w-full max-h-[90vh] overflow-y-auto shadow-2xl" onClick={(e) => e.stopPropagation()}>
                  <div className="flex justify-between items-center mb-6">
                    <h3 className="text-3xl font-bold bg-gradient-to-r from-teal-400 to-cyan-400 text-transparent bg-clip-text">
                      User Details
                    </h3>
                    <button 
                      onClick={() => { setUserDetails(null); setSelectedUserId(null) }} 
                      className="text-slate-400 hover:text-slate-200 text-3xl w-10 h-10 flex items-center justify-center hover:bg-slate-800 rounded-full transition"
                    >
                      &times;
                    </button>
                  </div>
                  
                  <div className="space-y-6">
                    {/* User Info */}
                    <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
                      <h4 className="text-xl font-semibold text-slate-200 mb-4 flex items-center gap-2">
                        <span>👤</span> User Information
                      </h4>
                      <div className="grid grid-cols-2 gap-6">
                        <div>
                          <div className="text-sm text-slate-400 mb-1">Email</div>
                          <div className="text-slate-100 font-medium">{userDetails.user.email}</div>
                        </div>
                        <div>
                          <div className="text-sm text-slate-400 mb-1">Tier</div>
                          <div className="text-slate-100 font-medium capitalize">{userDetails.user.tier}</div>
                        </div>
                        <div>
                          <div className="text-sm text-slate-400 mb-1">Total Revenue</div>
                          <div className="text-green-400 font-bold text-xl">${userDetails.total_paid.toFixed(2)}</div>
                        </div>
                        <div>
                          <div className="text-sm text-slate-400 mb-1">Total Token Cost</div>
                          <div className="text-orange-400 font-bold text-xl">${userDetails.token_usage.total_cost.toFixed(4)}</div>
                        </div>
                      </div>
                    </div>

                    {/* Transactions */}
                    <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
                      <h4 className="text-xl font-semibold text-slate-200 mb-4 flex items-center gap-2">
                        <span>💳</span> Transactions ({userDetails.transactions.length})
                      </h4>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-slate-700">
                              <th className="text-left py-3 px-3 text-slate-300">Date</th>
                              <th className="text-left py-3 px-3 text-slate-300">Amount</th>
                              <th className="text-left py-3 px-3 text-slate-300">Status</th>
                              <th className="text-left py-3 px-3 text-slate-300">Type</th>
                            </tr>
                          </thead>
                          <tbody>
                            {userDetails.transactions.map((t: any) => (
                              <tr key={t.id} className="border-b border-slate-800/50">
                                <td className="py-3 px-3 text-slate-300">{new Date(t.created_at).toLocaleDateString()}</td>
                                <td className="py-3 px-3 text-green-400 font-semibold">${t.amount.toFixed(2)}</td>
                                <td className="py-3 px-3">
                                  <span className={`px-2 py-1 rounded-lg text-xs font-medium ${
                                    t.status === 'completed' ? 'bg-green-500/20 text-green-300' : 'bg-red-500/20 text-red-300'
                                  }`}>
                                    {t.status}
                                  </span>
                                </td>
                                <td className="py-3 px-3 text-slate-400 text-xs">{t.event_type}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    {/* Token Usage */}
                    <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
                      <h4 className="text-xl font-semibold text-slate-200 mb-4 flex items-center gap-2">
                        <span>🔑</span> Token Usage
                      </h4>
                      <div className="grid grid-cols-2 gap-4 mb-6">
                        <div className="bg-slate-900/50 rounded-lg p-4">
                          <div className="text-sm text-slate-400 mb-1">Total Tokens</div>
                          <div className="text-slate-100 font-bold text-2xl">{userDetails.token_usage.total_tokens.toLocaleString()}</div>
                        </div>
                        <div className="bg-slate-900/50 rounded-lg p-4">
                          <div className="text-sm text-slate-400 mb-1">Total Cost</div>
                          <div className="text-orange-400 font-bold text-2xl">${userDetails.token_usage.total_cost.toFixed(4)}</div>
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-slate-400 mb-3">By Endpoint</div>
                        <div className="space-y-2">
                          {Object.entries(userDetails.token_usage.by_endpoint).map(([endpoint, data]: [string, any]) => (
                            <div key={endpoint} className="flex justify-between items-center py-2 px-3 bg-slate-900/30 rounded-lg">
                              <span className="text-slate-300 font-medium">{endpoint}</span>
                              <span className="text-slate-400 text-sm">
                                {data.total_tokens.toLocaleString()} tokens 
                                <span className="text-orange-400 ml-2">${data.total_cost.toFixed(4)}</span>
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Transactions Tab */}
        {activeTab === 'transactions' && (
          <div className="backdrop-blur-xl bg-slate-800/50 border border-slate-700/50 rounded-2xl p-6 animate-fadeIn">
            <h2 className="text-2xl font-bold text-slate-100 mb-6 flex items-center gap-2">
              <span>💳</span> Transactions
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left py-4 px-4 text-slate-300 font-semibold">ID</th>
                    <th className="text-left py-4 px-4 text-slate-300 font-semibold">User</th>
                    <th className="text-left py-4 px-4 text-slate-300 font-semibold">Amount</th>
                    <th className="text-left py-4 px-4 text-slate-300 font-semibold">Status</th>
                    <th className="text-left py-4 px-4 text-slate-300 font-semibold">Tier</th>
                    <th className="text-left py-4 px-4 text-slate-300 font-semibold">Type</th>
                    <th className="text-left py-4 px-4 text-slate-300 font-semibold">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((t) => (
                    <tr key={t.id} className="border-b border-slate-800/50 hover:bg-slate-700/30 transition-colors">
                      <td className="py-4 px-4 text-slate-300 font-mono">{t.id}</td>
                      <td className="py-4 px-4 text-slate-300">{t.user_email || `User ${t.user_id}`}</td>
                      <td className="py-4 px-4 text-green-400 font-bold text-lg">${t.amount.toFixed(2)}</td>
                      <td className="py-4 px-4">
                        <span className={`px-3 py-1 rounded-lg text-sm font-medium ${
                          t.status === 'completed' ? 'bg-green-500/20 text-green-300 border border-green-500/30' : 
                          t.status === 'failed' ? 'bg-red-500/20 text-red-300 border border-red-500/30' : 
                          'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30'
                        }`}>
                          {t.status}
                        </span>
                      </td>
                      <td className="py-4 px-4 text-slate-300 capitalize">{t.tier}</td>
                      <td className="py-4 px-4 text-slate-400 text-sm">{t.event_type}</td>
                      <td className="py-4 px-4 text-slate-400 text-sm">
                        {new Date(t.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Token Usage Tab */}
        {activeTab === 'tokens' && (
          <div className="backdrop-blur-xl bg-slate-800/50 border border-slate-700/50 rounded-2xl p-6 animate-fadeIn">
            <h2 className="text-2xl font-bold text-slate-100 mb-6 flex items-center gap-2">
              <span>🔑</span> Token Usage
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left py-4 px-4 text-slate-300 font-semibold">User</th>
                    <th className="text-left py-4 px-4 text-slate-300 font-semibold">Endpoint</th>
                    <th className="text-left py-4 px-4 text-slate-300 font-semibold">Model</th>
                    <th className="text-left py-4 px-4 text-slate-300 font-semibold">Input</th>
                    <th className="text-left py-4 px-4 text-slate-300 font-semibold">Output</th>
                    <th className="text-left py-4 px-4 text-slate-300 font-semibold">Total</th>
                    <th className="text-left py-4 px-4 text-slate-300 font-semibold">Cost</th>
                    <th className="text-left py-4 px-4 text-slate-300 font-semibold">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {tokenUsage.map((u) => (
                    <tr key={u.id} className="border-b border-slate-800/50 hover:bg-slate-700/30 transition-colors">
                      <td className="py-4 px-4 text-slate-300">{u.user_email || 'Anonymous'}</td>
                      <td className="py-4 px-4 text-slate-300 font-medium">{u.endpoint}</td>
                      <td className="py-4 px-4 text-slate-400 text-sm">{u.model}</td>
                      <td className="py-4 px-4 text-slate-300">{u.input_tokens.toLocaleString()}</td>
                      <td className="py-4 px-4 text-slate-300">{u.output_tokens.toLocaleString()}</td>
                      <td className="py-4 px-4 text-teal-400 font-bold">{u.total_tokens.toLocaleString()}</td>
                      <td className="py-4 px-4 text-orange-400 font-semibold">${u.estimated_cost.toFixed(4)}</td>
                      <td className="py-4 px-4 text-slate-400 text-sm">
                        {new Date(u.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Revenue Tab */}
        {activeTab === 'revenue' && revenueStats && (
          <div className="space-y-6 animate-fadeIn">
            {/* Revenue Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="backdrop-blur-xl bg-gradient-to-br from-green-500/10 to-emerald-500/10 border border-green-500/30 rounded-2xl p-6">
                <div className="text-3xl mb-2">💵</div>
                <div className="text-3xl font-bold text-green-400 mb-1">${revenueStats.total_revenue.toFixed(2)}</div>
                <div className="text-sm text-slate-400">Total Revenue</div>
              </div>
              <div className="backdrop-blur-xl bg-gradient-to-br from-orange-500/10 to-red-500/10 border border-orange-500/30 rounded-2xl p-6">
                <div className="text-3xl mb-2">💰</div>
                <div className="text-3xl font-bold text-orange-400 mb-1">${revenueStats.total_token_cost.toFixed(2)}</div>
                <div className="text-sm text-slate-400">Token Costs</div>
              </div>
              <div className="backdrop-blur-xl bg-gradient-to-br from-teal-500/10 to-cyan-500/10 border border-teal-500/30 rounded-2xl p-6">
                <div className="text-3xl mb-2">📈</div>
                <div className="text-3xl font-bold text-teal-400 mb-1">${revenueStats.net_revenue.toFixed(2)}</div>
                <div className="text-sm text-slate-400">Net Revenue</div>
              </div>
              <div className="backdrop-blur-xl bg-gradient-to-br from-blue-500/10 to-indigo-500/10 border border-blue-500/30 rounded-2xl p-6">
                <div className="text-3xl mb-2">🧾</div>
                <div className="text-3xl font-bold text-blue-400 mb-1">{revenueStats.total_transactions}</div>
                <div className="text-sm text-slate-400">Total Transactions</div>
              </div>
            </div>

            {/* Revenue by Tier */}
            <div className="backdrop-blur-xl bg-slate-800/50 border border-slate-700/50 rounded-2xl p-6">
              <h3 className="text-2xl font-bold text-slate-100 mb-6 flex items-center gap-2">
                <span>💎</span> Revenue by Tier
              </h3>
              <div className="space-y-3">
                {Object.entries(revenueStats.revenue_by_tier).map(([tier, revenue]) => {
                  const percentage = (revenue / revenueStats.total_revenue) * 100
                  return (
                    <div key={tier} className="bg-slate-900/50 rounded-xl p-4">
                      <div className="flex justify-between mb-2">
                        <span className="text-slate-300 capitalize font-medium">{tier}</span>
                        <span className="text-green-400 font-bold">${revenue.toFixed(2)}</span>
                      </div>
                      <div className="w-full bg-slate-700/50 rounded-full h-3">
                        <div 
                          className="bg-gradient-to-r from-green-500 to-emerald-500 h-3 rounded-full transition-all duration-500"
                          style={{ width: `${percentage}%` }}
                        ></div>
                      </div>
                      <div className="text-xs text-slate-500 mt-1">{percentage.toFixed(1)}%</div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Token Usage by Endpoint */}
            <div className="backdrop-blur-xl bg-slate-800/50 border border-slate-700/50 rounded-2xl p-6">
              <h3 className="text-2xl font-bold text-slate-100 mb-6 flex items-center gap-2">
                <span>🔑</span> Token Usage by Endpoint
              </h3>
              <div className="space-y-3">
                {Object.entries(revenueStats.token_usage_by_endpoint).map(([endpoint, data]) => (
                  <div key={endpoint} className="flex justify-between items-center py-3 px-4 bg-slate-900/50 rounded-xl hover:bg-slate-900/70 transition-colors">
                    <span className="text-slate-300 font-medium">{endpoint}</span>
                    <div className="text-right">
                      <div className="text-slate-400 text-sm">{data.total_tokens.toLocaleString()} tokens</div>
                      <div className="text-orange-400 font-semibold">${data.total_cost.toFixed(2)}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Top Users by Token Cost */}
            <div className="backdrop-blur-xl bg-slate-800/50 border border-slate-700/50 rounded-2xl p-6">
              <h3 className="text-2xl font-bold text-slate-100 mb-6 flex items-center gap-2">
                <span>👑</span> Top Users by Token Cost
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-700">
                      <th className="text-left py-3 px-4 text-slate-300 font-semibold">Rank</th>
                      <th className="text-left py-3 px-4 text-slate-300 font-semibold">User</th>
                      <th className="text-left py-3 px-4 text-slate-300 font-semibold">Tokens</th>
                      <th className="text-left py-3 px-4 text-slate-300 font-semibold">Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {revenueStats.top_users_by_token_cost.map((u, index) => (
                      <tr key={u.user_id} className="border-b border-slate-800/50 hover:bg-slate-700/30 transition-colors">
                        <td className="py-3 px-4 text-slate-400">
                          {index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `#${index + 1}`}
                        </td>
                        <td className="py-3 px-4 text-slate-300">{u.user_email || `User ${u.user_id}`}</td>
                        <td className="py-3 px-4 text-teal-400 font-semibold">{u.total_tokens.toLocaleString()}</td>
                        <td className="py-3 px-4 text-orange-400 font-bold">${u.total_cost.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Activity Tab */}
        {activeTab === 'activity' && (
          <div className="backdrop-blur-xl bg-slate-800/50 border border-slate-700/50 rounded-2xl p-6 animate-fadeIn">
            <h2 className="text-2xl font-bold text-slate-100 mb-6 flex items-center gap-2">
              <span>📜</span> Son İşlemler ({activities.length})
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left py-4 px-4 text-slate-300 font-semibold">Tarih</th>
                    <th className="text-left py-4 px-4 text-slate-300 font-semibold">Kullanıcı</th>
                    <th className="text-left py-4 px-4 text-slate-300 font-semibold">İşlem Tipi</th>
                    <th className="text-left py-4 px-4 text-slate-300 font-semibold">Başlık</th>
                    <th className="text-left py-4 px-4 text-slate-300 font-semibold">Tier</th>
                  </tr>
                </thead>
                <tbody>
                  {activities.map((activity) => {
                    const typeIcons = {
                      'summary': '📄',
                      'flashcards': '🗂️',
                      'truefalse': '✅',
                      'exam': '📝'
                    }
                    const typeColors = {
                      'summary': 'from-teal-500/20 to-cyan-500/20 border-teal-500/30 text-teal-300',
                      'flashcards': 'from-purple-500/20 to-pink-500/20 border-purple-500/30 text-purple-300',
                      'truefalse': 'from-green-500/20 to-emerald-500/20 border-green-500/30 text-green-300',
                      'exam': 'from-orange-500/20 to-red-500/20 border-orange-500/30 text-orange-300'
                    }
                    return (
                      <tr key={activity.id} className="border-b border-slate-800/50 hover:bg-slate-700/30 transition-colors">
                        <td className="py-4 px-4 text-slate-400 text-sm">
                          {new Date(activity.created_at).toLocaleString('tr-TR', { 
                            day: '2-digit',
                            month: '2-digit',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </td>
                        <td className="py-4 px-4">
                          <div className="text-slate-300 font-medium">{activity.user_email}</div>
                          {activity.user_name && (
                            <div className="text-slate-500 text-sm">{activity.user_name}</div>
                          )}
                        </td>
                        <td className="py-4 px-4">
                          <span className={`px-3 py-1 rounded-lg text-sm font-medium border bg-gradient-to-r ${typeColors[activity.type as keyof typeof typeColors] || 'bg-slate-700/50 text-slate-300'}`}>
                            <span className="mr-1">{typeIcons[activity.type as keyof typeof typeIcons]}</span>
                            {activity.type}
                          </span>
                        </td>
                        <td className="py-4 px-4 text-slate-300 max-w-md truncate">
                          {activity.title}
                        </td>
                        <td className="py-4 px-4">
                          <span className={`px-2 py-1 rounded-lg text-xs font-medium ${
                            activity.user_tier === 'premium' || activity.user_tier === 'pro'
                              ? 'bg-gradient-to-r from-purple-500/20 to-pink-500/20 text-purple-300 border border-purple-500/30'
                              : 'bg-slate-700/50 text-slate-400'
                          }`}>
                            {activity.user_tier}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Edit User Modal */}
        {editMode && selectedUser && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fadeIn">
            <div className="backdrop-blur-xl bg-slate-900/95 border border-slate-700/50 rounded-2xl p-8 max-w-md w-full shadow-2xl">
              <h3 className="text-3xl font-bold bg-gradient-to-r from-teal-400 to-cyan-400 text-transparent bg-clip-text mb-6">
                Edit User
              </h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Email</label>
                  <input
                    type="email"
                    value={selectedUser.email}
                    disabled
                    className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-xl text-slate-400 cursor-not-allowed"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Name</label>
                  <input
                    type="text"
                    value={editForm.name}
                    onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                    className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-xl text-slate-100 focus:outline-none focus:ring-2 focus:ring-teal-500/50"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Surname</label>
                  <input
                    type="text"
                    value={editForm.surname}
                    onChange={(e) => setEditForm({ ...editForm, surname: e.target.value })}
                    className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-xl text-slate-100 focus:outline-none focus:ring-2 focus:ring-teal-500/50"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Tier</label>
                  <select
                    value={editForm.tier}
                    onChange={(e) => setEditForm({ ...editForm, tier: e.target.value })}
                    className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-xl text-slate-100 focus:outline-none focus:ring-2 focus:ring-teal-500/50"
                  >
                    <option value="free">Free</option>
                    <option value="standard">Standard</option>
                    <option value="premium">Premium</option>
                    <option value="pro">Pro</option>
                  </select>
                </div>

                <div className="flex items-center gap-3 p-4 bg-slate-800/30 rounded-xl border border-slate-700/50">
                  <input
                    type="checkbox"
                    checked={editForm.is_admin}
                    onChange={(e) => setEditForm({ ...editForm, is_admin: e.target.checked })}
                    className="w-5 h-5 rounded accent-teal-500"
                  />
                  <label className="text-slate-300 font-medium">Grant Admin Access</label>
                </div>
              </div>

              <div className="flex gap-4 mt-8">
                <button
                  onClick={handleSaveUser}
                  className="flex-1 px-6 py-3 bg-gradient-to-r from-teal-500 to-cyan-500 text-white rounded-xl hover:shadow-lg hover:shadow-teal-500/50 transition-all duration-300 font-semibold"
                >
                  💾 Save Changes
                </button>
                <button
                  onClick={() => {
                    setEditMode(false)
                    setSelectedUser(null)
                  }}
                  className="flex-1 px-6 py-3 bg-slate-700/50 text-slate-300 rounded-xl hover:bg-slate-600/50 transition border border-slate-600"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      <style jsx global>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out;
        }

        .scrollbar-thin::-webkit-scrollbar {
          height: 6px;
        }

        .scrollbar-thin::-webkit-scrollbar-track {
          background: rgba(15, 23, 42, 0.5);
          border-radius: 10px;
        }

        .scrollbar-thin::-webkit-scrollbar-thumb {
          background: rgba(20, 184, 166, 0.5);
          border-radius: 10px;
        }

        .scrollbar-thin::-webkit-scrollbar-thumb:hover {
          background: rgba(20, 184, 166, 0.7);
        }
      `}</style>
    </div>
  )
}
