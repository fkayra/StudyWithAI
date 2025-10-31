'use client'

import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api'

interface Flashcard {
  type: string
  front: string
  back: string
  source?: {
    file_id: string
    evidence: string
  }
}

interface FlashcardDeck {
  deck: string
  cards: Flashcard[]
}

export default function FlashcardsPage() {
  const [deck, setDeck] = useState<FlashcardDeck | null>(null)
  const [loading, setLoading] = useState(false)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [flipped, setFlipped] = useState(false)
  const [prompt, setPrompt] = useState('')
  const [count, setCount] = useState(10)
  const [showPrompt, setShowPrompt] = useState(true)

  useEffect(() => {
    // Don't auto-generate, wait for user input
  }, [])

  const generateFlashcards = async () => {
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
      const response = await apiClient.post('/flashcards-from-files', {
        file_ids: fileIds,
        style: 'basic',
        deck_name: 'Study Deck',
        count: count,
        prompt: prompt || undefined,
      })

      // Check if response has the expected structure
      if (response.data && response.data.cards && response.data.cards.length > 0) {
        setDeck(response.data)
      } else {
        alert('No flashcards could be generated. The document might not have enough information.')
      }
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || 'Failed to generate flashcards'
      if (error.response?.status === 401) {
        alert('Please login to generate flashcards from your documents.')
      } else if (errorMsg.includes('INSUFFICIENT_CONTEXT')) {
        alert('Not enough information in the uploaded files to generate flashcards. Please upload more detailed documents.')
      } else {
        alert(errorMsg)
      }
    } finally {
      setLoading(false)
    }
  }

  const nextCard = () => {
    if (deck && currentIndex < deck.cards.length - 1) {
      setCurrentIndex(currentIndex + 1)
      setFlipped(false)
    }
  }

  const prevCard = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1)
      setFlipped(false)
    }
  }

  const exportDeck = () => {
    if (!deck) return

    const dataStr = JSON.stringify(deck, null, 2)
    const blob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${deck.deck}.json`
    link.click()
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0F172A] pt-20 flex items-center justify-center">
        <div className="glass-card p-8 text-center">
          <div className="text-6xl mb-4 animate-pulse">🎴</div>
          <div className="text-2xl text-slate-300 mb-2">Generating Flashcards...</div>
          <div className="text-sm text-slate-400">Creating {count} study cards</div>
        </div>
      </div>
    )
  }

  if (!deck && showPrompt) {
    return (
      <div className="min-h-screen bg-[#0F172A] pt-20 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="glass-card animate-fade-in">
            <div className="text-center mb-8">
              <div className="text-6xl mb-6">🎴</div>
              <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-[#14B8A6] to-[#06B6D4] bg-clip-text text-transparent">
                Generate Flashcards
              </h1>
              <p className="text-slate-300">
                AI will create study flashcards from your uploaded documents
              </p>
            </div>

            {/* Number of cards */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-slate-300 mb-3">
                Number of Flashcards
              </label>
              <input
                type="number"
                value={count}
                onChange={(e) => setCount(Math.max(1, Math.min(50, parseInt(e.target.value) || 10)))}
                min="1"
                max="50"
                className="input-modern"
              />
              <p className="text-xs text-slate-400 mt-2">
                💡 Choose between 1-50 cards
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
                placeholder="e.g., 'Focus on definitions', 'Include code examples', 'Make them challenging'..."
                className="input-modern h-32 resize-none"
              />
              <p className="text-xs text-slate-400 mt-2">
                💡 Leave empty for general flashcards, or add specific instructions
              </p>
            </div>

            {/* Generate Button */}
            <button
              onClick={generateFlashcards}
              disabled={loading}
              className="btn-primary w-full"
            >
              {loading ? '⏳ Generating Flashcards...' : `✨ Generate ${count} Flashcards`}
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (!deck || deck.cards.length === 0) {
    return (
      <div className="min-h-screen bg-[#0F172A] pt-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="glass-card p-12">
            <div className="text-6xl mb-6">❌</div>
            <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-[#14B8A6] to-[#06B6D4] bg-clip-text text-transparent">
              No Flashcards Generated
            </h1>
            <p className="text-slate-300 mb-8">
              Failed to generate flashcards. Try again or upload different documents.
            </p>
            <button onClick={() => setShowPrompt(true)} className="btn-primary">
              Try Again
            </button>
          </div>
        </div>
      </div>
    )
  }

  const currentCard = deck.cards[currentIndex]

  return (
    <div className="min-h-screen bg-[#0B1220] pt-20 px-4 pb-12">
      <div className="max-w-2xl mx-auto">
        <div className="glass-card p-6 mb-8">
          <h1 className="text-3xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            {deck.deck}
          </h1>
          <p className="text-slate-400">
            Card {currentIndex + 1} of {deck.cards.length}
          </p>
          <div className="progress-bar mt-4">
            <div
              className="progress-fill"
              style={{ width: `${((currentIndex + 1) / deck.cards.length) * 100}%` }}
            />
          </div>
        </div>

        {/* Flashcard */}
        <div
          onClick={() => setFlipped(!flipped)}
          className="glass-card p-12 min-h-[400px] flex flex-col items-center justify-center cursor-pointer hover:shadow-2xl transition-shadow duration-300 mb-8"
        >
          <div className="text-center">
            <div className="text-sm text-slate-400 mb-4">
              {flipped ? 'Back' : 'Front'}
            </div>
            <div className="text-2xl text-slate-100 font-medium leading-relaxed">
              {flipped ? currentCard.back : currentCard.front}
            </div>
            {flipped && currentCard.source && (
              <div className="mt-6 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg text-xs text-slate-400">
                📎 {currentCard.source.evidence}
              </div>
            )}
          </div>
          <div className="text-sm text-slate-500 mt-8">
            Click to flip
          </div>
        </div>

        {/* Navigation */}
        <div className="flex gap-4 mb-6">
          <button
            onClick={prevCard}
            disabled={currentIndex === 0}
            className="flex-1 btn-ghost disabled:opacity-30"
          >
            ← Previous
          </button>
          <button
            onClick={nextCard}
            disabled={currentIndex === deck.cards.length - 1}
            className="flex-1 btn-ghost disabled:opacity-30"
          >
            Next →
          </button>
        </div>

        {/* Export */}
        <div className="text-center">
          <button onClick={exportDeck} className="btn-primary">
            📥 Export Deck (JSON)
          </button>
        </div>
      </div>
    </div>
  )
}
