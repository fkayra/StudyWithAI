'use client'

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[#0B1220] pt-20 px-4 pb-12">
      <div className="max-w-4xl mx-auto">
        <div className="glass-card p-8">
          <h1 className="text-4xl font-bold mb-8 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            Privacy Policy
          </h1>

          <div className="space-y-6 text-slate-300">
            <section>
              <h2 className="text-2xl font-semibold text-slate-100 mb-3">Data Collection</h2>
              <p className="leading-relaxed">
                We collect only the information necessary to provide our services, including your email address,
                uploaded documents, and usage data. Your data is stored securely and never shared with third parties
                without your explicit consent.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-slate-100 mb-3">Document Processing</h2>
              <p className="leading-relaxed">
                Documents you upload are processed using OpenAI's API for generating summaries, flashcards, and exams.
                These documents are stored temporarily and deleted after processing unless you choose to save them.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-slate-100 mb-3">Security</h2>
              <p className="leading-relaxed">
                We use industry-standard encryption and security practices to protect your data. All API keys and
                sensitive information are stored server-side only and never exposed to the client.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-slate-100 mb-3">Your Rights</h2>
              <p className="leading-relaxed">
                You have the right to access, modify, or delete your personal data at any time. Contact our support
                team to exercise these rights.
              </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  )
}
