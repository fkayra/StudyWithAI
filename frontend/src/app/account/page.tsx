'use client'

import { useAuth } from '@/components/AuthProvider'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'

export default function AccountPage() {
  const { user, refreshUser } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!user) {
      router.push('/login')
    } else {
      refreshUser()
    }
  }, [])

  if (!user) {
    return null
  }

  const limits = user.tier === 'premium'
    ? { exam: 100, explain: 500, chat: 1000, upload: 100 }
    : { exam: 2, explain: 5, chat: 10, upload: 2 }

  const usage = user.usage || { exam: 0, explain: 0, chat: 0, upload: 0 }

  return (
    <div className="min-h-screen bg-[#0B1220] pt-20 px-4 pb-12">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold mb-8 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
          Profile
        </h1>

        {/* User Info */}
        <div className="glass-card p-6 mb-8">
          <h2 className="text-xl font-semibold mb-4 text-slate-100">Personal Information</h2>
          <div className="space-y-4">
            <div>
              <span className="text-slate-400 text-sm">Full Name</span>
              <p className="text-slate-100 font-medium text-lg">{user.name} {user.surname}</p>
            </div>
            <div>
              <span className="text-slate-400 text-sm">Email</span>
              <p className="text-slate-100 font-medium">{user.email}</p>
            </div>
            <div>
              <span className="text-slate-400 text-sm">Plan</span>
              <div className="mt-1">
                <span className={`px-4 py-2 rounded-full text-sm font-medium ${
                  user.tier === 'premium'
                    ? 'bg-gradient-to-r from-yellow-500 to-orange-500 text-white'
                    : 'bg-slate-700 text-slate-300'
                }`}>
                  {user.tier === 'premium' ? '⭐ Premium Plan' : 'Free Plan'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Usage Stats */}
        <div className="glass-card p-6 mb-8">
          <h2 className="text-xl font-semibold mb-6 text-slate-100">Today's Quota & Usage</h2>
          <div className="space-y-6">
            {Object.entries(usage).map(([kind, count]) => {
              const limit = limits[kind as keyof typeof limits]
              const remaining = limit - count
              const percentage = Math.min((count / limit) * 100, 100)
              
              return (
                <div key={kind}>
                  <div className="flex justify-between items-center mb-2">
                    <div>
                      <span className="text-slate-300 capitalize font-medium">{kind}</span>
                      <span className="text-slate-500 text-sm ml-2">
                        ({remaining} remaining)
                      </span>
                    </div>
                    <span className="text-slate-400 text-sm font-medium">
                      {count} / {limit}
                    </span>
                  </div>
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{
                        width: `${percentage}%`
                      }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
          <div className="mt-6 pt-6 border-t border-slate-700/50">
            <p className="text-sm text-slate-400">
              ℹ️ Your quotas reset daily at midnight UTC
            </p>
          </div>
        </div>

        {/* Upgrade */}
        {user.tier === 'free' && (
          <div className="glass-card p-8 bg-gradient-to-br from-blue-500/10 to-purple-500/10 border-blue-500/30">
            <h2 className="text-2xl font-semibold mb-3 text-slate-100">
              Upgrade to Premium
            </h2>
            <p className="text-slate-300 mb-6">
              Get unlimited access to all features, including more exams, explanations, and AI tutor conversations.
            </p>
            <button
              onClick={() => router.push('/pricing')}
              className="btn-primary"
            >
              View Pricing
            </button>
          </div>
        )}

        {/* Manage Subscription (for premium users) */}
        {user.tier === 'premium' && (
          <div className="glass-card p-6">
            <h2 className="text-xl font-semibold mb-4 text-slate-100">
              Manage Subscription
            </h2>
            <p className="text-slate-300 mb-4">
              Manage your billing and subscription through the Stripe customer portal.
            </p>
            <button
              onClick={() => {
                // In production, this would redirect to Stripe customer portal
                alert('Stripe customer portal would open here')
              }}
              className="btn-ghost"
            >
              Open Billing Portal
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
