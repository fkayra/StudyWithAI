'use client'

// Version: 2025-01-11-v3 - Exam-ready summary renderer
import { useState, useEffect, useCallback } from 'react'
import { apiClient, historyAPI } from '@/lib/api'
import MathText from '@/components/MathText'

// New exam-ready schema
interface Concept {
  term: string
  definition: string
  explanation: string
  example?: string
  key_points?: string[]
  pitfalls?: string[]  // New field from plan-then-write prompt
  when_to_use?: string[]  // New: application conditions
  limitations?: string[]  // New: edge cases, common mistakes
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
  worked_example?: string  // New: step-by-step calculation
  complexity?: string  // New: Big-O notation
}

interface Diagram {
  title: string
  description: string
  content: string
  type: string
}

interface Pseudocode {
  name: string
  code: string
  explanation: string
  example_trace?: string
}

interface PracticeProblem {
  problem: string
  difficulty: string
  solution: string
  steps: string[]
  key_concepts: string[]
}

interface Summary {
  title: string
  overview?: string
  learning_objectives?: string[]
  sections: Section[]
  formula_sheet?: Formula[]
  diagrams?: Diagram[]
  pseudocode?: Pseudocode[]
  practice_problems?: PracticeProblem[]
}

interface Coverage {
  score: number
  missing_topics: string[]
}

interface Citation {
  file_id: string
  evidence: string
  section?: string  // New: heading or slide title
}

interface SummaryData {
  summary: Summary
  citations: Citation[]
  coverage?: Coverage  // Optional: coverage info if available
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
        console.log('Loading history data:', historyData)
        
        // Normalize the data structure - handle both direct data and wrapped data
        let normalizedData: SummaryData | null = null
        
        if (historyData && historyData.summary) {
          // Already in correct format: {summary: {...}, citations: [...]}
          normalizedData = historyData
        } else if (historyData && typeof historyData === 'object') {
          // Might be just the summary object, wrap it
          normalizedData = {
            summary: historyData,
            citations: []
          }
        }
        
        if (normalizedData && normalizedData.summary) {
          console.log('Setting normalized history data:', normalizedData)
          console.log('Summary sections:', normalizedData.summary.sections)
          setData(normalizedData)
          // Don't remove viewHistory immediately - let it persist in case of navigation issues
          // sessionStorage.removeItem('viewHistory')
        } else {
          console.error('Invalid history data structure:', historyData)
          console.error('Trying to recover - checking if historyData has summary properties directly')
          // Last attempt: check if it's a valid summary object
          if (historyData && (historyData.title || historyData.sections)) {
            console.log('Found summary-like structure, wrapping it')
            const recoveredData: SummaryData = {
              summary: historyData as Summary,
              citations: historyData.citations || []
            }
            setData(recoveredData)
          } else {
            console.error('Could not recover history data')
          }
        }
        
        // Remove viewHistory after a short delay to allow state to update
        setTimeout(() => {
          sessionStorage.removeItem('viewHistory')
        }, 1000)
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
    
    // Note: We don't clear data on mount - let it persist from previous generation
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

      console.log('API Response received:', response.data)
      console.log('Response data type:', typeof response.data)
      console.log('Response data keys:', response.data ? Object.keys(response.data) : 'null')
      
      // Normalize the response data structure
      let normalizedData: SummaryData | null = null
      let rawData = response.data
      
      // Handle case where response.data might be a string that needs parsing
      if (typeof rawData === 'string') {
        try {
          console.log('Response data is a string, attempting to parse')
          rawData = JSON.parse(rawData)
        } catch (e) {
          console.error('Failed to parse response data as JSON:', e)
          alert('Invalid response format: received string that cannot be parsed as JSON')
          setLoading(false)
          return
        }
      }
      
