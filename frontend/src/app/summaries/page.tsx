'use client'

// Version: 2025-01-11-v3 - Exam-ready summary renderer
import { useState, useEffect, useCallback } from 'react'
import { apiClient, historyAPI } from '@/lib/api'

// New exam-ready schema
interface Concept {
  term: string
  definition: string
  explanation: string
  example?: string
  key_points?: string[]
}

interface Section {
  heading: string
  concepts: Concept[]
  bullets?: string[]  // Backward compatibility with old schema
}

interface Formula {
  name: string
  formula?: string  // Old schema
  expression?: string  // New schema
  variables: string | { [key: string]: string }  // Can be string or object
  when_to_use?: string  // Old schema
  notes?: string  // New schema
}

interface GlossaryTerm {
  term: string
  definition: string
}

interface ExamPractice {
  multiple_choice?: Array<{
    question: string
    options: { [key: string]: string }
    correct: string
    explanation: string
  }>
  short_answer?: Array<{
    question: string
    answer?: string
    key_points?: string[]
  }>
  problem_solving?: Array<{
    problem: string
    approach: string
    solution: string
  }>
}

interface Summary {
  title: string
  overview?: string
  learning_objectives?: string[]
  sections: Section[]
  formula_sheet?: Formula[]
  glossary?: GlossaryTerm[]
  exam_practice?: ExamPractice
}

interface Citation {
  file_id: string
  evidence: string
}

interface SummaryData {
  summary: Summary
  citations: Citation[]
}

interface UploadedFile {
  file_id: string
  filename: string
  mime: string
  size: number
}

