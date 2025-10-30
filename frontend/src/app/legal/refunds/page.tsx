'use client'

export default function RefundsPage() {
  return (
    <div className="min-h-screen bg-[#0B1220] pt-20 px-4 pb-12">
      <div className="max-w-4xl mx-auto">
        <div className="glass-card p-8">
          <h1 className="text-4xl font-bold mb-8 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            Refund Policy
          </h1>

          <div className="space-y-6 text-slate-300">
            <section>
              <h2 className="text-2xl font-semibold text-slate-100 mb-3">30-Day Money-Back Guarantee</h2>
              <p className="leading-relaxed">
                We offer a 30-day money-back guarantee for all premium subscriptions. If you're not satisfied with
                the service, contact us within 30 days of your purchase for a full refund.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-slate-100 mb-3">How to Request a Refund</h2>
              <p className="leading-relaxed">
                To request a refund, send an email to support@example.com with your account email and reason for
                the refund. We'll process your request within 5-7 business days.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-slate-100 mb-3">Cancellations</h2>
              <p className="leading-relaxed">
                You may cancel your subscription at any time through the Stripe customer portal. Your access will
                continue until the end of your current billing period.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-slate-100 mb-3">Exceptions</h2>
              <p className="leading-relaxed">
                Refunds are not available for accounts that have violated our terms of service or have been used
                fraudulently.
              </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  )
}
