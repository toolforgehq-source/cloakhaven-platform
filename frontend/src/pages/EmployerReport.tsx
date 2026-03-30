import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { api, PublicProfile } from "@/lib/api";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import Navbar from "@/components/Navbar";
import {
  ArrowLeft, Shield, AlertTriangle, CheckCircle, XCircle,
  User, BarChart3, FileText, TrendingUp
} from "lucide-react";

interface ReportData {
  profile: PublicProfile;
  findings_summary: Record<string, number>;
  risk_level: string;
  recommendation: string;
  searched_at: string;
}

const RISK_CONFIG: Record<string, { color: string; bg: string; icon: typeof Shield; label: string }> = {
  low: { color: "text-emerald-400", bg: "bg-emerald-500/10", icon: CheckCircle, label: "Low Risk" },
  medium: { color: "text-amber-400", bg: "bg-amber-500/10", icon: AlertTriangle, label: "Medium Risk" },
  high: { color: "text-orange-400", bg: "bg-orange-500/10", icon: AlertTriangle, label: "High Risk" },
  critical: { color: "text-red-400", bg: "bg-red-500/10", icon: XCircle, label: "Critical Risk" },
  unknown: { color: "text-slate-400", bg: "bg-slate-700", icon: Shield, label: "Insufficient Data" },
};

