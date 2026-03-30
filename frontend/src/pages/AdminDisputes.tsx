import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { api, AdminDisputeItem } from "@/lib/api";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import Navbar from "@/components/Navbar";
import { useToast } from "@/components/Toast";
import { AlertTriangle, CheckCircle, XCircle, ChevronLeft, ChevronRight, FileText } from "lucide-react";

export default function AdminDisputes() {
  useDocumentTitle("Review Disputes — Cloak Haven Admin");
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [disputes, setDisputes] = useState<AdminDisputeItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [resolving, setResolving] = useState<string | null>(null);
  const [reviewerNotes, setReviewerNotes] = useState<Record<string, string>>({});

  const pageSize = 20;

  const loadDisputes = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { page, page_size: pageSize };
      if (statusFilter) params.status = statusFilter;
      const res = await api.adminGetDisputes(params as { page: number; page_size: number; status?: string });
      setDisputes(res.disputes);
      setTotal(res.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load disputes");
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter]);

  useEffect(() => {
    if (user && !user.is_admin) {
      navigate("/dashboard");
      return;
    }
    loadDisputes();
  }, [user, navigate, loadDisputes]);

  const handleResolve = async (disputeId: string, resolution: "overturned" | "upheld") => {
    setResolving(disputeId);
    try {
      await api.adminResolveDispute(disputeId, {
        resolution,
        reviewer_notes: reviewerNotes[disputeId] || undefined,
      });
      toast("success", `Dispute ${resolution}`);
      loadDisputes();
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "Failed to resolve dispute");
    } finally {
      setResolving(null);
    }
  };

  const totalPages = Math.ceil(total / pageSize);

  const navLinks = [
    { to: "/admin", label: "Overview" },
    { to: "/admin/users", label: "Users" },
    { to: "/admin/disputes", label: "Disputes" },
    { to: "/dashboard", label: "Back to App" },
  ];

  const statusBadge = (status: string) => {
    const styles: Record<string, string> = {
      pending: "bg-amber-500/20 text-amber-400",
      overturned: "bg-emerald-500/20 text-emerald-400",
      upheld: "bg-red-500/20 text-red-400",
    };
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${styles[status] ?? "bg-slate-700 text-slate-300"}`}>
        {status}
      </span>
    );
  };

  const severityBadge = (severity: string) => {
    const styles: Record<string, string> = {
      critical: "bg-red-500/20 text-red-400",
      high: "bg-orange-500/20 text-orange-400",
      medium: "bg-amber-500/20 text-amber-400",
      positive: "bg-emerald-500/20 text-emerald-400",
    };
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${styles[severity] ?? "bg-slate-700 text-slate-300"}`}>
        {severity}
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <Navbar links={navLinks} rightContent={<button onClick={logout} className="text-sm text-slate-400 hover:text-white transition">Logout</button>} />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <AlertTriangle className="w-6 h-6 text-orange-400" /> Dispute Review
            </h1>
            <p className="text-sm text-slate-400 mt-1">{total} total disputes</p>
          </div>
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="px-4 py-2.5 bg-slate-900 border border-slate-800 rounded-lg text-sm text-white focus:outline-none focus:border-indigo-500"
          >
            <option value="">All statuses</option>
            <option value="pending">Pending</option>
            <option value="overturned">Overturned</option>
            <option value="upheld">Upheld</option>
          </select>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 mb-6 flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-sm text-slate-400">Loading disputes…</p>
            </div>
          </div>
        ) : disputes.length === 0 ? (
          <div className="text-center py-20">
            <FileText className="w-12 h-12 text-slate-600 mx-auto mb-3" />
            <p className="text-slate-400">No disputes found</p>
            <p className="text-sm text-slate-500 mt-1">All clear!</p>
          </div>
        ) : (
          <>
            <div className="space-y-4">
              {disputes.map((d) => (
                <div key={d.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                  <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <h3 className="font-semibold truncate">{d.finding_title}</h3>
                        {statusBadge(d.status)}
                        {severityBadge(d.finding_severity)}
                      </div>
                      <p className="text-sm text-slate-400">
                        by {d.user_name || d.user_email} · {new Date(d.submitted_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>

                  <div className="bg-slate-800/50 rounded-lg p-4 mb-4">
                    <p className="text-sm font-medium text-slate-300 mb-1">Reason for dispute:</p>
                    <p className="text-sm text-slate-400">{d.reason}</p>
                    {d.supporting_evidence && (
                      <>
                        <p className="text-sm font-medium text-slate-300 mt-3 mb-1">Supporting evidence:</p>
                        <p className="text-sm text-slate-400">{d.supporting_evidence}</p>
                      </>
                    )}
                  </div>

                  {d.status === "pending" ? (
                    <div>
                      <textarea
                        placeholder="Reviewer notes (optional)…"
                        value={reviewerNotes[d.id] ?? ""}
                        onChange={(e) => setReviewerNotes((prev) => ({ ...prev, [d.id]: e.target.value }))}
                        className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none mb-3"
                        rows={2}
                      />
                      <div className="flex gap-3">
                        <button
                          onClick={() => handleResolve(d.id, "overturned")}
                          disabled={resolving === d.id}
                          className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 rounded-lg text-sm font-medium transition disabled:opacity-50"
                        >
                          <CheckCircle className="w-4 h-4" /> Overturn (Remove Finding)
                        </button>
                        <button
                          onClick={() => handleResolve(d.id, "upheld")}
                          disabled={resolving === d.id}
                          className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm font-medium transition disabled:opacity-50"
                        >
                          <XCircle className="w-4 h-4" /> Uphold (Keep Finding)
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-sm">
                      {d.status === "overturned" ? (
                        <CheckCircle className="w-4 h-4 text-emerald-400" />
                      ) : (
                        <XCircle className="w-4 h-4 text-red-400" />
                      )}
                      <span className="text-slate-400">
                        Resolved {d.resolved_at ? new Date(d.resolved_at).toLocaleDateString() : ""}
                      </span>
                      {d.reviewer_notes && (
                        <span className="text-slate-500">— {d.reviewer_notes}</span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-6 pt-6 border-t border-slate-800">
                <p className="text-sm text-slate-400">Page {page} of {totalPages}</p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page === 1}
                    className="p-2 bg-slate-900 border border-slate-800 rounded-lg hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setPage(Math.min(totalPages, page + 1))}
                    disabled={page === totalPages}
                    className="p-2 bg-slate-900 border border-slate-800 rounded-lg hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
