'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
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

export default function ViewExamPage() {
  const router = useRouter()
  const [exam, setExam] = useState<ExamData | null>(null)
  const [answers, setAnswers] = useState<Record<number, string>>({})
  const [showResults, setShowResults] = useState(false)
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [explanation, setExplanation] = useState<Record<number, string>>({})
  const [loadingExplanation, setLoadingExplanation] = useState<Record<number, boolean>>({})
  const [chatOpen, setChatOpen] = useState<number | null>(null)
  const [chatMessages, setChatMessages] = useState<Array<{ role: string; content: string }>>([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [isLoaded, setIsLoaded] = useState(false)
  const [historyItemId, setHistoryItemId] = useState<string | null>(null)

  useEffect(() => {
    // Only run once - check if already loaded
    if (isLoaded) {
      console.log('Already loaded, skipping')
      return
    }
    
    // Load exam from sessionStorage (set by history page)
    const historyExamState = sessionStorage.getItem('viewHistoryExam')
    const historyId = sessionStorage.getItem('viewHistoryExamId')
    console.log('view-exam useEffect: historyExamState =', historyExamState, 'historyId =', historyId)
    
    if (historyExamState) {
      try {
        const state = JSON.parse(historyExamState)
        console.log('Parsed exam state:', state)
        
        if (state.exam) {
          setExam(state.exam)
          setAnswers(state.answers || {})
          setShowResults(state.showResults || false)
          setHistoryItemId(historyId)
          setIsLoaded(true)
          // Don't clear immediately - keep it in case of hot reload
          console.log('Exam loaded successfully')
        } else {
          console.error('No exam in state')
          router.push('/history')
        }
      } catch (e) {
        console.error('Failed to load history exam:', e)
        router.push('/history')
      }
    } else {
      // No exam data, redirect to history only if we haven't loaded yet
      if (!exam) {
        console.log('No exam data in sessionStorage and no exam loaded, redirecting to history')
        router.push('/history')
      }
    }
  }, [isLoaded, exam, router])

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
    setCurrentQuestionIndex(0)
    
    // History is already saved when exam is submitted from exam page
    // No need to update here - this page is just for viewing
    console.log('Exam submitted from view-exam page')
  }

  const getExplain = async (questionNum: number) => {
    if (explanation[questionNum]) {
      return
    }

    const question = exam?.questions.find((q) => q.number === questionNum)
    if (!question) return

    setLoadingExplanation((prev) => ({ ...prev, [questionNum]: true }))

    try {
      const response = await apiClient.post('/explain', {
        question: question.question,
        options: question.options,
        selected: answers[questionNum],
        correct: exam?.answer_key[questionNum.toString()],
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
    
    sendInitialChatMessage(questionContext)
  }

  const sendInitialChatMessage = async (questionContext: string) => {
    setChatLoading(true)
    try {
      const response = await apiClient.post('/chat', {
        messages: [
          { role: 'system', content: 'You are a helpful tutor helping a student understand this question.' },
          { role: 'user', content: questionContext },
        ],
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
      const response = await apiClient.post('/chat', {
        messages: newMessages,
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

  if (!exam) {
    return (
      <div className="min-h-screen bg-[#0F172A] pt-20 flex items-center justify-center">
        <div className="glass-card p-8 text-center">
          <div className="text-6xl mb-4 animate-pulse">⏳</div>
          <div className="text-2xl text-slate-300 mb-2">Loading Exam...</div>
        </div>
      </div>
    )
  }

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
          {/* Header with Back button */}
          <div className="mb-6">
            <button
              onClick={() => router.push('/history')}
              className="btn-ghost text-sm"
            >
              ← Back to History
            </button>
          </div>

          {/* Results Header */}
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
                // Navigate to exam page with current exam loaded
                // Keep history ID so it updates the same record
                sessionStorage.setItem('currentExam', JSON.stringify(exam))
                // Don't remove viewHistoryExamId - we need it for updating
                router.push('/exam')
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
        {/* Back button */}
        <div className="mb-6">
          <button
            onClick={() => router.push('/history')}
            className="btn-ghost text-sm"
          >
            ← Back to History
          </button>
        </div>

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
              
              return (
                <button
                  key={q.number}
                  onClick={() => goToQuestion(index)}
                  className={`w-10 h-10 rounded-lg font-semibold transition-all ${
                    isCurrent
                      ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white scale-110 shadow-lg'
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
