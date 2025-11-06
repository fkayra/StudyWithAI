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
        // Helper function to match balanced parentheses
        const findBalancedParens = (str: string, startIdx: number): string => {
          let depth = 0
          let i = startIdx
          const start = i
          
          while (i < str.length) {
            if (str[i] === '(') depth++
            else if (str[i] === ')') {
              depth--
              if (depth === 0) return str.substring(start, i + 1)
            }
            i++
          }
          return str.substring(start)
        }
        
        // Convert superscripts with nested parentheses: (g(x))^2 -> (g(x))^{2}
        let i = 0
        let result = ''
        while (i < processedText.length) {
          if (processedText[i] === '(' && processedText.indexOf('^', i) > i) {
            const parenExpr = findBalancedParens(processedText, i)
            const afterParen = i + parenExpr.length
            if (processedText[afterParen] === '^') {
              // Find the exponent (number or letter)
              const exponentMatch = processedText.substring(afterParen + 1).match(/^([a-zA-Z0-9]+)/)
              if (exponentMatch) {
                result += `\\(${parenExpr}^{${exponentMatch[1]}}\\)`
                i = afterParen + 1 + exponentMatch[1].length
                continue
              }
            }
          }
          result += processedText[i]
          i++
        }
        processedText = result
        
        // Convert letter^letter -> letter^{letter}
        processedText = processedText.replace(/([a-zA-Z])(\^)([a-zA-Z])/g, (match, base, caret, exp) => {
          if (!match.startsWith('\\(')) return `\\(${base}^{${exp}}\\)`
          return match
        })
        
        // Convert letter^number -> letter^{number}
        processedText = processedText.replace(/([a-zA-Z])(\^)(\d+)/g, (match, base, caret, exp) => {
          if (!match.startsWith('\\(')) return `\\(${base}^{${exp}}\\)`
          return match
        })
        
        // Convert fractions: 5/x -> \frac{5}{x}
        processedText = processedText.replace(/(\d+)\/([a-zA-Z])/g, (match, num, letter) => {
          if (!match.startsWith('\\(')) return `\\(\\frac{${num}}{${letter}}\\)`
          return match
        })
        
        // Convert square roots: √x -> \sqrt{x}
        processedText = processedText.replace(/√\(([^)]+)\)/g, '\\(\\sqrt{$1}\\)')
        processedText = processedText.replace(/√([a-zA-Z0-9]+)/g, '\\(\\sqrt{$1}\\)')
        
        // Convert subscripts: x_1 -> x_{1}
        processedText = processedText.replace(/([a-zA-Z])(_)(\d+)/g, (match, base, underscore, sub) => {
          if (!match.startsWith('\\(')) return `\\(${base}_{${sub}}\\)`
          return match
        })
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
