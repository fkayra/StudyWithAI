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
      let processedText = text

      // Convert plain text math notation to LaTeX if not already in LaTeX format
      if (!text.includes('\\(') && !text.includes('\\[')) {
        // Convert superscripts: x^2 -> x^{2}, x^10 -> x^{10}
        processedText = processedText.replace(/([a-zA-Z])(\^)(\d+)/g, '\\($1^{$3}\\)')
        
        // Convert fractions: 5/x -> \frac{5}{x}, (a+b)/c -> \frac{a+b}{c}
        processedText = processedText.replace(/(\d+)\/([a-zA-Z])/g, '\\(\\frac{$1}{$2}\\)')
        
        // Convert square roots: √x -> \sqrt{x}
        processedText = processedText.replace(/√\(([^)]+)\)/g, '\\(\\sqrt{$1}\\)')
        processedText = processedText.replace(/√([a-zA-Z0-9]+)/g, '\\(\\sqrt{$1}\\)')
        
        // Convert subscripts: x_1 -> x_{1}
        processedText = processedText.replace(/([a-zA-Z])(_)(\d+)/g, '\\($1_{$3}\\)')
      }

      // Replace inline math \(...\) with rendered LaTeX
      processedText = processedText.replace(/\\\((.*?)\\\)/g, (match, latex) => {
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
