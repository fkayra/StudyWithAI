'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api'
import { useAuth } from '@/components/AuthProvider'

export default function Home() {
  const router = useRouter()
  const { user } = useAuth()
  const [prompt, setPrompt] = useState('')
  const [level, setLevel] = useState<'ilkokul-ortaokul' | 'lise' | 'universite'>('lise')
  const [loading, setLoading] = useState(false)

  const handleGenerateTest = async () => {
    if (!prompt.trim()) {
      alert('Please enter a topic')
      return
    }

    // Check if user is logged in
    if (!user) {
      alert('Please login first to generate tests')
      router.push('/login')
      return
    }
    
    setLoading(true)
    try {
      const response = await apiClient.post('/ask', {
        prompt,
        level,
        count: 5
      })
      
      // Store exam in sessionStorage and navigate
      sessionStorage.setItem('currentExam', JSON.stringify(response.data))
      router.push('/exam')
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to generate test. Please check your connection and try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0B1220] pt-20 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent mb-4">
            AI Study Assistant
          </h1>
          <p className="text-xl text-slate-300">
            Generate grounded exams, flashcards, and summaries from your documents
          </p>
        </div>

        {/* Main Card */}
        <div className="glass-card p-8 mb-8">
          <h2 className="text-2xl font-semibold mb-6 text-slate-100">Generate a Test</h2>
          
          {/* Difficulty Selector */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-slate-300 mb-3">
              Difficulty Level
            </label>
            <div className="grid grid-cols-3 gap-3">
              <button
                onClick={() => setLevel('ilkokul-ortaokul')}
                className={`py-3 px-4 rounded-xl border transition-all duration-200 ${
                  level === 'ilkokul-ortaokul'
                    ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                    : 'border-white/15 text-slate-300 hover:bg-white/5'
                }`}
              >
                İlk-Ortaokul
              </button>
              <button
                onClick={() => setLevel('lise')}
                className={`py-3 px-4 rounded-xl border transition-all duration-200 ${
                  level === 'lise'
                    ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                    : 'border-white/15 text-slate-300 hover:bg-white/5'
                }`}
              >
                Lise
              </button>
              <button
                onClick={() => setLevel('universite')}
                className={`py-3 px-4 rounded-xl border transition-all duration-200 ${
                  level === 'universite'
                    ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                    : 'border-white/15 text-slate-300 hover:bg-white/5'
                }`}
              >
                Üniversite
              </button>
            </div>
          </div>

          {/* Prompt Input */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-slate-300 mb-3">
              Topic or Question
            </label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Enter a topic to generate questions about..."
              className="w-full h-32 px-4 py-3 bg-[#1F2937] border border-white/10 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            />
          </div>

          {/* Action Buttons */}
          <div className="flex gap-4">
            <button
              type="button"
              onClick={handleGenerateTest}
              disabled={loading || !prompt.trim()}
              className="btn-primary flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Generating...' : 'Generate Test'}
            </button>
            <button
              type="button"
              onClick={() => router.push('/upload')}
              className="btn-ghost"
            >
              Upload Files
            </button>
          </div>
          
          {!user && (
            <div className="mt-4 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg text-sm text-blue-300">
              💡 Tip: <a href="/login" className="underline hover:text-blue-200">Login</a> or <a href="/register" className="underline hover:text-blue-200">create an account</a> to start generating tests
            </div>
          )}
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="glass-card p-6">
            <div className="text-3xl mb-3">📄</div>
            <h3 className="text-lg font-semibold mb-2 text-slate-100">Document Upload</h3>
            <p className="text-slate-400 text-sm">
              Upload PDFs, PPTX, DOCX, and images to generate grounded content
            </p>
          </div>
          
          <div className="glass-card p-6">
            <div className="text-3xl mb-3">🎯</div>
            <h3 className="text-lg font-semibold mb-2 text-slate-100">Smart Exams</h3>
            <p className="text-slate-400 text-sm">
              AI generates MCQ exams strictly from your documents
            </p>
          </div>
          
          <div className="glass-card p-6">
            <div className="text-3xl mb-3">💡</div>
            <h3 className="text-lg font-semibold mb-2 text-slate-100">AI Tutor</h3>
            <p className="text-slate-400 text-sm">
              Get explanations and chat with an AI tutor for any question
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
