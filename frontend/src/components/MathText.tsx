'use client'

import { useEffect, useRef, useState } from 'react'
import katex from 'katex'
import 'katex/dist/katex.min.css'

interface MathTextProps {
  text: string
  className?: string
}

export default function MathText({ text, className = '' }: MathTextProps) {
  const containerRef = useRef<HTMLSpanElement>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!containerRef.current || !text) {
      if (containerRef.current && !text) {
        containerRef.current.textContent = ''
      }
      return
    }

    try {
      // Reset error state
      setError(false)
      
      let processedText = String(text)

      // Convert plain text math notation to LaTeX
      // First, detect if already has LaTeX markers
      const hasLatex = processedText.includes('\\(') || processedText.includes('\\[') || processedText.includes('$')
      
      if (!hasLatex) {
        // Auto-detect and wrap entire expressions with ^ in LaTeX
        // This handles: (g(x))^2, e^x, x^2, etc.
        // Be more careful with regex to avoid breaking text
        processedText = processedText.replace(/([a-zA-Z0-9()]+)\^([a-zA-Z0-9()]+)/g, '\\($1^{$2}\\)')
        
        // Convert fractions: 5/x -> \frac{5}{x} (only when it looks like math)
        processedText = processedText.replace(/(\d+)\/([a-zA-Z])/g, '\\(\\frac{$1}{$2}\\)')
        
        // Convert square roots: √x -> \sqrt{x}
        processedText = processedText.replace(/√\(([^)]+)\)/g, '\\(\\sqrt{$1}\\)')
        processedText = processedText.replace(/√([a-zA-Z0-9]+)/g, '\\(\\sqrt{$1}\\)')
        
        // Convert subscripts: x_1 -> x_{1} (only when it looks like math)
        processedText = processedText.replace(/([a-zA-Z])_(\d+)/g, '\\($1_{$2}\\)')
      }

      // Replace inline math \(...\) with rendered LaTeX
      // Use [\s\S] instead of . with s flag for ES2017 compatibility
      processedText = processedText.replace(/\\\(([\s\S]*?)\\\)/g, (match, latex) => {
        try {
          if (!latex || latex.trim() === '') return match
          return katex.renderToString(latex.trim(), {
            throwOnError: false,
            displayMode: false,
            strict: false,
          })
        } catch (e) {
          console.warn('KaTeX inline math error:', e, 'for:', latex)
          return match
        }
      })

      // Replace display math \[...\] with rendered LaTeX
      // Use [\s\S] instead of . with s flag for ES2017 compatibility
      processedText = processedText.replace(/\\\[([\s\S]*?)\\\]/g, (match, latex) => {
        try {
          if (!latex || latex.trim() === '') return match
          return katex.renderToString(latex.trim(), {
            throwOnError: false,
            displayMode: true,
            strict: false,
          })
        } catch (e) {
          console.warn('KaTeX display math error:', e, 'for:', latex)
          return match
        }
      })

      // Also handle $...$ syntax
      processedText = processedText.replace(/\$([^$]+)\$/g, (match, latex) => {
        try {
          if (!latex || latex.trim() === '') return match
          return katex.renderToString(latex.trim(), {
            throwOnError: false,
            displayMode: false,
            strict: false,
          })
        } catch (e) {
          console.warn('KaTeX $ syntax error:', e, 'for:', latex)
          return match
        }
      })

      // Only update if we have valid content
      if (containerRef.current) {
        containerRef.current.innerHTML = processedText
      }
    } catch (error) {
      console.error('MathText rendering error:', error, 'for text:', text)
      setError(true)
      // Fallback to plain text if rendering fails
      if (containerRef.current) {
        containerRef.current.textContent = text
      }
    }
  }, [text])

  // If there was an error, just show plain text
  if (error) {
    return <span className={className}>{text}</span>
  }

  return <span ref={containerRef} className={className} />
}
