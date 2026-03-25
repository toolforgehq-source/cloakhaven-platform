import { Link } from "react-router-dom";
import { Shield, Search, BarChart3, Users, ArrowRight, CheckCircle, Lock, Eye } from "lucide-react";

export default function Landing() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Nav */}
      <nav className="border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center font-bold text-sm">CH</div>
            <span className="text-lg font-semibold">Cloak Haven</span>
          </Link>
          <div className="flex items-center gap-6">
            <Link to="/search" className="text-sm text-slate-400 hover:text-white transition">Search</Link>
            <Link to="/pricing" className="text-sm text-slate-400 hover:text-white transition">Pricing</Link>
            <Link to="/login" className="text-sm text-slate-400 hover:text-white transition">Log in</Link>
            <Link to="/register" className="bg-indigo-500 hover:bg-indigo-600 text-white text-sm px-4 py-2 rounded-lg transition font-medium">
              Get Your Score
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-20">
        <div className="text-center max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 rounded-full px-4 py-1.5 text-sm text-indigo-400 mb-8">
            <Shield className="w-4 h-4" />
            Your digital reputation, quantified
          </div>
          <h1 className="text-5xl sm:text-6xl font-bold tracking-tight leading-tight">
            The FICO Score for Your{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400">
              Digital Identity
            </span>
          </h1>
          <p className="mt-6 text-lg text-slate-400 leading-relaxed max-w-2xl mx-auto">
            Cloak Haven scans your social media, web presence, and digital footprint to give you
            a comprehensive reputation score. Know what the world sees before they see it.
          </p>
          <div className="mt-10 flex items-center justify-center gap-4">
            <Link
              to="/register"
              className="bg-indigo-500 hover:bg-indigo-600 text-white px-8 py-3 rounded-lg text-base font-medium transition flex items-center gap-2"
            >
              Start Your Audit <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/search"
              className="bg-slate-800 hover:bg-slate-700 text-white px-8 py-3 rounded-lg text-base font-medium transition"
            >
              Search Someone
            </Link>
          </div>
        </div>

        {/* Score preview */}
        <div className="mt-20 max-w-md mx-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center">
            <p className="text-sm text-slate-500 mb-2">Sample Score</p>
            <div className="text-7xl font-bold text-emerald-400">847</div>
            <p className="text-emerald-400 font-medium mt-1">Very Good</p>
            <div className="mt-6 space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Social Media</span>
                <span className="text-white font-medium">820</span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-2">
                <div className="bg-emerald-400 h-2 rounded-full" style={{ width: "82%" }} />
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Web Presence</span>
                <span className="text-white font-medium">870</span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-2">
                <div className="bg-emerald-400 h-2 rounded-full" style={{ width: "87%" }} />
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Posting Behavior</span>
                <span className="text-white font-medium">855</span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-2">
                <div className="bg-green-400 h-2 rounded-full" style={{ width: "85.5%" }} />
              </div>
            </div>
            <p className="text-xs text-slate-500 mt-4">Score accuracy: 72% — Connect more platforms to improve</p>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="bg-slate-900/50 border-y border-slate-800 py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold">How It Works</h2>
            <p className="mt-4 text-slate-400 max-w-xl mx-auto">
              Three steps to understanding your digital reputation
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-8">
              <div className="w-12 h-12 bg-indigo-500/10 rounded-lg flex items-center justify-center mb-6">
                <Search className="w-6 h-6 text-indigo-400" />
              </div>
              <h3 className="text-lg font-semibold mb-3">1. We Scan</h3>
              <p className="text-slate-400 text-sm leading-relaxed">
                Connect your social accounts or upload your data exports. We also scan
                Google for your web presence. Nothing is stored — zero data retention on private uploads.
              </p>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-8">
              <div className="w-12 h-12 bg-indigo-500/10 rounded-lg flex items-center justify-center mb-6">
                <BarChart3 className="w-6 h-6 text-indigo-400" />
              </div>
              <h3 className="text-lg font-semibold mb-3">2. We Score</h3>
              <p className="text-slate-400 text-sm leading-relaxed">
                Our scoring engine analyzes every finding with recency, virality, and pattern
                modifiers. Juvenile content is excluded. Disputed items can be removed.
              </p>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-8">
              <div className="w-12 h-12 bg-indigo-500/10 rounded-lg flex items-center justify-center mb-6">
                <Eye className="w-6 h-6 text-indigo-400" />
              </div>
              <h3 className="text-lg font-semibold mb-3">3. You Own It</h3>
              <p className="text-slate-400 text-sm leading-relaxed">
                See exactly what impacts your score. Dispute inaccurate findings. Share your
                verified scorecard with employers and partners. Take control of your narrative.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Trust section */}
      <section className="py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-2 gap-16 items-center">
            <div>
              <h2 className="text-3xl font-bold mb-6">Built on Transparency</h2>
              <p className="text-slate-400 mb-8 leading-relaxed">
                Unlike other reputation services, Cloak Haven shows you exactly how your score
                is calculated. Every finding, every modifier, every weight — completely transparent.
              </p>
              <ul className="space-y-4">
                {[
                  "Open algorithm — see how every point is calculated",
                  "Dispute mechanism — challenge inaccurate findings",
                  "Juvenile content excluded — posts before 18 don't count",
                  "Zero data retention on private uploads",
                  "GDPR & CCPA compliant by design",
                ].map((item) => (
                  <li key={item} className="flex items-start gap-3">
                    <CheckCircle className="w-5 h-5 text-emerald-400 mt-0.5 shrink-0" />
                    <span className="text-slate-300 text-sm">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-8">
              <h3 className="font-semibold mb-6 flex items-center gap-2">
                <Lock className="w-5 h-5 text-indigo-400" />
                Score Breakdown
              </h3>
              <div className="space-y-4">
                {[
                  { label: "Social Media History", weight: "40%", color: "bg-indigo-500" },
                  { label: "Web Presence", weight: "35%", color: "bg-purple-500" },
                  { label: "Posting Behavior", weight: "25%", color: "bg-pink-500" },
                ].map((item) => (
                  <div key={item.label}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-slate-400">{item.label}</span>
                      <span className="text-white font-medium">{item.weight}</span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-3">
                      <div className={`${item.color} h-3 rounded-full`} style={{ width: item.weight }} />
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-6 pt-6 border-t border-slate-800">
                <p className="text-xs text-slate-500">
                  Modifiers: Recency (2x for &lt;30 days), Virality (up to 3x),
                  Pattern (up to 2x for repeated behavior)
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="bg-slate-900/50 border-y border-slate-800 py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold">Simple Pricing</h2>
            <p className="mt-4 text-slate-400">No hidden fees. Cancel anytime.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-8">
              <h3 className="font-semibold text-lg">One-Time Audit</h3>
              <div className="mt-4">
                <span className="text-4xl font-bold">$19</span>
                <span className="text-slate-500 ml-1">one-time</span>
              </div>
              <ul className="mt-6 space-y-3 text-sm text-slate-400">
                <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400" /> Full reputation scan</li>
                <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400" /> Detailed findings report</li>
                <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400" /> Score + breakdown</li>
                <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400" /> Shareable scorecard</li>
              </ul>
              <Link to="/register" className="mt-8 block text-center bg-slate-800 hover:bg-slate-700 text-white py-2.5 rounded-lg text-sm font-medium transition">
                Get Started
              </Link>
            </div>
            <div className="bg-slate-900 border-2 border-indigo-500 rounded-xl p-8 relative">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-indigo-500 text-xs font-medium px-3 py-1 rounded-full">
                Most Popular
              </div>
              <h3 className="font-semibold text-lg">Monthly Monitoring</h3>
              <div className="mt-4">
                <span className="text-4xl font-bold">$9</span>
                <span className="text-slate-500 ml-1">/month</span>
              </div>
              <ul className="mt-6 space-y-3 text-sm text-slate-400">
                <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400" /> Everything in One-Time</li>
                <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400" /> Continuous monitoring</li>
                <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400" /> Score update alerts</li>
                <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400" /> Dispute support</li>
              </ul>
              <Link to="/register" className="mt-8 block text-center bg-indigo-500 hover:bg-indigo-600 text-white py-2.5 rounded-lg text-sm font-medium transition">
                Start Monitoring
              </Link>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-8">
              <div className="flex items-center gap-2">
                <Users className="w-5 h-5 text-indigo-400" />
                <h3 className="font-semibold text-lg">Employer Tier</h3>
              </div>
              <div className="mt-4">
                <span className="text-4xl font-bold">$49</span>
                <span className="text-slate-500 ml-1">/month</span>
              </div>
              <ul className="mt-6 space-y-3 text-sm text-slate-400">
                <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400" /> Candidate search</li>
                <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400" /> Reputation reports</li>
                <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400" /> Risk assessment</li>
                <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400" /> API access</li>
              </ul>
              <Link to="/register" className="mt-8 block text-center bg-slate-800 hover:bg-slate-700 text-white py-2.5 rounded-lg text-sm font-medium transition">
                Contact Sales
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24">
        <div className="max-w-3xl mx-auto text-center px-4">
          <h2 className="text-3xl font-bold">Know Your Digital Reputation</h2>
          <p className="mt-4 text-slate-400">
            Every person has a digital footprint. Cloak Haven helps you understand yours
            before an employer, partner, or client finds it first.
          </p>
          <Link
            to="/register"
            className="mt-8 inline-flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white px-8 py-3 rounded-lg text-base font-medium transition"
          >
            Start Your Free Audit <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center font-bold text-sm">CH</div>
              <span className="font-semibold">Cloak Haven</span>
            </div>
            <div className="flex items-center gap-6 text-sm text-slate-400">
              <Link to="/privacy" className="hover:text-white transition">Privacy Policy</Link>
              <Link to="/terms" className="hover:text-white transition">Terms of Service</Link>
              <Link to="/search" className="hover:text-white transition">Search</Link>
            </div>
            <p className="text-sm text-slate-500">&copy; 2026 Cloak Haven. All rights reserved.</p>
          </div>
          <p className="text-xs text-slate-600 text-center mt-8">
            Cloak Haven scores are not consumer reports under the Fair Credit Reporting Act (FCRA)
            and are not intended as the sole basis for employment, housing, or credit decisions.
          </p>
        </div>
      </footer>
    </div>
  );
}
