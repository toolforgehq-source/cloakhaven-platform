import { useState, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

function getPasswordStrength(password: string): { level: number; label: string; color: string } {
  if (!password) return { level: 0, label: "", color: "" };
  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;

  if (score <= 1) return { level: 1, label: "Weak", color: "#EF4444" };
  if (score <= 2) return { level: 2, label: "Fair", color: "#EAB308" };
  if (score <= 3) return { level: 3, label: "Good", color: "#84CC16" };
  return { level: 4, label: "Strong", color: "#10B981" };
}

export default function Register() {
  useDocumentTitle("Create Account");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const strength = useMemo(() => getPasswordStrength(password), [password]);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    if (!/[A-Z]/.test(password) || !/[0-9]/.test(password)) {
      setError("Password must include at least one uppercase letter and one number");
      return;
    }
    if (dateOfBirth) {
      const age = Math.floor((Date.now() - new Date(dateOfBirth).getTime()) / (365.25 * 24 * 60 * 60 * 1000));
      if (age < 13) {
        setError("You must be at least 13 years old to create an account");
        return;
      }
    }
    setLoading(true);
    try {
      await register({ email, password, full_name: fullName, date_of_birth: dateOfBirth || undefined });
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 mb-6">
            <div className="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center font-bold text-sm text-white">CH</div>
            <span className="text-lg font-semibold text-white">Cloak Haven</span>
          </Link>
          <h1 className="text-2xl font-bold text-white">Create your account</h1>
          <p className="text-sm text-slate-400 mt-1">Start your reputation audit today</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-slate-900 border border-slate-800 rounded-xl p-8 space-y-5">
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-sm text-red-400">
              {error}
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">Full Name</label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              placeholder="John Doe"
              required
            />
          </div>
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
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">Date of Birth</label>
            <input
              type="date"
              value={dateOfBirth}
              onChange={(e) => setDateOfBirth(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              max={new Date().toISOString().split("T")[0]}
            />
            <p className="text-xs text-slate-500 mt-1">Used to exclude juvenile content from your score</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              placeholder="At least 8 characters"
              required
              minLength={8}
            />
            {password && (
              <div className="mt-2">
                <div className="flex gap-1">
                  {[1, 2, 3, 4].map((i) => (
                    <div
                      key={i}
                      className="h-1.5 flex-1 rounded-full transition-colors"
                      style={{ backgroundColor: i <= strength.level ? strength.color : "#334155" }}
                    />
                  ))}
                </div>
                <p className="text-xs mt-1" style={{ color: strength.color }}>{strength.label}</p>
              </div>
            )}
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white py-2.5 rounded-lg text-sm font-medium transition"
          >
            {loading ? "Creating account..." : "Create Account"}
          </button>
          <p className="text-xs text-slate-500 text-center">
            By signing up, you agree to our{" "}
            <Link to="/terms" className="text-indigo-400 hover:underline">Terms of Service</Link> and{" "}
            <Link to="/privacy" className="text-indigo-400 hover:underline">Privacy Policy</Link>.
          </p>
        </form>

        <p className="text-center text-sm text-slate-400 mt-6">
          Already have an account?{" "}
          <Link to="/login" className="text-indigo-400 hover:text-indigo-300 font-medium">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
