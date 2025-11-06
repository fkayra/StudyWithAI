'use client'

import { useEffect, useRef } from 'react'
import katex from 'katex'
import 'katex/dist/katex.min.css'

interface MathTextProps {
  text: string
  className?: string
}

export default function MathText({ text, className = '' }: MathTextProps) {
  const containerRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (!containerRef.current) return

    try {
      // Replace inline math \(...\) with rendered LaTeX
      let processedText = text.replace(/\\\((.*?)\\\)/g, (match, latex) => {
        try {
          return katex.renderToString(latex, {
            throwOnError: false,
            displayMode: false,
          })
        } catch (e) {
          return match
        }
      })

      // Replace display math \[...\] with rendered LaTeX
      processedText = processedText.replace(/\\\[(.*?)\\\]/g, (match, latex) => {
        try {
          return katex.renderToString(latex, {
            throwOnError: false,
            displayMode: true,
          })
        } catch (e) {
          return match
        }
      })

      containerRef.current.innerHTML = processedText
    } catch (error) {
      // Fallback to plain text if rendering fails
      if (containerRef.current) {
        containerRef.current.textContent = text
      }
    }
  }, [text])

  return <span ref={containerRef} className={className} />
}
