import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { api, Finding } from "@/lib/api";
import { Flag, ArrowLeft, AlertTriangle, Shield, Send } from "lucide-react";
import Navbar from "@/components/Navbar";

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-500/10 text-red-400 border-red-500/20",
  high: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  medium: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  positive: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  neutral: "bg-slate-700 text-slate-400 border-slate-600",
};

export default function DisputeForm() {
  const { id } = useParams<{ id: string }>();
  const { user, logout } = useAuth();
  const [finding, setFinding] = useState<Finding | null>(null);
  const [reason, setReason] = useState("");
  const [evidence, setEvidence] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (!id) return;
    loadFinding();
  }, [id]);

  const loadFinding = async () => {
    setLoading(true);
    try {
      const data = await api.getFinding(id!);
      setFinding(data);
    } catch {
      setError("Finding not found");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || reason.length < 10) return;
    setSubmitting(true);
    setError("");
    try {
      await api.createDispute(id, {
        reason,
        supporting_evidence: evidence || undefined,
      });
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit dispute");
    } finally {
      setSubmitting(false);
    }
  };

  const navLinks = [
    { to: "/dashboard", label: "Dashboard" },
    { to: "/findings", label: "Findings" },
    { to: "/search", label: "Search" },
    { to: "/settings", label: "Settings" },
  ];

  const navRight = (
    <div className="flex items-center gap-3 md:pl-4 md:border-l md:border-slate-800">
      <span className="text-sm text-slate-400">{user?.email}</span>
      <button onClick={logout} className="text-sm text-red-400 hover:text-red-300">Sign out</button>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-950">
      <Navbar links={navLinks} rightContent={navRight} />

      <main className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Link to="/findings" className="flex items-center gap-1 text-sm text-slate-400 hover:text-white mb-6 transition">
          <ArrowLeft className="w-4 h-4" /> Back to Findings
        </Link>

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : error && !finding ? (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
            <AlertTriangle className="w-10 h-10 text-amber-400 mx-auto mb-3" />
            <p className="text-white font-medium">{error}</p>
            <Link to="/findings" className="text-indigo-400 hover:text-indigo-300 text-sm mt-3 inline-block">
              Return to Findings
            </Link>
          </div>
        ) : success ? (
          <div className="bg-slate-900 border border-emerald-500/20 rounded-xl p-12 text-center">
            <Shield className="w-12 h-12 text-emerald-400 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-white mb-2">Dispute Submitted</h2>
            <p className="text-slate-400 mb-6">
              Your dispute has been submitted and is pending review. We'll notify you once a decision is made.
              Disputed findings are temporarily excluded from your score calculation.
            </p>
            <div className="flex gap-3 justify-center">
              <Link
                to="/findings"
                className="bg-indigo-500 hover:bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium transition"
              >
                Back to Findings
              </Link>
              <Link
                to="/dashboard"
                className="bg-slate-800 hover:bg-slate-700 text-white px-5 py-2 rounded-lg text-sm font-medium transition"
              >
                Go to Dashboard
              </Link>
            </div>
          </div>
        ) : finding ? (
          <>
            <div className="flex items-center gap-3 mb-6">
              <Flag className="w-6 h-6 text-amber-400" />
              <div>
                <h1 className="text-2xl font-bold text-white">Dispute Finding</h1>
                <p className="text-sm text-slate-400">Challenge a finding you believe is inaccurate or unfair</p>
              </div>
            </div>

            {/* Finding being disputed */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 mb-6">
              <div className="flex items-center gap-2 mb-2">
                <span className={`text-xs px-2 py-0.5 rounded border ${SEVERITY_COLORS[finding.severity] || SEVERITY_COLORS.neutral}`}>
                  {finding.severity}
                </span>
                <span className="text-xs text-slate-500 capitalize">{finding.source}</span>
                <span className="text-xs text-slate-600">{finding.category.replace(/_/g, " ")}</span>
              </div>
              <h3 className="text-sm font-medium text-white mb-1">{finding.title}</h3>
              {finding.description && (
                <p className="text-xs text-slate-400">{finding.description}</p>
              )}
              {finding.evidence_snippet && (
                <p className="text-xs text-slate-500 mt-2 italic">"{finding.evidence_snippet}"</p>
              )}
              <div className="flex items-center gap-3 mt-3">
                <span className={`text-xs font-medium ${finding.final_score_impact > 0 ? "text-emerald-400" : finding.final_score_impact < 0 ? "text-red-400" : "text-slate-500"}`}>
                  Score impact: {finding.final_score_impact > 0 ? "+" : ""}{finding.final_score_impact.toFixed(1)}
                </span>
              </div>
            </div>

            {/* Dispute form */}
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-white mb-2">
                  Reason for dispute <span className="text-red-400">*</span>
                </label>
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  rows={4}
                  minLength={10}
                  maxLength={2000}
                  required
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
                  placeholder="Explain why this finding is inaccurate, taken out of context, or should not affect your score. Minimum 10 characters."
                />
                <p className="text-xs text-slate-500 mt-1">{reason.length}/2000 characters (minimum 10)</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-white mb-2">
                  Supporting evidence <span className="text-slate-500">(optional)</span>
                </label>
                <textarea
                  value={evidence}
                  onChange={(e) => setEvidence(e.target.value)}
                  rows={3}
                  maxLength={5000}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
                  placeholder="Provide any URLs, screenshots, or additional context that supports your dispute."
                />
                <p className="text-xs text-slate-500 mt-1">{evidence.length}/5000 characters</p>
              </div>

              {error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
                  <p className="text-sm text-red-400">{error}</p>
                </div>
              )}

              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
                <h3 className="text-sm font-medium text-white mb-2">What happens next?</h3>
                <ul className="text-xs text-slate-400 space-y-1.5">
                  <li>1. Your dispute is submitted for review by our moderation team.</li>
                  <li>2. The finding is temporarily excluded from your score calculation while under review.</li>
                  <li>3. We'll review the finding and your evidence within 5 business days.</li>
                  <li>4. If overturned, the finding is permanently removed from your score. If upheld, it remains.</li>
                </ul>
              </div>

              <button
                type="submit"
                disabled={submitting || reason.length < 10}
                className="w-full bg-amber-500 hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed text-white py-3 rounded-xl text-sm font-medium transition flex items-center justify-center gap-2"
              >
                {submitting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Submitting...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    Submit Dispute
                  </>
                )}
              </button>
            </form>
          </>
        ) : null}
      </main>
    </div>
  );
}
