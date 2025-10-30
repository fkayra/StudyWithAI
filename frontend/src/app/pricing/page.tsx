'use client'

import { useState } from 'react'
import { useAuth } from '@/components/AuthProvider'
import { apiClient } from '@/lib/api'
import { loadStripe } from '@stripe/stripe-js'

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || '')

export default function PricingPage() {
  const { user } = useAuth()
  const [loading, setLoading] = useState(false)

  const handlePurchase = async () => {
    if (!user) {
      alert('Please login first')
      return
    }

    setLoading(true)

    try {
      const response = await apiClient.post('/billing/create-checkout-session', {
        priceId: 'price_premium_monthly', // Replace with actual Stripe price ID
        successUrl: `${window.location.origin}/account?success=true`,
        cancelUrl: `${window.location.origin}/pricing?canceled=true`,
      })

      const stripe = await stripePromise
      if (stripe && response.data.sessionId) {
        await stripe.redirectToCheckout({ sessionId: response.data.sessionId })
      } else if (response.data.url) {
        window.location.href = response.data.url
      }
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to create checkout session')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0B1220] pt-20 px-4 pb-12">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            Choose Your Plan
          </h1>
          <p className="text-xl text-slate-300">
            Unlock unlimited AI-powered study assistance
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {/* Free Tier */}
          <div className="glass-card p-8">
            <div className="text-center mb-6">
              <h2 className="text-2xl font-bold text-slate-100 mb-2">Free</h2>
              <div className="text-4xl font-bold text-slate-300 mb-1">$0</div>
              <div className="text-slate-400 text-sm">forever</div>
            </div>

            <ul className="space-y-3 mb-8">
              <li className="flex items-center text-slate-300">
                <span className="text-green-400 mr-3">✓</span>
                2 exams per day
              </li>
              <li className="flex items-center text-slate-300">
                <span className="text-green-400 mr-3">✓</span>
                5 explanations per day
              </li>
              <li className="flex items-center text-slate-300">
                <span className="text-green-400 mr-3">✓</span>
                10 chat messages per day
              </li>
              <li className="flex items-center text-slate-300">
                <span className="text-green-400 mr-3">✓</span>
                2 file uploads per day
              </li>
              <li className="flex items-center text-slate-300">
                <span className="text-green-400 mr-3">✓</span>
                Grounded summaries
              </li>
              <li className="flex items-center text-slate-300">
                <span className="text-green-400 mr-3">✓</span>
                Flashcard generation
              </li>
            </ul>

            <button
              disabled={user?.tier === 'free'}
              className="w-full btn-ghost disabled:opacity-50"
            >
              {user?.tier === 'free' ? 'Current Plan' : 'Start Free'}
            </button>
          </div>

          {/* Premium Tier */}
          <div className="glass-card p-8 border-2 border-blue-500 relative">
            <div className="absolute -top-4 left-1/2 transform -translate-x-1/2 px-4 py-1 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full text-white text-sm font-medium">
              Most Popular
            </div>

            <div className="text-center mb-6">
              <h2 className="text-2xl font-bold text-slate-100 mb-2">Premium</h2>
              <div className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent mb-1">
                $9.99
              </div>
              <div className="text-slate-400 text-sm">per month</div>
            </div>

            <ul className="space-y-3 mb-8">
              <li className="flex items-center text-slate-300">
                <span className="text-green-400 mr-3">✓</span>
                100 exams per day
              </li>
              <li className="flex items-center text-slate-300">
                <span className="text-green-400 mr-3">✓</span>
                500 explanations per day
              </li>
              <li className="flex items-center text-slate-300">
                <span className="text-green-400 mr-3">✓</span>
                1000 chat messages per day
              </li>
              <li className="flex items-center text-slate-300">
                <span className="text-green-400 mr-3">✓</span>
                100 file uploads per day
              </li>
              <li className="flex items-center text-slate-300">
                <span className="text-green-400 mr-3">✓</span>
                Everything in Free
              </li>
              <li className="flex items-center text-slate-300">
                <span className="text-green-400 mr-3">✓</span>
                Priority support
              </li>
              <li className="flex items-center text-slate-300">
                <span className="text-green-400 mr-3">✓</span>
                Exam history
              </li>
            </ul>

            <button
              onClick={handlePurchase}
              disabled={loading || user?.tier === 'premium'}
              className="w-full btn-primary disabled:opacity-50"
            >
              {loading ? 'Loading...' : user?.tier === 'premium' ? 'Current Plan' : 'Upgrade to Premium'}
            </button>
          </div>
        </div>

        {/* Legal Links */}
        <div className="mt-12 text-center text-slate-400 text-sm space-x-4">
          <a href="/legal/privacy" className="hover:text-slate-300 transition-colors">
            Privacy Policy
          </a>
          <span>•</span>
          <a href="/legal/terms" className="hover:text-slate-300 transition-colors">
            Terms of Service
          </a>
          <span>•</span>
          <a href="/legal/refunds" className="hover:text-slate-300 transition-colors">
            Refund Policy
          </a>
        </div>
      </div>
    </div>
  )
}