export default function SummariesPage() {
  const [data, setData] = useState<SummaryData | null>(null)
  const [loading, setLoading] = useState(false)
  const [prompt, setPrompt] = useState('')
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [uploading, setUploading] = useState(false)
  const [dragActive, setDragActive] = useState(false)

  useEffect(() => {
    // Check if viewing from history
    const viewHistory = sessionStorage.getItem('viewHistory')
    if (viewHistory) {
      try {
        const historyData = JSON.parse(viewHistory)
        setData(historyData)
        sessionStorage.removeItem('viewHistory')
      } catch (e) {
        console.error('Failed to load history:', e)
      }
    }
    
    // Load existing uploaded files from sessionStorage
    const uploadedFilesStr = sessionStorage.getItem('uploadedFiles')
    if (uploadedFilesStr) {
      try {
        const uploadedFiles = JSON.parse(uploadedFilesStr)
        setFiles(uploadedFiles)
      } catch (e) {
        console.error('Failed to load uploaded files:', e)
      }
    }
  }, [])

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    const droppedFiles = Array.from(e.dataTransfer.files)
    await uploadFiles(droppedFiles)
  }, [])

  const handleFileInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files)
      await uploadFiles(selectedFiles)
    }
  }

  const uploadFiles = async (filesToUpload: File[]) => {
    setUploading(true)
    const formData = new FormData()
    filesToUpload.forEach((file) => {
      formData.append('files', file)
    })

    try {
      const response = await apiClient.post('/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      const newFiles = response.data
      setFiles((prev) => {
        const updatedFiles = [...prev, ...newFiles]
        sessionStorage.setItem('uploadedFiles', JSON.stringify(updatedFiles))
        return updatedFiles
      })
      const newFileIds = newFiles.map((f: UploadedFile) => f.file_id)
      const existingIds = sessionStorage.getItem('uploadedFileIds')
      const allFileIds = existingIds ? [...JSON.parse(existingIds), ...newFileIds] : newFileIds
      sessionStorage.setItem('uploadedFileIds', JSON.stringify(allFileIds))
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const removeFile = (fileId: string) => {
    setFiles((prev) => {
      const updatedFiles = prev.filter(f => f.file_id !== fileId)
      if (updatedFiles.length > 0) {
        sessionStorage.setItem('uploadedFiles', JSON.stringify(updatedFiles))
      } else {
        sessionStorage.removeItem('uploadedFiles')
      }
      return updatedFiles
    })
    
    const fileIdsStr = sessionStorage.getItem('uploadedFileIds')
    if (fileIdsStr) {
      const fileIds = JSON.parse(fileIdsStr)
      const updatedIds = fileIds.filter((id: string) => id !== fileId)
      if (updatedIds.length > 0) {
        sessionStorage.setItem('uploadedFileIds', JSON.stringify(updatedIds))
      } else {
        sessionStorage.removeItem('uploadedFileIds')
      }
    }
  }

  const generateSummary = async () => {
    const fileIdsStr = sessionStorage.getItem('uploadedFileIds')
    const fileIds = fileIdsStr ? JSON.parse(fileIdsStr) : null
    
    if (!fileIds && !prompt.trim()) {
      alert('Please provide either a topic/prompt or upload documents')
      return
    }

    setLoading(true)
    const globalLanguage = localStorage.getItem('appLanguage') || 'en'

    try {
      const response = await apiClient.post('/summarize-from-files', {
        file_ids: fileIds || undefined,
        language: globalLanguage,
        outline: true,
        prompt: prompt || undefined,
      })

      setData(response.data)
      
      let titlePrefix = ''
      if (fileIds) {
        const uploadedFilesStr = sessionStorage.getItem('uploadedFiles')
        if (uploadedFilesStr) {
          try {
            const uploadedFiles = JSON.parse(uploadedFilesStr)
            titlePrefix = uploadedFiles.map((f: any) => f.filename).slice(0, 2).join(', ')
            if (uploadedFiles.length > 2) {
              titlePrefix += ` +${uploadedFiles.length - 2} more`
            }
          } catch (e) {
            titlePrefix = 'Documents'
          }
        }
      } else if (prompt.trim()) {
        titlePrefix = `Topic: ${prompt.substring(0, 30)}${prompt.length > 30 ? '...' : ''}`
      }
      
      await historyAPI.save({
        type: 'summary',
        title: `${titlePrefix} - ${response.data.summary?.title || 'Summary'}`,
        data: response.data
      })
      
      sessionStorage.removeItem('uploadedFiles')
      sessionStorage.removeItem('uploadedFileIds')
      setFiles([])
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

  if (data) {
    const summary = data.summary
    
    // Calculate stats
    const totalConcepts = summary.sections.reduce((acc, s) => acc + (s.concepts?.length || 0), 0)
    const totalBullets = summary.sections.reduce((acc, s) => acc + (s.bullets?.length || 0), 0)
    const totalFormulas = summary.formula_sheet?.length || 0
    const totalGlossary = summary.glossary?.length || 0

    return (
      <div className="min-h-screen bg-[#0F172A] pt-20 px-4 pb-12">
        <div className="fixed inset-0 -z-10">
          <div className="absolute top-20 left-1/4 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl animate-pulse-slow"></div>
          <div className="absolute bottom-20 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }}></div>
        </div>

        <div className="max-w-5xl mx-auto">
          {/* Header */}
          <div className="glass-card mb-8 animate-fade-in">
            <div className="flex items-center gap-4 mb-6">
              <div className="text-5xl">📚</div>
              <div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-[#14B8A6] to-[#06B6D4] bg-clip-text text-transparent">
                  {summary.title}
                </h1>
                {summary.overview && (
                  <p className="text-slate-300 mt-3 leading-relaxed">{summary.overview}</p>
                )}
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
              <div className="p-4 bg-gradient-to-br from-teal-500/10 to-teal-600/10 border border-teal-500/30 rounded-xl">
                <div className="text-teal-400 text-sm font-medium mb-1">Sections</div>
                <div className="text-2xl font-bold text-slate-100">{summary.sections.length}</div>
              </div>
              <div className="p-4 bg-gradient-to-br from-cyan-500/10 to-cyan-600/10 border border-cyan-500/30 rounded-xl">
                <div className="text-cyan-400 text-sm font-medium mb-1">Concepts</div>
                <div className="text-2xl font-bold text-slate-100">{totalConcepts || totalBullets}</div>
              </div>
              <div className="p-4 bg-gradient-to-br from-blue-500/10 to-blue-600/10 border border-blue-500/30 rounded-xl">
                <div className="text-blue-400 text-sm font-medium mb-1">Formulas</div>
                <div className="text-2xl font-bold text-slate-100">{totalFormulas}</div>
              </div>
              <div className="p-4 bg-gradient-to-br from-emerald-500/10 to-emerald-600/10 border border-emerald-500/30 rounded-xl">
                <div className="text-emerald-400 text-sm font-medium mb-1">Terms</div>
                <div className="text-2xl font-bold text-slate-100">{totalGlossary}</div>
              </div>
            </div>
          </div>

          {/* Learning Objectives */}
          {summary.learning_objectives && summary.learning_objectives.length > 0 && (
            <div className="glass-card mb-8 animate-slide-up">
              <div className="flex items-center gap-3 mb-6">
                <div className="text-3xl">🎯</div>
                <h2 className="text-2xl font-semibold text-slate-100">Learning Objectives</h2>
              </div>
              <ul className="space-y-3">
                {summary.learning_objectives.map((obj, i) => (
                  <li key={i} className="flex items-start">
                    <span className="flex-shrink-0 w-6 h-6 bg-gradient-to-br from-teal-500/20 to-cyan-500/20 rounded-full flex items-center justify-center mr-3 mt-0.5">
                      <span className="text-teal-400 text-xs font-bold">{i + 1}</span>
                    </span>
                    <span className="text-slate-300 leading-relaxed">{obj}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Main Content Sections */}
          <div className="space-y-8">
            {summary.sections && summary.sections.map((section, sectionIdx) => (
              <div key={sectionIdx} className="glass-card animate-slide-up" style={{ animationDelay: `${sectionIdx * 0.1}s` }}>
                <div className="flex items-start gap-4 mb-6">
                  <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-teal-500/20 to-cyan-500/20 border border-teal-500/30 rounded-xl flex items-center justify-center text-teal-400 font-bold">
                    {sectionIdx + 1}
                  </div>
                  <h2 className="text-2xl font-semibold text-slate-100 flex-1">{section.heading}</h2>
                </div>

                {/* Concepts (new schema) */}
                {section.concepts && section.concepts.length > 0 && (
                  <div className="space-y-6">
                    {section.concepts.map((concept, conceptIdx) => (
                      <div key={conceptIdx} className="p-5 bg-gradient-to-br from-teal-500/5 to-cyan-500/5 border border-teal-500/20 rounded-xl hover:border-teal-500/40 transition-all">
                        <div className="flex items-start gap-3 mb-3">
                          <div className="flex-shrink-0 w-8 h-8 bg-teal-500/20 rounded-lg flex items-center justify-center text-teal-400 text-sm font-bold mt-0.5">
                            {conceptIdx + 1}
                          </div>
                          <div className="flex-1">
                            <h3 className="text-xl font-semibold text-slate-100 mb-2">{concept.term}</h3>
                            <p className="text-sm text-cyan-400 italic mb-3 pl-4 border-l-2 border-cyan-500/30">
                              {concept.definition}
                            </p>
                            <p className="text-slate-300 leading-relaxed mb-4">
                              {concept.explanation}
                            </p>
                            
                            {concept.example && (
                              <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg mb-4">
                                <div className="text-xs font-semibold text-blue-400 mb-1 uppercase tracking-wide">Example</div>
                                <p className="text-slate-300 text-sm leading-relaxed">{concept.example}</p>
                              </div>
                            )}
                            
                            {concept.key_points && concept.key_points.length > 0 && (
                              <div className="mt-3">
                                <div className="text-xs font-semibold text-teal-400 mb-2 uppercase tracking-wide">Key Points</div>
                                <ul className="space-y-2">
                                  {concept.key_points.map((point, i) => (
                                    <li key={i} className="flex items-start text-sm">
                                      <span className="text-teal-400 mr-2">▸</span>
                                      <span className="text-slate-300">{point}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Bullets (old schema - backward compatibility) */}
                {section.bullets && section.bullets.length > 0 && (
                  <ul className="space-y-3">
                    {section.bullets.map((bullet, bulletIdx) => (
                      <li key={bulletIdx} className="flex items-start group">
                        <span className="flex-shrink-0 w-6 h-6 bg-gradient-to-br from-teal-500/20 to-cyan-500/20 rounded-full flex items-center justify-center mr-3 mt-0.5 group-hover:scale-110 transition-transform">
                          <span className="text-teal-400 text-xs">✓</span>
                        </span>
                        <span className="text-slate-300 leading-relaxed">{bullet}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>

          {/* Formula Sheet */}
          {summary.formula_sheet && summary.formula_sheet.length > 0 && (
            <div className="glass-card mt-8 animate-scale-in">
              <div className="flex items-center gap-3 mb-6">
                <div className="text-3xl">🧮</div>
                <h2 className="text-2xl font-semibold text-slate-100">Formula Sheet</h2>
              </div>
              <div className="space-y-4">
                {summary.formula_sheet.map((formula, idx) => (
                  <div key={idx} className="p-5 bg-gradient-to-br from-purple-500/10 to-pink-500/10 border border-purple-500/30 rounded-xl hover:border-purple-500/50 transition-all">
                    <div className="text-lg font-semibold text-slate-100 mb-2">{formula.name}</div>
                    {(formula.formula || formula.expression) && (
                      <div className="text-2xl font-mono text-purple-300 mb-3 p-3 bg-black/20 rounded-lg">
                        {formula.expression || formula.formula}
                      </div>
                    )}
                    {formula.variables && (
                      <div className="text-sm text-slate-300 mb-2">
                        <span className="text-purple-400 font-semibold">Variables: </span>
                        {typeof formula.variables === 'string' ? formula.variables : JSON.stringify(formula.variables)}
                      </div>
                    )}
                    {(formula.when_to_use || formula.notes) && (
                      <div className="text-sm text-slate-300">
                        <span className="text-purple-400 font-semibold">Notes: </span>
                        {formula.notes || formula.when_to_use}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Glossary */}
          {summary.glossary && summary.glossary.length > 0 && (
            <div className="glass-card mt-8 animate-scale-in">
              <div className="flex items-center gap-3 mb-6">
                <div className="text-3xl">📖</div>
                <h2 className="text-2xl font-semibold text-slate-100">Glossary</h2>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {summary.glossary.map((term, idx) => (
                  <div key={idx} className="p-4 bg-gradient-to-br from-emerald-500/10 to-green-500/10 border border-emerald-500/30 rounded-xl hover:border-emerald-500/50 transition-all">
                    <div className="font-semibold text-emerald-300 mb-1">{term.term}</div>
                    <div className="text-sm text-slate-300">{term.definition}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Exam Practice */}
          {summary.exam_practice && (
            <div className="glass-card mt-8 animate-scale-in">
              <div className="flex items-center gap-3 mb-6">
                <div className="text-3xl">✍️</div>
                <h2 className="text-2xl font-semibold text-slate-100">Exam Practice</h2>
              </div>
              
              {/* Multiple Choice */}
              {summary.exam_practice?.multiple_choice && summary.exam_practice.multiple_choice.length > 0 && (
                <div className="mb-8">
                  <h3 className="text-xl font-semibold text-slate-200 mb-4">Multiple Choice Questions</h3>
                  <div className="space-y-4">
                    {summary.exam_practice.multiple_choice.map((q, idx) => (
                      <div key={idx} className="p-5 bg-gradient-to-br from-orange-500/10 to-red-500/10 border border-orange-500/30 rounded-xl">
                        <div className="font-semibold text-slate-100 mb-3">{idx + 1}. {q.question}</div>
                        <div className="space-y-2 mb-3">
                          {q.options && Object.entries(q.options).map(([key, value]) => (
                            <div key={key} className={`p-3 rounded-lg ${key === q.correct ? 'bg-green-500/20 border border-green-500/50' : 'bg-slate-800/30'}`}>
                              <span className="font-semibold text-slate-200">{key}) </span>
                              <span className="text-slate-300">{value}</span>
                              {key === q.correct && <span className="text-green-400 ml-2">✓ Correct</span>}
                            </div>
                          ))}
                        </div>
                        {q.explanation && (
                          <div className="text-sm text-slate-400 italic">
                            <span className="text-orange-400 font-semibold">Explanation: </span>
                            {q.explanation}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Short Answer */}
              {summary.exam_practice?.short_answer && summary.exam_practice.short_answer.length > 0 && (
                <div className="mb-8">
                  <h3 className="text-xl font-semibold text-slate-200 mb-4">Short Answer Questions</h3>
                  <div className="space-y-4">
                    {summary.exam_practice.short_answer.map((q, idx) => (
                      <div key={idx} className="p-5 bg-gradient-to-br from-blue-500/10 to-indigo-500/10 border border-blue-500/30 rounded-xl">
                        <div className="font-semibold text-slate-100 mb-3">{idx + 1}. {q.question}</div>
                        {q.answer && (
                          <div className="text-sm text-slate-300 mt-2">
                            <span className="text-blue-400 font-semibold">Answer: </span>
                            {q.answer}
                          </div>
                        )}
                        {q.key_points && q.key_points.length > 0 && (
                          <>
                            <div className="text-sm text-blue-400 font-semibold mb-2 mt-3">Key Points to Include:</div>
                            <ul className="space-y-1">
                              {q.key_points.map((point, i) => (
                                <li key={i} className="text-slate-300 text-sm flex items-start">
                                  <span className="text-blue-400 mr-2">•</span>
                                  {point}
                                </li>
                              ))}
                            </ul>
                          </>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Problem Solving */}
              {summary.exam_practice?.problem_solving && summary.exam_practice.problem_solving.length > 0 && (
                <div>
                  <h3 className="text-xl font-semibold text-slate-200 mb-4">Problem Solving</h3>
                  <div className="space-y-4">
                    {summary.exam_practice.problem_solving.map((p, idx) => (
                      <div key={idx} className="p-5 bg-gradient-to-br from-violet-500/10 to-purple-500/10 border border-violet-500/30 rounded-xl">
                        <div className="font-semibold text-slate-100 mb-3">{idx + 1}. {p.problem}</div>
                        <div className="mb-3">
                          <div className="text-sm text-violet-400 font-semibold mb-1">Approach:</div>
                          <div className="text-slate-300 text-sm">{p.approach}</div>
                        </div>
                        <div>
                          <div className="text-sm text-violet-400 font-semibold mb-1">Solution:</div>
                          <div className="text-slate-300 text-sm whitespace-pre-wrap">{p.solution}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Citations */}
          {data.citations && data.citations.length > 0 && (
            <div className="glass-card mt-8 animate-scale-in">
              <div className="flex items-center gap-3 mb-6">
                <div className="text-3xl">📎</div>
                <h2 className="text-2xl font-semibold text-slate-100">Evidence & Sources</h2>
              </div>
              <div className="space-y-3">
                {data.citations.map((citation, index) => (
                  <div key={index} className="p-4 bg-gradient-to-br from-teal-500/5 to-cyan-500/5 border border-teal-500/20 rounded-xl hover:border-teal-500/40 transition-all duration-200 group">
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

          {/* Actions */}
          <div className="flex gap-4 mt-8 animate-fade-in">
            <button onClick={() => window.print()} className="btn-ghost flex-1">
              🖨️ Print
            </button>
            <button
              onClick={() => {
                const text = JSON.stringify(data, null, 2)
                navigator.clipboard.writeText(text)
                alert('Copied to clipboard!')
              }}
              className="btn-ghost flex-1"
            >
              📋 Copy JSON
            </button>
            <button
              onClick={() => {
                setData(null)
                setFiles([])
                sessionStorage.removeItem('uploadedFileIds')
              }}
              className="btn-primary flex-1"
            >
              📄 New Summary
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0F172A] pt-20 px-4 pb-12">
      <div className="fixed inset-0 -z-10">
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl animate-pulse-slow"></div>
        <div className="absolute bottom-20 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }}></div>
      </div>

      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8 animate-fade-in">
          <div className="text-6xl mb-4">📝</div>
          <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-[#14B8A6] to-[#06B6D4] bg-clip-text text-transparent">
            Generate Summary
          </h1>
          <p className="text-xl text-slate-300">
            Enter a topic or upload documents for AI-generated study notes
          </p>
        </div>

        {/* Prompt Area */}
        <div className="glass-card mb-6 animate-slide-up">
          <h2 className="text-2xl font-semibold mb-4 text-slate-100">1. Enter Topic or Instructions (Optional)</h2>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g., 'Explain quantum physics basics', 'Summarize photosynthesis', 'Key concepts in World War II'..."
            className="input-modern h-32 resize-none w-full"
          />
          <p className="text-slate-400 text-sm mt-2">
            Or upload documents below for document-based summaries
          </p>
        </div>

        {/* Upload Area */}
        <div className="glass-card mb-6 animate-slide-up">
          <h2 className="text-2xl font-semibold mb-4 text-slate-100">2. Upload Documents (Optional)</h2>
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-2xl p-12 text-center transition-all duration-300 transform ${
              dragActive
                ? 'border-[#14B8A6] bg-gradient-to-br from-[#14B8A6]/20 to-[#06B6D4]/20 scale-[1.02]'
                : 'border-white/20 hover:border-white/40 hover:bg-white/5'
            }`}
          >
            <div className={`text-6xl mb-4 transition-transform duration-300 ${dragActive ? 'scale-110 animate-bounce' : ''}`}>
              📤
            </div>
            <p className="text-xl text-slate-300 mb-2 font-semibold">
              {dragActive ? 'Drop files here!' : 'Drag and drop files here'}
            </p>
            <p className="text-sm text-slate-400 mb-6">
              Supported: PDF, DOCX, PPTX, TXT
            </p>
            <input
              type="file"
              id="file-upload"
              multiple
              accept=".pdf,.docx,.pptx,.txt"
              onChange={handleFileInput}
              className="hidden"
              disabled={uploading}
            />
            <label htmlFor="file-upload" className={`btn-primary inline-block cursor-pointer ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}>
              {uploading ? '⏳ Uploading...' : '📁 Browse Files'}
            </label>
          </div>

          {files.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-medium text-slate-300 mb-3">Uploaded Files ({files.length})</h3>
              <div className="space-y-2">
                {files.map((file, index) => (
                  <div key={index} className="flex items-center justify-between p-3 bg-[#1E293B]/50 rounded-xl border border-white/5 group hover:border-white/10 transition-all">
                    <div className="flex items-center space-x-3">
                      <div className="text-2xl">{file.mime.includes('pdf') ? '📄' : file.mime.includes('presentation') ? '📊' : '📝'}</div>
                      <div>
                        <p className="text-slate-200 font-medium">{file.filename}</p>
                        <p className="text-slate-400 text-xs">{(file.size / 1024).toFixed(1)} KB</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="text-green-400 text-lg">✓</div>
                      <button
                        onClick={() => removeFile(file.file_id)}
                        className="text-red-400 hover:text-red-300 hover:scale-110 transition-all p-1 hover:bg-red-400/10 rounded text-sm"
                        title="Remove file"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Generate Button */}
        <div className="glass-card mb-6 animate-scale-in">
          <button
            onClick={generateSummary}
            disabled={loading}
            className="btn-primary w-full text-lg py-4"
          >
            {loading ? '⏳ Generating Summary...' : '✨ Generate Summary'}
          </button>
          <p className="text-slate-400 text-sm text-center mt-4">
            {files.length > 0 && prompt.trim() 
              ? `Will summarize ${files.length} document(s) with your instructions`
              : files.length > 0
              ? `Will summarize ${files.length} document(s)`
              : prompt.trim()
              ? 'Will create summary based on your topic'
              : 'Enter a topic or upload documents to continue'}
          </p>
        </div>
      </div>
    </div>
  )
}
