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
      
      // Store exam in sessionStorage and navigate
      sessionStorage.setItem('currentExam', JSON.stringify(response.data))
      router.push('/exam')
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
    <div className="min-h-screen bg-[#0F172A] pt-20 px-4 overflow-hidden">
      {/* Animated background gradient */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl animate-pulse-slow"></div>
        <div className="absolute bottom-20 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }}></div>
      </div>

      <div className="max-w-7xl mx-auto">
        {/* Hero Section */}
        <div className="text-center mb-16 animate-fade-in">
          <h1 className="text-6xl md:text-7xl font-bold bg-gradient-to-r from-[#14B8A6] via-[#06B6D4] to-[#0891B2] bg-clip-text text-transparent mb-6 animate-slide-down">
            StudyWithAI
          </h1>
          <p className="text-2xl text-slate-300 mb-4 animate-slide-up">
            AI-Powered Study Assistant
          </p>
          <p className="text-lg text-slate-400 max-w-2xl mx-auto animate-slide-up" style={{ animationDelay: '0.1s' }}>
            Generate grounded exams, flashcards, and summaries from your documents with intelligent AI
          </p>
          
          {/* CTA Buttons */}
          <div className="flex gap-4 justify-center mt-8 animate-slide-up" style={{ animationDelay: '0.2s' }}>
            <button onClick={() => router.push('/upload')} className="btn-primary">
              Get Started 🚀
            </button>
            <button onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })} className="btn-ghost">
              Learn More
            </button>
          </div>
        </div>

        {/* Quick Test Generator - Moved higher */}
        <div className="glass-card mb-16 animate-fade-in" style={{ animationDelay: '0.4s' }}>
          <h2 className="text-3xl font-semibold mb-2 text-slate-100">Quick Test Generator</h2>
          <p className="text-slate-400 mb-6">Generate a test instantly on any topic</p>
          
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
                  className={`py-3 px-4 rounded-xl border transition-all duration-200 transform hover:scale-105 active:scale-95 ${
                    level === item.value
                      ? 'border-[#14B8A6] bg-gradient-to-r from-[#14B8A6]/20 to-[#06B6D4]/20 text-[#06B6D4] shadow-lg shadow-teal-500/25'
                      : 'border-white/15 text-slate-300 hover:bg-white/5 hover:border-white/30'
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
              Topic or Question
            </label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Enter a topic to generate questions about... (e.g., 'Photosynthesis', 'World War II', 'Linear Algebra')"
              className="input-modern h-32 resize-none"
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
                'Generate Test ✨'
              )}
            </button>
            <button
              type="button"
              onClick={() => router.push('/upload')}
              className="btn-ghost px-6"
            >
              Upload Files 📄
            </button>
          </div>
          
          {!user && (
            <div className="mt-6 p-4 bg-gradient-to-r from-teal-500/10 to-cyan-500/10 border border-teal-500/30 rounded-xl text-sm text-teal-300 animate-pulse-slow">
              💡 <span className="font-semibold">Pro Tip:</span> <a href="/login" className="underline hover:text-teal-200 transition-colors">Login</a> or <a href="/register" className="underline hover:text-teal-200 transition-colors">create an account</a> for unlimited tests and to track your progress!
            </div>
          )}
        </div>

        {/* Features Grid - Moved higher */}
        <div id="features" className="mb-16">
          <h2 className="text-4xl font-bold text-center mb-4 text-slate-100">Powerful Features</h2>
          <p className="text-center text-slate-400 mb-12 max-w-2xl mx-auto">
            Everything you need to study smarter, not harder
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                icon: '📄',
                title: 'Document Upload',
                desc: 'Upload PDFs, PPTX, DOCX, and images to generate grounded content',
                delay: '0s'
              },
              {
                icon: '🎯',
                title: 'Smart Exams',
                desc: 'AI generates MCQ exams strictly from your documents with intelligent question generation',
                delay: '0.1s'
              },
              {
                icon: '💡',
                title: 'AI Tutor',
                desc: 'Get detailed explanations and chat with an AI tutor for personalized help',
                delay: '0.2s'
              },
              {
                icon: '📊',
                title: 'Progress Tracking',
                desc: 'Monitor your performance with detailed analytics and insights',
                delay: '0.3s'
              },
              {
                icon: '🎴',
                title: 'Flashcards',
                desc: 'Auto-generate flashcards from your study materials for quick review',
                delay: '0.4s'
              },
              {
                icon: '📝',
                title: 'Smart Summaries',
                desc: 'Get concise, structured summaries of your documents instantly',
                delay: '0.5s'
              }
            ].map((feature, i) => (
              <div
                key={i}
                className="glass-card card-hover animate-scale-in group"
                style={{ animationDelay: feature.delay }}
              >
                <div className="text-5xl mb-4 transition-transform group-hover:scale-110 group-hover:rotate-12 duration-300">
                  {feature.icon}
                </div>
                <h3 className="text-xl font-semibold mb-3 text-slate-100 group-hover:text-[#06B6D4] transition-colors">
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
        <div className="glass-card text-center mb-12 animate-slide-up">
          <h2 className="text-3xl font-bold mb-4 bg-gradient-to-r from-[#14B8A6] to-[#06B6D4] bg-clip-text text-transparent">
            Ready to Transform Your Study Experience?
          </h2>
          <p className="text-slate-300 mb-6 max-w-2xl mx-auto">
            Join thousands of students who are already studying smarter with AI-powered tools
          </p>
          <div className="flex gap-4 justify-center">
            <button onClick={() => router.push('/register')} className="btn-primary">
              Sign Up Free
            </button>
            <button onClick={() => router.push('/pricing')} className="btn-ghost">
              View Pricing
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
