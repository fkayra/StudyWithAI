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

  // Optional: Removed strict auth check - backend handles quotas

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

  const generateFromFiles = (type: 'summary' | 'flashcards' | 'exam') => {
    if (files.length === 0) {
      alert('Please upload files first')
      return
    }

    const fileIds = files.map((f) => f.file_id)
    sessionStorage.setItem('uploadedFileIds', JSON.stringify(fileIds))

    if (type === 'summary') {
      router.push('/summaries')
    } else if (type === 'flashcards') {
      router.push('/flashcards')
    } else if (type === 'exam') {
      router.push('/exam?grounded=true')
    }
  }

  return (
    <div className="min-h-screen bg-[#0B1220] pt-20 px-4 pb-12">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold text-center mb-8 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
          Upload Documents
        </h1>

        {/* Upload Area */}
        <div className="glass-card p-8 mb-8">
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors ${
              dragActive
                ? 'border-blue-500 bg-blue-500/10'
                : 'border-white/20 hover:border-white/40'
            }`}
          >
            <div className="text-6xl mb-4">📤</div>
            <p className="text-xl text-slate-300 mb-2">
              Drag and drop files here
            </p>
            <p className="text-sm text-slate-400 mb-6">
              Supported: PDF, PPTX, DOCX, JPG, PNG
            </p>
            <input
              type="file"
              id="file-upload"
              multiple
              accept=".pdf,.pptx,.docx,.jpg,.jpeg,.png"
              onChange={handleFileInput}
              className="hidden"
            />
            <label
              htmlFor="file-upload"
              className="btn-primary inline-block cursor-pointer"
            >
              {uploading ? 'Uploading...' : 'Browse Files'}
            </label>
          </div>
        </div>

        {/* Uploaded Files List */}
        {files.length > 0 && (
          <div className="glass-card p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4 text-slate-100">
              Uploaded Files ({files.length})
            </h2>
            <div className="space-y-2">
              {files.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-[#1F2937] rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    <div className="text-2xl">
                      {file.mime.includes('pdf') ? '📄' : 
                       file.mime.includes('image') ? '🖼️' : '📝'}
                    </div>
                    <div>
                      <p className="text-slate-200 font-medium">{file.filename}</p>
                      <p className="text-slate-400 text-xs">
                        {(file.size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        {files.length > 0 && (
          <div className="glass-card p-6">
            <h2 className="text-xl font-semibold mb-4 text-slate-100">
              Generate From Files
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <button
                onClick={() => generateFromFiles('summary')}
                className="p-4 bg-gradient-to-br from-blue-500/20 to-blue-600/20 border border-blue-500/50 rounded-xl hover:border-blue-500 transition-all duration-200"
              >
                <div className="text-3xl mb-2">📊</div>
                <div className="font-semibold text-slate-100">Summary</div>
                <div className="text-xs text-slate-400 mt-1">
                  Extract key points
                </div>
              </button>

              <button
                onClick={() => generateFromFiles('flashcards')}
                className="p-4 bg-gradient-to-br from-purple-500/20 to-purple-600/20 border border-purple-500/50 rounded-xl hover:border-purple-500 transition-all duration-200"
              >
                <div className="text-3xl mb-2">🎴</div>
                <div className="font-semibold text-slate-100">Flashcards</div>
                <div className="text-xs text-slate-400 mt-1">
                  Create study cards
                </div>
              </button>

              <button
                onClick={() => generateFromFiles('exam')}
                className="p-4 bg-gradient-to-br from-green-500/20 to-green-600/20 border border-green-500/50 rounded-xl hover:border-green-500 transition-all duration-200"
              >
                <div className="text-3xl mb-2">✅</div>
                <div className="font-semibold text-slate-100">Exam</div>
                <div className="text-xs text-slate-400 mt-1">
                  Generate quiz
                </div>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
