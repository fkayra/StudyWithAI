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

type Tab = 'overview' | 'users' | 'transactions' | 'tokens' | 'revenue'

export default function AdminPage() {
  const { user } = useAuth()
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<Tab>('overview')
  const [users, setUsers] = useState<User[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [tokenUsage, setTokenUsage] = useState<TokenUsage[]>([])
  const [revenueStats, setRevenueStats] = useState<RevenueStats | null>(null)
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

  const loadData = async () => {
    try {
      setLoading(true)
      const [usersData, statsData] = await Promise.all([
        adminAPI.getUsers(0, 100),
        adminAPI.getStats()
      ])
      setUsers(usersData)
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

  useEffect(() => {
    if (activeTab === 'transactions') {
      loadTransactions()
    } else if (activeTab === 'tokens') {
      loadTokenUsage()
    } else if (activeTab === 'revenue') {
      loadRevenueStats()
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
      <div className="min-h-screen bg-[#0F172A] pt-20 flex items-center justify-center">
        <div className="text-slate-300">Loading...</div>
      </div>
    )
  }

  if (!user?.is_admin) {
    return null
  }

  const tabs = [
    { id: 'overview' as Tab, label: '📊 Overview', icon: '📊' },
    { id: 'users' as Tab, label: '👥 Users', icon: '👥' },
    { id: 'transactions' as Tab, label: '💳 Transactions', icon: '💳' },
    { id: 'tokens' as Tab, label: '🔑 Token Usage', icon: '🔑' },
    { id: 'revenue' as Tab, label: '💰 Revenue', icon: '💰' }
  ]

  return (
    <div className="min-h-screen bg-[#0F172A] pt-20 px-4 pb-12">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-slate-100 mb-2">Admin Panel</h1>
          <p className="text-slate-400">Manage users, subscriptions, transactions, and analytics</p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400">
            {error}
            <button onClick={() => setError('')} className="ml-4 text-red-300 hover:text-red-200">×</button>
          </div>
        )}

        {/* Tabs */}
        <div className="mb-6 flex gap-2 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-lg font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-gradient-to-r from-teal-500 to-cyan-500 text-white'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && stats && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="glass-card border border-slate-700/50 p-6">
                <div className="text-2xl font-bold text-slate-100 mb-1">{stats.users.total}</div>
                <div className="text-sm text-slate-400">Total Users</div>
              </div>
              <div className="glass-card border border-slate-700/50 p-6">
                <div className="text-2xl font-bold text-blue-400 mb-1">{stats.users.premium}</div>
                <div className="text-sm text-slate-400">Premium Users</div>
              </div>
              <div className="glass-card border border-slate-700/50 p-6">
                <div className="text-2xl font-bold text-teal-400 mb-1">{stats.content.total_history}</div>
                <div className="text-sm text-slate-400">Total History Items</div>
              </div>
              <div className="glass-card border border-slate-700/50 p-6">
                <div className="text-2xl font-bold text-purple-400 mb-1">{stats.recent_registrations_7d}</div>
                <div className="text-sm text-slate-400">New Users (7d)</div>
              </div>
            </div>

            <div className="flex gap-4">
              <button
                onClick={loadData}
                className="px-4 py-2 bg-gradient-to-r from-teal-500 to-cyan-500 text-white rounded-lg hover:shadow-lg transition-all"
              >
                Refresh Data
              </button>
              <button
                onClick={handleClearCache}
                className="px-4 py-2 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-lg hover:shadow-lg transition-all"
              >
                Clear Cache
              </button>
            </div>
          </div>
        )}

        {/* Users Tab */}
        {activeTab === 'users' && (
          <div className="glass-card border border-slate-700/50 p-6">
            <h2 className="text-2xl font-bold text-slate-100 mb-4">User Management</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left py-3 px-4 text-slate-300">ID</th>
                    <th className="text-left py-3 px-4 text-slate-300">Email</th>
                    <th className="text-left py-3 px-4 text-slate-300">Name</th>
                    <th className="text-left py-3 px-4 text-slate-300">Tier</th>
                    <th className="text-left py-3 px-4 text-slate-300">Admin</th>
                    <th className="text-left py-3 px-4 text-slate-300">Created</th>
                    <th className="text-left py-3 px-4 text-slate-300">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-b border-slate-800 hover:bg-slate-800/30">
                      <td className="py-3 px-4 text-slate-300">{u.id}</td>
                      <td className="py-3 px-4 text-slate-300">{u.email}</td>
                      <td className="py-3 px-4 text-slate-300">
                        {u.name || ''} {u.surname || ''}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded text-xs ${
                          u.tier === 'premium' || u.tier === 'pro' 
                            ? 'bg-purple-500/20 text-purple-300' 
                            : 'bg-slate-700 text-slate-300'
                        }`}>
                          {u.tier}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        {u.is_admin ? (
                          <span className="px-2 py-1 rounded text-xs bg-red-500/20 text-red-300">Admin</span>
                        ) : (
                          <span className="text-slate-500">-</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-slate-400 text-sm">
                        {new Date(u.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleEditUser(u)}
                            className="px-3 py-1 bg-blue-500/20 text-blue-300 rounded text-sm hover:bg-blue-500/30 transition"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => loadUserDetails(u.id)}
                            className="px-3 py-1 bg-green-500/20 text-green-300 rounded text-sm hover:bg-green-500/30 transition"
                          >
                            Details
                          </button>
                          {u.id !== user.id && (
                            <button
                              onClick={() => handleDeleteUser(u.id)}
                              className="px-3 py-1 bg-red-500/20 text-red-300 rounded text-sm hover:bg-red-500/30 transition"
                            >
                              Delete
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* User Details Modal */}
            {userDetails && selectedUserId && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => { setUserDetails(null); setSelectedUserId(null) }}>
                <div className="glass-card border border-slate-700/50 p-6 max-w-4xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-2xl font-bold text-slate-100">User Details</h3>
                    <button onClick={() => { setUserDetails(null); setSelectedUserId(null) }} className="text-slate-400 hover:text-slate-200">×</button>
                  </div>
                  
                  <div className="space-y-6">
                    <div>
                      <h4 className="text-lg font-semibold text-slate-200 mb-2">User Information</h4>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <div className="text-sm text-slate-400">Email</div>
                          <div className="text-slate-100">{userDetails.user.email}</div>
                        </div>
                        <div>
                          <div className="text-sm text-slate-400">Tier</div>
                          <div className="text-slate-100">{userDetails.user.tier}</div>
                        </div>
                        <div>
                          <div className="text-sm text-slate-400">Total Paid</div>
                          <div className="text-green-400 font-bold">${userDetails.total_paid.toFixed(2)}</div>
                        </div>
                        <div>
                          <div className="text-sm text-slate-400">Total Token Cost</div>
                          <div className="text-orange-400 font-bold">${userDetails.token_usage.total_cost.toFixed(4)}</div>
                        </div>
                      </div>
                    </div>

                    <div>
                      <h4 className="text-lg font-semibold text-slate-200 mb-2">Transactions ({userDetails.transactions.length})</h4>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-slate-700">
                              <th className="text-left py-2 px-2 text-slate-300">Date</th>
                              <th className="text-left py-2 px-2 text-slate-300">Amount</th>
                              <th className="text-left py-2 px-2 text-slate-300">Status</th>
                              <th className="text-left py-2 px-2 text-slate-300">Type</th>
                            </tr>
                          </thead>
                          <tbody>
                            {userDetails.transactions.map((t: any) => (
                              <tr key={t.id} className="border-b border-slate-800">
                                <td className="py-2 px-2 text-slate-300">{new Date(t.created_at).toLocaleDateString()}</td>
                                <td className="py-2 px-2 text-green-400">${t.amount.toFixed(2)}</td>
                                <td className="py-2 px-2">
                                  <span className={`px-2 py-1 rounded text-xs ${
                                    t.status === 'completed' ? 'bg-green-500/20 text-green-300' : 'bg-red-500/20 text-red-300'
                                  }`}>
                                    {t.status}
                                  </span>
                                </td>
                                <td className="py-2 px-2 text-slate-300 text-xs">{t.event_type}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    <div>
                      <h4 className="text-lg font-semibold text-slate-200 mb-2">Token Usage</h4>
                      <div className="grid grid-cols-2 gap-4 mb-4">
                        <div>
                          <div className="text-sm text-slate-400">Total Tokens</div>
                          <div className="text-slate-100 font-bold">{userDetails.token_usage.total_tokens.toLocaleString()}</div>
                        </div>
                        <div>
                          <div className="text-sm text-slate-400">Total Cost</div>
                          <div className="text-orange-400 font-bold">${userDetails.token_usage.total_cost.toFixed(4)}</div>
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-slate-400 mb-2">By Endpoint</div>
                        {Object.entries(userDetails.token_usage.by_endpoint).map(([endpoint, data]: [string, any]) => (
                          <div key={endpoint} className="flex justify-between py-1 border-b border-slate-800">
                            <span className="text-slate-300">{endpoint}</span>
                            <span className="text-slate-400">{data.total_tokens.toLocaleString()} tokens (${data.total_cost.toFixed(4)})</span>
                          </div>
                        ))}
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
          <div className="glass-card border border-slate-700/50 p-6">
            <h2 className="text-2xl font-bold text-slate-100 mb-4">Transactions</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left py-3 px-4 text-slate-300">ID</th>
                    <th className="text-left py-3 px-4 text-slate-300">User</th>
                    <th className="text-left py-3 px-4 text-slate-300">Amount</th>
                    <th className="text-left py-3 px-4 text-slate-300">Status</th>
                    <th className="text-left py-3 px-4 text-slate-300">Tier</th>
                    <th className="text-left py-3 px-4 text-slate-300">Type</th>
                    <th className="text-left py-3 px-4 text-slate-300">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((t) => (
                    <tr key={t.id} className="border-b border-slate-800 hover:bg-slate-800/30">
                      <td className="py-3 px-4 text-slate-300">{t.id}</td>
                      <td className="py-3 px-4 text-slate-300">{t.user_email || `User ${t.user_id}`}</td>
                      <td className="py-3 px-4 text-green-400 font-semibold">${t.amount.toFixed(2)}</td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded text-xs ${
                          t.status === 'completed' ? 'bg-green-500/20 text-green-300' : 
                          t.status === 'failed' ? 'bg-red-500/20 text-red-300' : 
                          'bg-yellow-500/20 text-yellow-300'
                        }`}>
                          {t.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-300">{t.tier}</td>
                      <td className="py-3 px-4 text-slate-400 text-sm">{t.event_type}</td>
                      <td className="py-3 px-4 text-slate-400 text-sm">
                        {new Date(t.created_at).toLocaleDateString()}
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
          <div className="glass-card border border-slate-700/50 p-6">
            <h2 className="text-2xl font-bold text-slate-100 mb-4">Token Usage</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left py-3 px-4 text-slate-300">User</th>
                    <th className="text-left py-3 px-4 text-slate-300">Endpoint</th>
                    <th className="text-left py-3 px-4 text-slate-300">Model</th>
                    <th className="text-left py-3 px-4 text-slate-300">Input</th>
                    <th className="text-left py-3 px-4 text-slate-300">Output</th>
                    <th className="text-left py-3 px-4 text-slate-300">Total</th>
                    <th className="text-left py-3 px-4 text-slate-300">Cost</th>
                    <th className="text-left py-3 px-4 text-slate-300">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {tokenUsage.map((u) => (
                    <tr key={u.id} className="border-b border-slate-800 hover:bg-slate-800/30">
                      <td className="py-3 px-4 text-slate-300">{u.user_email || 'Anonymous'}</td>
                      <td className="py-3 px-4 text-slate-300">{u.endpoint}</td>
                      <td className="py-3 px-4 text-slate-400 text-sm">{u.model}</td>
                      <td className="py-3 px-4 text-slate-300">{u.input_tokens.toLocaleString()}</td>
                      <td className="py-3 px-4 text-slate-300">{u.output_tokens.toLocaleString()}</td>
                      <td className="py-3 px-4 text-slate-300 font-semibold">{u.total_tokens.toLocaleString()}</td>
                      <td className="py-3 px-4 text-orange-400">${u.estimated_cost.toFixed(4)}</td>
                      <td className="py-3 px-4 text-slate-400 text-sm">
                        {new Date(u.created_at).toLocaleDateString()}
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
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="glass-card border border-slate-700/50 p-6">
                <div className="text-2xl font-bold text-green-400 mb-1">${revenueStats.total_revenue.toFixed(2)}</div>
                <div className="text-sm text-slate-400">Total Revenue</div>
              </div>
              <div className="glass-card border border-slate-700/50 p-6">
                <div className="text-2xl font-bold text-orange-400 mb-1">${revenueStats.total_token_cost.toFixed(2)}</div>
                <div className="text-sm text-slate-400">Token Costs</div>
              </div>
              <div className="glass-card border border-slate-700/50 p-6">
                <div className="text-2xl font-bold text-teal-400 mb-1">${revenueStats.net_revenue.toFixed(2)}</div>
                <div className="text-sm text-slate-400">Net Revenue</div>
              </div>
              <div className="glass-card border border-slate-700/50 p-6">
                <div className="text-2xl font-bold text-blue-400 mb-1">{revenueStats.total_transactions}</div>
                <div className="text-sm text-slate-400">Transactions</div>
              </div>
            </div>

            <div className="glass-card border border-slate-700/50 p-6">
              <h3 className="text-xl font-bold text-slate-100 mb-4">Revenue by Tier</h3>
              <div className="space-y-2">
                {Object.entries(revenueStats.revenue_by_tier).map(([tier, revenue]) => (
                  <div key={tier} className="flex justify-between py-2 border-b border-slate-800">
                    <span className="text-slate-300 capitalize">{tier}</span>
                    <span className="text-green-400 font-semibold">${revenue.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="glass-card border border-slate-700/50 p-6">
              <h3 className="text-xl font-bold text-slate-100 mb-4">Token Usage by Endpoint</h3>
              <div className="space-y-2">
                {Object.entries(revenueStats.token_usage_by_endpoint).map(([endpoint, data]) => (
                  <div key={endpoint} className="flex justify-between py-2 border-b border-slate-800">
                    <span className="text-slate-300">{endpoint}</span>
                    <span className="text-slate-400">{data.total_tokens.toLocaleString()} tokens (${data.total_cost.toFixed(2)})</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="glass-card border border-slate-700/50 p-6">
              <h3 className="text-xl font-bold text-slate-100 mb-4">Top Users by Token Cost</h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-700">
                      <th className="text-left py-2 px-4 text-slate-300">User</th>
                      <th className="text-left py-2 px-4 text-slate-300">Tokens</th>
                      <th className="text-left py-2 px-4 text-slate-300">Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {revenueStats.top_users_by_token_cost.map((u) => (
                      <tr key={u.user_id} className="border-b border-slate-800">
                        <td className="py-2 px-4 text-slate-300">{u.user_email || `User ${u.user_id}`}</td>
                        <td className="py-2 px-4 text-slate-300">{u.total_tokens.toLocaleString()}</td>
                        <td className="py-2 px-4 text-orange-400">${u.total_cost.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Edit User Modal */}
        {editMode && selectedUser && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="glass-card border border-slate-700/50 p-6 max-w-md w-full">
              <h3 className="text-2xl font-bold text-slate-100 mb-4">Edit User</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Email</label>
                  <input
                    type="email"
                    value={selectedUser.email}
                    disabled
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-300"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Name</label>
                  <input
                    type="text"
                    value={editForm.name}
                    onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                    className="w-full px-4 py-2 bg-[#1F2937] border border-white/10 rounded-lg text-slate-100"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Surname</label>
                  <input
                    type="text"
                    value={editForm.surname}
                    onChange={(e) => setEditForm({ ...editForm, surname: e.target.value })}
                    className="w-full px-4 py-2 bg-[#1F2937] border border-white/10 rounded-lg text-slate-100"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Tier</label>
                  <select
                    value={editForm.tier}
                    onChange={(e) => setEditForm({ ...editForm, tier: e.target.value })}
                    className="w-full px-4 py-2 bg-[#1F2937] border border-white/10 rounded-lg text-slate-100"
                  >
                    <option value="free">Free</option>
                    <option value="standard">Standard</option>
                    <option value="premium">Premium</option>
                    <option value="pro">Pro</option>
                  </select>
                </div>

                <div>
                  <label className="flex items-center gap-2 text-slate-300">
                    <input
                      type="checkbox"
                      checked={editForm.is_admin}
                      onChange={(e) => setEditForm({ ...editForm, is_admin: e.target.checked })}
                      className="rounded"
                    />
                    <span>Admin</span>
                  </label>
                </div>
              </div>

              <div className="flex gap-4 mt-6">
                <button
                  onClick={handleSaveUser}
                  className="flex-1 px-4 py-2 bg-gradient-to-r from-teal-500 to-cyan-500 text-white rounded-lg hover:shadow-lg transition-all"
                >
                  Save
                </button>
                <button
                  onClick={() => {
                    setEditMode(false)
                    setSelectedUser(null)
                  }}
                  className="flex-1 px-4 py-2 bg-slate-700 text-slate-300 rounded-lg hover:bg-slate-600 transition"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
