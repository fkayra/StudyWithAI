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

  useEffect(() => {
    generateFlashcards()
  }, [])

  const generateFlashcards = async () => {
    const fileIdsStr = sessionStorage.getItem('uploadedFileIds')
    if (!fileIdsStr) {
      alert('No files uploaded. Please upload documents first.')
      return
    }

    const fileIds = JSON.parse(fileIdsStr)
    setLoading(true)

    try {
      const response = await apiClient.post('/flashcards-from-files', {
        file_ids: fileIds,
        style: 'basic',
        deck_name: 'Study Deck',
        count: 10,
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
      <div className="min-h-screen bg-[#0B1220] pt-20 flex items-center justify-center">
        <div className="text-2xl text-slate-300">Generating flashcards...</div>
      </div>
    )
  }

  if (!deck || deck.cards.length === 0) {
    return (
      <div className="min-h-screen bg-[#0B1220] pt-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-4xl font-bold mb-8 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            No Flashcards Generated
          </h1>
          <p className="text-slate-300 mb-8">
            Upload documents first to generate flashcards.
          </p>
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
