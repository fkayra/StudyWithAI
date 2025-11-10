'use client'

import { useEffect, useRef } from 'react'
import mermaid from 'mermaid'

interface MermaidDiagramProps {
  content: string
  className?: string
}

export default function MermaidDiagram({ content, className = '' }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const renderedRef = useRef(false)

  useEffect(() => {
    if (!containerRef.current || renderedRef.current) return

    // Initialize mermaid with dark theme
    mermaid.initialize({
      startOnLoad: true,
      theme: 'dark',
      themeVariables: {
        primaryColor: '#14B8A6',
        primaryTextColor: '#E2E8F0',
        primaryBorderColor: '#0D9488',
        lineColor: '#06B6D4',
        secondaryColor: '#0891B2',
        tertiaryColor: '#0E7490',
        background: '#0F172A',
        mainBkg: '#1E293B',
        secondBkg: '#334155',
        border1: '#475569',
        border2: '#64748B',
        fontSize: '14px'
      },
      flowchart: {
        htmlLabels: true,
        curve: 'basis'
      }
    })

    // Generate unique ID for this diagram
    const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`
    
    // Render the diagram
    mermaid.render(id, content).then(({ svg }) => {
      if (containerRef.current) {
        containerRef.current.innerHTML = svg
        renderedRef.current = true
      }
    }).catch((error) => {
      console.error('Mermaid rendering error:', error)
      if (containerRef.current) {
        containerRef.current.innerHTML = `
          <div class="text-red-400 text-sm">
            Failed to render diagram. Showing raw content:
          </div>
          <pre class="text-slate-300 text-xs mt-2 whitespace-pre-wrap">${content}</pre>
        `
      }
    })

    return () => {
      renderedRef.current = false
    }
  }, [content])

  return (
    <div 
      ref={containerRef} 
      className={`mermaid-container ${className}`}
      style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center',
        minHeight: '200px'
      }}
    >
      {/* Mermaid will render here */}
    </div>
  )
}
