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
    <div className="min-h-screen bg-gradient-to-br from-[#0A0E1A] via-[#0F172A] to-[#1E1B4B] pt-20 px-4 overflow-hidden relative">
      {/* Animated background gradient blobs */}
      <div className="fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-gradient-to-br from-teal-500/20 to-cyan-500/20 rounded-full blur-3xl animate-pulse-slow"></div>
        <div className="absolute bottom-20 right-1/4 w-96 h-96 bg-gradient-to-br from-purple-500/15 to-pink-500/15 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }}></div>
        <div className="absolute top-1/2 left-1/2 w-64 h-64 bg-gradient-to-br from-orange-500/10 to-yellow-500/10 rounded-full blur-3xl animate-float" style={{ animationDelay: '2s' }}></div>
      </div>

      <div className="max-w-7xl mx-auto relative">
        {/* Hero Section */}
        <div className="text-center mb-20 animate-fade-in">
          {/* Floating emoji */}
          <div className="text-8xl mb-6 animate-float">
            🚀
          </div>
          
          <h1 className="text-7xl md:text-8xl font-black mb-6 animate-slide-down">
            <span className="bg-gradient-to-r from-teal-400 via-cyan-400 to-blue-500 bg-clip-text text-transparent">
              StudyWith
            </span>
            <span className="bg-gradient-to-r from-purple-400 via-pink-400 to-orange-400 bg-clip-text text-transparent">
              AI
            </span>
          </h1>
          
          <p className="text-3xl text-transparent bg-gradient-to-r from-slate-200 to-slate-400 bg-clip-text mb-6 animate-slide-up font-semibold">
            Your AI-Powered Study Companion
          </p>
          
          <p className="text-xl text-slate-300 max-w-3xl mx-auto mb-10 animate-slide-up leading-relaxed" style={{ animationDelay: '0.1s' }}>
            Transform your learning experience with AI-generated exams, flashcards, and summaries. 
            <span className="text-teal-400 font-semibold"> Study smarter, not harder.</span>
          </p>
          
          {/* CTA Buttons */}
          <div className="flex gap-6 justify-center animate-slide-up" style={{ animationDelay: '0.2s' }}>
            <button 
              onClick={() => router.push('/upload')} 
              className="group relative px-8 py-4 bg-gradient-to-r from-teal-500 to-cyan-500 text-white font-bold rounded-2xl overflow-hidden transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-teal-500/50"
            >
              <span className="relative z-10 flex items-center gap-2">
                Get Started Free
                <span className="group-hover:translate-x-1 transition-transform">🚀</span>
              </span>
              <div className="absolute inset-0 bg-gradient-to-r from-cyan-500 to-blue-500 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            </button>
            <button 
              onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })} 
              className="px-8 py-4 border-2 border-slate-600 text-slate-200 font-bold rounded-2xl hover:border-teal-500 hover:text-teal-400 hover:bg-teal-500/10 transition-all duration-300 hover:scale-105"
            >
              Explore Features
            </button>
          </div>

          {/* Stats bar */}
          <div className="mt-16 grid grid-cols-3 gap-6 max-w-3xl mx-auto animate-scale-in" style={{ animationDelay: '0.3s' }}>
            {[
              { icon: '⚡', label: 'Instant AI', value: 'Generation' },
              { icon: '🎯', label: '100% Accurate', value: 'Grounding' },
              { icon: '🌟', label: 'Smart', value: 'Learning' }
            ].map((stat, i) => (
              <div key={i} className="glass-card p-6 hover:scale-105 transition-transform duration-300 group cursor-pointer">
                <div className="text-4xl mb-2 group-hover:animate-bounce-slow">{stat.icon}</div>
                <div className="text-2xl font-bold text-transparent bg-gradient-to-r from-teal-400 to-cyan-400 bg-clip-text">{stat.value}</div>
                <div className="text-sm text-slate-400">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Test Generator - Moved higher */}
        <div className="relative mb-20 animate-fade-in" style={{ animationDelay: '0.5s' }}>
          {/* Glow effect behind card */}
          <div className="absolute -inset-1 bg-gradient-to-r from-teal-500 via-purple-500 to-pink-500 rounded-3xl blur-xl opacity-20 group-hover:opacity-30 transition-opacity"></div>
          
          <div className="relative glass-card border-2 border-teal-500/30 hover:border-teal-500/50 transition-all duration-300">
            <div className="flex items-center gap-3 mb-6">
              <div className="text-5xl animate-wiggle">⚡</div>
              <div>
                <h2 className="text-4xl font-bold text-transparent bg-gradient-to-r from-teal-400 to-cyan-400 bg-clip-text">Quick Test Generator</h2>
                <p className="text-slate-400">Generate a test instantly on any topic - no login required!</p>
              </div>
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
            <div className="mt-6 p-5 bg-gradient-to-r from-purple-500/10 via-pink-500/10 to-orange-500/10 border-2 border-purple-500/30 rounded-2xl text-sm text-purple-300 relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-r from-purple-500/5 to-pink-500/5 translate-x-full group-hover:translate-x-0 transition-transform duration-700"></div>
              <p className="relative z-10">
                <span className="text-2xl mr-2">💡</span>
                <span className="font-bold text-transparent bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text">Pro Tip:</span> 
                <a href="/login" className="underline hover:text-pink-300 transition-colors mx-1 font-semibold">Login</a> 
                or 
                <a href="/register" className="underline hover:text-pink-300 transition-colors mx-1 font-semibold">create an account</a> 
                for unlimited tests and progress tracking!
              </p>
            </div>
          )}
          </div>
        </div>

        {/* Features Grid */}
        <div id="features" className="mb-20">
          <div className="text-center mb-12">
            <h2 className="text-5xl font-black mb-4 text-transparent bg-gradient-to-r from-teal-400 via-purple-400 to-pink-400 bg-clip-text">
              Powerful Features
            </h2>
            <p className="text-xl text-slate-300 max-w-2xl mx-auto">
              Everything you need to ace your studies 🎓
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                icon: '📄',
                title: 'Document Upload',
                desc: 'Upload PDFs, PPTX, DOCX to generate grounded content',
                color: 'from-teal-500 to-emerald-500',
                glow: 'teal',
                delay: '0s'
              },
              {
                icon: '🎯',
                title: 'Smart Exams',
                desc: 'AI generates intelligent MCQ exams from your documents',
                color: 'from-cyan-500 to-blue-500',
                glow: 'cyan',
                delay: '0.1s'
              },
              {
                icon: '💡',
                title: 'AI Tutor',
                desc: 'Chat with AI for detailed explanations and personalized help',
                color: 'from-purple-500 to-pink-500',
                glow: 'purple',
                delay: '0.2s'
              },
              {
                icon: '📊',
                title: 'Progress Tracking',
                desc: 'Monitor performance with detailed analytics and insights',
                color: 'from-orange-500 to-red-500',
                glow: 'orange',
                delay: '0.3s'
              },
              {
                icon: '🎴',
                title: 'Flashcards',
                desc: 'Auto-generate flashcards for quick and effective review',
                color: 'from-pink-500 to-rose-500',
                glow: 'pink',
                delay: '0.4s'
              },
              {
                icon: '📝',
                title: 'Smart Summaries',
                desc: 'Get structured summaries of your documents instantly',
                color: 'from-yellow-500 to-amber-500',
                glow: 'yellow',
                delay: '0.5s'
              }
            ].map((feature, i) => (
              <div
                key={i}
                className="relative group animate-scale-in"
                style={{ animationDelay: feature.delay }}
              >
                {/* Glow effect */}
                <div className={`absolute -inset-0.5 bg-gradient-to-r ${feature.color} rounded-2xl blur opacity-20 group-hover:opacity-40 transition-opacity duration-500`}></div>
                
                <div className="relative glass-card border border-white/10 group-hover:border-white/30 transition-all duration-300 h-full">
                  <div className="text-6xl mb-4 transition-all duration-500 group-hover:scale-125 group-hover:rotate-12 inline-block">
                    {feature.icon}
                  </div>
                  <h3 className={`text-2xl font-bold mb-3 text-transparent bg-gradient-to-r ${feature.color} bg-clip-text`}>
                    {feature.title}
                  </h3>
                  <p className="text-slate-300 leading-relaxed">
                    {feature.desc}
                  </p>
                  
                  {/* Hover indicator */}
                  <div className={`mt-4 h-1 w-0 bg-gradient-to-r ${feature.color} rounded-full group-hover:w-full transition-all duration-500`}></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* CTA Section */}
        <div className="relative mb-20 animate-slide-up">
          <div className="absolute -inset-1 bg-gradient-to-r from-teal-500 via-purple-500 to-pink-500 rounded-3xl blur-2xl opacity-30"></div>
          
          <div className="relative glass-card text-center border-2 border-purple-500/30 overflow-hidden">
            {/* Animated gradient overlay */}
            <div className="absolute inset-0 bg-gradient-to-r from-teal-500/5 via-purple-500/5 to-pink-500/5 animate-shimmer" style={{ backgroundSize: '200% 100%' }}></div>
            
            <div className="relative z-10 py-12">
              <div className="text-6xl mb-6 animate-bounce-slow">✨</div>
              <h2 className="text-5xl font-black mb-6 text-transparent bg-gradient-to-r from-teal-400 via-purple-400 to-pink-400 bg-clip-text">
                Ready to Level Up?
              </h2>
              <p className="text-xl text-slate-200 mb-8 max-w-2xl mx-auto leading-relaxed">
                Join thousands of students who are already studying smarter with AI-powered tools
              </p>
              <div className="flex gap-6 justify-center">
                <button 
                  onClick={() => router.push('/register')} 
                  className="group relative px-10 py-5 bg-gradient-to-r from-purple-500 to-pink-500 text-white font-bold text-lg rounded-2xl overflow-hidden transition-all duration-300 hover:scale-110 hover:shadow-2xl hover:shadow-purple-500/50"
                >
                  <span className="relative z-10 flex items-center gap-2">
                    Sign Up Free
                    <span className="group-hover:translate-x-1 transition-transform">→</span>
                  </span>
                  <div className="absolute inset-0 bg-gradient-to-r from-pink-500 to-orange-500 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                </button>
                <button 
                  onClick={() => router.push('/pricing')} 
                  className="px-10 py-5 border-2 border-purple-500 text-purple-300 font-bold text-lg rounded-2xl hover:bg-purple-500/20 hover:border-purple-400 transition-all duration-300 hover:scale-105"
                >
                  View Pricing
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
