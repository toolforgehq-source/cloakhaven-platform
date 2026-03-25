import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { api, ScoreData, Finding, SocialAccount } from "@/lib/api";
import {
  Shield, AlertTriangle, TrendingUp, Upload,
  Twitter, Instagram, Facebook, Linkedin, BarChart3,
  ChevronRight, RefreshCw, Share2
} from "lucide-react";

function ScoreGauge({ score, color, label }: { score: number; color: string; label: string }) {
  const pct = (score / 1000) * 100;
  return (
    <div className="text-center">
      <div className="relative w-40 h-40 mx-auto">
        <svg className="w-40 h-40 -rotate-90" viewBox="0 0 120 120">
          <circle cx="60" cy="60" r="52" fill="none" stroke="#1E293B" strokeWidth="10" />
          <circle
            cx="60" cy="60" r="52" fill="none"
            stroke={color} strokeWidth="10" strokeLinecap="round"
            strokeDasharray={`${pct * 3.267} 326.7`}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-4xl font-bold text-white">{score}</span>
          <span className="text-sm font-medium" style={{ color }}>{label}</span>
        </div>
      </div>
    </div>
  );
}

function ComponentBar({ label, score, weight }: { label: string; score: number; weight: string }) {
  const pct = (score / 1000) * 100;
  let color = "#10B981";
  if (score < 500) color = "#EF4444";
  else if (score < 700) color = "#EAB308";
  else if (score < 800) color = "#84CC16";

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-slate-400">{label} <span className="text-slate-600">({weight})</span></span>
        <span className="text-white font-medium">{score}</span>
      </div>
      <div className="w-full bg-slate-800 rounded-full h-2">
        <div className="h-2 rounded-full transition-all duration-500" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}

const PLATFORM_ICONS: Record<string, typeof Twitter> = {
  twitter: Twitter,
  instagram: Instagram,
  facebook: Facebook,
  linkedin: Linkedin,
};

