import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { api, AdminUserItem } from "@/lib/api";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import Navbar from "@/components/Navbar";
import { useToast } from "@/components/Toast";
import { Search, Shield, ShieldOff, Trash2, ChevronLeft, ChevronRight, Users, AlertTriangle } from "lucide-react";

export default function AdminUsers() {
  useDocumentTitle("Manage Users — Cloak Haven Admin");
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [users, setUsers] = useState<AdminUserItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const pageSize = 20;

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { page, page_size: pageSize };
      if (search) params.search = search;
      if (tierFilter) params.tier = tierFilter;
      const res = await api.adminGetUsers(params as { page: number; page_size: number; search?: string; tier?: string });
      setUsers(res.users);
      setTotal(res.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load users");
    } finally {
      setLoading(false);
    }
  }, [page, search, tierFilter]);

  useEffect(() => {
    if (user && !user.is_admin) {
      navigate("/dashboard");
      return;
    }
    loadUsers();
  }, [user, navigate, loadUsers]);

  const handleToggleAdmin = async (userId: string, currentlyAdmin: boolean) => {
    try {
      await api.adminSetUserAdmin(userId, !currentlyAdmin);
      toast("success", `Admin status ${currentlyAdmin ? "revoked" : "granted"}`);
      loadUsers();
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "Failed to update admin status");
    }
  };

  const handleChangeTier = async (userId: string, tier: string) => {
    try {
      await api.adminSetUserTier(userId, tier);
      toast("success", `Tier updated to ${tier}`);
      loadUsers();
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "Failed to update tier");
    }
  };

  const handleDelete = async (userId: string, email: string) => {
    if (!confirm(`Delete user ${email}? This cannot be undone.`)) return;
    try {
      await api.adminDeleteUser(userId);
      toast("success", "User deleted");
      loadUsers();
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "Failed to delete user");
    }
  };

  const totalPages = Math.ceil(total / pageSize);

  const navLinks = [
    { to: "/admin", label: "Overview" },
    { to: "/admin/users", label: "Users" },
    { to: "/admin/disputes", label: "Disputes" },
    { to: "/dashboard", label: "Back to App" },
  ];

  const tierBadge = (tier: string) => {
    const colors: Record<string, string> = {
      free: "bg-slate-700 text-slate-300",
      audit: "bg-indigo-500/20 text-indigo-400",
      subscriber: "bg-emerald-500/20 text-emerald-400",
      employer: "bg-amber-500/20 text-amber-400",
    };
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${colors[tier] ?? "bg-slate-700 text-slate-300"}`}>
        {tier}
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
              <Users className="w-6 h-6 text-indigo-400" /> User Management
            </h1>
            <p className="text-sm text-slate-400 mt-1">{total} total users</p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search by email or name…"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="w-full pl-10 pr-4 py-2.5 bg-slate-900 border border-slate-800 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>
          <select
            value={tierFilter}
            onChange={(e) => { setTierFilter(e.target.value); setPage(1); }}
            className="px-4 py-2.5 bg-slate-900 border border-slate-800 rounded-lg text-sm text-white focus:outline-none focus:border-indigo-500"
          >
            <option value="">All tiers</option>
            <option value="free">Free</option>
            <option value="audit">Audit</option>
            <option value="subscriber">Subscriber</option>
            <option value="employer">Employer</option>
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
              <p className="text-sm text-slate-400">Loading users…</p>
            </div>
          </div>
        ) : users.length === 0 ? (
          <div className="text-center py-20">
            <Users className="w-12 h-12 text-slate-600 mx-auto mb-3" />
            <p className="text-slate-400">No users found</p>
          </div>
        ) : (
          <>
            {/* Desktop table */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-800 text-left text-slate-400">
                    <th className="pb-3 font-medium">User</th>
                    <th className="pb-3 font-medium">Tier</th>
                    <th className="pb-3 font-medium">Score</th>
                    <th className="pb-3 font-medium">Findings</th>
                    <th className="pb-3 font-medium">Disputes</th>
                    <th className="pb-3 font-medium">Joined</th>
                    <th className="pb-3 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-900/50 transition">
                      <td className="py-3">
                        <div>
                          <p className="font-medium">{u.full_name || u.display_name || "—"}</p>
                          <p className="text-xs text-slate-400">{u.email}</p>
                          {u.is_admin && <span className="text-xs text-indigo-400 font-medium">Admin</span>}
                        </div>
                      </td>
                      <td className="py-3">{tierBadge(u.subscription_tier)}</td>
                      <td className="py-3">{u.overall_score ?? "—"}</td>
                      <td className="py-3">{u.findings_count}</td>
                      <td className="py-3">{u.disputes_count}</td>
                      <td className="py-3 text-slate-400">{new Date(u.created_at).toLocaleDateString()}</td>
                      <td className="py-3">
                        <div className="flex items-center justify-end gap-2">
                          <select
                            value={u.subscription_tier}
                            onChange={(e) => handleChangeTier(u.id, e.target.value)}
                            className="px-2 py-1 bg-slate-800 border border-slate-700 rounded text-xs text-white"
                          >
                            <option value="free">Free</option>
                            <option value="audit">Audit</option>
                            <option value="subscriber">Subscriber</option>
                            <option value="employer">Employer</option>
                          </select>
                          <button
                            onClick={() => handleToggleAdmin(u.id, u.is_admin)}
                            className={`p-1.5 rounded transition ${u.is_admin ? "text-indigo-400 hover:bg-indigo-500/20" : "text-slate-500 hover:bg-slate-800"}`}
                            title={u.is_admin ? "Revoke admin" : "Grant admin"}
                          >
                            {u.is_admin ? <ShieldOff className="w-4 h-4" /> : <Shield className="w-4 h-4" />}
                          </button>
                          <button
                            onClick={() => handleDelete(u.id, u.email)}
                            className="p-1.5 text-red-400 hover:bg-red-500/20 rounded transition"
                            title="Delete user"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile cards */}
            <div className="md:hidden space-y-3">
              {users.map((u) => (
                <div key={u.id} className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <p className="font-medium">{u.full_name || u.display_name || "—"}</p>
                      <p className="text-xs text-slate-400">{u.email}</p>
                      {u.is_admin && <span className="text-xs text-indigo-400 font-medium">Admin</span>}
                    </div>
                    {tierBadge(u.subscription_tier)}
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-center text-xs mb-3">
                    <div className="bg-slate-800 rounded-lg py-2">
                      <p className="font-bold text-sm">{u.overall_score ?? "—"}</p>
                      <p className="text-slate-400">Score</p>
                    </div>
                    <div className="bg-slate-800 rounded-lg py-2">
                      <p className="font-bold text-sm">{u.findings_count}</p>
                      <p className="text-slate-400">Findings</p>
                    </div>
                    <div className="bg-slate-800 rounded-lg py-2">
                      <p className="font-bold text-sm">{u.disputes_count}</p>
                      <p className="text-slate-400">Disputes</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <select
                      value={u.subscription_tier}
                      onChange={(e) => handleChangeTier(u.id, e.target.value)}
                      className="flex-1 px-2 py-1.5 bg-slate-800 border border-slate-700 rounded text-xs text-white"
                    >
                      <option value="free">Free</option>
                      <option value="audit">Audit</option>
                      <option value="subscriber">Subscriber</option>
                      <option value="employer">Employer</option>
                    </select>
                    <button
                      onClick={() => handleToggleAdmin(u.id, u.is_admin)}
                      className={`p-1.5 rounded ${u.is_admin ? "text-indigo-400 hover:bg-indigo-500/20" : "text-slate-500 hover:bg-slate-800"}`}
                    >
                      {u.is_admin ? <ShieldOff className="w-4 h-4" /> : <Shield className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={() => handleDelete(u.id, u.email)}
                      className="p-1.5 text-red-400 hover:bg-red-500/20 rounded"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-6 pt-6 border-t border-slate-800">
                <p className="text-sm text-slate-400">
                  Page {page} of {totalPages}
                </p>
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
