'use client'

import Link from 'next/link'
import { useAuth } from './AuthProvider'
import { useRouter, usePathname } from 'next/navigation'

export function Navigation() {
  const { user, logout } = useAuth()
  const router = useRouter()
  const pathname = usePathname()

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  const navLinks = [
    { href: '/upload', label: '📄 Upload', icon: '📄' },
    { href: '/summaries', label: '📝 Summaries', icon: '📝' },
    { href: '/flashcards', label: '🎴 Flashcards', icon: '🎴' },
    { href: '/exam', label: '🎯 Exams', icon: '🎯' },
  ]

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-[#111827]/95 backdrop-blur-xl border-b border-white/10 shadow-lg shadow-black/20 animate-slide-down">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-8">
            <Link 
              href="/" 
              className="text-2xl font-bold bg-gradient-to-r from-[#6366F1] via-[#60A5FA] to-[#3B82F6] bg-clip-text text-transparent hover:scale-105 transition-transform duration-200"
            >
              StudyWithAI
            </Link>
            
            {user && (
              <div className="hidden md:flex space-x-1">
                {navLinks.map((link) => {
                  const isActive = pathname === link.href
                  return (
                    <Link
                      key={link.href}
                      href={link.href}
                      className={`px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
                        isActive
                          ? 'bg-gradient-to-r from-[#6366F1]/20 to-[#60A5FA]/20 text-[#60A5FA] border border-[#6366F1]/50'
                          : 'text-slate-300 hover:text-white hover:bg-white/5'
                      }`}
                    >
                      {link.label}
                    </Link>
                  )
                })}
              </div>
            )}
          </div>

          <div className="flex items-center space-x-4">
            {user ? (
              <>
                <Link href="/account" className="group">
                  <span className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-200 group-hover:scale-105 ${
                    user.tier === 'premium' 
                      ? 'bg-gradient-to-r from-yellow-500 to-orange-500 text-white shadow-lg shadow-yellow-500/25' 
                      : 'bg-gradient-to-r from-slate-700 to-slate-600 text-slate-300 group-hover:from-slate-600 group-hover:to-slate-500'
                  }`}>
                    {user.tier === 'premium' ? '⭐ Premium' : 'Free Plan'}
                  </span>
                </Link>
                <button
                  onClick={handleLogout}
                  className="text-slate-300 hover:text-white transition-colors px-3 py-2 rounded-lg hover:bg-white/5"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link 
                  href="/login" 
                  className="text-slate-300 hover:text-white transition-colors px-4 py-2 rounded-lg hover:bg-white/5"
                >
                  Login
                </Link>
                <Link 
                  href="/register" 
                  className="bg-gradient-to-r from-[#6366F1] to-[#60A5FA] text-white rounded-xl px-5 py-2 text-sm font-medium hover:shadow-lg hover:shadow-blue-500/25 transition-all duration-200 hover:scale-105 active:scale-95"
                >
                  Sign Up Free
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