      if (rawData) {
        // Check if it's already in the correct format
        if (rawData.summary && typeof rawData.summary === 'object') {
          // Handle case where summary itself might be a string
          if (typeof rawData.summary === 'string') {
            try {
              rawData.summary = JSON.parse(rawData.summary)
            } catch (e) {
              console.error('Failed to parse summary string:', e)
            }
          }
          // Already in correct format: {summary: {...}, citations: [...]}
          console.log('Data is in correct format with summary key')
          normalizedData = {
            summary: rawData.summary,
            citations: rawData.citations || []
          }
        } 
        // Check if it's the summary object directly (has title or sections)
        else if (rawData.title || (rawData.sections && Array.isArray(rawData.sections))) {
          // Just the summary object, wrap it
          console.log('Data is summary object directly, wrapping it')
          normalizedData = {
            summary: rawData,
            citations: rawData.citations || []
          }
        }
        // Check if summary is nested differently
        else if (rawData.data && rawData.data.summary) {
          console.log('Data is nested under data key')
          normalizedData = {
            summary: rawData.data.summary,
            citations: rawData.data.citations || []
          }
        }
      }
      
      // Validate and normalize the summary structure
      if (normalizedData && normalizedData.summary) {
        // Ensure sections is an array of objects, not strings
        if (normalizedData.summary.sections) {
          normalizedData.summary.sections = normalizedData.summary.sections.map((section: any, idx: number) => {
            // If section is a string, convert it to a proper section object
            if (typeof section === 'string') {
              return {
                heading: `Section ${idx + 1}`,
                bullets: [section],
                concepts: []
              }
            }
            // Ensure section has required properties
            if (!section.heading) {
              section.heading = `Section ${idx + 1}`
            }
            // Ensure concepts is an array
            if (!section.concepts) {
              section.concepts = []
            }
            // Ensure bullets is an array if it exists
            if (section.bullets && !Array.isArray(section.bullets)) {
              section.bullets = [section.bullets]
            }
            return section
          })
        } else if (normalizedData.summary.title && !normalizedData.summary.sections) {
          // If we have a title but no sections, create a default section
          normalizedData.summary.sections = [{
            heading: 'Content',
            bullets: [normalizedData.summary.overview || 'No content available'],
            concepts: []
          }]
        }
        
        // Ensure concepts in each section are objects, not strings
        normalizedData.summary.sections?.forEach((section: any) => {
          if (section.concepts && Array.isArray(section.concepts)) {
            section.concepts = section.concepts.map((concept: any, idx: number) => {
              // If concept is a string, convert it to a proper concept object
              if (typeof concept === 'string') {
                return {
                  term: `Concept ${idx + 1}`,
                  definition: concept,
                  explanation: concept,
                  key_points: []
                }
              }
              // Ensure concept has required properties
              if (!concept.term) {
                concept.term = `Concept ${idx + 1}`
              }
              if (!concept.definition) {
                concept.definition = concept.explanation || ''
              }
              if (!concept.explanation) {
                concept.explanation = concept.definition || ''
              }
              return concept
            })
          }
        })
      }
      
