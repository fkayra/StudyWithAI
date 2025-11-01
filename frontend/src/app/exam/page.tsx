'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import { apiClient } from '@/lib/api'

interface Question {
  number: number
  question: string
  options: {
    A: string
    B: string
    C: string
    D: string
  }
}

interface ExamData {
  questions: Question[]
  answer_key: Record<string, string>
  grounding?: Array<{
    number: number
    sources: Array<{ file_id: string; evidence: string }>
  }>
}

interface UploadedFile {
  file_id: string
  filename: string
  mime: string
  size: number
}

export default function ExamPage() {
  const searchParams = useSearchParams()
  const isGrounded = searchParams?.get('grounded') === 'true'
  const isQuickMode = searchParams?.get('quick') === 'true'

  const [exam, setExam] = useState<ExamData | null>(null)
  const [loading, setLoading] = useState(false)
  const [answers, setAnswers] = useState<Record<number, string>>({})
  const [showResults, setShowResults] = useState(false)
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [explanation, setExplanation] = useState<Record<number, string>>({})
  const [loadingExplanation, setLoadingExplanation] = useState<Record<number, boolean>>({})
  const [chatOpen, setChatOpen] = useState<number | null>(null)
  const [chatMessages, setChatMessages] = useState<Array<{ role: string; content: string }>>([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [level, setLevel] = useState<'ilkokul-ortaokul' | 'lise' | 'universite'>('lise')
  const [prompt, setPrompt] = useState('')
  const [count, setCount] = useState(5)
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [uploading, setUploading] = useState(false)
  const [dragActive, setDragActive] = useState(false)
  const [isQuickExam, setIsQuickExam] = useState(false)

  useEffect(() => {
    // If this is a quick exam from home page
    if (isQuickMode) {
      setIsQuickExam(true) // Mark as quick exam
      const storedExam = sessionStorage.getItem('currentExam')
      if (storedExam) {
        setExam(JSON.parse(storedExam))
        // Clear it immediately after loading so it doesn't persist
        sessionStorage.removeItem('currentExam')
      }
      return
    }

    // For normal exam page (generated from uploaded files):
    // Priority 1: Load active exam state (if user is in middle of exam)
    const examState = sessionStorage.getItem('currentExamState')
    if (examState) {
      try {
        const state = JSON.parse(examState)
        setExam(state.exam)
        setAnswers(state.answers || {})
        setShowResults(state.showResults || false)
      } catch (e) {
        console.error('Failed to load exam state:', e)
      }
    } else {
      // Priority 2: Load new exam (just generated)
      const storedExam = sessionStorage.getItem('currentExam')
      if (storedExam) {
        setExam(JSON.parse(storedExam))
        // Clear it immediately after loading so it doesn't persist
        sessionStorage.removeItem('currentExam')
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
  }, [isQuickMode])

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

  const generateGroundedExam = async () => {
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
      const response = await apiClient.post('/exam-from-files', {
        file_ids: fileIds || undefined,
        level,
        count: count,
        language: globalLanguage,
        prompt: prompt || undefined,
      })

      if (response.data.status === 'INSUFFICIENT_CONTEXT') {
        alert('Not enough information in files to generate exam')
        return
      }

      // Clear old exam states before setting new exam
      sessionStorage.removeItem('currentExam')
      sessionStorage.removeItem('currentExamState')
      
      setExam(response.data)
      setAnswers({})
      setShowResults(false)
      setCurrentQuestionIndex(0)
      
      // Save new exam to currentExam
      sessionStorage.setItem('currentExam', JSON.stringify(response.data))
      
      // Don't save to history yet - save when exam is completed
      // Just set the exam for now
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to generate exam')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = () => {
    if (!exam) return
    
    // Check for unanswered questions
    const unansweredQuestions: number[] = []
    exam.questions.forEach((q) => {
      if (!answers[q.number]) {
        unansweredQuestions.push(q.number)
      }
    })
    
    if (unansweredQuestions.length > 0) {
      const confirmSubmit = window.confirm(
        `Şu sorular henüz işaretlenmedi: ${unansweredQuestions.join(', ')}\n\nYine de sınavı bitirmek istiyor musunuz?`
      )
      if (!confirmSubmit) return
    }
    
    setShowResults(true)
    setCurrentQuestionIndex(0) // Go back to first question to review
    
    // Only save to currentExamState if this is a NORMAL exam (from uploaded files)
    // Quick exams should NOT persist in the main Exams tab
    if (!isQuickExam) {
      const examState = {
        exam: exam,
        answers: answers,
        showResults: true
      }
      sessionStorage.setItem('currentExamState', JSON.stringify(examState))
    }
    
    // Generate title based on what was provided
    let titlePrefix = ''
    const isQuickExamFromStorage = sessionStorage.getItem('isQuickExam') === 'true'
    
    if (isQuickExamFromStorage) {
      // This is a quick exam from home page
      const quickPrompt = sessionStorage.getItem('quickExamPrompt') || 'Quick Test'
      titlePrefix = `Quick: ${quickPrompt.substring(0, 30)}${quickPrompt.length > 30 ? '...' : ''}`
      // Clear the quick exam markers
      sessionStorage.removeItem('isQuickExam')
      sessionStorage.removeItem('quickExamPrompt')
    } else {
      // Check what was used to generate
      const storedFileIds = sessionStorage.getItem('uploadedFileIds')
      const fileIds = storedFileIds ? JSON.parse(storedFileIds) : null
      
      if (fileIds) {
        // Generated from files
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
        // Generated from prompt only
        titlePrefix = `Topic: ${prompt.substring(0, 30)}${prompt.length > 30 ? '...' : ''}`
      } else {
        titlePrefix = 'Exam'
      }
    }
    
    // Calculate score for title
    const score = Object.keys(answers).filter(
      (key) => answers[parseInt(key)] === exam.answer_key[key]
    ).length
    
    // Save completed exam to history with answers and unique title
    const historyItem = {
      id: Date.now().toString(),
      type: 'exam' as const,
      title: `${titlePrefix} - ${score}/${exam.questions.length} (${Math.round((score/exam.questions.length)*100)}%)`,
      timestamp: Date.now(),
      data: {
        exam: exam,
        answers: answers
      }
    }
    const existingHistory = JSON.parse(localStorage.getItem('studyHistory') || '[]')
    localStorage.setItem('studyHistory', JSON.stringify([historyItem, ...existingHistory]))
  }

  const goToQuestion = (index: number) => {
    setCurrentQuestionIndex(index)
  }

  const nextQuestion = () => {
    if (exam && currentQuestionIndex < exam.questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1)
    }
  }

  const prevQuestion = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1)
    }
  }

  const skipQuestion = () => {
    nextQuestion()
  }

  const getExplain = async (questionNum: number) => {
    if (explanation[questionNum]) {
      return
    }

    const question = exam?.questions.find((q) => q.number === questionNum)
    if (!question) return

    setLoadingExplanation((prev) => ({ ...prev, [questionNum]: true }))

    try {
      // Get file_ids from session storage if this is a grounded exam
      const fileIdsStr = sessionStorage.getItem('uploadedFileIds')
      const file_ids = fileIdsStr && isGrounded ? JSON.parse(fileIdsStr) : undefined

      const response = await apiClient.post('/explain', {
        question: question.question,
        options: question.options,
        selected: answers[questionNum],
        correct: exam?.answer_key[questionNum.toString()],
        file_ids: file_ids,
      })

      setExplanation((prev) => ({
        ...prev,
        [questionNum]: response.data.explanation,
      }))
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to get explanation')
    } finally {
      setLoadingExplanation((prev) => ({ ...prev, [questionNum]: false }))
    }
  }

  const openChat = (questionNum: number) => {
    const question = exam?.questions.find((q) => q.number === questionNum)
    if (!question) return

    setChatOpen(questionNum)
    
    // Pre-fill with the question and options
    const questionContext = `Question ${questionNum}: ${question.question}\n\nOptions:\nA) ${question.options.A}\nB) ${question.options.B}\nC) ${question.options.C}\nD) ${question.options.D}`
    
    setChatMessages([
      {
        role: 'system',
        content: `You are a helpful tutor helping a student understand this question.`,
      },
      {
        role: 'user',
        content: questionContext,
      },
    ])
    
    // Auto-send the first message to get initial response
    sendInitialChatMessage(questionContext)
  }

  const sendInitialChatMessage = async (questionContext: string) => {
    setChatLoading(true)
    try {
      // Get file_ids from session storage if this is a grounded exam
      const fileIdsStr = sessionStorage.getItem('uploadedFileIds')
      const file_ids = fileIdsStr && isGrounded ? JSON.parse(fileIdsStr) : undefined

      const response = await apiClient.post('/chat', {
        messages: [
          { role: 'system', content: 'You are a helpful tutor helping a student understand this question.' },
          { role: 'user', content: questionContext },
        ],
        file_ids: file_ids,
      })

      setChatMessages((prev) => [
        ...prev,
        { role: 'assistant', content: response.data.response },
      ])
    } catch (error: any) {
      console.error('Failed to get initial response:', error)
    } finally {
      setChatLoading(false)
    }
  }

  const sendChatMessage = async () => {
    if (!chatInput.trim()) return

    const newMessages = [
      ...chatMessages,
      { role: 'user', content: chatInput },
    ]
    setChatMessages(newMessages)
    setChatInput('')
    setChatLoading(true)

    try {
      // Get file_ids from session storage if this is a grounded exam
      const fileIdsStr = sessionStorage.getItem('uploadedFileIds')
      const file_ids = fileIdsStr && isGrounded ? JSON.parse(fileIdsStr) : undefined

      const response = await apiClient.post('/chat', {
        messages: newMessages,
        file_ids: file_ids,
      })

      setChatMessages([
        ...newMessages,
        { role: 'assistant', content: response.data.response },
      ])
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Chat failed')
    } finally {
      setChatLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0F172A] pt-20 flex items-center justify-center">
        <div className="glass-card p-8 text-center">
          <div className="text-6xl mb-4 animate-pulse">🎯</div>
          <div className="text-2xl text-slate-300 mb-2">Generating Exam...</div>
          <div className="text-sm text-slate-400">Creating {count} questions at {level} level</div>
        </div>
      </div>
    )
  }

  if (exam) {
    const score = showResults
      ? Object.keys(answers).filter(
          (key) => answers[parseInt(key)] === exam.answer_key[key]
        ).length
      : 0

    // Show results view with all questions
    if (showResults) {
      return (
        <div className="min-h-screen bg-[#0B1220] pt-20 px-4 pb-12">
          <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="glass-card p-6 mb-8">
              <h1 className="text-3xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                Exam Results
              </h1>
              <p className="text-slate-400">
                {exam.questions.length} questions
              </p>
              <div className="mt-4 p-4 bg-blue-500/10 border border-blue-500/50 rounded-lg">
                <div className="text-2xl font-bold text-blue-400">
                  Score: {score} / {exam.questions.length} ({Math.round((score / exam.questions.length) * 100)}%)
                </div>
                <div className="h-2 rounded-lg bg-white/15 mt-2 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-green-500 to-green-400 transition-all duration-500"
                    style={{ width: `${(score / exam.questions.length) * 100}%` }}
                  />
                </div>
              </div>
            </div>

            {/* All Questions - Results View */}
            <div className="space-y-6">
              {exam.questions.map((question) => {
                const userAnswer = answers[question.number]
                const correctAnswer = exam.answer_key[question.number.toString()]
                const isCorrect = userAnswer === correctAnswer

                return (
                  <div key={question.number} className="glass-card p-6">
                    <div className="flex items-start justify-between mb-4">
                      <h3 className="text-lg font-semibold text-slate-100 flex-1">
                        {question.number}. {question.question}
                      </h3>
                      <div className={`text-2xl ${isCorrect ? '' : 'opacity-50'}`}>
                        {isCorrect ? '✅' : '❌'}
                      </div>
                    </div>

                    <div className="space-y-2 mb-4">
                      {Object.entries(question.options).map(([key, value]) => {
                        const isSelected = userAnswer === key
                        const isCorrectOption = key === correctAnswer
                        const isWrong = isSelected && !isCorrect

                        return (
                          <div
                            key={key}
                            className={`w-full text-left p-4 rounded-lg border ${
                              isCorrectOption
                                ? 'border-green-500 bg-green-500/10'
                                : isWrong
                                ? 'border-red-500 bg-red-500/10'
                                : isSelected
                                ? 'border-blue-500 bg-blue-500/10'
                                : 'border-white/10'
                            }`}
                          >
                            <span className="font-medium">{key})</span> {value}
                          </div>
                        )
                      })}
                    </div>

                    <div className="space-y-3">
                      <button
                        onClick={() => getExplain(question.number)}
                        disabled={loadingExplanation[question.number]}
                        className="btn-ghost text-sm disabled:opacity-50 disabled:cursor-wait"
                      >
                        {loadingExplanation[question.number] ? (
                          <>
                            <span className="inline-block animate-spin mr-2">⏳</span>
                            Loading...
                          </>
                        ) : (
                          '💡 Explain'
                        )}
                      </button>
                      <button
                        onClick={() => openChat(question.number)}
                        className="btn-ghost text-sm ml-2"
                      >
                        💬 Chat with Tutor
                      </button>

                      {explanation[question.number] && (
                        <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg text-slate-300 text-sm">
                          {explanation[question.number]}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>

            <div className="mt-8 text-center">
              <button
                onClick={() => {
                  setShowResults(false)
                  setAnswers({})
                  setCurrentQuestionIndex(0)
                  // Clear saved exam state for fresh restart
                  sessionStorage.removeItem('currentExamState')
                }}
                className="btn-primary px-8"
              >
                🔄 Restart Exam
              </button>
            </div>

            {/* Chat Drawer */}
            {chatOpen !== null && (
              <div className="fixed inset-0 bg-black/50 z-50 flex items-end justify-end">
                <div className="glass-card w-full max-w-md h-[600px] m-4 flex flex-col">
                  <div className="p-4 border-b border-white/10 flex justify-between items-center">
                    <h3 className="font-semibold text-slate-100">Chat with Tutor</h3>
                    <button
                      onClick={() => setChatOpen(null)}
                      className="text-slate-400 hover:text-slate-200"
                    >
                      ✕
                    </button>
                  </div>

                  <div className="flex-1 overflow-y-auto p-4 space-y-3">
                    {chatMessages.filter((m) => m.role !== 'system').map((msg, i) => (
                      <div
                        key={i}
                        className={`p-3 rounded-lg ${
                          msg.role === 'user'
                            ? 'bg-blue-500/20 ml-8'
                            : 'bg-slate-700/50 mr-8'
                        }`}
                      >
                        <div className="text-xs text-slate-400 mb-1">
                          {msg.role === 'user' ? 'You' : 'AI Tutor'}
                        </div>
                        <p className="text-sm text-slate-200 whitespace-pre-wrap">{msg.content}</p>
                      </div>
                    ))}
                    {chatLoading && (
                      <div className="p-3 rounded-lg bg-slate-700/50 mr-8">
                        <div className="flex items-center gap-2 text-slate-400">
                          <span className="inline-block animate-spin">⏳</span>
                          <span className="text-sm">AI Tutor is thinking...</span>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="p-4 border-t border-white/10">
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && !chatLoading && sendChatMessage()}
                        disabled={chatLoading}
                        placeholder="Ask a follow-up question..."
                        className="flex-1 px-4 py-2 bg-[#1F2937] border border-white/10 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                      />
                      <button 
                        onClick={sendChatMessage} 
                        disabled={chatLoading || !chatInput.trim()}
                        className="btn-primary px-4 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {chatLoading ? '...' : 'Send'}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )
    }

    // Taking exam view - single question
    const currentQuestion = exam.questions[currentQuestionIndex]
    const userAnswer = answers[currentQuestion.number]

    return (
      <div className="min-h-screen bg-[#0B1220] pt-20 px-4 pb-12">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="glass-card p-6 mb-6">
            <h1 className="text-3xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
              Exam
            </h1>
            <p className="text-slate-400">
              {exam.questions.length} questions • Question {currentQuestionIndex + 1} of {exam.questions.length}
            </p>
          </div>

          {/* Question Navigation */}
          <div className="glass-card p-4 mb-6">
            <div className="flex flex-wrap gap-2">
              {exam.questions.map((q, index) => {
                const isAnswered = !!answers[q.number]
                const isCurrent = index === currentQuestionIndex
                const isCorrectAnswer = showResults && answers[q.number] === exam.answer_key[q.number.toString()]
                
                return (
                  <button
                    key={q.number}
                    onClick={() => goToQuestion(index)}
                    className={`w-10 h-10 rounded-lg font-semibold transition-all ${
                      isCurrent
                        ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white scale-110 shadow-lg'
                        : showResults
                        ? isCorrectAnswer
                          ? 'bg-green-500/20 border border-green-500/50 text-green-400'
                          : isAnswered
                          ? 'bg-red-500/20 border border-red-500/50 text-red-400'
                          : 'bg-slate-700/20 border border-slate-500/30 text-slate-500'
                        : isAnswered
                        ? 'bg-blue-500/20 border border-blue-500/50 text-blue-400'
                        : 'bg-slate-700/20 border border-slate-500/30 text-slate-400 hover:border-slate-400'
                    }`}
                  >
                    {q.number}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Current Question */}
          <div className="glass-card p-6 mb-6">
            <div className="flex items-start justify-between mb-6">
              <h3 className="text-xl font-semibold text-slate-100 flex-1">
                {currentQuestion.number}. {currentQuestion.question}
              </h3>
            </div>

            <div className="space-y-3 mb-6">
              {Object.entries(currentQuestion.options).map(([key, value]) => {
                const isSelected = userAnswer === key

                return (
                  <button
                    key={key}
                    onClick={() => {
                      setAnswers({ ...answers, [currentQuestion.number]: key })
                      // Auto-advance to next question immediately
                      if (currentQuestionIndex < exam.questions.length - 1) {
                        setCurrentQuestionIndex(currentQuestionIndex + 1)
                      }
                    }}
                    className={`w-full text-left p-4 rounded-lg border transition-all duration-200 ${
                      isSelected
                        ? 'border-blue-500 bg-blue-500/10'
                        : 'border-white/10 hover:border-white/30 hover:bg-white/5'
                    }`}
                  >
                    <span className="font-medium">{key})</span> {value}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Navigation Buttons */}
          <div className="flex gap-4">
            <button
              onClick={prevQuestion}
              disabled={currentQuestionIndex === 0}
              className="btn-ghost flex-1 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              ← Önceki
            </button>
            
            <button
              onClick={skipQuestion}
              className="btn-ghost flex-1"
            >
              Boş Geç →
            </button>
            
            <button
              onClick={handleSubmit}
              className="btn-primary flex-1"
            >
              Sınavı Bitir 🏁
            </button>
            
            <button
              onClick={nextQuestion}
              disabled={currentQuestionIndex === exam.questions.length - 1}
              className="btn-ghost flex-1 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Sonraki →
            </button>
          </div>
        </div>
      </div>
    )
  }

  // No exam loaded - show upload interface (rest of component)
  return (
    <div className="min-h-screen bg-[#0F172A] pt-20 px-4 pb-12">
      <div className="fixed inset-0 -z-10">
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl animate-pulse-slow"></div>
        <div className="absolute bottom-20 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }}></div>
      </div>

      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8 animate-fade-in">
          <div className="text-6xl mb-4">🎯</div>
          <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-[#14B8A6] to-[#06B6D4] bg-clip-text text-transparent">
            Generate Practice Exam
          </h1>
          <p className="text-xl text-slate-300">
            Upload documents and AI will create exam questions
          </p>
        </div>

        {/* Upload Area */}
        <div className="glass-card mb-6 animate-slide-up">
          <h2 className="text-2xl font-semibold mb-4 text-slate-100">1. Upload Documents</h2>
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

        {/* Settings (shown after upload) */}
        {files.length > 0 && (
          <div className="glass-card mb-6 animate-scale-in">
            <h2 className="text-2xl font-semibold mb-2 text-slate-100">2. Customize (Optional)</h2>
            <p className="text-slate-400 text-sm mb-4">Adjust settings or leave default values</p>

            {/* Difficulty Level */}
            <div className="mb-4">
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

            {/* Number of questions */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-300 mb-3">
                Number of Questions
              </label>
              <input
                type="number"
                value={count}
                onChange={(e) => setCount(Math.max(1, Math.min(20, parseInt(e.target.value) || 5)))}
                min="1"
                max="20"
                className="input-modern"
              />
            </div>

            {/* Optional Prompt */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-300 mb-3">
                Additional Instructions
              </label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="e.g., 'Focus on specific topics', 'Include calculations', 'Make them tricky'..."
                className="input-modern h-24 resize-none"
              />
            </div>

            {/* Generate Button */}
            <button
              onClick={generateGroundedExam}
              disabled={loading}
              className="btn-primary w-full"
            >
              {loading ? '⏳ Generating Exam...' : `✨ Generate ${count} Questions`}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
