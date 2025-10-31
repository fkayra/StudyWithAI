'use client'

import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api'

interface Summary {
  title: string
  sections: Array<{
    heading: string
    bullets: string[]
  }>
}

interface Citation {
  file_id: string
  evidence: string
}

interface SummaryData {
  summary: Summary
  citations: Citation[]
}

export default function SummariesPage() {
  const [data, setData] = useState<SummaryData | null>(null)
  const [loading, setLoading] = useState(false)
  const [prompt, setPrompt] = useState('')
  const [showPrompt, setShowPrompt] = useState(true)

  useEffect(() => {
    // Check if viewing from history
    const viewHistory = sessionStorage.getItem('viewHistory')
    if (viewHistory) {
      try {
        const historyData = JSON.parse(viewHistory)
        setData(historyData)
        setShowPrompt(false)
        sessionStorage.removeItem('viewHistory')
      } catch (e) {
        console.error('Failed to load history:', e)
      }
    }
  }, [])

  const generateSummary = async () => {
    const fileIdsStr = sessionStorage.getItem('uploadedFileIds')
    if (!fileIdsStr) {
      // Redirect to upload page instead of showing alert
      window.location.href = '/upload'
      return
    }

    const fileIds = JSON.parse(fileIdsStr)
    setLoading(true)
    setShowPrompt(false)

    try {
      const response = await apiClient.post('/summarize-from-files', {
        file_ids: fileIds,
        language: 'en',
        outline: true,
        prompt: prompt || undefined, // Send prompt if provided
      })

      setData(response.data)
      
      // Save to history
      const historyItem = {
        id: Date.now().toString(),
        type: 'summary' as const,
        title: response.data.summary?.title || 'Summary',
        timestamp: Date.now(),
        data: response.data
      }
      const existingHistory = JSON.parse(localStorage.getItem('studyHistory') || '[]')
      localStorage.setItem('studyHistory', JSON.stringify([historyItem, ...existingHistory]))
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to generate summary')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0F172A] pt-20 flex items-center justify-center">
        <div className="glass-card p-8 text-center">
          <div className="text-6xl mb-4 animate-pulse">📝</div>
          <div className="text-2xl text-slate-300 mb-2">Generating Summary...</div>
          <div className="text-sm text-slate-400">Analyzing your documents with AI</div>
        </div>
      </div>
    )
  }

  if (!data && showPrompt) {
    return (
      <div className="min-h-screen bg-[#0F172A] pt-20 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="glass-card animate-fade-in">
            <div className="text-center mb-8">
              <div className="text-6xl mb-6">📚</div>
              <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-[#14B8A6] to-[#06B6D4] bg-clip-text text-transparent">
                Generate Summary
              </h1>
              <p className="text-slate-300">
                AI will create study notes from your uploaded documents
              </p>
            </div>

            {/* Optional Prompt */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-slate-300 mb-3">
                Additional Instructions (Optional)
              </label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="e.g., 'Focus on key formulas and definitions', 'Include examples', 'Summarize in Turkish'..."
                className="input-modern h-32 resize-none"
              />
              <p className="text-xs text-slate-400 mt-2">
                💡 Leave empty for a general summary, or add specific instructions
              </p>
            </div>

            {/* Generate Button */}
            <button
              onClick={generateSummary}
              disabled={loading}
              className="btn-primary w-full"
            >
              {loading ? '⏳ Generating Summary...' : '✨ Generate Summary'}
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0F172A] pt-20 px-4 pb-12">
      {/* Animated background */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl animate-pulse-slow"></div>
        <div className="absolute bottom-20 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }}></div>
      </div>

      <div className="max-w-4xl mx-auto">
        {/* Title Card */}
        <div className="glass-card mb-8 animate-fade-in">
          <div className="flex items-center gap-4 mb-6">
            <div className="text-5xl">📝</div>
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-[#14B8A6] to-[#06B6D4] bg-clip-text text-transparent">
                {data.summary.title}
              </h1>
              <p className="text-slate-400 mt-2">
                {data.summary.sections.length} sections • AI-generated summary
              </p>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="flex gap-4 mt-6">
            <div className="flex-1 p-4 bg-gradient-to-br from-teal-500/10 to-teal-600/10 border border-teal-500/30 rounded-xl">
              <div className="text-teal-400 text-sm font-medium mb-1">Sections</div>
              <div className="text-2xl font-bold text-slate-100">{data.summary.sections.length}</div>
            </div>
            <div className="flex-1 p-4 bg-gradient-to-br from-cyan-500/10 to-cyan-600/10 border border-cyan-500/30 rounded-xl">
              <div className="text-cyan-400 text-sm font-medium mb-1">Key Points</div>
              <div className="text-2xl font-bold text-slate-100">
                {data.summary.sections.reduce((acc, section) => acc + section.bullets.length, 0)}
              </div>
            </div>
            <div className="flex-1 p-4 bg-gradient-to-br from-emerald-500/10 to-emerald-600/10 border border-emerald-500/30 rounded-xl">
              <div className="text-emerald-400 text-sm font-medium mb-1">Citations</div>
              <div className="text-2xl font-bold text-slate-100">{data.citations.length}</div>
            </div>
          </div>
        </div>

        {/* Sections */}
        <div className="space-y-6">
          {data.summary.sections.map((section, index) => (
            <div 
              key={index} 
              className="glass-card card-hover animate-slide-up"
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-teal-500/20 to-cyan-500/20 border border-teal-500/30 rounded-xl flex items-center justify-center text-teal-400 font-bold">
                  {index + 1}
                </div>
                <div className="flex-1">
                  <h2 className="text-2xl font-semibold mb-4 text-slate-100">
                    {section.heading}
                  </h2>
                  <ul className="space-y-3">
                    {section.bullets.map((bullet, bulletIndex) => (
                      <li key={bulletIndex} className="flex items-start group">
                        <span className="flex-shrink-0 w-6 h-6 bg-gradient-to-br from-teal-500/20 to-cyan-500/20 rounded-full flex items-center justify-center mr-3 mt-0.5 group-hover:scale-110 transition-transform">
                          <span className="text-teal-400 text-xs">✓</span>
                        </span>
                        <span className="text-slate-300 leading-relaxed">{bullet}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Citations */}
        {data.citations && data.citations.length > 0 && (
          <div className="glass-card mt-8 animate-scale-in" style={{ animationDelay: '0.5s' }}>
            <div className="flex items-center gap-3 mb-6">
              <div className="text-3xl">📎</div>
              <h2 className="text-2xl font-semibold text-slate-100">
                Evidence & Sources
              </h2>
            </div>
            <div className="space-y-3">
              {data.citations.map((citation, index) => (
                <div
                  key={index}
                  className="p-4 bg-gradient-to-br from-teal-500/5 to-cyan-500/5 border border-teal-500/20 rounded-xl hover:border-teal-500/40 transition-all duration-200 group"
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 w-8 h-8 bg-teal-500/20 rounded-lg flex items-center justify-center text-teal-400 text-sm font-semibold group-hover:scale-110 transition-transform">
                      {index + 1}
                    </div>
                    <div className="flex-1">
                      <div className="text-xs text-teal-400 font-medium mb-1">{citation.file_id}</div>
                      <div className="text-sm text-slate-300 leading-relaxed">{citation.evidence}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-4 mt-8 animate-fade-in">
          <button
            onClick={() => window.print()}
            className="btn-ghost flex-1"
          >
            🖨️ Print Summary
          </button>
          <button
            onClick={() => {
              const text = JSON.stringify(data, null, 2)
              navigator.clipboard.writeText(text)
              alert('Copied to clipboard!')
            }}
            className="btn-ghost flex-1"
          >
            📋 Copy to Clipboard
          </button>
          <button
            onClick={() => window.location.href = '/upload'}
            className="btn-primary flex-1"
          >
            📄 Upload More Files
          </button>
        </div>
      </div>
    </div>
  )
}
