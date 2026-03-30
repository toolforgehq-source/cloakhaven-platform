import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { api, Dispute } from "@/lib/api";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import Navbar from "@/components/Navbar";
import { AlertTriangle, CheckCircle, XCircle, Clock, FileText, ExternalLink } from "lucide-react";

export default function Disputes() {
  useDocumentTitle("My Disputes — Cloak Haven");
  const { user, logout } = useAuth();
  const [disputes, setDisputes] = useState<Dispute[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getDisputes()
      .then((res) => setDisputes(res.disputes))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const navLinks = [
    { to: "/dashboard", label: "Dashboard" },
    { to: "/findings", label: "Findings" },
    { to: "/disputes", label: "Disputes" },
    { to: "/settings", label: "Settings" },
    ...(user?.is_admin ? [{ to: "/admin", label: "Admin" }] : []),
  ];

  const statusIcon = (status: string) => {
    switch (status) {
      case "pending":
        return <Clock className="w-5 h-5 text-amber-400" />;
      case "overturned":
        return <CheckCircle className="w-5 h-5 text-emerald-400" />;
      case "upheld":
        return <XCircle className="w-5 h-5 text-red-400" />;
      default:
        return <Clock className="w-5 h-5 text-slate-400" />;
    }
  };

  const statusLabel = (status: string) => {
    const styles: Record<string, string> = {
      pending: "bg-amber-500/20 text-amber-400",
      overturned: "bg-emerald-500/20 text-emerald-400",
      upheld: "bg-red-500/20 text-red-400",
    };
    return (
      <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${styles[status] ?? "bg-slate-700 text-slate-300"}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <Navbar
        links={navLinks}
        rightContent={<button onClick={logout} className="text-sm text-slate-400 hover:text-white transition">Logout</button>}
      />
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">My Disputes</h1>
            <p className="text-sm text-slate-400 mt-1">Track the status of your disputed findings</p>
          </div>
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
            <h3 className="text-lg font-semibold mb-2">No disputes yet</h3>
            <p className="text-slate-400 text-sm mb-6">
              If you disagree with a finding, you can submit a dispute from the finding detail page.
            </p>
            <Link
              to="/findings"
              className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-medium transition"
            >
              <ExternalLink className="w-4 h-4" /> View Findings
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {disputes.map((d) => (
              <div key={d.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition">
                <div className="flex items-start gap-4">
                  <div className="mt-0.5 shrink-0">
                    {statusIcon(d.status)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-2">
                      {statusLabel(d.status)}
                      <span className="text-xs text-slate-500">
                        Submitted {new Date(d.submitted_at).toLocaleDateString()}
                      </span>
                    </div>

                    <p className="text-sm text-slate-300 mb-2">{d.reason}</p>

                    {d.supporting_evidence && (
                      <div className="bg-slate-800/50 rounded-lg p-3 mb-3">
                        <p className="text-xs text-slate-400 mb-1 font-medium">Evidence provided:</p>
                        <p className="text-sm text-slate-400">{d.supporting_evidence}</p>
                      </div>
                    )}

                    {d.reviewer_notes && (
                      <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-lg p-3 mb-3">
                        <p className="text-xs text-indigo-400 mb-1 font-medium">Reviewer notes:</p>
                        <p className="text-sm text-slate-300">{d.reviewer_notes}</p>
                      </div>
                    )}

                    {d.resolved_at && (
                      <p className="text-xs text-slate-500">
                        Resolved {new Date(d.resolved_at).toLocaleDateString()}
                      </p>
                    )}

                    <div className="mt-3">
                      <Link
                        to={`/findings/${d.finding_id}`}
                        className="text-sm text-indigo-400 hover:text-indigo-300 inline-flex items-center gap-1 transition"
                      >
                        View finding <ExternalLink className="w-3 h-3" />
                      </Link>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Info box */}
        <div className="mt-8 bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h3 className="font-semibold mb-2 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" /> How Disputes Work
          </h3>
          <ul className="text-sm text-slate-400 space-y-2">
            <li className="flex items-start gap-2">
              <Clock className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <span><strong className="text-slate-300">Pending:</strong> Your dispute has been submitted and is awaiting review.</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <span><strong className="text-slate-300">Overturned:</strong> The finding was removed from your score calculation.</span>
            </li>
            <li className="flex items-start gap-2">
              <XCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
              <span><strong className="text-slate-300">Upheld:</strong> The finding was reviewed and determined to be accurate.</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
