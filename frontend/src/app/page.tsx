'use client'

import { useRouter } from 'next/navigation'
import { useAuth } from '@/components/AuthProvider'

export default function Home() {
  const router = useRouter()
  const { user } = useAuth()

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
              onClick={() => router.push('/register')} 
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
