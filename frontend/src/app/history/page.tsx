'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { historyAPI } from '@/lib/api'

interface HistoryItem {
  id: string | number
  type: 'summary' | 'flashcards' | 'truefalse' | 'exam'
  title: string
  timestamp: number
  data: any
  score?: {
    correct: number
    total: number
    percentage: number
  }
}

export default function HistoryPage() {
  const router = useRouter()
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [filter, setFilter] = useState<'all' | 'summary' | 'flashcards' | 'truefalse' | 'exam'>('all')

  useEffect(() => {
    loadHistory()
  }, [])

  const loadHistory = async () => {
    try {
      const items = await historyAPI.getAll()
      setHistory(items.sort((a: HistoryItem, b: HistoryItem) => b.timestamp - a.timestamp))
    } catch (e) {
      console.error('Failed to load history:', e)
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
  }

  const viewItem = (item: HistoryItem) => {
    console.log('View item:', item)
    
    // Store the data and navigate to the appropriate page
    if (item.type === 'summary') {
      sessionStorage.setItem('viewHistory', JSON.stringify(item.data))
      router.push('/summaries')
    } else if (item.type === 'flashcards') {
      sessionStorage.setItem('viewHistory', JSON.stringify(item.data))
      router.push('/flashcards')
    } else if (item.type === 'truefalse') {
      sessionStorage.setItem('viewHistory', JSON.stringify(item.data))
      router.push('/truefalse')
    } else if (item.type === 'exam') {
      console.log('Exam data structure:', {
        hasExam: !!item.data.exam,
        hasAnswers: !!item.data.answers,
        dataKeys: Object.keys(item.data)
      })
      
      // Store the history item ID so we can update it later
      sessionStorage.setItem('viewHistoryExamId', item.id)
      
      // For exams, use separate page (/view-exam) to avoid navigation confusion
      // Check if data has exam and answers (completed exam) or if data IS the exam
      if (item.data.exam && item.data.answers) {
        // Data structure: { exam: {...}, answers: {...} }
        console.log('Loading completed exam with results')
        sessionStorage.setItem('viewHistoryExam', JSON.stringify({
          exam: item.data.exam,
          answers: item.data.answers,
          showResults: true
        }))
      } else if (item.data.exam) {
        // Data structure: { exam: {...} } without answers
        console.log('Loading exam without answers')
        sessionStorage.setItem('viewHistoryExam', JSON.stringify({
          exam: item.data.exam,
          answers: {},
          showResults: false
        }))
      } else if (item.data.questions) {
        // Old data structure: item.data IS the exam itself
        console.log('Loading exam from old data structure')
        sessionStorage.setItem('viewHistoryExam', JSON.stringify({
          exam: item.data,
          answers: {},
          showResults: false
        }))
      }
      
      console.log('Navigating to /view-exam')
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
            {history.length > 0 && (
              <button
                onClick={clearHistory}
                className="btn-ghost text-red-400 hover:bg-red-500/10 hover:border-red-500/30"
              >
                🗑️ Clear All
              </button>
            )}
          </div>

          {/* Filter buttons */}
          <div className="flex gap-2 mt-6">
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
                      </div>

                      {/* Actions */}
                      <div className="flex gap-2">
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
    </div>
  )
}