export default function Dashboard() {
  const { user, logout } = useAuth();
  const [score, setScore] = useState<ScoreData | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [auditing, setAuditing] = useState(false);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const [scoreData, findingsData, accountsData] = await Promise.allSettled([
        api.getScore(),
        api.getFindings({ page_size: 5 }),
        api.getAccounts(),
      ]);

      if (scoreData.status === "fulfilled") setScore(scoreData.value);
      if (findingsData.status === "fulfilled") setFindings(findingsData.value.findings);
      if (accountsData.status === "fulfilled") setAccounts(accountsData.value.accounts);
    } catch {
      // Silently handle — user may not have a score yet
    } finally {
      setLoading(false);
    }
  };

  const handleStartAudit = async () => {
    setAuditing(true);
    try {
      await api.startAudit();
      await loadDashboard();
    } catch {
      // Handle error
    } finally {
      setAuditing(false);
    }
  };

  if (loading) {
    return (
      <DashboardShell user={user} logout={logout}>
        <div className="flex items-center justify-center h-96">
          <RefreshCw className="w-6 h-6 text-indigo-400 animate-spin" />
        </div>
      </DashboardShell>
    );
  }

  return (
    <DashboardShell user={user} logout={logout}>
      {/* Score Section */}
      {score ? (
        <div className="grid lg:grid-cols-3 gap-6 mb-8">
          {/* Main Score */}
          <div className="lg:col-span-1 bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-white flex items-center gap-2">
                <Shield className="w-5 h-5 text-indigo-400" />
                Your Score
              </h2>
              {score.is_verified && (
                <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                  Verified
                </span>
              )}
            </div>
            <ScoreGauge score={score.overall_score} color={score.score_color} label={score.score_label} />
            <div className="mt-4 text-center">
              <p className="text-xs text-slate-500">
                Accuracy: {score.score_accuracy_pct.toFixed(0)}% — Connect more platforms to improve
              </p>
            </div>
            <div className="mt-4 flex gap-2">
              <button
                onClick={handleStartAudit}
                disabled={auditing}
                className="flex-1 bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white py-2 rounded-lg text-sm font-medium transition flex items-center justify-center gap-1"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${auditing ? "animate-spin" : ""}`} />
                {auditing ? "Scanning..." : "Re-scan"}
              </button>
              <Link
                to={`/scorecard/${user?.id}`}
                className="flex-1 bg-slate-800 hover:bg-slate-700 text-white py-2 rounded-lg text-sm font-medium transition flex items-center justify-center gap-1"
              >
                <Share2 className="w-3.5 h-3.5" /> Share
              </Link>
            </div>
          </div>

          {/* Components */}
          <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="font-semibold text-white mb-6 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-indigo-400" />
              Score Breakdown
            </h2>
            <div className="space-y-5">
              <ComponentBar label="Social Media" score={score.social_media_score} weight="40%" />
              <ComponentBar label="Web Presence" score={score.web_presence_score} weight="35%" />
              <ComponentBar label="Posting Behavior" score={score.posting_behavior_score} weight="25%" />
            </div>
            <div className="mt-6 pt-6 border-t border-slate-800 grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-2xl font-bold text-white">
                  {score.score_breakdown.categories ? Object.keys(score.score_breakdown.categories).length : 0}
                </p>
                <p className="text-xs text-slate-400">Categories</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{score.score_breakdown.juvenile_exclusions}</p>
                <p className="text-xs text-slate-400">Juvenile Excluded</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{score.score_breakdown.disputed_exclusions}</p>
                <p className="text-xs text-slate-400">Disputes Won</p>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center mb-8">
          <Shield className="w-12 h-12 text-indigo-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">No Score Yet</h2>
          <p className="text-slate-400 mb-6 max-w-md mx-auto">
            Connect your social accounts or upload your data to get your reputation score.
          </p>
          <button
            onClick={handleStartAudit}
            disabled={auditing}
            className="bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition"
          >
            {auditing ? "Starting audit..." : "Start Your Audit"}
          </button>
        </div>
      )}

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Recent Findings */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
              Recent Findings
            </h2>
            <Link to="/findings" className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1">
              View all <ChevronRight className="w-3 h-3" />
            </Link>
          </div>
          {findings.length === 0 ? (
            <p className="text-sm text-slate-500 py-8 text-center">No findings yet. Start an audit to scan your presence.</p>
          ) : (
            <div className="space-y-3">
              {findings.map((f) => (
                <Link
                  key={f.id}
                  to={`/findings/${f.id}`}
                  className="block bg-slate-800/50 rounded-lg p-3 hover:bg-slate-800 transition"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white font-medium truncate">{f.title}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          f.severity === "critical" ? "bg-red-500/10 text-red-400" :
                          f.severity === "high" ? "bg-orange-500/10 text-orange-400" :
                          f.severity === "medium" ? "bg-yellow-500/10 text-yellow-400" :
                          f.severity === "positive" ? "bg-emerald-500/10 text-emerald-400" :
                          "bg-slate-700 text-slate-400"
                        }`}>
                          {f.severity}
                        </span>
                        <span className="text-xs text-slate-500">{f.source}</span>
                        <span className="text-xs text-slate-600">
                          {f.final_score_impact > 0 ? "+" : ""}{f.final_score_impact.toFixed(1)}
                        </span>
                      </div>
                    </div>
                    {f.is_disputed && (
                      <span className="text-xs bg-amber-500/10 text-amber-400 px-1.5 py-0.5 rounded ml-2 shrink-0">
                        Disputed
                      </span>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Connected Accounts */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-emerald-400" />
              Connected Platforms
            </h2>
            <Link to="/settings" className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1">
              Manage <ChevronRight className="w-3 h-3" />
            </Link>
          </div>
          <div className="space-y-3">
            {(["twitter", "instagram", "facebook", "linkedin", "tiktok"] as const).map((platform) => {
              const connected = accounts.find((a) => a.platform === platform);
              const Icon = PLATFORM_ICONS[platform] || Upload;
              return (
                <div key={platform} className="flex items-center justify-between bg-slate-800/50 rounded-lg p-3">
                  <div className="flex items-center gap-3">
                    <Icon className="w-5 h-5 text-slate-400" />
                    <div>
                      <p className="text-sm text-white capitalize">{platform === "twitter" ? "X / Twitter" : platform}</p>
                      {connected && (
                        <p className="text-xs text-slate-500">
                          {connected.connection_type === "api" ? "API Connected" : "Data Uploaded"}
                          {connected.last_scan_at && ` · Last scan ${new Date(connected.last_scan_at).toLocaleDateString()}`}
                        </p>
                      )}
                    </div>
                  </div>
                  {connected ? (
                    <span className="text-xs bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full">Connected</span>
                  ) : (
                    <Link to="/settings" className="text-xs text-indigo-400 hover:text-indigo-300">Connect</Link>
                  )}
                </div>
              );
            })}
          </div>
          <div className="mt-4 pt-4 border-t border-slate-800">
            <Link
              to="/settings"
              className="flex items-center justify-center gap-2 bg-slate-800 hover:bg-slate-700 text-white py-2 rounded-lg text-sm transition"
            >
              <Upload className="w-4 h-4" /> Upload Data Archive
            </Link>
          </div>
        </div>
      </div>
    </DashboardShell>
  );
}

function DashboardShell({ children, user, logout }: { children: React.ReactNode; user: { email?: string } | null; logout: () => void }) {
  return (
    <div className="min-h-screen bg-slate-950">
      <nav className="border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link to="/dashboard" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center font-bold text-sm text-white">CH</div>
            <span className="text-lg font-semibold text-white">Cloak Haven</span>
          </Link>
          <div className="flex items-center gap-6">
            <Link to="/dashboard" className="text-sm text-white font-medium">Dashboard</Link>
            <Link to="/findings" className="text-sm text-slate-400 hover:text-white transition">Findings</Link>
            <Link to="/search" className="text-sm text-slate-400 hover:text-white transition">Search</Link>
            <Link to="/settings" className="text-sm text-slate-400 hover:text-white transition">Settings</Link>
            <div className="flex items-center gap-3 pl-4 border-l border-slate-800">
              <span className="text-sm text-slate-400">{user?.email}</span>
              <button onClick={logout} className="text-sm text-red-400 hover:text-red-300">Sign out</button>
            </div>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  );
}
