import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { api, Finding } from "@/lib/api";
import { AlertTriangle, Filter, ChevronLeft, ChevronRight, ExternalLink, Flag, Shield } from "lucide-react";
import Navbar from "@/components/Navbar";

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-500/10 text-red-400 border-red-500/20",
  high: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  medium: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  positive: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  neutral: "bg-slate-700 text-slate-400 border-slate-600",
};

export default function Findings() {
  const { user, logout } = useAuth();
  const [findings, setFindings] = useState<Finding[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [filterSource, setFilterSource] = useState<string>("");
  const [filterSeverity, setFilterSeverity] = useState<string>("");
  const pageSize = 20;

  useEffect(() => {
    loadFindings();
  }, [page, filterSource, filterSeverity]);

  const loadFindings = async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { page, page_size: pageSize };
      if (filterSource) params.source = filterSource;
      if (filterSeverity) params.severity = filterSeverity;
      const data = await api.getFindings(params);
      setFindings(data.findings);
      setTotal(data.total);
    } catch {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  const totalPages = Math.ceil(total / pageSize);

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

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <AlertTriangle className="w-6 h-6 text-amber-400" />
            Findings ({total})
          </h1>
          <div className="flex items-center gap-3">
            <Filter className="w-4 h-4 text-slate-400" />
            <select
              value={filterSource}
              onChange={(e) => { setFilterSource(e.target.value); setPage(1); }}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All Sources</option>
              <option value="twitter">Twitter</option>
              <option value="google">Google</option>
              <option value="instagram">Instagram</option>
              <option value="tiktok">TikTok</option>
              <option value="facebook">Facebook</option>
              <option value="linkedin">LinkedIn</option>
            </select>
            <select
              value={filterSeverity}
              onChange={(e) => { setFilterSeverity(e.target.value); setPage(1); }}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All Severity</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="positive">Positive</option>
            </select>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-20 text-slate-400">Loading findings...</div>
        ) : findings.length === 0 ? (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
            <Shield className="w-12 h-12 text-indigo-400 mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-white mb-2">No Findings</h2>
            <p className="text-sm text-slate-400">Start an audit from your dashboard to discover findings.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {findings.map((f) => (
              <div key={f.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`text-xs px-2 py-0.5 rounded border ${SEVERITY_COLORS[f.severity] || SEVERITY_COLORS.neutral}`}>
                        {f.severity}
                      </span>
                      <span className="text-xs text-slate-500 capitalize">{f.source}</span>
                      <span className="text-xs text-slate-600">{f.category.replace(/_/g, " ")}</span>
                      {f.is_juvenile_content && (
                        <span className="text-xs bg-blue-500/10 text-blue-400 px-1.5 py-0.5 rounded">Juvenile - Excluded</span>
                      )}
                    </div>
                    <h3 className="text-sm font-medium text-white mb-1">{f.title}</h3>
                    {f.description && <p className="text-xs text-slate-400 line-clamp-2">{f.description}</p>}
                    {f.evidence_snippet && (
                      <p className="text-xs text-slate-500 mt-2 italic line-clamp-2">"{f.evidence_snippet}"</p>
                    )}
                    <div className="flex items-center gap-4 mt-3">
                      <span className={`text-xs font-medium ${f.final_score_impact > 0 ? "text-emerald-400" : f.final_score_impact < 0 ? "text-red-400" : "text-slate-500"}`}>
                        Impact: {f.final_score_impact > 0 ? "+" : ""}{f.final_score_impact.toFixed(1)}
                      </span>
                      {f.platform_engagement_count > 0 && (
                        <span className="text-xs text-slate-500">{f.platform_engagement_count.toLocaleString()} engagements</span>
                      )}
                      {f.original_date && (
                        <span className="text-xs text-slate-500">{new Date(f.original_date).toLocaleDateString()}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-4 shrink-0">
                    {f.evidence_url && (
                      <a href={f.evidence_url} target="_blank" rel="noopener noreferrer"
                        className="text-slate-500 hover:text-slate-300 transition">
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                    {!f.is_disputed && f.final_score_impact < 0 && (
                      <Link to={`/findings/${f.id}/dispute`}
                        className="text-xs text-amber-400 hover:text-amber-300 flex items-center gap-1">
                        <Flag className="w-3 h-3" /> Dispute
                      </Link>
                    )}
                    {f.is_disputed && (
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        f.dispute_status === "overturned" ? "bg-emerald-500/10 text-emerald-400" :
                        f.dispute_status === "upheld" ? "bg-red-500/10 text-red-400" :
                        "bg-amber-500/10 text-amber-400"
                      }`}>
                        {f.dispute_status || "Pending"}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-4 mt-8">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="flex items-center gap-1 text-sm text-slate-400 hover:text-white disabled:opacity-50 disabled:hover:text-slate-400 transition"
            >
              <ChevronLeft className="w-4 h-4" /> Previous
            </button>
            <span className="text-sm text-slate-500">Page {page} of {totalPages}</span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="flex items-center gap-1 text-sm text-slate-400 hover:text-white disabled:opacity-50 disabled:hover:text-slate-400 transition"
            >
              Next <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
