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
  const [selectedFolder, setSelectedFolder] = useState<number | null>(null)
  const [filter, setFilter] = useState<'all' | 'summary' | 'flashcards' | 'truefalse' | 'exam'>('all')
  const [showFolderManager, setShowFolderManager] = useState(false)
  const [showMoveDialog, setShowMoveDialog] = useState(false)
  const [selectedItemId, setSelectedItemId] = useState<string | number | null>(null)
  const [selectedTargetFolder, setSelectedTargetFolder] = useState<number | null>(null)
  const [showDeleteFolderConfirm, setShowDeleteFolderConfirm] = useState(false)
  const [folderToDelete, setFolderToDelete] = useState<number | null>(null)
  const [newFolderName, setNewFolderName] = useState('')
  const [newFolderIcon, setNewFolderIcon] = useState('📁')

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
      await folderAPI.create({ name: newFolderName, icon: newFolderIcon })
      setNewFolderName('')
      setNewFolderIcon('📁')
      await loadFolders()
    } catch (e) {
      console.error('Failed to create folder:', e)
    }
  }

  const deleteFolder = async () => {
    if (folderToDelete === null) return
    try {
      await folderAPI.delete(folderToDelete)
      await loadFolders()
      if (selectedFolder === folderToDelete) setSelectedFolder(null)
      await loadHistory()
      setShowDeleteFolderConfirm(false)
      setFolderToDelete(null)
    } catch (e) {
      console.error('Failed to delete folder:', e)
    }
  }

  const moveToFolder = async () => {
    if (selectedItemId === null) return
    try {
      await historyAPI.update(selectedItemId, { folder_id: selectedTargetFolder || 0 })
      await loadHistory()
      await loadFolders()
      setShowMoveDialog(false)
      setSelectedItemId(null)
      setSelectedTargetFolder(null)
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
    await loadFolders()
  }

  const viewItem = (item: HistoryItem) => {
    // Store the data and navigate to the appropriate page
    if (item.type === 'summary') {
      sessionStorage.setItem('viewHistory', JSON.stringify(item.data))
      router.push('/summaries')
    } else if (item.type === 'flashcards') {
      sessionStorage.setItem('viewHistory', JSON.stringify(item.data))
      router.push('/flashcards')
    } else if (item.type === 'truefalse') {
      sessionStorage.setItem('viewHistory', JSON.stringify(item.data))
      sessionStorage.setItem('viewHistoryTrueFalseId', String(item.id))
      router.push('/truefalse')
    } else if (item.type === 'exam') {
      sessionStorage.setItem('viewHistoryExamId', String(item.id))
      sessionStorage.setItem('viewHistoryExamTitle', item.title)
      
      if (item.data.exam && item.data.answers) {
        sessionStorage.setItem('viewHistoryExam', JSON.stringify({
          exam: item.data.exam,
          answers: item.data.answers,
          showResults: true
        }))
      } else if (item.data.exam) {
        sessionStorage.setItem('viewHistoryExam', JSON.stringify({
          exam: item.data.exam,
          answers: {},
          showResults: false
        }))
      } else if (item.data.questions) {
        sessionStorage.setItem('viewHistoryExam', JSON.stringify({
          exam: item.data,
          answers: {},
          showResults: false
        }))
      }
      
      router.push('/view-exam')
    }
  }

  const filteredHistory = filter === 'all' 
    ? history 
    : history.filter(item => item.type === filter)

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'summary': return '📝'
      case 'flashcards': return '🎴'
      case 'truefalse': return '✅❌'
      case 'exam': return '🎯'
      default: return '📄'
    }
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'summary': return 'from-teal-500/20 to-teal-600/20 border-teal-500/50'
      case 'flashcards': return 'from-cyan-500/20 to-cyan-600/20 border-cyan-500/50'
      case 'truefalse': return 'from-green-500/20 to-red-500/20 border-green-500/50'
      case 'exam': return 'from-emerald-500/20 to-emerald-600/20 border-emerald-500/50'
      default: return 'from-slate-500/20 to-slate-600/20 border-slate-500/50'
    }
  }

  const uncategorizedCount = history.filter(item => !item.folder_id).length

  return (
    <div className="min-h-screen bg-[#0F172A] pt-20 px-4 pb-12">
      {/* Animated background */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl animate-pulse-slow"></div>
        <div className="absolute bottom-20 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }}></div>
      </div>

      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="glass-card mb-8 animate-fade-in">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-4 mb-2">
                <div className="text-5xl">📚</div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-[#14B8A6] to-[#06B6D4] bg-clip-text text-transparent">
                  History
                </h1>
              </div>
              <p className="text-slate-400">
                View and access your past summaries, flashcards, and exams
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setShowFolderManager(true)}
                className="btn-ghost"
              >
                📁 Folders
              </button>
              {history.length > 0 && (
                <button
                  onClick={clearHistory}
                  className="btn-ghost text-red-400 hover:bg-red-500/10 hover:border-red-500/30"
                >
                  🗑️ Clear All
                </button>
              )}
            </div>
          </div>

          {/* Filters */}
          <div className="flex gap-2 mt-6 flex-wrap">
            {/* Folder filter */}
            <select
              value={selectedFolder === null ? 'all' : selectedFolder}
              onChange={(e) => setSelectedFolder(e.target.value === 'all' ? null : parseInt(e.target.value))}
              className="px-4 py-2 rounded-xl border border-white/15 bg-[#1F2937] text-slate-300 hover:bg-white/5 transition-all duration-200"
            >
              <option value="all">📚 All Folders</option>
              <option value="0">📄 Uncategorized ({uncategorizedCount})</option>
              {folders.map(folder => (
                <option key={folder.id} value={folder.id}>
                  {folder.icon} {folder.name} ({folder.item_count})
                </option>
              ))}
            </select>

            <div className="border-l border-white/15 mx-2"></div>

            {/* Type filter */}
            {[
              { value: 'all', label: 'All', icon: '📚' },
              { value: 'summary', label: 'Summaries', icon: '📝' },
              { value: 'flashcards', label: 'Flashcards', icon: '🎴' },
              { value: 'truefalse', label: 'True/False', icon: '✅❌' },
              { value: 'exam', label: 'Exams', icon: '🎯' }
            ].map((item) => (
              <button
                key={item.value}
                onClick={() => setFilter(item.value as any)}
                className={`px-4 py-2 rounded-xl border transition-all duration-200 ${
                  filter === item.value
                    ? 'border-[#14B8A6] bg-gradient-to-r from-[#14B8A6]/20 to-[#06B6D4]/20 text-[#06B6D4]'
                    : 'border-white/15 text-slate-300 hover:bg-white/5'
                }`}
              >
                {item.icon} {item.label}
              </button>
            ))}
          </div>
        </div>

        {/* History list */}
        {filteredHistory.length === 0 ? (
          <div className="glass-card text-center p-12 animate-scale-in">
            <div className="text-6xl mb-4">📭</div>
            <h2 className="text-2xl font-semibold text-slate-100 mb-2">
              No History Yet
            </h2>
            <p className="text-slate-400 mb-6">
              {filter === 'all' 
                ? 'Start generating summaries, flashcards, or exams to see them here!'
                : `No ${filter} in your history yet.`}
            </p>
            <button onClick={() => router.push('/upload')} className="btn-primary">
              Upload Documents 📄
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredHistory.map((item, index) => (
              <div
                key={item.id}
                className="glass-card card-hover animate-slide-up group"
                style={{ animationDelay: `${index * 0.05}s` }}
              >
                <div className="flex items-start gap-4">
                  {/* Icon */}
                  <div className={`flex-shrink-0 w-16 h-16 bg-gradient-to-br ${getTypeColor(item.type)} rounded-xl flex items-center justify-center ${item.type === 'truefalse' ? 'text-2xl' : 'text-3xl'} group-hover:scale-110 transition-transform`}>
                    {getTypeIcon(item.type)}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <h3 className="text-xl font-semibold text-slate-100 mb-1 truncate">
                          {item.title}
                        </h3>
                        <div className="flex items-center gap-3 text-sm text-slate-400 flex-wrap">
                          <span className="capitalize">{item.type}</span>
                          <span>•</span>
                          <span>{new Date(item.timestamp).toLocaleDateString('tr-TR', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}</span>
                          {item.score && (
                            <>
                              <span>•</span>
                              <span className={`font-semibold px-2 py-0.5 rounded ${
                                item.score.percentage >= 80 
                                  ? 'text-green-400 bg-green-500/10' 
                                  : item.score.percentage >= 60 
                                  ? 'text-yellow-400 bg-yellow-500/10' 
                                  : 'text-red-400 bg-red-500/10'
                              }`}>
                                {item.score.correct}/{item.score.total} ({item.score.percentage}%)
                              </span>
                            </>
                          )}
                        </div>
                        {/* Folder badge */}
                        {item.folder_id && (() => {
                          const folder = folders.find(f => f.id === item.folder_id)
                          return folder ? (
                            <div className="mt-2">
                              <span className="inline-flex items-center gap-1 px-2 py-1 bg-white/5 border border-white/10 rounded-lg text-xs text-slate-300">
                                <span>{folder.icon || '📁'}</span>
                                <span>{folder.name}</span>
                              </span>
                            </div>
                          ) : null
                        })()}
                      </div>

                      {/* Actions */}
                      <div className="flex gap-2">
                        <button
                          onClick={() => {
                            setSelectedItemId(item.id)
                            setSelectedTargetFolder(item.folder_id || null)
                            setShowMoveDialog(true)
                          }}
                          className="px-4 py-2 border border-white/15 text-slate-300 rounded-xl hover:bg-[#14B8A6]/10 hover:border-[#14B8A6]/30 hover:text-[#14B8A6] transition-all duration-200"
                          title="Move to folder"
                        >
                          📁
                        </button>
                        <button
                          onClick={() => viewItem(item)}
                          className="px-4 py-2 bg-gradient-to-r from-[#14B8A6] to-[#06B6D4] text-white rounded-xl hover:shadow-lg hover:shadow-teal-500/25 transition-all duration-200 hover:scale-105"
                        >
                          View
                        </button>
                        <button
                          onClick={() => deleteItem(item.id)}
                          className="px-4 py-2 border border-white/15 text-slate-300 rounded-xl hover:bg-red-500/10 hover:border-red-500/30 hover:text-red-400 transition-all duration-200"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Folder Manager Dialog */}
      {showFolderManager && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fade-in">
          <div className="glass-card p-6 w-full max-w-2xl animate-scale-in">
            <h2 className="text-3xl font-bold bg-gradient-to-r from-[#14B8A6] to-[#06B6D4] bg-clip-text text-transparent mb-6">
              Manage Folders
            </h2>
            
            {/* Create new folder */}
            <div className="mb-6 p-4 bg-white/5 rounded-xl border border-white/10">
              <h3 className="text-lg font-semibold text-slate-100 mb-3">Create New Folder</h3>
              <div className="flex gap-3">
                <select
                  value={newFolderIcon}
                  onChange={(e) => setNewFolderIcon(e.target.value)}
                  className="px-3 py-2 bg-[#1F2937] border border-white/10 rounded-xl text-2xl"
                >
                  {['📁', '📚', '🎓', '💼', '🏆', '🎯', '⭐', '🔥', '💡', '🚀'].map(icon => (
                    <option key={icon} value={icon}>{icon}</option>
                  ))}
                </select>
                <input
                  type="text"
                  value={newFolderName}
                  onChange={(e) => setNewFolderName(e.target.value)}
                  placeholder="Folder name..."
                  className="flex-1 px-4 py-2 bg-[#1F2937] border border-white/10 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-[#14B8A6]"
                  onKeyPress={(e) => e.key === 'Enter' && createFolder()}
                />
                <button
                  onClick={createFolder}
                  disabled={!newFolderName.trim()}
                  className="px-6 py-2 bg-gradient-to-r from-[#14B8A6] to-[#06B6D4] text-white rounded-xl hover:shadow-lg hover:shadow-teal-500/25 transition-all duration-200 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Create
                </button>
              </div>
            </div>

            {/* Folders list */}
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {folders.length === 0 ? (
                <p className="text-slate-400 text-center py-8">No folders yet. Create one above!</p>
              ) : (
                folders.map(folder => (
                  <div key={folder.id} className="flex items-center justify-between p-4 bg-white/5 rounded-xl border border-white/10 hover:bg-white/10 transition-all group">
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">{folder.icon || '📁'}</span>
                      <div>
                        <div className="text-slate-100 font-medium">{folder.name}</div>
                        <div className="text-sm text-slate-400">{folder.item_count} items</div>
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        setFolderToDelete(folder.id)
                        setShowDeleteFolderConfirm(true)
                      }}
                      className="opacity-0 group-hover:opacity-100 px-3 py-1 text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
                    >
                      Delete
                    </button>
                  </div>
                ))
              )}
            </div>

            <button
              onClick={() => setShowFolderManager(false)}
              className="w-full mt-6 px-4 py-3 border border-white/15 text-slate-300 rounded-xl hover:bg-white/5 transition-all"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Move to Folder Dialog */}
      {showMoveDialog && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fade-in">
          <div className="glass-card p-6 w-full max-w-md animate-scale-in">
            <h2 className="text-2xl font-bold bg-gradient-to-r from-[#14B8A6] to-[#06B6D4] bg-clip-text text-transparent mb-4">
              Move to Folder
            </h2>
            
            <div className="space-y-2 max-h-96 overflow-y-auto mb-6">
              <label
                className={`w-full flex items-center px-4 py-3 rounded-xl border transition-all cursor-pointer ${
                  selectedTargetFolder === null
                    ? 'bg-[#14B8A6]/10 border-[#14B8A6]/50 text-[#14B8A6]'
                    : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10'
                }`}
              >
                <input
                  type="radio"
                  name="targetFolder"
                  checked={selectedTargetFolder === null}
                  onChange={() => setSelectedTargetFolder(null)}
                  className="mr-3 w-4 h-4 accent-[#14B8A6]"
                />
                <span className="mr-2">📄</span>
                <span>Uncategorized</span>
              </label>

              {folders.map(folder => (
                <label
                  key={folder.id}
                  className={`w-full flex items-center px-4 py-3 rounded-xl border transition-all cursor-pointer ${
                    selectedTargetFolder === folder.id
                      ? 'bg-[#14B8A6]/10 border-[#14B8A6]/50 text-[#14B8A6]'
                      : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10'
                  }`}
                >
                  <input
                    type="radio"
                    name="targetFolder"
                    checked={selectedTargetFolder === folder.id}
                    onChange={() => setSelectedTargetFolder(folder.id)}
                    className="mr-3 w-4 h-4 accent-[#14B8A6]"
                  />
                  <span className="mr-2">{folder.icon || '📁'}</span>
                  <span className="flex-1">{folder.name}</span>
                  <span className="text-xs text-slate-500">({folder.item_count})</span>
                </label>
              ))}
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowMoveDialog(false)
                  setSelectedItemId(null)
                  setSelectedTargetFolder(null)
                }}
                className="flex-1 px-4 py-3 border border-white/15 text-slate-300 rounded-xl hover:bg-white/5 transition-all"
              >
                Cancel
              </button>
              <button
                onClick={moveToFolder}
                className="flex-1 px-4 py-3 bg-gradient-to-r from-[#14B8A6] to-[#06B6D4] text-white rounded-xl hover:shadow-lg hover:shadow-teal-500/25 transition-all duration-200 hover:scale-105"
              >
                ✓ Move
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Folder Confirmation */}
      {showDeleteFolderConfirm && folderToDelete !== null && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fade-in">
          <div className="glass-card p-6 w-full max-w-md animate-scale-in">
            <h2 className="text-2xl font-bold text-red-400 mb-4">Delete Folder?</h2>
            
            <p className="text-slate-300 mb-2">
              Are you sure you want to delete <strong>{folders.find(f => f.id === folderToDelete)?.name}</strong>?
            </p>
            <p className="text-slate-400 text-sm mb-6">
              All items in this folder will become uncategorized. This action cannot be undone.
            </p>

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowDeleteFolderConfirm(false)
                  setFolderToDelete(null)
                }}
                className="flex-1 px-4 py-3 border border-white/15 text-slate-300 rounded-xl hover:bg-white/5 transition-all"
              >
                Cancel
              </button>
              <button
                onClick={deleteFolder}
                className="flex-1 px-4 py-3 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl hover:shadow-lg hover:shadow-red-500/25 transition-all duration-200 hover:scale-105"
              >
                🗑️ Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
