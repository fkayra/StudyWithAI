'use client'

import { useState } from 'react'
import { useAuth } from '@/components/AuthProvider'
import { apiClient } from '@/lib/api'
import { loadStripe } from '@stripe/stripe-js'
import { Pricing } from '@/components/blocks/pricing'

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || '')

export default function PricingPage() {
  const { user } = useAuth()
  const [loading, setLoading] = useState(false)

  const handlePurchase = async (planName: string) => {
    if (!user) {
      alert('Please login first')
      return
    }

    if (planName === 'Free') {
      return // Free plan doesn't need purchase
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

  const plans = [
    {
      name: "FREE",
      price: "0",
      yearlyPrice: "0",
      period: "forever",
      features: [
        "2 exams per day",
        "5 explanations per day",
        "10 chat messages per day",
        "2 file uploads per day",
        "Grounded summaries",
        "Flashcard generation",
      ],
      description: "Perfect for trying out our platform",
      buttonText: user?.tier === 'free' ? 'Current Plan' : 'Start Free',
      href: user?.tier === 'free' ? '#' : '/register',
      isPopular: false,
    },
    {
      name: "STARTER",
      price: "9.99",
      yearlyPrice: "7.99",
      period: "per month",
      features: [
        "100 exams per day",
        "500 explanations per day",
        "1000 chat messages per day",
        "100 file uploads per day",
        "Everything in Free",
        "Priority support",
        "Exam history",
      ],
      description: "Ideal for serious students",
      buttonText: loading 
        ? 'Loading...' 
        : user?.tier === 'starter' || user?.tier === 'premium'
          ? 'Current Plan' 
          : 'Upgrade to Starter',
      href: user?.tier === 'starter' || user?.tier === 'premium' ? '#' : '#',
      isPopular: true,
      onClick: () => handlePurchase('Starter'),
    },
    {
      name: "PROFESSIONAL",
      price: "20",
      yearlyPrice: "16",
      period: "per month",
      features: [
        "200 exams per day",
        "1000 explanations per day",
        "2000 chat messages per day",
        "200 file uploads per day",
        "Everything in Starter",
        "Priority support",
        "Exam history",
        "Advanced analytics",
        "API access",
      ],
      description: "For power users and professionals",
      buttonText: loading 
        ? 'Loading...' 
        : user?.tier === 'professional' 
          ? 'Current Plan' 
          : 'Upgrade to Professional',
      href: user?.tier === 'professional' ? '#' : '#',
      isPopular: false,
      onClick: () => handlePurchase('Professional'),
    },
  ]

  return (
    <div className="min-h-screen bg-[#0B1220]">
      <Pricing
        plans={plans}
        title="Choose Your Plan"
        description="Unlock unlimited AI-powered study assistance\nAll plans include access to our platform and dedicated support."
      />
      
      {/* Legal Links */}
      <div className="container pb-12 text-center text-slate-400 text-sm space-x-4">
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
  )
}