export default function EmployerReport() {
  useDocumentTitle("Candidate Report — Cloak Haven");
  const { name } = useParams<{ name: string }>();
  const { user, logout } = useAuth();
  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!name) return;
    api.employerSearch(decodeURIComponent(name))
      .then((data) => {
        setReport({
          profile: data.profile,
          findings_summary: data.findings_summary,
          risk_level: data.risk_level,
          recommendation: data.recommendation,
          searched_at: data.searched_at,
        });
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [name]);

  const navLinks = [
    { to: "/dashboard", label: "Dashboard" },
    { to: "/employer", label: "Employer Search" },
    { to: "/settings", label: "Settings" },
    ...(user?.is_admin ? [{ to: "/admin", label: "Admin" }] : []),
  ];

  const risk = RISK_CONFIG[report?.risk_level ?? "unknown"] ?? RISK_CONFIG.unknown;
  const RiskIcon = risk.icon;

  const totalFindings = report ? Object.values(report.findings_summary).reduce((a, b) => a + b, 0) : 0;

  const categoryLabels: Record<string, string> = {
    hate_speech: "Hate Speech",
    harassment: "Harassment",
    violence: "Violence",
    substance_abuse: "Substance Abuse",
    explicit_content: "Explicit Content",
    misinformation: "Misinformation",
    professional_misconduct: "Professional Misconduct",
    positive_engagement: "Positive Engagement",
    community_leadership: "Community Leadership",
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <Navbar
        links={navLinks}
        rightContent={<button onClick={logout} className="text-sm text-slate-400 hover:text-white transition">Logout</button>}
      />
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Link to="/employer" className="flex items-center gap-1 text-sm text-slate-400 hover:text-white mb-6 transition">
          <ArrowLeft className="w-4 h-4" /> Back to Search
        </Link>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-sm text-slate-400">Generating report…</p>
            </div>
          </div>
        ) : error ? (
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6 text-center">
            <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-3" />
            <p className="text-red-400 font-medium">{error}</p>
            <Link to="/employer" className="text-indigo-400 hover:text-indigo-300 text-sm mt-3 inline-block">
              Return to Search
            </Link>
          </div>
        ) : report ? (
          <div className="space-y-6">
            {/* Header with profile */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <div className="flex flex-col sm:flex-row items-start gap-6">
                <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center shrink-0">
                  <User className="w-8 h-8 text-slate-500" />
                </div>
                <div className="flex-1">
                  <h1 className="text-2xl font-bold">{report.profile.lookup_name}</h1>
                  {report.profile.lookup_username && (
                    <p className="text-slate-400">@{report.profile.lookup_username}</p>
                  )}
                  <div className="flex items-center gap-3 mt-2">
                    {report.profile.is_claimed ? (
                      <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2.5 py-1 rounded-full">
                        Verified Profile
                      </span>
                    ) : (
                      <span className="text-xs bg-slate-700 text-slate-400 px-2.5 py-1 rounded-full">
                        Unverified
                      </span>
                    )}
                    {report.profile.score_accuracy_pct !== null && (
                      <span className="text-xs text-slate-500">
                        {report.profile.score_accuracy_pct.toFixed(0)}% data accuracy
                      </span>
                    )}
                  </div>
                </div>
                {report.profile.public_score !== null && (
                  <div className="text-center sm:text-right">
                    <p className="text-4xl font-bold" style={{ color: report.profile.score_color || "#6366F1" }}>
                      {report.profile.public_score}
                    </p>
                    <p className="text-sm" style={{ color: report.profile.score_color || "#6366F1" }}>
                      {report.profile.score_label}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Risk Assessment */}
            <div className={`${risk.bg} border border-slate-800 rounded-xl p-6`}>
              <div className="flex items-start gap-4">
                <RiskIcon className={`w-8 h-8 ${risk.color} shrink-0 mt-0.5`} />
                <div className="flex-1">
                  <h2 className={`text-xl font-bold ${risk.color}`}>{risk.label}</h2>
                  <p className="text-slate-300 mt-2">{report.recommendation}</p>
                  <p className="text-xs text-slate-500 mt-3">
                    Report generated {new Date(report.searched_at).toLocaleString()}
                  </p>
                </div>
              </div>
            </div>

            {/* Findings Breakdown */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <BarChart3 className="w-5 h-5 text-indigo-400" />
                  <h3 className="font-semibold">Findings Summary</h3>
                </div>
                <p className="text-3xl font-bold mb-1">{totalFindings}</p>
                <p className="text-sm text-slate-400">Total findings analyzed</p>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <TrendingUp className="w-5 h-5 text-indigo-400" />
                  <h3 className="font-semibold">Score Details</h3>
                </div>
                <p className="text-3xl font-bold mb-1">
                  {report.profile.public_score ?? "N/A"}
                  <span className="text-lg text-slate-400"> / 1000</span>
                </p>
                <p className="text-sm text-slate-400">Reputation score</p>
              </div>
            </div>

            {/* Category Breakdown */}
            {totalFindings > 0 && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <FileText className="w-5 h-5 text-indigo-400" />
                  <h3 className="font-semibold">Category Breakdown</h3>
                </div>
                <div className="space-y-3">
                  {Object.entries(report.findings_summary)
                    .sort(([, a], [, b]) => b - a)
                    .map(([category, count]) => {
                      const pct = totalFindings > 0 ? (count / totalFindings) * 100 : 0;
                      const isPositive = category.includes("positive") || category.includes("leadership");
                      return (
                        <div key={category}>
                          <div className="flex justify-between text-sm mb-1">
                            <span className="text-slate-300">
                              {categoryLabels[category] ?? category.replace(/_/g, " ")}
                            </span>
                            <span className={isPositive ? "text-emerald-400" : "text-slate-400"}>
                              {count}
                            </span>
                          </div>
                          <div className="w-full bg-slate-800 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full ${isPositive ? "bg-emerald-500" : "bg-indigo-500"}`}
                              style={{ width: `${Math.max(pct, 2)}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>
            )}

            {/* FCRA Disclaimer */}
            <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-5">
              <div className="flex items-start gap-3">
                <Shield className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm text-amber-300 font-medium">FCRA Compliance Disclaimer</p>
                  <p className="text-xs text-slate-400 mt-1">
                    This report is NOT a consumer report under the Fair Credit Reporting Act (FCRA).
                    Cloak Haven scores must not be used as the sole basis for employment, housing, credit,
                    or insurance decisions. This report is for informational purposes only. You agree to
                    comply with all applicable federal, state, and local laws.
                  </p>
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
