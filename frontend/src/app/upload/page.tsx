'use client'

import { useState, useCallback, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api'
import { useAuth } from '@/components/AuthProvider'

interface UploadedFile {
  file_id: string
  filename: string
  mime: string
  size: number
}

export default function UploadPage() {
  const router = useRouter()
  const { user } = useAuth()
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [uploading, setUploading] = useState(false)
  const [dragActive, setDragActive] = useState(false)

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    const droppedFiles = Array.from(e.dataTransfer.files)
    await uploadFiles(droppedFiles)
  }, [])

  const handleFileInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files)
      await uploadFiles(selectedFiles)
    }
  }

  const uploadFiles = async (filesToUpload: File[]) => {
    setUploading(true)

    const formData = new FormData()
    filesToUpload.forEach((file) => {
      formData.append('files', file)
    })

    try {
      const response = await apiClient.post('/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      setFiles((prev) => [...prev, ...response.data])
      
      // Store file IDs in session storage
      const fileIds = response.data.map((f: UploadedFile) => f.file_id)
      sessionStorage.setItem('uploadedFileIds', JSON.stringify(fileIds))
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const generateFromFiles = (type: 'summary' | 'flashcards' | 'truefalse' | 'exam') => {
    if (files.length === 0) {
      alert('Please upload files first')
      return
    }

    const fileIds = files.map((f) => f.file_id)
    sessionStorage.setItem('uploadedFileIds', JSON.stringify(fileIds))
    // Also save complete file info
    sessionStorage.setItem('uploadedFiles', JSON.stringify(files))
    
    // Clear any old exam/summary/flashcards data when uploading new files
    sessionStorage.removeItem('currentExam')
    sessionStorage.removeItem('currentExamState')
    sessionStorage.removeItem('viewHistory')

    if (type === 'summary') {
      router.push('/summaries')
    } else if (type === 'flashcards') {
      router.push('/flashcards')
    } else if (type === 'truefalse') {
      router.push('/truefalse')
    } else if (type === 'exam') {
      router.push('/exam?grounded=true')
    }
  }

  return (
    <div className="min-h-screen bg-[#0F172A] pt-20 px-4 pb-12 overflow-hidden">
      {/* Animated background */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute top-40 right-1/4 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl animate-pulse-slow"></div>
        <div className="absolute bottom-20 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }}></div>
      </div>

      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-12 animate-fade-in">
          <h1 className="text-5xl md:text-6xl font-bold mb-4 bg-gradient-to-r from-[#14B8A6] to-[#06B6D4] bg-clip-text text-transparent">
            Upload Documents
          </h1>
          <p className="text-xl text-slate-300">
            Upload your study materials and let AI do the rest
          </p>
        </div>

        {/* Upload Area */}
        <div className="glass-card mb-8 animate-slide-up">
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-2xl p-16 text-center transition-all duration-300 transform ${
              dragActive
                ? 'border-[#14B8A6] bg-gradient-to-br from-[#14B8A6]/20 to-[#06B6D4]/20 scale-[1.02]'
                : 'border-white/20 hover:border-white/40 hover:bg-white/5'
            }`}
          >
            <div className={`text-7xl mb-6 transition-transform duration-300 ${dragActive ? 'scale-110 animate-bounce' : ''}`}>
              📤
            </div>
            <p className="text-2xl text-slate-300 mb-2 font-semibold">
              {dragActive ? 'Drop files here!' : 'Drag and drop files here'}
            </p>
            <p className="text-sm text-slate-400 mb-8">
              Supported: PDF, DOCX, PPTX, TXT (Max 10MB per file)
            </p>
            <input
              type="file"
              id="file-upload"
              multiple
              accept=".pdf,.docx,.pptx,.txt"
              onChange={handleFileInput}
              className="hidden"
              disabled={uploading}
            />
            <label
              htmlFor="file-upload"
              className={`btn-primary inline-block cursor-pointer ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              {uploading ? (
                <span className="flex items-center gap-2">
                  <span className="animate-spin">⏳</span>
                  Uploading...
                </span>
              ) : (
                'Browse Files 📁'
              )}
            </label>
          </div>
        </div>

        {/* Uploaded Files List */}
        {files.length > 0 && (
          <div className="glass-card mb-8 animate-scale-in">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-semibold text-slate-100">
                Uploaded Files
              </h2>
              <span className="px-4 py-2 bg-gradient-to-r from-[#14B8A6]/20 to-[#06B6D4]/20 text-[#06B6D4] rounded-xl text-sm font-semibold border border-[#14B8A6]/30">
                {files.length} {files.length === 1 ? 'file' : 'files'}
              </span>
            </div>
            <div className="space-y-3">
              {files.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-4 bg-[#1E293B]/50 rounded-xl border border-white/5 hover:border-white/10 transition-all duration-200 animate-slide-up card-hover"
                  style={{ animationDelay: `${index * 0.05}s` }}
                >
                  <div className="flex items-center space-x-4">
                    <div className="text-4xl">
                      {file.mime.includes('pdf') ? '📄' : 
                       file.mime.includes('image') ? '🖼️' : 
                       file.mime.includes('presentation') ? '📊' : '📝'}
                    </div>
                    <div>
                      <p className="text-slate-200 font-medium text-lg">{file.filename}</p>
                      <p className="text-slate-400 text-sm">
                        {(file.size / 1024).toFixed(1)} KB • {file.mime.split('/')[1].toUpperCase()}
                      </p>
                    </div>
                  </div>
                  <div className="text-green-400 text-2xl">✓</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        {files.length > 0 && (
          <div className="glass-card animate-slide-up" style={{ animationDelay: '0.3s' }}>
            <h2 className="text-2xl font-semibold mb-2 text-slate-100">
              What would you like to generate?
            </h2>
            <p className="text-slate-400 mb-6">
              Choose an AI-powered tool to process your documents
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                {
                  type: 'summary' as const,
                  icon: '📝',
                  title: 'Summary',
                  desc: 'Extract key points and insights',
                  gradient: 'from-teal-500/20 to-teal-600/20',
                  border: 'border-teal-500/50',
                  hoverBorder: 'hover:border-teal-400',
                  shadow: 'hover:shadow-lg hover:shadow-teal-500/25'
                },
                {
                  type: 'flashcards' as const,
                  icon: '🎴',
                  title: 'Flashcards',
                  desc: 'Create interactive study cards',
                  gradient: 'from-cyan-500/20 to-cyan-600/20',
                  border: 'border-cyan-500/50',
                  hoverBorder: 'hover:border-cyan-400',
                  shadow: 'hover:shadow-lg hover:shadow-cyan-500/25'
                },
                {
                  type: 'truefalse' as const,
                  icon: '✓✗',
                  title: 'True/False',
                  desc: 'Test knowledge with statements',
                  gradient: 'from-green-500/20 to-red-500/20',
                  border: 'border-green-500/50',
                  hoverBorder: 'hover:border-green-400',
                  shadow: 'hover:shadow-lg hover:shadow-green-500/25'
                },
                {
                  type: 'exam' as const,
                  icon: '🎯',
                  title: 'Practice Exam',
                  desc: 'Generate a quiz from content',
                  gradient: 'from-emerald-500/20 to-emerald-600/20',
                  border: 'border-emerald-500/50',
                  hoverBorder: 'hover:border-emerald-400',
                  shadow: 'hover:shadow-lg hover:shadow-emerald-500/25'
                }
              ].map((item, i) => (
                <button
                  key={item.type}
                  onClick={() => generateFromFiles(item.type)}
                  className={`p-6 bg-gradient-to-br ${item.gradient} border ${item.border} ${item.hoverBorder} ${item.shadow} rounded-2xl transition-all duration-300 hover:scale-105 active:scale-95 group animate-scale-in`}
                  style={{ animationDelay: `${i * 0.1}s` }}
                >
                  <div className="text-5xl mb-4 group-hover:scale-110 transition-transform duration-300">
                    {item.icon}
                  </div>
                  <div className="font-bold text-xl text-slate-100 mb-2">
                    {item.title}
                  </div>
                  <div className="text-sm text-slate-400">
                    {item.desc}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Empty state help */}
        {files.length === 0 && !uploading && (
          <div className="glass-card text-center animate-fade-in" style={{ animationDelay: '0.2s' }}>
            <div className="text-4xl mb-4">💡</div>
            <h3 className="text-xl font-semibold text-slate-100 mb-2">
              No files uploaded yet
            </h3>
            <p className="text-slate-400 mb-4">
              Upload your study materials to get started with AI-powered learning tools
            </p>
            <div className="flex gap-3 justify-center text-sm text-slate-400">
              <span>✓ Instant processing</span>
              <span>✓ Secure upload</span>
              <span>✓ Multiple formats</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
