'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { historyAPI, folderAPI } from '@/lib/api'

interface HistoryItem {
  id: string | number
  type: 'summary' | 'flashcards' | 'truefalse' | 'exam'
  title: string
  timestamp: number
  folder_id?: number | null
  data: any
  score?: {
    correct: number
    total: number
    percentage: number
  }
}

interface Folder {
  id: number
  name: string
  color?: string
  icon?: string
  item_count: number
}

export default function HistoryPage() {
  const router = useRouter()
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [folders, setFolders] = useState<Folder[]>([])
  const [selectedFolder, setSelectedFolder] = useState<number | null>(null) // null = all, 0 = uncategorized
  const [filter, setFilter] = useState<'all' | 'summary' | 'flashcards' | 'truefalse' | 'exam'>('all')
  const [showNewFolderDialog, setShowNewFolderDialog] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [newFolderIcon, setNewFolderIcon] = useState('📁')
  const [newFolderColor, setNewFolderColor] = useState('#3B82F6')
  const [moveToFolderItemId, setMoveToFolderItemId] = useState<string | number | null>(null)

  useEffect(() => {
    loadHistory()
    loadFolders()
  }, [selectedFolder])

  const loadHistory = async () => {
    try {
      const items = selectedFolder !== null
        ? await historyAPI.getByFolder(selectedFolder)
        : await historyAPI.getAll()
      setHistory(items.sort((a: HistoryItem, b: HistoryItem) => b.timestamp - a.timestamp))
    } catch (e) {
      console.error('Failed to load history:', e)
    }
  }

  const loadFolders = async () => {
    try {
      const items = await folderAPI.getAll()
      setFolders(items)
    } catch (e) {
      console.error('Failed to load folders:', e)
    }
  }

  const createFolder = async () => {
    if (!newFolderName.trim()) return
    
    try {
      await folderAPI.create({
        name: newFolderName,
        icon: newFolderIcon,
        color: newFolderColor
      })
      setShowNewFolderDialog(false)
      setNewFolderName('')
      setNewFolderIcon('📁')
      setNewFolderColor('#3B82F6')
      await loadFolders()
    } catch (e) {
      console.error('Failed to create folder:', e)
    }
  }

  const deleteFolder = async (id: number) => {
    if (confirm('Delete this folder? Items will become uncategorized.')) {
      try {
        await folderAPI.delete(id)
        await loadFolders()
        if (selectedFolder === id) {
          setSelectedFolder(null)
        }
        await loadHistory()
      } catch (e) {
        console.error('Failed to delete folder:', e)
      }
    }
  }

  const moveItemToFolder = async (itemId: string | number, folderId: number | null) => {
    try {
      await historyAPI.update(itemId, { folder_id: folderId || 0 })
      await loadHistory()
      await loadFolders()
      setMoveToFolderItemId(null)
    } catch (e) {
      console.error('Failed to move item:', e)
    }
  }

  const clearHistory = async () => {
    if (confirm('Are you sure you want to clear all history?')) {
      await historyAPI.clearAll()
      setHistory([])
    }
  }

  const deleteItem = async (id: string | number) => {
    await historyAPI.delete(id)
    const newHistory = history.filter(item => item.id !== id)
    setHistory(newHistory)
    await loadFolders() // Update counts
  }

  const openItem = (item: HistoryItem) => {
    const params = new URLSearchParams({
      from: 'history',
      id: String(item.id)
    })
    
    if (item.type === 'exam') {
      router.push(`/view-exam?${params}`)
    } else if (item.type === 'summary') {
      router.push(`/summaries?${params}`)
    } else if (item.type === 'flashcards') {
      router.push(`/flashcards?${params}`)
    } else if (item.type === 'truefalse') {
      router.push(`/truefalse?${params}`)
    }
  }

  const getTypeIcon = (type: string) => {
    switch(type) {
      case 'summary': return '📝'
      case 'flashcards': return '🎴'
      case 'truefalse': return '✅❌'
      case 'exam': return '🎯'
      default: return '📄'
    }
  }

  const getTypeColor = (type: string) => {
    switch(type) {
      case 'summary': return 'from-teal-500 to-emerald-500'
      case 'flashcards': return 'from-cyan-500 to-blue-500'
      case 'truefalse': return 'from-green-500 to-emerald-500'
      case 'exam': return 'from-blue-500 to-indigo-500'
      default: return 'from-slate-500 to-slate-600'
    }
  }

  const filteredHistory = filter === 'all' 
    ? history 
    : history.filter(item => item.type === filter)

  // Count items in "All Items"
  const allItemsCount = history.length
  
  // Count uncategorized items
  const uncategorizedCount = history.filter(item => !item.folder_id).length

  const folderIcons = ['📁', '📚', '🎓', '💼', '🏆', '🎯', '⭐', '🔥', '💡', '🚀']
  const folderColors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6', '#F97316']

  return (
    <div className="min-h-screen bg-[#0B1220] pt-20 px-4 pb-12">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8 flex justify-between items-center">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            Study History
          </h1>
          <button
            onClick={clearHistory}
            className="px-4 py-2 bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl hover:bg-red-500/20 transition-all text-sm"
          >
            Clear All
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Folders Sidebar */}
          <div className="lg:col-span-1">
            <div className="glass-card p-4 sticky top-24">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-semibold text-slate-200">Folders</h2>
                <button
                  onClick={() => setShowNewFolderDialog(true)}
                  className="text-teal-400 hover:text-teal-300 transition-colors"
                  title="Create folder"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                </button>
              </div>

              {/* All Items */}
              <button
                onClick={() => setSelectedFolder(null)}
                className={`w-full text-left px-3 py-2 rounded-lg mb-1 transition-all ${
                  selectedFolder === null
                    ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30'
                    : 'text-slate-400 hover:bg-white/5'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span>📚</span>
                    <span className="text-sm font-medium">All Items</span>
                  </div>
                  <span className="text-xs opacity-70">{allItemsCount}</span>
                </div>
              </button>

              {/* Uncategorized */}
              <button
                onClick={() => setSelectedFolder(0)}
                className={`w-full text-left px-3 py-2 rounded-lg mb-1 transition-all ${
                  selectedFolder === 0
                    ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30'
                    : 'text-slate-400 hover:bg-white/5'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span>📄</span>
                    <span className="text-sm font-medium">Uncategorized</span>
                  </div>
                  <span className="text-xs opacity-70">{uncategorizedCount}</span>
                </div>
              </button>

              <div className="border-t border-white/10 my-3"></div>

              {/* User Folders */}
              <div className="space-y-1">
                {folders.map((folder) => (
                  <div key={folder.id} className="group relative">
                    <button
                      onClick={() => setSelectedFolder(folder.id)}
                      className={`w-full text-left px-3 py-2 rounded-lg transition-all ${
                        selectedFolder === folder.id
                          ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30'
                          : 'text-slate-400 hover:bg-white/5'
                      }`}
                      style={selectedFolder === folder.id ? { borderLeftColor: folder.color || '#3B82F6', borderLeftWidth: '3px' } : {}}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          <span>{folder.icon || '📁'}</span>
                          <span className="text-sm font-medium truncate">{folder.name}</span>
                        </div>
                        <span className="text-xs opacity-70 ml-2">{folder.item_count}</span>
                      </div>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        deleteFolder(folder.id)
                      }}
                      className="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 p-1 hover:bg-red-500/20 rounded transition-all"
                      title="Delete folder"
                    >
                      <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* History Items */}
          <div className="lg:col-span-3">
            {/* Type Filter */}
            <div className="flex gap-2 mb-6 flex-wrap">
              {(['all', 'summary', 'flashcards', 'truefalse', 'exam'] as const).map((type) => (
                <button
                  key={type}
                  onClick={() => setFilter(type)}
                  className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                    filter === type
                      ? 'bg-gradient-to-r from-teal-500 to-cyan-500 text-white'
                      : 'bg-white/5 text-slate-400 hover:bg-white/10'
                  }`}
                >
                  {type === 'all' ? 'All' : type.charAt(0).toUpperCase() + type.slice(1)}
                </button>
              ))}
            </div>

            {/* History List */}
            {filteredHistory.length === 0 ? (
              <div className="glass-card p-12 text-center">
                <div className="text-6xl mb-4">📚</div>
                <p className="text-slate-400 text-lg">No history yet</p>
                <p className="text-slate-500 text-sm mt-2">Start creating summaries, flashcards, or exams!</p>
              </div>
            ) : (
              <div className="space-y-4">
                {filteredHistory.map((item) => (
                  <div key={item.id} className="glass-card p-6 hover:bg-white/5 transition-all group">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-4 flex-1 min-w-0">
                        <div className={`p-3 rounded-xl bg-gradient-to-r ${getTypeColor(item.type)}`}>
                          <span className="text-2xl">{getTypeIcon(item.type)}</span>
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <button
                            onClick={() => openItem(item)}
                            className="text-left w-full"
                          >
                            <h3 className="text-lg font-semibold text-slate-100 hover:text-teal-400 transition-colors truncate">
                              {item.title}
                            </h3>
                          </button>
                          
                          <div className="flex items-center gap-3 mt-2 text-sm text-slate-400">
                            <span className="capitalize">{item.type}</span>
                            <span>•</span>
                            <span>{new Date(item.timestamp).toLocaleDateString()}</span>
                            {item.score && (
                              <>
                                <span>•</span>
                                <span className={`font-medium ${
                                  item.score.percentage >= 70 ? 'text-green-400' : 'text-yellow-400'
                                }`}>
                                  Score: {item.score.correct}/{item.score.total} ({item.score.percentage}%)
                                </span>
                              </>
                            )}
                          </div>

                          {item.folder_id && (
                            <div className="mt-2">
                              {(() => {
                                const folder = folders.find(f => f.id === item.folder_id)
                                return folder ? (
                                  <span 
                                    className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs text-slate-300"
                                    style={{ 
                                      backgroundColor: `${folder.color || '#3B82F6'}20`,
                                      borderLeft: `2px solid ${folder.color || '#3B82F6'}`
                                    }}
                                  >
                                    <span>{folder.icon || '📁'}</span>
                                    <span>{folder.name}</span>
                                  </span>
                                ) : null
                              })()}
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => setMoveToFolderItemId(item.id)}
                          className="p-2 hover:bg-teal-500/20 rounded-lg transition-all"
                          title="Move to folder"
                        >
                          <svg className="w-5 h-5 text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => deleteItem(item.id)}
                          className="p-2 hover:bg-red-500/20 rounded-lg transition-all"
                          title="Delete"
                        >
                          <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* New Folder Dialog */}
      {showNewFolderDialog && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="glass-card p-6 w-full max-w-md">
            <h2 className="text-2xl font-bold text-slate-100 mb-4">Create New Folder</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Folder Name</label>
                <input
                  type="text"
                  value={newFolderName}
                  onChange={(e) => setNewFolderName(e.target.value)}
                  placeholder="My Study Folder"
                  className="w-full px-4 py-3 bg-[#1F2937] border border-white/10 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-500"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Icon</label>
                <div className="flex gap-2 flex-wrap">
                  {folderIcons.map((icon) => (
                    <button
                      key={icon}
                      onClick={() => setNewFolderIcon(icon)}
                      className={`text-2xl p-2 rounded-lg transition-all ${
                        newFolderIcon === icon
                          ? 'bg-teal-500/20 ring-2 ring-teal-500'
                          : 'bg-white/5 hover:bg-white/10'
                      }`}
                    >
                      {icon}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Color</label>
                <div className="flex gap-2 flex-wrap">
                  {folderColors.map((color) => (
                    <button
                      key={color}
                      onClick={() => setNewFolderColor(color)}
                      className={`w-10 h-10 rounded-lg transition-all ${
                        newFolderColor === color
                          ? 'ring-2 ring-white ring-offset-2 ring-offset-[#0B1220]'
                          : ''
                      }`}
                      style={{ backgroundColor: color }}
                    />
                  ))}
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => {
                  setShowNewFolderDialog(false)
                  setNewFolderName('')
                  setNewFolderIcon('📁')
                  setNewFolderColor('#3B82F6')
                }}
                className="flex-1 px-4 py-3 bg-white/5 text-slate-400 rounded-xl hover:bg-white/10 transition-all"
              >
                Cancel
              </button>
              <button
                onClick={createFolder}
                disabled={!newFolderName.trim()}
                className="flex-1 px-4 py-3 bg-gradient-to-r from-teal-500 to-cyan-500 text-white rounded-xl hover:shadow-lg hover:shadow-teal-500/25 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Move to Folder Dialog */}
      {moveToFolderItemId !== null && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="glass-card p-6 w-full max-w-md">
            <h2 className="text-2xl font-bold text-slate-100 mb-4">Move to Folder</h2>
            
            <div className="space-y-2 max-h-96 overflow-y-auto">
              <button
                onClick={() => moveItemToFolder(moveToFolderItemId, null)}
                className="w-full text-left px-4 py-3 bg-white/5 hover:bg-white/10 rounded-lg transition-all text-slate-300"
              >
                <div className="flex items-center gap-2">
                  <span>📄</span>
                  <span>Uncategorized</span>
                </div>
              </button>

              {folders.map((folder) => (
                <button
                  key={folder.id}
                  onClick={() => moveItemToFolder(moveToFolderItemId, folder.id)}
                  className="w-full text-left px-4 py-3 bg-white/5 hover:bg-white/10 rounded-lg transition-all text-slate-300"
                  style={{ borderLeft: `3px solid ${folder.color || '#3B82F6'}` }}
                >
                  <div className="flex items-center gap-2">
                    <span>{folder.icon || '📁'}</span>
                    <span>{folder.name}</span>
                    <span className="text-xs text-slate-500 ml-auto">({folder.item_count} items)</span>
                  </div>
                </button>
              ))}
            </div>

            <button
              onClick={() => setMoveToFolderItemId(null)}
              className="w-full mt-4 px-4 py-3 bg-white/5 text-slate-400 rounded-xl hover:bg-white/10 transition-all"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
