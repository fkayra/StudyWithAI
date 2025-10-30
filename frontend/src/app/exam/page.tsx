'use client'

import { useState, useEffect } from 'react'
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

export default function ExamPage() {
  const searchParams = useSearchParams()
  const isGrounded = searchParams?.get('grounded') === 'true'

  const [exam, setExam] = useState<ExamData | null>(null)
  const [loading, setLoading] = useState(false)
  const [answers, setAnswers] = useState<Record<number, string>>({})
  const [showResults, setShowResults] = useState(false)
  const [explanation, setExplanation] = useState<Record<number, string>>({})
  const [chatOpen, setChatOpen] = useState<number | null>(null)
  const [chatMessages, setChatMessages] = useState<Array<{ role: string; content: string }>>([])
  const [chatInput, setChatInput] = useState('')
  const [level, setLevel] = useState<'ilkokul-ortaokul' | 'lise' | 'universite'>('lise')

  useEffect(() => {
    // Try to load exam from session storage
    const storedExam = sessionStorage.getItem('currentExam')
    if (storedExam) {
      setExam(JSON.parse(storedExam))
    } else if (isGrounded) {
      // Generate from uploaded files
      generateGroundedExam()
    }
  }, [])

  const generateGroundedExam = async () => {
    const fileIdsStr = sessionStorage.getItem('uploadedFileIds')
    if (!fileIdsStr) {
      alert('No files uploaded')
      return
    }

    const fileIds = JSON.parse(fileIdsStr)
    setLoading(true)

    try {
      const response = await apiClient.post('/exam-from-files', {
        file_ids: fileIds,
        level,
        count: 5,
      })

      if (response.data.status === 'INSUFFICIENT_CONTEXT') {
        alert('Not enough information in files to generate exam')
        return
      }

      setExam(response.data)
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to generate exam')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = () => {
    setShowResults(true)
  }

  const getExplain = async (questionNum: number) => {
    if (explanation[questionNum]) {
      return
    }

    const question = exam?.questions.find((q) => q.number === questionNum)
    if (!question) return

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
    }
  }

  const openChat = (questionNum: number) => {
    const question = exam?.questions.find((q) => q.number === questionNum)
    if (!question) return

    setChatOpen(questionNum)
    setChatMessages([
      {
        role: 'system',
        content: `You are a helpful tutor. The student is asking about this question: ${question.question}`,
      },
    ])
  }

  const sendChatMessage = async () => {
    if (!chatInput.trim()) return

    const newMessages = [
      ...chatMessages,
      { role: 'user', content: chatInput },
    ]
    setChatMessages(newMessages)
    setChatInput('')

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
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0B1220] pt-20 flex items-center justify-center">
        <div className="text-2xl text-slate-300">Generating exam...</div>
      </div>
    )
  }

  if (!exam) {
    return (
      <div className="min-h-screen bg-[#0B1220] pt-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-4xl font-bold mb-8 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            No Exam Loaded
          </h1>
          <p className="text-slate-300 mb-8">
            Generate an exam from the home page or upload documents first.
          </p>
        </div>
      </div>
    )
  }

  const score = showResults
    ? Object.keys(answers).filter(
        (key) => answers[parseInt(key)] === exam.answer_key[key]
      ).length
    : 0

  return (
    <div className="min-h-screen bg-[#0B1220] pt-20 px-4 pb-12">
      <div className="max-w-4xl mx-auto">
        <div className="glass-card p-6 mb-8">
          <h1 className="text-3xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            Exam
          </h1>
          <p className="text-slate-400">
            {exam.questions.length} questions
          </p>
          {showResults && (
            <div className="mt-4 p-4 bg-blue-500/10 border border-blue-500/50 rounded-lg">
              <div className="text-2xl font-bold text-blue-400">
                Score: {score} / {exam.questions.length}
              </div>
              <div className="progress-bar mt-2">
                <div
                  className="progress-fill"
                  style={{ width: `${(score / exam.questions.length) * 100}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Questions */}
        <div className="space-y-6">
          {exam.questions.map((question) => {
            const userAnswer = answers[question.number]
            const correctAnswer = exam.answer_key[question.number.toString()]
            const isCorrect = showResults && userAnswer === correctAnswer

            return (
              <div key={question.number} className="glass-card p-6">
                <div className="flex items-start justify-between mb-4">
                  <h3 className="text-lg font-semibold text-slate-100 flex-1">
                    {question.number}. {question.question}
                  </h3>
                  {showResults && (
                    <div className={`text-2xl ${isCorrect ? '' : 'opacity-50'}`}>
                      {isCorrect ? '✅' : '❌'}
                    </div>
                  )}
                </div>

                <div className="space-y-2 mb-4">
                  {Object.entries(question.options).map(([key, value]) => {
                    const isSelected = userAnswer === key
                    const isCorrectOption = showResults && key === correctAnswer
                    const isWrong = showResults && isSelected && !isCorrect

                    return (
                      <button
                        key={key}
                        onClick={() => !showResults && setAnswers({ ...answers, [question.number]: key })}
                        disabled={showResults}
                        className={`w-full text-left p-4 rounded-lg border transition-all duration-200 ${
                          isCorrectOption
                            ? 'border-green-500 bg-green-500/10'
                            : isWrong
                            ? 'border-red-500 bg-red-500/10'
                            : isSelected
                            ? 'border-blue-500 bg-blue-500/10'
                            : 'border-white/10 hover:border-white/30 hover:bg-white/5'
                        }`}
                      >
                        <span className="font-medium">{key})</span> {value}
                      </button>
                    )
                  })}
                </div>

                {showResults && (
                  <div className="space-y-3">
                    <button
                      onClick={() => getExplain(question.number)}
                      className="btn-ghost text-sm"
                    >
                      💡 Explain
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
                )}
              </div>
            )
          })}
        </div>

        {!showResults && (
          <div className="mt-8 text-center">
            <button onClick={handleSubmit} className="btn-primary px-12">
              Submit Exam
            </button>
          </div>
        )}

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
                    <p className="text-sm text-slate-200">{msg.content}</p>
                  </div>
                ))}
              </div>

              <div className="p-4 border-t border-white/10">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && sendChatMessage()}
                    placeholder="Ask a question..."
                    className="flex-1 px-4 py-2 bg-[#1F2937] border border-white/10 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button onClick={sendChatMessage} className="btn-primary px-4">
                    Send
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
