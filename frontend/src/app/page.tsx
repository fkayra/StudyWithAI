'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api'
import { useAuth } from '@/components/AuthProvider'
import { DashboardMockup, ExamMockup } from '@/components/MockupSVG'

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
    
    setLoading(true)
    try {
      const response = await apiClient.post('/ask', {
        prompt,
        level,
        count: 5
      })
      
      // Clear old exam states before storing new exam
      sessionStorage.removeItem('currentExam')
      sessionStorage.removeItem('currentExamState')
      
      // Mark this as a quick exam (not from uploaded files)
      sessionStorage.setItem('isQuickExam', 'true')
      sessionStorage.setItem('quickExamPrompt', prompt)
      
      // Store new exam in sessionStorage and navigate
      sessionStorage.setItem('currentExam', JSON.stringify(response.data))
      router.push('/exam?quick=true')
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || 'Failed to generate test.'
      if (error.response?.status === 403) {
        alert(errorMsg + ' Please login or upgrade to Premium for more quota.')
      } else {
        alert(errorMsg + ' Please check your connection and try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0F172A] pt-20 px-4">
      {/* Subtle background accent */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute top-40 left-1/3 w-[600px] h-[600px] bg-teal-500/5 rounded-full blur-3xl"></div>
      </div>

      <div className="max-w-6xl mx-auto">
        {/* Hero Section */}
        <div className="text-center mb-20 pt-12 animate-fade-in">
          <h1 className="text-6xl md:text-7xl font-bold mb-6 animate-slide-down">
            <span className="text-slate-100">Study</span>
            <span className="text-transparent bg-gradient-to-r from-teal-400 to-cyan-400 bg-clip-text">With</span>
            <span className="text-slate-100">AI</span>
          </h1>
          
          <p className="text-2xl text-slate-300 mb-4 animate-slide-up">
            Smart Study Tools, Powered by AI
          </p>
          
          <p className="text-lg text-slate-400 max-w-2xl mx-auto mb-10 animate-slide-up leading-relaxed" style={{ animationDelay: '0.1s' }}>
            Generate exams, flashcards, and summaries from your documents. 
            Study smarter with AI-powered insights.
          </p>
          
          {/* CTA Buttons */}
          <div className="flex gap-4 justify-center animate-slide-up" style={{ animationDelay: '0.2s' }}>
            <button 
              onClick={() => router.push('/upload')} 
              className="px-8 py-4 bg-gradient-to-r from-teal-500 to-cyan-500 text-white font-semibold rounded-xl hover:shadow-lg hover:shadow-teal-500/30 transition-all duration-300 hover:scale-105"
            >
              Get Started
            </button>
            <button 
              onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })} 
              className="px-8 py-4 border border-slate-600 text-slate-300 font-semibold rounded-xl hover:border-slate-500 hover:bg-slate-800/50 transition-all duration-300"
            >
              Learn More
            </button>
          </div>
        </div>

        {/* Quick Test Generator */}
        <div className="glass-card mb-16 max-w-3xl mx-auto animate-fade-in" style={{ animationDelay: '0.3s' }}>
          <div className="mb-6">
            <h2 className="text-3xl font-bold text-slate-100 mb-2">Quick Test Generator</h2>
            <p className="text-slate-400">Create a practice test on any topic instantly</p>
          </div>
          
          {/* Difficulty Selector */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-slate-300 mb-3">
              Difficulty Level
            </label>
            <div className="grid grid-cols-3 gap-3">
              {[
                { value: 'ilkokul-ortaokul', label: 'İlk-Ortaokul' },
                { value: 'lise', label: 'Lise' },
                { value: 'universite', label: 'Üniversite' }
              ].map((item) => (
                <button
                  key={item.value}
                  onClick={() => setLevel(item.value as any)}
                  className={`py-3 px-4 rounded-lg border transition-all duration-200 ${
                    level === item.value
                      ? 'border-teal-500 bg-teal-500/10 text-teal-400'
                      : 'border-slate-700 text-slate-400 hover:border-slate-600 hover:bg-slate-800/50'
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          {/* Prompt Input */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-slate-300 mb-3">
              Topic or Subject
            </label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g., Photosynthesis, World War II, Linear Algebra..."
              className="input-modern h-28 resize-none"
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
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="animate-spin">⏳</span>
                  Generating...
                </span>
              ) : (
                'Generate Test'
              )}
            </button>
            <button
              type="button"
              onClick={() => router.push('/upload')}
              className="btn-ghost px-8"
            >
              Upload Files
            </button>
          </div>
          
          {!user && (
            <div className="mt-6 p-4 bg-teal-500/5 border border-teal-500/20 rounded-lg text-sm text-slate-300">
              <span className="text-teal-400 font-semibold">💡 Tip:</span> <a href="/login" className="underline hover:text-teal-400 transition-colors">Login</a> or <a href="/register" className="underline hover:text-teal-400 transition-colors">create an account</a> to save your progress and access unlimited tests
            </div>
          )}
        </div>

        {/* Features Grid */}
        <div id="features" className="mb-16">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold text-slate-100 mb-3">
              Everything You Need to Study Better
            </h2>
            <p className="text-lg text-slate-400 max-w-2xl mx-auto">
              Powerful AI tools designed to help you learn more effectively
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                icon: '📚',
                title: 'Smart Summaries',
                desc: 'Get structured, easy-to-understand summaries of your study materials'
              },
              {
                icon: '🎯',
                title: 'Practice Exams',
                desc: 'Generate custom exams with multiple-choice questions from your documents'
              },
              {
                icon: '🎴',
                title: 'Flashcards',
                desc: 'Automatically create flashcards for quick review and memorization'
              },
              {
                icon: '💬',
                title: 'AI Tutor',
                desc: 'Get instant explanations and answers to your questions'
              },
              {
                icon: '📊',
                title: 'Track Progress',
                desc: 'Monitor your learning with detailed performance analytics'
              },
              {
                icon: '📄',
                title: 'Multi-Format',
                desc: 'Upload PDFs, Word docs, PowerPoints, and text files'
              }
            ].map((feature, i) => (
              <div
                key={i}
                className="glass-card group hover:border-teal-500/30 transition-all duration-300"
              >
                <div className="text-5xl mb-4 transition-transform group-hover:scale-110 duration-300">
                  {feature.icon}
                </div>
                <h3 className="text-xl font-semibold mb-2 text-slate-100">
                  {feature.title}
                </h3>
                <p className="text-slate-400 text-sm leading-relaxed">
                  {feature.desc}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* CTA Section */}
        <div className="glass-card text-center mb-16 max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-slate-100 mb-4">
            Ready to Get Started?
          </h2>
          <p className="text-slate-300 mb-6 max-w-xl mx-auto">
            Join students who are improving their study efficiency with AI-powered tools
          </p>
          <div className="flex gap-4 justify-center">
            <button 
              onClick={() => router.push('/register')} 
              className="px-8 py-3 bg-gradient-to-r from-teal-500 to-cyan-500 text-white font-semibold rounded-xl hover:shadow-lg hover:shadow-teal-500/30 transition-all duration-300 hover:scale-105"
            >
              Sign Up Free
            </button>
            <button 
              onClick={() => router.push('/pricing')} 
              className="px-8 py-3 border border-slate-600 text-slate-300 font-semibold rounded-xl hover:border-slate-500 hover:bg-slate-800/50 transition-all duration-300"
            >
              View Pricing
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
