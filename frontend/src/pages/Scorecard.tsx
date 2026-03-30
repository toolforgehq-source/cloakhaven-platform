import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { api, Scorecard as ScorecardData } from "@/lib/api";
import { Shield, Copy, Check, ExternalLink } from "lucide-react";

export default function ScorecardPage() {
  const { userId } = useParams<{ userId: string }>();
  const [scorecard, setScorecard] = useState<ScorecardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!userId) return;
    loadScorecard();
  }, [userId]);

  const loadScorecard = async () => {
    setLoading(true);
    try {
      const data = await api.getScorecard(userId!);
      setScorecard(data);
    } catch {
      setError("Scorecard not available. The user may have a private profile or no score yet.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <PageShell>
        <div className="flex items-center justify-center h-96">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </PageShell>
    );
  }

  if (error || !scorecard) {
    return (
      <PageShell>
        <div className="max-w-lg mx-auto bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
          <Shield className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">Scorecard Unavailable</h2>
          <p className="text-slate-400 mb-6">{error}</p>
          <Link to="/search" className="text-indigo-400 hover:text-indigo-300 text-sm">
            Search for someone
          </Link>
        </div>
      </PageShell>
    );
  }

  return (
    <PageShell>
      <div className="max-w-lg mx-auto">
        {/* Card */}
        <div className="bg-gradient-to-br from-slate-900 via-slate-900 to-indigo-950 border border-slate-700 rounded-2xl overflow-hidden shadow-2xl">
          {/* Header */}
          <div className="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-white/20 flex items-center justify-center font-bold text-xs text-white">CH</div>
              <span className="text-white font-semibold text-sm">Cloak Haven</span>
            </div>
            <span className="text-white/70 text-xs">Digital Reputation Scorecard</span>
          </div>

          {/* Body */}
          <div className="p-6">
            {/* Name + Score */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-xl font-bold text-white">{scorecard.display_name}</h1>
                <div className="flex items-center gap-2 mt-1">
                  {scorecard.is_verified ? (
                    <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                      Verified
                    </span>
                  ) : (
                    <span className="text-xs bg-slate-700 text-slate-400 px-2 py-0.5 rounded-full">
                      Unverified
                    </span>
                  )}
                  <span className="text-xs text-slate-500">
                    {scorecard.score_accuracy_pct.toFixed(0)}% accuracy
                  </span>
                </div>
              </div>
              <div className="text-center">
                <div
                  className="w-20 h-20 rounded-full border-4 flex items-center justify-center"
                  style={{ borderColor: scorecard.score_color }}
                >
                  <span className="text-2xl font-bold text-white">{scorecard.overall_score}</span>
                </div>
                <p className="text-xs font-medium mt-1" style={{ color: scorecard.score_color }}>
                  {scorecard.score_label}
                </p>
              </div>
            </div>

            {/* Breakdown */}
            <div className="space-y-3 mb-6">
              <ScoreBar label="Social Media" score={scorecard.social_media_score} weight="40%" />
              <ScoreBar label="Web Presence" score={scorecard.web_presence_score} weight="35%" />
              <ScoreBar label="Behavior" score={scorecard.posting_behavior_score} weight="25%" />
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-3 mb-6">
              <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                <p className="text-lg font-bold text-white">{scorecard.total_findings}</p>
                <p className="text-xs text-slate-400">Findings</p>
              </div>
              <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                <p className="text-lg font-bold text-white">{scorecard.platforms_analyzed.length}</p>
                <p className="text-xs text-slate-400">Platforms</p>
              </div>
              <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                <p className="text-lg font-bold text-white">
                  {scorecard.score_accuracy_pct >= 90 ? "High" : scorecard.score_accuracy_pct >= 50 ? "Med" : "Low"}
                </p>
                <p className="text-xs text-slate-400">Confidence</p>
              </div>
            </div>

            {/* Category breakdown */}
            {Object.keys(scorecard.category_breakdown).length > 0 && (
              <div className="mb-6">
                <h3 className="text-xs text-slate-500 uppercase tracking-wider mb-2">Findings by Category</h3>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(scorecard.category_breakdown).map(([cat, count]) => (
                    <div key={cat} className="flex items-center justify-between bg-slate-800/30 rounded px-3 py-1.5">
                      <span className="text-xs text-slate-400 capitalize">{cat.replace(/_/g, " ")}</span>
                      <span className="text-xs font-medium text-white">{count as number}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Timestamp */}
            <div className="text-center border-t border-slate-800 pt-4">
              <p className="text-xs text-slate-500">
                Score calculated {new Date(scorecard.calculated_at).toLocaleDateString("en-US", {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}
              </p>
            </div>
          </div>

          {/* FCRA Footer */}
          <div className="px-6 py-3 bg-slate-900/80 border-t border-slate-800">
            <p className="text-[10px] text-slate-500 text-center">
              This scorecard is for informational purposes only and is not a consumer report under the FCRA.
              It should not be used as the sole basis for employment, housing, credit, or insurance decisions.
            </p>
          </div>
        </div>

        {/* Share actions */}
        <div className="flex gap-3 mt-6">
          <button
            onClick={handleCopyLink}
            className="flex-1 bg-slate-800 hover:bg-slate-700 text-white py-2.5 rounded-xl text-sm font-medium transition flex items-center justify-center gap-2"
          >
            {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
            {copied ? "Copied!" : "Copy Link"}
          </button>
          <Link
            to="/search"
            className="flex-1 bg-indigo-500 hover:bg-indigo-600 text-white py-2.5 rounded-xl text-sm font-medium transition flex items-center justify-center gap-2"
          >
            <ExternalLink className="w-4 h-4" />
            Search More
          </Link>
        </div>
      </div>
    </PageShell>
  );
}

function ScoreBar({ label, score, weight }: { label: string; score: number; weight: string }) {
  const pct = (score / 1000) * 100;
  let color = "#10B981";
  if (score < 500) color = "#EF4444";
  else if (score < 700) color = "#EAB308";
  else if (score < 800) color = "#84CC16";

  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-slate-400">{label} <span className="text-slate-600">({weight})</span></span>
        <span className="text-white font-medium">{score}</span>
      </div>
      <div className="w-full bg-slate-800 rounded-full h-1.5">
        <div className="h-1.5 rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}

function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-950">
      <nav className="border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center font-bold text-sm text-white">CH</div>
            <span className="text-lg font-semibold text-white">Cloak Haven</span>
          </Link>
          <div className="flex items-center gap-6">
            <Link to="/search" className="text-sm text-slate-400 hover:text-white transition">Search</Link>
            <Link to="/login" className="text-sm text-slate-400 hover:text-white transition">Log in</Link>
            <Link to="/register" className="bg-indigo-500 hover:bg-indigo-600 text-white text-sm px-4 py-2 rounded-lg transition font-medium">
              Get Your Score
            </Link>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  );
}
