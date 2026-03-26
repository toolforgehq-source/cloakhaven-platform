import { useState } from "react";
import { Link } from "react-router-dom";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 mb-6">
            <div className="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center font-bold text-sm text-white">CH</div>
            <span className="text-lg font-semibold text-white">Cloak Haven</span>
          </Link>
          <h1 className="text-2xl font-bold text-white">Reset your password</h1>
          <p className="text-sm text-slate-400 mt-1">
            Enter your email and we'll send you a reset link
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-8">
          {submitted ? (
            <div className="text-center py-4">
              <div className="w-12 h-12 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-white mb-2">Check your email</h2>
              <p className="text-sm text-slate-400 mb-6">
                If an account exists for <span className="text-white">{email}</span>, we'll send a password reset link shortly.
              </p>
              <Link
                to="/login"
                className="text-sm text-indigo-400 hover:text-indigo-300 font-medium"
              >
                Back to sign in
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  placeholder="you@example.com"
                  required
                />
              </div>
              <button
                type="submit"
                className="w-full bg-indigo-500 hover:bg-indigo-600 text-white py-2.5 rounded-lg text-sm font-medium transition"
              >
                Send Reset Link
              </button>
            </form>
          )}
        </div>

        <p className="text-center text-sm text-slate-400 mt-6">
          Remember your password?{" "}
          <Link to="/login" className="text-indigo-400 hover:text-indigo-300 font-medium">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
