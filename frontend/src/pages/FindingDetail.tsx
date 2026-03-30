import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { api, Finding } from "@/lib/api";
import { ArrowLeft, ExternalLink, Flag, Calendar, Users, AlertTriangle, Shield } from "lucide-react";
import Navbar from "@/components/Navbar";

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-500/10 text-red-400 border-red-500/20",
  high: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  medium: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  positive: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  neutral: "bg-slate-700 text-slate-400 border-slate-600",
};

export default function FindingDetail() {
  const { id } = useParams<{ id: string }>();
  const { user, logout } = useAuth();
  const [finding, setFinding] = useState<Finding | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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
        ) : error || !finding ? (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
            <AlertTriangle className="w-10 h-10 text-amber-400 mx-auto mb-3" />
            <p className="text-white font-medium">{error || "Finding not found"}</p>
            <Link to="/findings" className="text-indigo-400 hover:text-indigo-300 text-sm mt-3 inline-block">
              Return to Findings
            </Link>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Header */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <div className="flex items-center gap-2 mb-3">
                <span className={`text-xs px-2 py-0.5 rounded border ${SEVERITY_COLORS[finding.severity] || SEVERITY_COLORS.neutral}`}>
                  {finding.severity}
                </span>
                <span className="text-xs text-slate-500 capitalize">{finding.source}</span>
                <span className="text-xs text-slate-600 capitalize">{finding.category.replace(/_/g, " ")}</span>
                {finding.is_juvenile_content && (
                  <span className="text-xs bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded">Juvenile - Excluded</span>
                )}
              </div>
              <h1 className="text-xl font-bold text-white mb-2">{finding.title}</h1>
              {finding.description && (
                <p className="text-sm text-slate-400">{finding.description}</p>
              )}
            </div>

            {/* Evidence */}
            {(finding.evidence_snippet || finding.evidence_url) && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h2 className="text-sm font-semibold text-white mb-3">Evidence</h2>
                {finding.evidence_snippet && (
                  <blockquote className="border-l-2 border-indigo-500 pl-4 mb-4">
                    <p className="text-sm text-slate-400 italic">"{finding.evidence_snippet}"</p>
                  </blockquote>
                )}
                {finding.evidence_url && (
                  <a
                    href={finding.evidence_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-sm text-indigo-400 hover:text-indigo-300 transition"
                  >
                    <ExternalLink className="w-4 h-4" />
                    View source
                  </a>
                )}
              </div>
            )}

            {/* Details grid */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <div className="flex items-center gap-2 mb-2">
                  <Shield className="w-4 h-4 text-indigo-400" />
                  <h3 className="text-xs text-slate-500 uppercase tracking-wider">Score Impact</h3>
                </div>
                <p className={`text-2xl font-bold ${finding.final_score_impact > 0 ? "text-emerald-400" : finding.final_score_impact < 0 ? "text-red-400" : "text-slate-400"}`}>
                  {finding.final_score_impact > 0 ? "+" : ""}{finding.final_score_impact.toFixed(1)}
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  Base: {finding.base_score_impact > 0 ? "+" : ""}{finding.base_score_impact.toFixed(1)}
                </p>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <div className="flex items-center gap-2 mb-2">
                  <Users className="w-4 h-4 text-indigo-400" />
                  <h3 className="text-xs text-slate-500 uppercase tracking-wider">Engagement</h3>
                </div>
                <p className="text-2xl font-bold text-white">
                  {finding.platform_engagement_count.toLocaleString()}
                </p>
                <p className="text-xs text-slate-500 mt-1">Total interactions</p>
              </div>

              {finding.original_date && (
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                  <div className="flex items-center gap-2 mb-2">
                    <Calendar className="w-4 h-4 text-indigo-400" />
                    <h3 className="text-xs text-slate-500 uppercase tracking-wider">Original Date</h3>
                  </div>
                  <p className="text-lg font-bold text-white">
                    {new Date(finding.original_date).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                    })}
                  </p>
                </div>
              )}

              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="w-4 h-4 text-indigo-400" />
                  <h3 className="text-xs text-slate-500 uppercase tracking-wider">Status</h3>
                </div>
                {finding.is_disputed ? (
                  <div>
                    <span className={`text-sm font-medium ${
                      finding.dispute_status === "overturned" ? "text-emerald-400" :
                      finding.dispute_status === "upheld" ? "text-red-400" :
                      "text-amber-400"
                    }`}>
                      {finding.dispute_status === "overturned" ? "Dispute Won" :
                       finding.dispute_status === "upheld" ? "Dispute Denied" :
                       "Dispute Pending"}
                    </span>
                  </div>
                ) : (
                  <p className="text-sm font-medium text-white">Active</p>
                )}
              </div>
            </div>

            {/* Dispute action */}
            {!finding.is_disputed && finding.final_score_impact < 0 && (
              <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-sm font-medium text-amber-300 mb-1">Think this is wrong?</h3>
                    <p className="text-xs text-slate-400">
                      If this finding is inaccurate or taken out of context, you can dispute it.
                      Disputed findings are temporarily excluded from your score while under review.
                    </p>
                  </div>
                  <Link
                    to={`/findings/${finding.id}/dispute`}
                    className="shrink-0 ml-4 bg-amber-500 hover:bg-amber-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition flex items-center gap-1"
                  >
                    <Flag className="w-3.5 h-3.5" />
                    Dispute
                  </Link>
                </div>
              </div>
            )}

            {/* Found date */}
            <p className="text-xs text-slate-600 text-center">
              Discovered {new Date(finding.created_at).toLocaleDateString("en-US", {
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
