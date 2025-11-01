'use client'

import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '@/lib/api'

interface Flashcard {
  front: string
  back: string
  type?: string
  source?: {
    file_id: string
    evidence: string
  }
}

interface FlashcardsData {
  deck?: string
  cards: Flashcard[]
}

interface UploadedFile {
  file_id: string
  filename: string
  mime: string
  size: number
}

export default function FlashcardsPage() {
  const [data, setData] = useState<FlashcardsData | null>(null)
  const [loading, setLoading] = useState(false)
  const [prompt, setPrompt] = useState('')
  const [count, setCount] = useState(10)
  const [currentCard, setCurrentCard] = useState(0)
  const [flipped, setFlipped] = useState(false)
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
        // Save complete file info to sessionStorage
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
      // Update sessionStorage with remaining files
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

  const generateFlashcards = async () => {
    // Require either files or prompt
    const fileIdsStr = sessionStorage.getItem('uploadedFileIds')
    const fileIds = fileIdsStr ? JSON.parse(fileIdsStr) : null
    
    if (!fileIds && !prompt.trim()) {
      alert('Please provide either a topic/prompt or upload documents')
      return
    }
    setLoading(true)

    // Get global language from localStorage
    const globalLanguage = localStorage.getItem('appLanguage') || 'en'

    try {
      const response = await apiClient.post('/flashcards-from-files', {
        file_ids: fileIds || undefined,
        count,
        language: globalLanguage,
        prompt: prompt || undefined,
      })

      setData(response.data)
      setCurrentCard(0)
      setFlipped(false)
      
      // Generate title based on what was provided
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
      
      // Save to history
      const historyItem = {
        id: Date.now().toString(),
        type: 'flashcards' as const,
        title: `${titlePrefix} - ${response.data.cards?.length || count} Cards`,
        timestamp: Date.now(),
        data: response.data
      }
      const existingHistory = JSON.parse(localStorage.getItem('studyHistory') || '[]')
      localStorage.setItem('studyHistory', JSON.stringify([historyItem, ...existingHistory]))
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to generate flashcards')
    } finally {
      setLoading(false)
    }
  }

  const nextCard = () => {
    if (data && data.cards && currentCard < data.cards.length - 1) {
      setFlipped(false)
      setTimeout(() => setCurrentCard(currentCard + 1), 150)
    }
  }

  const prevCard = () => {
    if (currentCard > 0) {
      setFlipped(false)
      setTimeout(() => setCurrentCard(currentCard - 1), 150)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0F172A] pt-20 flex items-center justify-center">
        <div className="glass-card p-8 text-center">
          <div className="text-6xl mb-4 animate-pulse">🎴</div>
          <div className="text-2xl text-slate-300 mb-2">Generating Flashcards...</div>
          <div className="text-sm text-slate-400">Creating {count} study cards with AI</div>
        </div>
      </div>
    )
  }

  if (data && data.cards && data.cards.length > 0) {
    const card = data.cards[currentCard]
    return (
      <div className="min-h-screen bg-[#0F172A] pt-20 px-4 pb-12">
        <div className="fixed inset-0 -z-10">
          <div className="absolute top-20 left-1/4 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl animate-pulse-slow"></div>
          <div className="absolute bottom-20 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }}></div>
        </div>

        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-8 animate-fade-in">
            <div className="text-6xl mb-4">🎴</div>
            <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-[#14B8A6] to-[#06B6D4] bg-clip-text text-transparent">
              Flashcards
            </h1>
            <p className="text-xl text-slate-300">
              Card {currentCard + 1} of {data.cards.length}
            </p>
          </div>

          <div
            onClick={() => setFlipped(!flipped)}
            className="relative h-96 cursor-pointer mb-8 animate-scale-in"
          >
            <div
              className={`absolute inset-0 transition-all duration-700 ease-in-out ${flipped ? 'rotate-y-180' : ''}`}
              style={{
                transformStyle: 'preserve-3d',
                transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
              }}
            >
              {/* Front */}
              <div
                className="absolute inset-0 backface-hidden bg-gradient-to-br from-[#0F172A] via-[#1E293B] to-[#0F172A] rounded-3xl p-12 flex flex-col items-center justify-center text-center shadow-2xl"
                style={{ backfaceVisibility: 'hidden' }}
              >
                <div className="text-xs uppercase tracking-wider text-teal-400 mb-6 font-semibold">Question</div>
                <div className="text-3xl text-slate-100 leading-relaxed font-light">{card.front}</div>
                <div className="mt-10 text-slate-500 text-sm">Tap to reveal</div>
              </div>

              {/* Back */}
              <div
                className="absolute inset-0 backface-hidden bg-gradient-to-br from-[#0F172A] via-[#1E293B] to-[#0F172A] rounded-3xl p-12 flex flex-col items-center justify-center text-center shadow-2xl"
                style={{
                  backfaceVisibility: 'hidden',
                  transform: 'rotateY(180deg)',
                }}
              >
                <div className="text-xs uppercase tracking-wider text-cyan-400 mb-6 font-semibold">Answer</div>
                <div className="text-3xl text-slate-100 leading-relaxed font-light">{card.back}</div>
                <div className="mt-10 text-slate-500 text-sm">Tap to flip back</div>
              </div>
            </div>
          </div>

          <div className="flex gap-4 mb-8">
            <button
              onClick={prevCard}
              disabled={currentCard === 0}
              className="btn-ghost flex-1 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              ← Previous
            </button>
            <button
              onClick={nextCard}
              disabled={currentCard === data.cards.length - 1}
              className="btn-primary flex-1 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Next →
            </button>
          </div>

          <div className="flex gap-4 animate-fade-in">
            <button
              onClick={() => {
                setData(null)
                setFiles([])
                sessionStorage.removeItem('uploadedFileIds')
              }}
              className="btn-ghost flex-1"
            >
              📄 Create New Set
            </button>
            <button
              onClick={() => {
                setCurrentCard(0)
                setFlipped(false)
              }}
              className="btn-ghost flex-1"
            >
              🔄 Restart
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
          <div className="text-6xl mb-4">🎴</div>
          <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-[#14B8A6] to-[#06B6D4] bg-clip-text text-transparent">
            Generate Flashcards
          </h1>
          <p className="text-xl text-slate-300">
            Enter a topic or upload documents for AI-generated flashcards
          </p>
        </div>

        {/* Prompt Area - Primary */}
        <div className="glass-card mb-6 animate-slide-up">
          <h2 className="text-2xl font-semibold mb-4 text-slate-100">1. Enter Topic or Instructions (Optional)</h2>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g., 'Create flashcards about photosynthesis', 'Focus on key chemistry formulas'..."
            className="input-modern h-32 resize-none w-full"
          />
          <p className="text-slate-400 text-sm mt-2">
            Or upload documents below for document-based flashcards
          </p>
        </div>

        {/* Upload Area - Optional */}
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

        {/* Settings */}
        <div className="glass-card mb-6 animate-slide-up">
          <h2 className="text-2xl font-semibold mb-4 text-slate-100">3. Settings</h2>
          <label className="block text-sm font-medium text-slate-300 mb-3">
            Number of Cards
          </label>
          <input
            type="number"
            min="1"
            max="50"
            value={count}
            onChange={(e) => setCount(parseInt(e.target.value))}
            className="input-modern"
          />
        </div>

        {/* Generate Button */}
        <div className="glass-card mb-6 animate-scale-in">
          <button
            onClick={generateFlashcards}
            disabled={loading}
            className="btn-primary w-full text-lg py-4"
          >
            {loading ? '⏳ Generating Flashcards...' : '✨ Generate Flashcards'}
          </button>
          <p className="text-slate-400 text-sm text-center mt-4">
            {files.length > 0 && prompt.trim() 
              ? `Will create ${count} flashcards from ${files.length} document(s) with your instructions`
              : files.length > 0
              ? `Will create ${count} flashcards from ${files.length} document(s)`
              : prompt.trim()
              ? `Will create ${count} flashcards based on your topic`
              : 'Enter a topic or upload documents to continue'}
          </p>
        </div>
      </div>
    </div>
  )
}
