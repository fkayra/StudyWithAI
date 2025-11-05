'use client'

import { useRouter } from 'next/navigation'
import { useAuth } from '@/components/AuthProvider'
import { useEffect, useState } from 'react'
import { historyAPI } from '@/lib/api'

export default function Dashboard() {
  const router = useRouter()
  const { user } = useAuth()
  const [stats, setStats] = useState({
    summaries: 0,
    flashcards: 0,
    truefalse: 0,
    exams: 0
  })

  useEffect(() => {
    // Load stats from API (which handles both backend and localStorage)
    const loadStats = async () => {
      try {
        const history = await historyAPI.getAll()
        const summariesCount = history.filter((item: any) => item.type === 'summary').length
        const flashcardsCount = history.filter((item: any) => item.type === 'flashcards').length
        const truefalseCount = history.filter((item: any) => item.type === 'truefalse').length
        const examsCount = history.filter((item: any) => item.type === 'exam').length
        
        setStats({
          summaries: summariesCount,
          flashcards: flashcardsCount,
          truefalse: truefalseCount,
          exams: examsCount
        })
      } catch (error) {
        console.error('Failed to load history stats:', error)
      }
    }
    
    loadStats()
  }, [])

  const features = [
    {
      id: 'summaries',
      title: 'Summaries',
      description: 'Generate comprehensive study summaries from your documents',
      icon: '📝',
      path: '/summaries',
      color: 'from-teal-500 to-emerald-500',
      stat: stats.summaries,
      statLabel: 'created'
    },
    {
      id: 'flashcards',
      title: 'Flashcards',
      description: 'Create interactive flashcards for quick review and memorization',
      icon: '🎴',
      path: '/flashcards',
      color: 'from-cyan-500 to-blue-500',
      stat: stats.flashcards,
      statLabel: 'sets'
    },
    {
      id: 'truefalse',
      title: 'True/False',
      description: 'Practice with true or false statements to test your knowledge',
      icon: '✅❌',
      path: '/truefalse',
      color: 'from-green-500 to-emerald-500',
      stat: stats.truefalse,
      statLabel: 'sets'
    },
    {
      id: 'exams',
      title: 'Exams',
      description: 'Generate practice exams with AI-powered questions',
      icon: '🎯',
      path: '/exam',
      color: 'from-blue-500 to-indigo-500',
      stat: stats.exams,
      statLabel: 'taken'
    },
    {
      id: 'history',
      title: 'History',
      description: 'View and manage all your past study materials',
      icon: '📊',
      path: '/history',
      color: 'from-purple-500 to-pink-500',
      stat: stats.summaries + stats.flashcards + stats.truefalse + stats.exams,
      statLabel: 'total items'
    }
  ]

  return (
    <div className="min-h-screen bg-[#0F172A] pt-20 px-4">
      {/* Subtle background accent */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute top-40 right-1/4 w-[500px] h-[500px] bg-teal-500/5 rounded-full blur-3xl"></div>
      </div>

      <div className="max-w-7xl mx-auto py-12">
        {/* Header */}
        <div className="mb-12 animate-fade-in">
          <h1 className="text-5xl font-bold text-slate-100 mb-3">
            Welcome back{user?.email ? `, ${user.email.split('@')[0]}` : ''}
          </h1>
          <p className="text-xl text-slate-400">
            Choose a tool to continue your study session
          </p>
        </div>

        {/* Quick Actions */}
        <div className="mb-8 animate-slide-up">
          <button
            onClick={() => router.push('/upload')}
            className="w-full md:w-auto px-8 py-4 bg-gradient-to-r from-teal-500 to-cyan-500 text-white font-semibold rounded-xl hover:shadow-lg hover:shadow-teal-500/30 transition-all duration-300 hover:scale-[1.02]"
          >
            📄 Upload New Documents
          </button>
        </div>

        {/* Feature Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
          {features.map((feature, index) => (
            <div
              key={feature.id}
              onClick={() => router.push(feature.path)}
              className="group relative cursor-pointer animate-scale-in"
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              {/* Glow effect on hover */}
              <div className={`absolute -inset-0.5 bg-gradient-to-r ${feature.color} rounded-2xl blur opacity-0 group-hover:opacity-20 transition-opacity duration-500`}></div>
              
              {/* Card content */}
              <div className="relative glass-card h-full border border-slate-700/50 group-hover:border-slate-600 transition-all duration-300 p-8">
                <div className="flex items-start justify-between mb-4">
                  <div className="text-6xl group-hover:scale-110 transition-transform duration-300">
                    {feature.icon}
                  </div>
                  <div className="text-right">
                    <div className={`text-3xl font-bold text-transparent bg-gradient-to-r ${feature.color} bg-clip-text`}>
                      {feature.stat}
                    </div>
                    <div className="text-sm text-slate-500 uppercase tracking-wide">
                      {feature.statLabel}
                    </div>
                  </div>
                </div>
                
                <h2 className="text-2xl font-bold text-slate-100 mb-2 group-hover:text-teal-400 transition-colors">
                  {feature.title}
                </h2>
                <p className="text-slate-400 leading-relaxed mb-4">
                  {feature.description}
                </p>
                
                {/* Arrow indicator */}
                <div className="flex items-center gap-2 text-slate-500 group-hover:text-teal-400 transition-colors">
                  <span className="text-sm font-medium">Get started</span>
                  <span className="transform group-hover:translate-x-1 transition-transform">→</span>
                </div>
                
                {/* Bottom accent line */}
                <div className={`absolute bottom-0 left-0 h-1 w-0 bg-gradient-to-r ${feature.color} group-hover:w-full transition-all duration-500 rounded-b-xl`}></div>
              </div>
            </div>
          ))}
        </div>

        {/* Additional Info Section */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-slide-up" style={{ animationDelay: '0.4s' }}>
          <div className="glass-card border border-slate-700/50 p-6">
            <div className="text-3xl mb-3">⚡</div>
            <h3 className="text-lg font-semibold text-slate-200 mb-2">Instant Generation</h3>
            <p className="text-sm text-slate-400">AI-powered tools create your study materials in seconds</p>
          </div>
          
          <div className="glass-card border border-slate-700/50 p-6">
            <div className="text-3xl mb-3">🎯</div>
            <h3 className="text-lg font-semibold text-slate-200 mb-2">Smart Content</h3>
            <p className="text-sm text-slate-400">Questions and summaries grounded in your documents</p>
          </div>
          
          <div className="glass-card border border-slate-700/50 p-6">
            <div className="text-3xl mb-3">📈</div>
            <h3 className="text-lg font-semibold text-slate-200 mb-2">Track Progress</h3>
            <p className="text-sm text-slate-400">Monitor your learning journey with detailed history</p>
          </div>
        </div>

        {/* Getting Started Tips */}
        <div className="mt-12 glass-card border border-teal-500/20 p-8 animate-fade-in" style={{ animationDelay: '0.5s' }}>
          <h3 className="text-2xl font-bold text-slate-100 mb-4 flex items-center gap-3">
            <span>💡</span>
            <span>Quick Tips</span>
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex gap-3">
              <div className="text-teal-400 font-bold">1.</div>
              <div>
                <p className="text-slate-300 font-medium">Upload your documents</p>
                <p className="text-sm text-slate-500">Supports PDF, DOCX, PPTX, and TXT files</p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="text-teal-400 font-bold">2.</div>
              <div>
                <p className="text-slate-300 font-medium">Choose your tool</p>
                <p className="text-sm text-slate-500">Generate summaries, flashcards, or exams</p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="text-teal-400 font-bold">3.</div>
              <div>
                <p className="text-slate-300 font-medium">Study and learn</p>
                <p className="text-sm text-slate-500">Review your materials and track progress</p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="text-teal-400 font-bold">4.</div>
              <div>
                <p className="text-slate-300 font-medium">Check your history</p>
                <p className="text-sm text-slate-500">Access all past materials anytime</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
