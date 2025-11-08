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

export default function AdminPage() {
  const { user } = useAuth()
  const router = useRouter()
  const [users, setUsers] = useState<User[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
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

  useEffect(() => {
    // Check if user is admin
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

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0F172A] pt-20 flex items-center justify-center">
        <div className="text-slate-300">Loading...</div>
      </div>
    )
  }

  if (!user?.is_admin) {
    return null
  }

  return (
    <div className="min-h-screen bg-[#0F172A] pt-20 px-4 pb-12">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-slate-100 mb-2">Admin Panel</h1>
          <p className="text-slate-400">Manage users, subscriptions, and system statistics</p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400">
            {error}
          </div>
        )}

        {/* Statistics Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
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
        )}

        {/* Actions */}
        <div className="mb-6 flex gap-4">
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

        {/* User Management */}
        <div className="glass-card border border-slate-700/50 p-6 mb-6">
          <h2 className="text-2xl font-bold text-slate-100 mb-4">User Management</h2>
          
          {/* User List */}
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
        </div>

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

