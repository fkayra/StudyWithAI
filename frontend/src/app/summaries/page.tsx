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

  useEffect(() => {
    generateSummary()
  }, [])

  const generateSummary = async () => {
    const fileIdsStr = sessionStorage.getItem('uploadedFileIds')
    if (!fileIdsStr) {
      alert('No files uploaded. Please upload documents first.')
      return
    }

    const fileIds = JSON.parse(fileIdsStr)
    setLoading(true)

    try {
      const response = await apiClient.post('/summarize-from-files', {
        file_ids: fileIds,
        language: 'en',
        outline: true,
      })

      setData(response.data)
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to generate summary')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0B1220] pt-20 flex items-center justify-center">
        <div className="text-2xl text-slate-300">Generating summary...</div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-[#0B1220] pt-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-4xl font-bold mb-8 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            No Summary Generated
          </h1>
          <p className="text-slate-300 mb-8">
            Upload documents first to generate a summary.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0B1220] pt-20 px-4 pb-12">
      <div className="max-w-4xl mx-auto">
        <div className="glass-card p-8 mb-8">
          <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            {data.summary.title}
          </h1>
        </div>

        {/* Sections */}
        <div className="space-y-6">
          {data.summary.sections.map((section, index) => (
            <div key={index} className="glass-card p-6">
              <h2 className="text-2xl font-semibold mb-4 text-slate-100">
                {section.heading}
              </h2>
              <ul className="space-y-3">
                {section.bullets.map((bullet, bulletIndex) => (
                  <li key={bulletIndex} className="flex items-start">
                    <span className="text-blue-400 mr-3 mt-1">•</span>
                    <span className="text-slate-300 leading-relaxed">{bullet}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Citations */}
        {data.citations.length > 0 && (
          <div className="glass-card p-6 mt-8">
            <h2 className="text-xl font-semibold mb-4 text-slate-100">
              📎 Evidence & Citations
            </h2>
            <div className="space-y-2">
              {data.citations.map((citation, index) => (
                <div
                  key={index}
                  className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg text-sm text-slate-300"
                >
                  {citation.evidence}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
