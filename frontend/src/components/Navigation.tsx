'use client'

import Link from 'next/link'
import { useAuth } from './AuthProvider'
import { useRouter } from 'next/navigation'

export function Navigation() {
  const { user, logout } = useAuth()
  const router = useRouter()

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-[#111827]/90 backdrop-blur-md border-b border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-8">
            <Link href="/" className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
              AI Study Assistant
            </Link>
            
            {user && (
              <div className="hidden md:flex space-x-4">
                <Link href="/upload" className="text-slate-300 hover:text-white transition-colors">
                  Upload
                </Link>
                <Link href="/summaries" className="text-slate-300 hover:text-white transition-colors">
                  Summaries
                </Link>
                <Link href="/flashcards" className="text-slate-300 hover:text-white transition-colors">
                  Flashcards
                </Link>
                <Link href="/exam" className="text-slate-300 hover:text-white transition-colors">
                  Exams
                </Link>
              </div>
            )}
          </div>

          <div className="flex items-center space-x-4">
            {user ? (
              <>
                <Link href="/account" className="text-slate-300 hover:text-white transition-colors">
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                    user.tier === 'premium' 
                      ? 'bg-gradient-to-r from-yellow-500 to-orange-500 text-white' 
                      : 'bg-slate-700 text-slate-300'
                  }`}>
                    {user.tier === 'premium' ? '⭐ Premium' : 'Free'}
                  </span>
                </Link>
                <button
                  onClick={handleLogout}
                  className="text-slate-300 hover:text-white transition-colors"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link href="/login" className="text-slate-300 hover:text-white transition-colors">
                  Login
                </Link>
                <Link href="/register" className="btn-primary px-4 py-2 text-sm">
                  Sign Up
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
