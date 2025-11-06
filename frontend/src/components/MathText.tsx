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

      // Convert plain text math notation to LaTeX
      // First, detect if already has LaTeX markers
      const hasLatex = text.includes('\\(') || text.includes('\\[')
      
      if (!hasLatex) {
        // Auto-detect and wrap entire expressions with ^ in LaTeX
        // This handles: (g(x))^2, e^x, x^2, etc.
        processedText = processedText.replace(/([a-zA-Z0-9()]+)\^([a-zA-Z0-9]+)/g, '\\($1^{$2}\\)')
        
        // Convert fractions: 5/x -> \frac{5}{x}
        processedText = processedText.replace(/(\d+)\/([a-zA-Z])/g, '\\(\\frac{$1}{$2}\\)')
        
        // Convert square roots: √x -> \sqrt{x}
        processedText = processedText.replace(/√\(([^)]+)\)/g, '\\(\\sqrt{$1}\\)')
        processedText = processedText.replace(/√([a-zA-Z0-9]+)/g, '\\(\\sqrt{$1}\\)')
        
        // Convert subscripts: x_1 -> x_{1}
        processedText = processedText.replace(/([a-zA-Z])_(\d+)/g, '\\($1_{$2}\\)')
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
