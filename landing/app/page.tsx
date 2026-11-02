import Link from "next/link";
import { MessageSquare, Sparkles, Globe, BarChart3, Shield, Zap, Star, CheckCircle } from "lucide-react";

const FEATURES = [
  { icon: Globe, title: "Multi-Platform", desc: "Connect Amazon, Flipkart, Myntra, Google Business, and more from one dashboard." },
  { icon: Sparkles, title: "AI-Powered Replies", desc: "GPT-4o generates human-like replies. Templates for high-volume responses." },
  { icon: MessageSquare, title: "Unified Inbox", desc: "All reviews from every platform in one place with smart filters." },
  { icon: BarChart3, title: "Analytics", desc: "Sentiment trends, reply rates, and platform breakdowns." },
  { icon: Shield, title: "Smart Flagging", desc: "Sensitive reviews auto-escalated for human review before AI replies." },
  { icon: Zap, title: "Chrome Extension", desc: "Reply directly on Flipkart and Myntra seller portals with one click." },
];

const PLATFORMS = ["Amazon", "Flipkart", "Myntra", "Google Business", "Meesho"];

const TESTIMONIALS = [
  { name: "Rajesh K.", role: "Amazon Seller", text: "ReviewFlow cut our review response time by 80%. The AI replies sound genuinely human." },
  { name: "Priya S.", role: "Flipkart Seller", text: "Managing reviews across 3 platforms was a nightmare. Now it's all in one dashboard." },
  { name: "Amit P.", role: "D2C Brand Owner", text: "The template system handles our 5-star thank-yous, AI handles the tricky 1-stars. Perfect combo." },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      <nav className="border-b border-gray-100 px-6 py-4 flex items-center justify-between max-w-6xl mx-auto">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">RF</div>
          <span className="font-semibold text-lg">ReviewFlow</span>
        </div>
        <div className="flex items-center gap-4">
          <Link href="#features" className="text-sm text-gray-600 hover:text-gray-900">Features</Link>
          <Link href="#pricing" className="text-sm text-gray-600 hover:text-gray-900">Pricing</Link>
          <Link href="http://localhost:3000/login" className="text-sm text-gray-600 hover:text-gray-900">Sign In</Link>
          <Link href="http://localhost:3000/register" className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">Start Free</Link>
        </div>
      </nav>

      <section className="max-w-6xl mx-auto px-6 py-24 text-center">
        <div className="inline-flex items-center gap-2 bg-blue-50 text-blue-700 px-4 py-1.5 rounded-full text-sm font-medium mb-6">
          <Sparkles className="w-4 h-4" /> AI-Powered Review Management
        </div>
        <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6 leading-tight">
          Manage every review.<br /><span className="text-blue-600">Reply with AI.</span>
        </h1>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto mb-8">
          Unified review management for Amazon, Flipkart, Myntra, and Google Business.
          AI drafts human-like replies. You stay in control.
        </p>
        <div className="flex gap-4 justify-center">
          <Link href="http://localhost:3000/register" className="bg-blue-600 text-white px-8 py-3 rounded-xl font-medium hover:bg-blue-700 text-lg">Start for Free</Link>
          <Link href="#how-it-works" className="border border-gray-300 px-8 py-3 rounded-xl font-medium hover:bg-gray-50 text-lg">See How It Works</Link>
        </div>
        <div className="flex justify-center gap-6 mt-8 text-sm text-gray-500">
          {PLATFORMS.map(p => <span key={p}>{p}</span>)}
        </div>
      </section>

      <section id="how-it-works" className="bg-gray-50 py-20">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center mb-12">How It Works</h2>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              { step: "1", title: "Connect", desc: "Link your Amazon, Flipkart, Myntra, or Google Business accounts in minutes." },
              { step: "2", title: "Monitor", desc: "All reviews flow into one unified dashboard with sentiment analysis." },
              { step: "3", title: "Reply with AI", desc: "Choose Template, AI, or Manual mode per platform. Publish in one click." },
            ].map(s => (
              <div key={s.step} className="text-center">
                <div className="w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center text-xl font-bold mx-auto mb-4">{s.step}</div>
                <h3 className="text-xl font-semibold mb-2">{s.title}</h3>
                <p className="text-gray-600">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="features" className="py-20">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center mb-4">Everything you need</h2>
          <p className="text-gray-600 text-center mb-12">Built for Indian e-commerce sellers and global Amazon brands</p>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map(f => (
              <div key={f.title} className="p-6 rounded-2xl border border-gray-100 hover:shadow-md transition-shadow">
                <f.icon className="w-8 h-8 text-blue-600 mb-4" />
                <h3 className="font-semibold text-lg mb-2">{f.title}</h3>
                <p className="text-gray-600 text-sm">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="pricing" className="bg-gray-50 py-20">
        <div className="max-w-6xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-4">Simple pricing</h2>
          <p className="text-gray-600 mb-8">Start free. Scale as you grow.</p>
          <div className="grid md:grid-cols-4 gap-6">
            {[
              { name: "Free", price: "₹0", features: ["1 platform", "50 reviews/mo", "10 AI replies"] },
              { name: "Growth", price: "₹1,499", features: ["3 platforms", "500 reviews/mo", "200 AI replies", "20 templates"] },
              { name: "Professional", price: "₹3,999", features: ["10 platforms", "5,000 reviews/mo", "Webhooks", "Priority support"], highlight: true },
              { name: "Enterprise", price: "₹9,999", features: ["Unlimited", "SSO", "Dedicated CSM", "Custom integrations"] },
            ].map(plan => (
              <div key={plan.name} className={`bg-white rounded-2xl p-6 border ${plan.highlight ? "border-blue-500 ring-2 ring-blue-500" : "border-gray-200"}`}>
                {plan.highlight && <div className="text-xs font-semibold text-blue-600 mb-2">MOST POPULAR</div>}
                <h3 className="font-bold text-lg">{plan.name}</h3>
                <div className="text-3xl font-bold my-3">{plan.price}<span className="text-sm text-gray-500 font-normal">/mo</span></div>
                <ul className="space-y-2 text-sm text-gray-600 mb-6">
                  {plan.features.map(f => <li key={f} className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-green-500" />{f}</li>)}
                </ul>
                <Link href="http://localhost:3000/register" className={`block py-2 rounded-lg text-sm font-medium ${plan.highlight ? "bg-blue-600 text-white" : "border border-gray-200 hover:bg-gray-50"}`}>
                  {plan.name === "Free" ? "Start Free" : "Start Trial"}
                </Link>
              </div>
            ))}
          </div>
          <Link href="http://localhost:3000/pricing" className="text-blue-600 text-sm mt-6 inline-block hover:underline">View full pricing details →</Link>
        </div>
      </section>

      <section className="py-20">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center mb-12">Loved by sellers</h2>
          <div className="grid md:grid-cols-3 gap-6">
            {TESTIMONIALS.map(t => (
              <div key={t.name} className="bg-white p-6 rounded-2xl border border-gray-100">
                <div className="flex gap-1 mb-3">{[...Array(5)].map((_, i) => <Star key={i} className="w-4 h-4 fill-yellow-400 text-yellow-400" />)}</div>
                <p className="text-gray-700 text-sm mb-4">&ldquo;{t.text}&rdquo;</p>
                <div className="font-medium text-sm">{t.name}</div>
                <div className="text-xs text-gray-500">{t.role}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-blue-600 py-16 text-center text-white">
        <h2 className="text-3xl font-bold mb-4">Ready to manage reviews smarter?</h2>
        <p className="text-blue-100 mb-8">Join sellers who save hours every week with AI-powered review management.</p>
        <Link href="http://localhost:3000/register" className="bg-white text-blue-600 px-8 py-3 rounded-xl font-medium hover:bg-blue-50 text-lg inline-block">Get Started Free</Link>
      </section>

      <footer className="border-t border-gray-100 py-8 text-center text-sm text-gray-500">
        © 2026 ReviewFlow. All rights reserved.
      </footer>
    </div>
  );
}