      if (normalizedData && normalizedData.summary) {
        console.log('Normalized data:', normalizedData)
        
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
        
        // Save to history (non-blocking) - save the normalized structure
        try {
          await historyAPI.save({
            type: 'summary',
            title: `${titlePrefix} - ${normalizedData.summary?.title || 'Summary'}`,
            data: normalizedData
          })
        } catch (historyError) {
          console.warn('Failed to save to history:', historyError)
          // Don't fail the request if history save fails
        }
        
        // Set data AFTER all processing is done - this ensures the summary is displayed
        // Deep clone to ensure React detects the change
        setData(JSON.parse(JSON.stringify(normalizedData)))
        
        // Clear files after successful generation (but keep data in state)
        sessionStorage.removeItem('uploadedFiles')
        sessionStorage.removeItem('uploadedFileIds')
        setFiles([])
        
        // Clear prompt after successful generation
        setPrompt('')
      } else {
        console.error('Invalid response structure. Full response:', response)
        console.error('Response data:', JSON.stringify(response.data, null, 2))
        console.error('Expected structure: {summary: {...}, citations: [...]} or {title: "...", sections: [...]}')
        
        // Try to extract any useful information for debugging
        if (response.data) {
          console.error('Available keys in response.data:', Object.keys(response.data))
          if (response.data.error) {
            console.error('Error in response:', response.data.error)
          }
        }
        
        alert(`Received invalid response from server. Please check the browser console for details.\n\nResponse structure doesn't match expected format.`)
        setLoading(false)
        return // Exit early to prevent further processing
      }
    } catch (error: any) {
      console.error('Summary generation error:', error)
      alert(error.response?.data?.detail || error.message || 'Failed to generate summary')
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

  // Debug: Log current state (can be removed in production)
  // console.log('Render - data state:', data)
  // console.log('Render - data.summary:', data?.summary)
  // console.log('Render - data.summary?.sections:', data?.summary?.sections)
  
  if (data && data.summary) {
    let summary = data.summary
    
    // Validate and normalize summary structure
    // Handle case where summary might be a string
    if (typeof summary === 'string') {
      try {
        console.log('Summary is a string in render, parsing...')
        summary = JSON.parse(summary)
      } catch (e) {
        console.error('Failed to parse summary string in render:', e)
        return (
          <div className="min-h-screen bg-[#0F172A] pt-20 px-4 pb-12 flex items-center justify-center">
            <div className="glass-card p-8 text-center max-w-2xl">
              <div className="text-4xl mb-4">⚠️</div>
              <h2 className="text-2xl font-bold text-red-400 mb-4">Invalid Summary Data</h2>
              <p className="text-slate-300 mb-4">The summary data is in an invalid format and cannot be displayed.</p>
              <button
                onClick={() => setData(null)}
                className="btn-primary"
              >
                Start Over
              </button>
            </div>
          </div>
        )
      }
    }
    
    // Ensure sections is an array
    if (!Array.isArray(summary.sections)) {
      console.warn('Sections is not an array in render:', summary.sections, typeof summary.sections)
      if (typeof summary.sections === 'string') {
        try {
          summary.sections = JSON.parse(summary.sections)
        } catch (e) {
          summary.sections = []
        }
      } else if (!summary.sections) {
        // If no sections but we have overview, create a section from it
        if (summary.overview) {
          summary.sections = [{
            heading: 'Overview',
            bullets: [summary.overview],
            concepts: []
          }]
        } else {
          summary.sections = []
        }
      } else {
        summary.sections = []
      }
    }
    
    // Normalize sections to ensure they have the right structure
    summary.sections = summary.sections.map((section: any, idx: number) => {
      // If section is a string, convert to object
      if (typeof section === 'string') {
        return {
          heading: `Section ${idx + 1}`,
          bullets: [section],
          concepts: []
        }
      }
      // Ensure section is an object with required fields
      if (typeof section !== 'object' || section === null) {
        return {
          heading: `Section ${idx + 1}`,
          bullets: [],
          concepts: []
        }
      }
      // Ensure heading exists
      if (!section.heading) {
        section.heading = `Section ${idx + 1}`
      }
      // Ensure concepts is an array
      if (!Array.isArray(section.concepts)) {
        section.concepts = []
      }
      // Normalize concepts
      section.concepts = section.concepts.map((concept: any, cIdx: number) => {
        if (typeof concept === 'string') {
          return {
            term: `Concept ${cIdx + 1}`,
            definition: concept,
            explanation: concept,
            key_points: []
          }
        }
        if (typeof concept !== 'object' || concept === null) {
          return {
            term: `Concept ${cIdx + 1}`,
            definition: '',
            explanation: '',
            key_points: []
          }
        }
        // Ensure required fields exist
        return {
          term: concept.term || `Concept ${cIdx + 1}`,
          definition: concept.definition || concept.explanation || '',
          explanation: concept.explanation || concept.definition || '',
          example: concept.example || '',
          key_points: Array.isArray(concept.key_points) ? concept.key_points : [],
          pitfalls: Array.isArray(concept.pitfalls) ? concept.pitfalls : [],
          when_to_use: Array.isArray(concept.when_to_use) ? concept.when_to_use : [],
          limitations: Array.isArray(concept.limitations) ? concept.limitations : []
        }
      })
      // Ensure bullets is an array if it exists
      if (section.bullets && !Array.isArray(section.bullets)) {
        section.bullets = [section.bullets]
      }
      return section
    })
    
    // Calculate stats with safe checks
    const totalConcepts = summary.sections?.reduce((acc, s) => acc + (s.concepts?.length || 0), 0) || 0
    const totalBullets = summary.sections?.reduce((acc, s) => acc + (s.bullets?.length || 0), 0) || 0
    const totalFormulas = Array.isArray(summary.formula_sheet) ? summary.formula_sheet.length : 0
    const totalDiagrams = Array.isArray(summary.diagrams) ? summary.diagrams.length : 0
    const totalPseudocode = Array.isArray(summary.pseudocode) ? summary.pseudocode.length : 0
    const totalPractice = Array.isArray(summary.practice_problems) ? summary.practice_problems.length : 0
    
    // console.log('Render - Stats calculated:', { totalConcepts, totalBullets, totalFormulas, totalGlossary })
    // console.log('Render - Normalized sections:', summary.sections)

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
                  {summary.title || 'Summary'}
                </h1>
                {summary.overview && (
                  <p className="text-slate-300 mt-3 leading-relaxed"><MathText text={summary.overview} /></p>
                )}
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
              <div className="p-4 bg-gradient-to-br from-teal-500/10 to-teal-600/10 border border-teal-500/30 rounded-xl">
                <div className="text-teal-400 text-sm font-medium mb-1">Sections</div>
                <div className="text-2xl font-bold text-slate-100">{summary.sections?.length || 0}</div>
              </div>
              <div className="p-4 bg-gradient-to-br from-cyan-500/10 to-cyan-600/10 border border-cyan-500/30 rounded-xl">
                <div className="text-cyan-400 text-sm font-medium mb-1">Concepts</div>
                <div className="text-2xl font-bold text-slate-100">{totalConcepts || totalBullets}</div>
              </div>
              <div className="p-4 bg-gradient-to-br from-blue-500/10 to-blue-600/10 border border-blue-500/30 rounded-xl">
                <div className="text-blue-400 text-sm font-medium mb-1">Diagrams</div>
                <div className="text-2xl font-bold text-slate-100">{totalDiagrams}</div>
              </div>
              <div className="p-4 bg-gradient-to-br from-purple-500/10 to-purple-600/10 border border-purple-500/30 rounded-xl">
                <div className="text-purple-400 text-sm font-medium mb-1">Practice</div>
                <div className="text-2xl font-bold text-slate-100">{totalPractice}</div>
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
                    <span className="text-slate-300 leading-relaxed"><MathText text={obj} /></span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Main Content Sections */}
          {summary.sections && summary.sections.length > 0 ? (
          <div className="space-y-8">
            {summary.sections.map((section, sectionIdx) => (
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
                              <MathText text={concept.definition} />
                            </p>
                            <p className="text-slate-300 leading-relaxed mb-4">
                              <MathText text={concept.explanation} />
                            </p>
                            
                            {concept.example && (
                              <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg mb-4">
                                <div className="text-xs font-semibold text-blue-400 mb-1 uppercase tracking-wide">Example</div>
                                <p className="text-slate-300 text-sm leading-relaxed">
                                  <MathText text={concept.example} />
                                </p>
                              </div>
                            )}
                            
                            {concept.key_points && concept.key_points.length > 0 && (
                              <div className="mt-3">
                                <div className="text-xs font-semibold text-teal-400 mb-2 uppercase tracking-wide">Key Points</div>
                                <ul className="space-y-2">
                                  {concept.key_points.map((point, i) => (
                                    <li key={i} className="flex items-start text-sm">
                                      <span className="text-teal-400 mr-2">▸</span>
                                      <span className="text-slate-300"><MathText text={point} /></span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            
                            {concept.pitfalls && concept.pitfalls.length > 0 && (
                              <div className="mt-3">
                                <div className="text-xs font-semibold text-amber-400 mb-2 uppercase tracking-wide">⚠️ Common Pitfalls</div>
                                <ul className="space-y-2">
                                  {concept.pitfalls.map((pitfall, i) => (
                                    <li key={i} className="flex items-start text-sm">
                                      <span className="text-amber-400 mr-2">⚠</span>
                                      <span className="text-slate-300"><MathText text={pitfall} /></span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            
                            {concept.when_to_use && concept.when_to_use.length > 0 && (
                              <div className="mt-3">
                                <div className="text-xs font-semibold text-green-400 mb-2 uppercase tracking-wide">✓ When to Use</div>
                                <ul className="space-y-2">
                                  {concept.when_to_use.map((condition, i) => (
                                    <li key={i} className="flex items-start text-sm">
                                      <span className="text-green-400 mr-2">✓</span>
                                      <span className="text-slate-300"><MathText text={condition} /></span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            
                            {concept.limitations && concept.limitations.length > 0 && (
                              <div className="mt-3">
                                <div className="text-xs font-semibold text-red-400 mb-2 uppercase tracking-wide">⊗ Limitations</div>
                                <ul className="space-y-2">
                                  {concept.limitations.map((limitation, i) => (
                                    <li key={i} className="flex items-start text-sm">
                                      <span className="text-red-400 mr-2">⊗</span>
                                      <span className="text-slate-300"><MathText text={limitation} /></span>
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
                        <span className="text-slate-300 leading-relaxed"><MathText text={bullet} /></span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
          ) : (
            <div className="glass-card p-8 text-center">
              <div className="text-4xl mb-4">📄</div>
              <div className="text-xl text-slate-300 mb-2">No sections available</div>
              <div className="text-sm text-slate-400">The summary data is incomplete or still being processed.</div>
            </div>
          )}

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
                        <MathText text={formula.expression || formula.formula || ''} />
                      </div>
                    )}
                    {formula.variables && (
                      <div className="text-sm text-slate-300 mb-2">
                        <span className="text-purple-400 font-semibold">Variables: </span>
                        {typeof formula.variables === 'string' ? formula.variables : JSON.stringify(formula.variables)}
                      </div>
                    )}
                    
                    {formula.worked_example && (
                      <div className="mt-3 p-3 bg-black/20 rounded-lg border border-purple-500/20">
                        <div className="text-xs text-purple-400 font-semibold mb-2 uppercase tracking-wide">Worked Example</div>
                        <div className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">
                          <MathText text={formula.worked_example} />
                        </div>
                      </div>
                    )}
                    
                    {formula.complexity && (
                      <div className="text-sm text-slate-300 mt-3">
                        <span className="text-purple-400 font-semibold">Complexity: </span>
                        <span className="font-mono text-purple-300">{formula.complexity}</span>
                      </div>
                    )}
                    
                    {(formula.when_to_use || formula.notes) && (
                      <div className="text-sm text-slate-400 mt-3">
                        <span className="text-purple-400 font-semibold">Notes: </span>
                        <MathText text={formula.notes || formula.when_to_use || ''} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Diagrams */}
          {summary.diagrams && summary.diagrams.length > 0 && (
            <div className="glass-card mt-8 animate-scale-in">
              <div className="flex items-center gap-3 mb-6">
                <div className="text-3xl">📊</div>
                <h2 className="text-2xl font-semibold text-slate-100">Visual Diagrams</h2>
              </div>
              <div className="space-y-6">
                {summary.diagrams.map((diagram, idx) => (
                  <div key={idx} className="p-6 bg-gradient-to-br from-blue-500/10 to-indigo-500/10 border border-blue-500/30 rounded-xl hover:border-blue-500/50 transition-all">
                    <div className="font-semibold text-blue-300 mb-2 text-lg">{diagram.title}</div>
                    <div className="text-sm text-slate-400 mb-4 italic">{diagram.description}</div>
                    <div className="p-4 bg-slate-900/50 rounded-lg border border-slate-700/50 font-mono text-sm text-slate-300 whitespace-pre-wrap overflow-x-auto">
                      {diagram.content}
                    </div>
                    <div className="mt-2 text-xs text-slate-500">Type: {diagram.type}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Pseudocode */}
          {summary.pseudocode && summary.pseudocode.length > 0 && (
            <div className="glass-card mt-8 animate-scale-in">
              <div className="flex items-center gap-3 mb-6">
                <div className="text-3xl">💻</div>
                <h2 className="text-2xl font-semibold text-slate-100">Pseudocode Examples</h2>
              </div>
              <div className="space-y-6">
                {summary.pseudocode.map((pseudo, idx) => (
                  <div key={idx} className="p-6 bg-gradient-to-br from-emerald-500/10 to-teal-500/10 border border-emerald-500/30 rounded-xl hover:border-emerald-500/50 transition-all">
                    <div className="font-semibold text-emerald-300 mb-3 text-lg">{pseudo.name}</div>
                    <div className="p-4 bg-slate-900/50 rounded-lg border border-slate-700/50 font-mono text-sm text-slate-300 whitespace-pre-wrap overflow-x-auto mb-4">
                      {pseudo.code}
                    </div>
                    <div className="text-sm text-slate-400 mb-3">
                      <span className="font-semibold text-teal-400">Explanation:</span> {pseudo.explanation}
                    </div>
                    {pseudo.example_trace && (
                      <div className="p-3 bg-teal-500/10 border border-teal-500/30 rounded-lg">
                        <div className="text-xs text-teal-400 font-semibold mb-1">Example Trace:</div>
                        <div className="text-sm text-slate-300 font-mono">{pseudo.example_trace}</div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Practice Problems */}
          {summary.practice_problems && summary.practice_problems.length > 0 && (
            <div className="glass-card mt-8 animate-scale-in">
              <div className="flex items-center gap-3 mb-6">
                <div className="text-3xl">🎯</div>
                <h2 className="text-2xl font-semibold text-slate-100">Practice Problems</h2>
              </div>
              <div className="space-y-6">
                {summary.practice_problems.map((problem, idx) => (
                  <div key={idx} className="p-6 bg-gradient-to-br from-purple-500/10 to-pink-500/10 border border-purple-500/30 rounded-xl hover:border-purple-500/50 transition-all">
                    <div className="flex items-center gap-3 mb-3">
                      <span className="px-3 py-1 bg-purple-500/20 border border-purple-500/40 rounded-full text-xs font-semibold text-purple-300 uppercase">
                        {problem.difficulty}
                      </span>
                      <span className="text-slate-500 text-sm">Problem {idx + 1}</span>
                    </div>
                    <div className="mb-4 text-slate-200 leading-relaxed">
                      <span className="font-semibold text-purple-300">Problem:</span> <MathText text={problem.problem} />
                    </div>
                    <div className="mb-4 p-4 bg-slate-900/50 rounded-lg border border-slate-700/50">
                      <div className="font-semibold text-pink-300 mb-2">Solution Steps:</div>
                      <ol className="space-y-2">
                        {problem.steps.map((step, sIdx) => (
                          <li key={sIdx} className="flex items-start text-sm text-slate-300">
                            <span className="flex-shrink-0 w-6 h-6 bg-purple-500/20 rounded-full flex items-center justify-center mr-3 text-xs font-bold text-purple-300">
                              {sIdx + 1}
                            </span>
                            <span className="flex-1"><MathText text={step} /></span>
                          </li>
                        ))}
                      </ol>
                    </div>
                    <div className="mb-3 p-3 bg-purple-500/10 border border-purple-500/30 rounded-lg">
                      <div className="text-sm text-purple-300 font-semibold mb-1">Final Answer:</div>
                      <div className="text-slate-200"><MathText text={problem.solution} /></div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <span className="text-xs text-slate-500">Key Concepts:</span>
                      {problem.key_concepts.map((concept, cIdx) => (
                        <span key={cIdx} className="px-2 py-1 bg-purple-500/10 border border-purple-500/30 rounded text-xs text-purple-300">
                          {concept}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Exam Practice Section - REMOVED
              Token budget now redirected to deeper explanations and worked examples
          */}

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
                        {citation.section && (
                          <div className="text-xs text-teal-300 font-semibold mb-1">📍 {citation.section}</div>
                        )}
                        <div className="text-sm text-slate-300 leading-relaxed">{citation.evidence}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Missing Topics (Coverage Info) */}
          {data.coverage && data.coverage.missing_topics && data.coverage.missing_topics.length > 0 && (
            <div className="glass-card mt-8 animate-scale-in">
              <div className="flex items-center gap-3 mb-4">
                <div className="text-3xl">⚠️</div>
                <div className="flex-1">
                  <h2 className="text-2xl font-semibold text-slate-100">Topics Not Covered</h2>
                  <p className="text-sm text-amber-400 mt-1">Coverage: {(data.coverage.score * 100).toFixed(0)}% - The following topics from the source were not included in the summary</p>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {data.coverage.missing_topics.map((topic, index) => (
                  <div key={index} className="p-3 bg-gradient-to-br from-amber-500/10 to-orange-500/10 border border-amber-500/30 rounded-lg">
                    <div className="flex items-start gap-2">
                      <div className="text-amber-400 text-xs mt-0.5">▸</div>
                      <div className="text-sm text-slate-300">{topic}</div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-4 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                <div className="text-xs text-blue-300">
                  💡 <span className="font-semibold">Tip:</span> These topics were detected in the source material but may not have been included in the summary. You can refer back to the original document for details on these specific topics.
                </div>
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
