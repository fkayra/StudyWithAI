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
    
    // Pre-process content: handle escaped newlines and cleanup
    let processedContent = content
      // Replace literal \n with actual newlines (from JSON parsing)
      .replace(/\\n/g, '\n')
      // Remove any extra spaces around arrows
      .replace(/\s*-->\s*/g, ' --> ')
      // Ensure proper spacing around edge labels
      .replace(/-->\s*\|\s*/g, ' -->|')
      .replace(/\s*\|\s*-->/g, '| ')
    
    console.log('[Mermaid] Original content:', content)
    console.log('[Mermaid] Processed content:', processedContent)
    
    // Render the diagram
    mermaid.render(id, processedContent).then(({ svg }) => {
      if (containerRef.current) {
        containerRef.current.innerHTML = svg
        renderedRef.current = true
      }
    }).catch((error) => {
      console.error('Mermaid rendering error:', error)
      console.error('Failed content:', processedContent)
      if (containerRef.current) {
        containerRef.current.innerHTML = `
          <div class="text-red-400 text-sm mb-2">
            Failed to render diagram. Showing raw content:
          </div>
          <pre class="text-slate-300 text-xs mt-2 whitespace-pre-wrap bg-slate-800 p-3 rounded border border-slate-600">${processedContent}</pre>
          <div class="text-xs text-slate-500 mt-2">Error: ${error.message || 'Syntax error'}</div>
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
