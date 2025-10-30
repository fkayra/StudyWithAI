'use client'

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-[#0B1220] pt-20 px-4 pb-12">
      <div className="max-w-4xl mx-auto">
        <div className="glass-card p-8">
          <h1 className="text-4xl font-bold mb-8 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            Terms of Service
          </h1>

          <div className="space-y-6 text-slate-300">
            <section>
              <h2 className="text-2xl font-semibold text-slate-100 mb-3">Acceptance of Terms</h2>
              <p className="leading-relaxed">
                By accessing and using this service, you accept and agree to be bound by the terms and provision
                of this agreement.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-slate-100 mb-3">Use License</h2>
              <p className="leading-relaxed">
                Permission is granted to temporarily use this service for personal, non-commercial educational purposes only.
                This is the grant of a license, not a transfer of title.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-slate-100 mb-3">Service Availability</h2>
              <p className="leading-relaxed">
                We strive to provide uninterrupted service but do not guarantee that the service will always be available
                or error-free. We reserve the right to modify or discontinue the service at any time.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-slate-100 mb-3">User Responsibilities</h2>
              <p className="leading-relaxed">
                Users are responsible for maintaining the confidentiality of their account credentials and for all
                activities that occur under their account.
              </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  )
}
