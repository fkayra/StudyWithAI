'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { apiClient } from '@/lib/api'

interface TrueFalseCard {
  statement: string
  answer: boolean
  explanation: string
}

interface TrueFalseData {
  cards: TrueFalseCard[]
}

interface UploadedFile {
  file_id: string
  filename: string
  mime: string
  size: number
}

export default function TrueFalsePage() {
  const [data, setData] = useState<TrueFalseData | null>(null)
  const [loading, setLoading] = useState(false)
  const [prompt, setPrompt] = useState('')
  const [count, setCount] = useState(10)
  const [currentCard, setCurrentCard] = useState(0)
  const [userAnswer, setUserAnswer] = useState<boolean | null>(null)
  const [showResult, setShowResult] = useState(false)
  const [score, setScore] = useState({ correct: 0, total: 0 })
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [uploading, setUploading] = useState(false)
  const [dragActive, setDragActive] = useState(false)
  const [answeredCards, setAnsweredCards] = useState<Set<number>>(new Set())
  const [isCompleted, setIsCompleted] = useState(false)
  
  // Swipe functionality
  const [swipeDirection, setSwipeDirection] = useState<'left' | 'right' | null>(null)
  const [swipeOffset, setSwipeOffset] = useState(0)
  const cardRef = useRef<HTMLDivElement>(null)
  const touchStartX = useRef<number | null>(null)
  const touchStartY = useRef<number | null>(null)

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

  const generateTrueFalse = async () => {
    const fileIdsStr = sessionStorage.getItem('uploadedFileIds')
    const fileIds = fileIdsStr ? JSON.parse(fileIdsStr) : null
    
    if (!fileIds && !prompt.trim()) {
      alert('Please provide either a topic/prompt or upload documents')
      return
    }
    setLoading(true)

    const globalLanguage = localStorage.getItem('appLanguage') || 'en'

    try {
      const response = await apiClient.post('/truefalse-from-files', {
        file_ids: fileIds || undefined,
        count,
        language: globalLanguage,
        prompt: prompt || undefined,
      })

      setData(response.data)
      setCurrentCard(0)
      setUserAnswer(null)
      setShowResult(false)
      setScore({ correct: 0, total: 0 })
      setAnsweredCards(new Set())
      setIsCompleted(false)
      
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
        type: 'truefalse' as const,
        title: `${titlePrefix} - ${response.data.cards?.length || count} Cards`,
        timestamp: Date.now(),
        data: response.data
      }
      const existingHistory = JSON.parse(localStorage.getItem('studyHistory') || '[]')
      localStorage.setItem('studyHistory', JSON.stringify([historyItem, ...existingHistory]))
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to generate True/False cards')
    } finally {
      setLoading(false)
    }
  }

  const handleAnswer = (answer: boolean) => {
    if (showResult) return
    
    setUserAnswer(answer)
    setShowResult(true)
    
    const card = data?.cards[currentCard]
    if (card && answer === card.answer) {
      setScore(prev => ({ correct: prev.correct + 1, total: prev.total + 1 }))
    } else {
      setScore(prev => ({ ...prev, total: prev.total + 1 }))
    }
    
    // Track that this card has been answered
    setAnsweredCards(prev => {
      const newSet = new Set(prev)
      newSet.add(currentCard)
      
      // Check if all cards have been answered
      if (data && data.cards && newSet.size === data.cards.length) {
        setIsCompleted(true)
      }
      
      return newSet
    })
  }

  const nextCard = () => {
    if (data && data.cards && currentCard < data.cards.length - 1) {
      setCurrentCard(currentCard + 1)
      setUserAnswer(null)
      setShowResult(false)
      setSwipeOffset(0)
      setSwipeDirection(null)
    } else if (data && data.cards && currentCard === data.cards.length - 1) {
      // If on last card and all cards are answered, show completion
      if (answeredCards.size === data.cards.length) {
        setIsCompleted(true)
      }
    }
  }

  const prevCard = () => {
    if (currentCard > 0) {
      setCurrentCard(currentCard - 1)
      setUserAnswer(null)
      setShowResult(false)
      setSwipeOffset(0)
      setSwipeDirection(null)
    }
  }

  // Swipe handlers
  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX
    touchStartY.current = e.touches[0].clientY
  }

  const handleTouchMove = (e: React.TouchEvent) => {
    if (touchStartX.current === null || touchStartY.current === null) return
    
    const touchX = e.touches[0].clientX
    const touchY = e.touches[0].clientY
    const deltaX = touchX - touchStartX.current
    const deltaY = touchY - touchStartY.current
    
    // Only handle horizontal swipes
    if (Math.abs(deltaX) > Math.abs(deltaY)) {
      e.preventDefault()
      setSwipeOffset(deltaX)
      
      if (deltaX > 50) {
        setSwipeDirection('right')
      } else if (deltaX < -50) {
        setSwipeDirection('left')
      } else {
        setSwipeDirection(null)
      }
    }
  }

  const handleTouchEnd = () => {
    if (swipeDirection === 'right' && swipeOffset > 100) {
      handleAnswer(true)
    } else if (swipeDirection === 'left' && swipeOffset < -100) {
      handleAnswer(false)
    }
    
    setSwipeOffset(0)
    setSwipeDirection(null)
    touchStartX.current = null
    touchStartY.current = null
  }

  // Mouse drag handlers for desktop
  const handleMouseDown = (e: React.MouseEvent) => {
    touchStartX.current = e.clientX
    touchStartY.current = e.clientY
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (touchStartX.current === null || touchStartY.current === null) return
    
    const deltaX = e.clientX - touchStartX.current
    const deltaY = e.clientY - touchStartY.current
    
    if (Math.abs(deltaX) > Math.abs(deltaY)) {
      setSwipeOffset(deltaX)
      
      if (deltaX > 50) {
        setSwipeDirection('right')
      } else if (deltaX < -50) {
        setSwipeDirection('left')
      } else {
        setSwipeDirection(null)
      }
    }
  }

  const handleMouseUp = () => {
    if (swipeDirection === 'right' && swipeOffset > 100) {
      handleAnswer(true)
    } else if (swipeDirection === 'left' && swipeOffset < -100) {
      handleAnswer(false)
    }
    
    setSwipeOffset(0)
    setSwipeDirection(null)
    touchStartX.current = null
    touchStartY.current = null
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0F172A] pt-20 flex items-center justify-center">
        <div className="glass-card p-8 text-center">
          <div className="text-6xl mb-4 animate-pulse">✅</div>
          <div className="text-2xl text-slate-300 mb-2">Generating True/False Cards...</div>
          <div className="text-sm text-slate-400">Creating {count} statement cards with AI</div>
        </div>
      </div>
    )
  }

  if (data && data.cards && data.cards.length > 0) {
    // Show completion screen if all cards are answered
    if (isCompleted && answeredCards.size === data.cards.length) {
      // Calculate percentage based on answered cards
      const totalAnswered = answeredCards.size > 0 ? answeredCards.size : data.cards.length
      const percentage = totalAnswered > 0 
        ? Math.round((score.correct / totalAnswered) * 100)
        : 0
      
      return (
        <div className="min-h-screen bg-[#0F172A] pt-20 px-4 pb-12 flex items-center justify-center">
          <div className="fixed inset-0 -z-10">
            <div className="absolute top-20 left-1/4 w-96 h-96 bg-green-500/10 rounded-full blur-3xl animate-pulse-slow"></div>
            <div className="absolute bottom-20 right-1/4 w-96 h-96 bg-red-500/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }}></div>
          </div>

          <div className="max-w-2xl mx-auto text-center animate-scale-in">
            <div className="glass-card p-12">
              <div className="text-8xl mb-6 animate-bounce">🎉</div>
              <h1 className="text-5xl font-bold mb-6 bg-gradient-to-r from-[#10B981] to-[#EF4444] bg-clip-text text-transparent">
                You Finished!
              </h1>
              <div className="mb-8">
                <div className="text-4xl font-bold text-slate-100 mb-2">
                  {score.correct || 0} / {answeredCards.size || data.cards.length} Correct
                </div>
                <div className={`text-3xl font-semibold mb-4 ${
                  percentage >= 80 ? 'text-green-400' : 
                  percentage >= 60 ? 'text-yellow-400' : 
                  'text-red-400'
                }`}>
                  {isNaN(percentage) ? 0 : percentage}%
                </div>
                <div className="w-full bg-slate-700 rounded-full h-4 mb-4">
                  <div 
                    className={`h-4 rounded-full transition-all duration-500 ${
                      percentage >= 80 ? 'bg-gradient-to-r from-green-500 to-green-400' : 
                      percentage >= 60 ? 'bg-gradient-to-r from-yellow-500 to-yellow-400' : 
                      'bg-gradient-to-r from-red-500 to-red-400'
                    }`}
                    style={{ width: `${Math.min(100, Math.max(0, isNaN(percentage) ? 0 : percentage))}%` }}
                  ></div>
                </div>
              </div>
              
              <div className="flex gap-4 justify-center">
                <button
                  onClick={() => {
                    setData(null)
                    setFiles([])
                    setCurrentCard(0)
                    setUserAnswer(null)
                    setShowResult(false)
                    setScore({ correct: 0, total: 0 })
                    setAnsweredCards(new Set())
                    setIsCompleted(false)
                    sessionStorage.removeItem('uploadedFileIds')
                  }}
                  className="btn-primary text-lg px-8 py-4"
                >
                  📄 Create New Cards
                </button>
                <button
                  onClick={() => {
                    window.location.href = '/'
                  }}
                  className="btn-ghost text-lg px-8 py-4"
                >
                  🏠 Main Menu
                </button>
              </div>
            </div>
          </div>
        </div>
      )
    }
    
    const card = data.cards[currentCard]
    const isCorrect = userAnswer !== null && userAnswer === card.answer
    
    return (
      <div className="min-h-screen bg-[#0F172A] pt-20 px-4 pb-12">
        <div className="fixed inset-0 -z-10">
          <div className="absolute top-20 left-1/4 w-96 h-96 bg-green-500/10 rounded-full blur-3xl animate-pulse-slow"></div>
          <div className="absolute bottom-20 right-1/4 w-96 h-96 bg-red-500/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }}></div>
        </div>

        <div className="max-w-3xl mx-auto">
        <div className="text-center mb-8 animate-fade-in">
          <div className="text-6xl mb-4">✅</div>
          <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-[#10B981] to-[#EF4444] bg-clip-text text-transparent">
            True / False
          </h1>
            <p className="text-xl text-slate-300">
              Card {currentCard + 1} of {data.cards.length}
            </p>
            {score.total > 0 && (
              <p className="text-sm text-slate-400 mt-2">
                Score: {score.correct}/{score.total} ({Math.round((score.correct / score.total) * 100)}%)
              </p>
            )}
          </div>

          {/* Swipeable Card */}
          <div
            ref={cardRef}
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            onTouchEnd={handleTouchEnd}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            className="relative mb-8 animate-scale-in cursor-grab active:cursor-grabbing"
            style={{
              transform: `translateX(${swipeOffset}px)`,
              transition: swipeOffset === 0 ? 'transform 0.3s ease-out' : 'none',
            }}
          >
            <div
              className={`relative h-96 rounded-3xl p-12 flex flex-col items-center justify-center text-center shadow-2xl transition-all duration-300 ${
                swipeDirection === 'right'
                  ? 'bg-gradient-to-br from-green-500/20 via-[#0F172A] to-[#0F172A] border-2 border-green-500/50'
                  : swipeDirection === 'left'
                  ? 'bg-gradient-to-br from-red-500/20 via-[#0F172A] to-[#0F172A] border-2 border-red-500/50'
                  : showResult
                  ? isCorrect
                    ? 'bg-gradient-to-br from-green-500/20 via-[#0F172A] to-[#0F172A] border-2 border-green-500/50'
                    : 'bg-gradient-to-br from-red-500/20 via-[#0F172A] to-[#0F172A] border-2 border-red-500/50'
                  : 'bg-gradient-to-br from-[#0F172A] via-[#1E293B] to-[#0F172A] border border-white/10'
              }`}
            >
              {swipeDirection === 'right' && (
                <div className="absolute top-8 right-8 text-6xl text-green-400 opacity-50">TRUE</div>
              )}
              {swipeDirection === 'left' && (
                <div className="absolute top-8 left-8 text-6xl text-red-400 opacity-50">FALSE</div>
              )}
              
              <div className="text-xs uppercase tracking-wider text-slate-400 mb-6 font-semibold">Statement</div>
              <div className="text-3xl text-slate-100 leading-relaxed font-light mb-8">{card.statement}</div>
              
              {showResult && (
                <div className="mt-6 animate-fade-in">
                  <div className={`text-4xl mb-4 ${isCorrect ? 'text-green-400' : 'text-red-400'}`}>
                    {isCorrect ? '✓ Correct!' : '✗ Incorrect'}
                  </div>
                  <div className="text-sm text-slate-400 mb-2">Correct answer: <span className="font-semibold text-slate-200">{card.answer ? 'True' : 'False'}</span></div>
                  <div className="text-sm text-slate-300 italic">{card.explanation}</div>
                </div>
              )}
              
              {!showResult && (
                <div className="text-slate-500 text-sm mt-4">
                  Swipe right for True, left for False
                </div>
              )}
            </div>
          </div>

          {/* Answer Buttons */}
          {!showResult && (
            <div className="flex gap-4 mb-8 animate-fade-in">
              <button
                onClick={() => handleAnswer(false)}
                className="btn-ghost flex-1 border-red-500/50 hover:bg-red-500/10 hover:border-red-500 text-red-400 py-6 text-xl font-semibold"
              >
                ✗ FALSE
              </button>
              <button
                onClick={() => handleAnswer(true)}
                className="btn-ghost flex-1 border-green-500/50 hover:bg-green-500/10 hover:border-green-500 text-green-400 py-6 text-xl font-semibold"
              >
                ✓ TRUE
              </button>
            </div>
          )}

          {/* Navigation */}
          <div className="flex gap-4 mb-8">
            <button
              onClick={prevCard}
              disabled={currentCard === 0}
              className="btn-ghost flex-1 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              ← Previous
            </button>
            {showResult && (
              <button
                onClick={() => {
                  if (currentCard === data.cards.length - 1) {
                    // If on last card, check if all are answered
                    if (answeredCards.size === data.cards.length) {
                      setIsCompleted(true)
                    }
                  } else {
                    nextCard()
                  }
                }}
                className="btn-primary flex-1"
              >
                {currentCard === data.cards.length - 1 ? 'Finish' : 'Next →'}
              </button>
            )}
            {!showResult && (
              <button
                onClick={nextCard}
                disabled={currentCard === data.cards.length - 1}
                className="btn-ghost flex-1 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                Skip →
              </button>
            )}
          </div>

          <div className="flex gap-4 animate-fade-in">
            <button
              onClick={() => {
                setData(null)
                setFiles([])
                setCurrentCard(0)
                setUserAnswer(null)
                setShowResult(false)
                setScore({ correct: 0, total: 0 })
                setAnsweredCards(new Set())
                setIsCompleted(false)
                sessionStorage.removeItem('uploadedFileIds')
              }}
              className="btn-ghost flex-1"
            >
              📄 Create New Set
            </button>
            <button
              onClick={() => {
                setCurrentCard(0)
                setUserAnswer(null)
                setShowResult(false)
                setScore({ correct: 0, total: 0 })
                setAnsweredCards(new Set())
                setIsCompleted(false)
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
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-green-500/10 rounded-full blur-3xl animate-pulse-slow"></div>
        <div className="absolute bottom-20 right-1/4 w-96 h-96 bg-red-500/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }}></div>
      </div>

      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8 animate-fade-in">
          <div className="text-6xl mb-4">✅</div>
          <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-[#10B981] to-[#EF4444] bg-clip-text text-transparent">
            Generate True/False Cards
          </h1>
          <p className="text-xl text-slate-300">
            Enter a topic or upload documents for AI-generated True/False statements
          </p>
        </div>

        {/* Prompt Area */}
        <div className="glass-card mb-6 animate-slide-up">
          <h2 className="text-2xl font-semibold mb-4 text-slate-100">1. Enter Topic or Instructions (Optional)</h2>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g., 'Create True/False statements about photosynthesis', 'Focus on key chemistry concepts'..."
            className="input-modern h-32 resize-none w-full"
          />
          <p className="text-slate-400 text-sm mt-2">
            Or upload documents below for document-based True/False statements
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
            onClick={generateTrueFalse}
            disabled={loading}
            className="btn-primary w-full text-lg py-4"
          >
            {loading ? '⏳ Generating Cards...' : '✨ Generate True/False Cards'}
          </button>
          <p className="text-slate-400 text-sm text-center mt-4">
            {files.length > 0 && prompt.trim() 
              ? `Will create ${count} True/False statements from ${files.length} document(s) with your instructions`
              : files.length > 0
              ? `Will create ${count} True/False statements from ${files.length} document(s)`
              : prompt.trim()
              ? `Will create ${count} True/False statements based on your topic`
              : 'Enter a topic or upload documents to continue'}
          </p>
        </div>
      </div>
    </div>
  )
}

