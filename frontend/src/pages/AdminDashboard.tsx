import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { api, AdminStats } from "@/lib/api";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import Navbar from "@/components/Navbar";
import { Users, FileText, AlertTriangle, Activity, Shield, TrendingUp, Clock, BarChart3 } from "lucide-react";

export default function AdminDashboard() {
  useDocumentTitle("Admin Dashboard — Cloak Haven");
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (user && !user.is_admin) {
      navigate("/dashboard");
      return;
    }
    api.adminGetStats()
      .then(setStats)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [user, navigate]);

  const navLinks = [
    { to: "/admin", label: "Overview" },
    { to: "/admin/users", label: "Users" },
    { to: "/admin/disputes", label: "Disputes" },
    { to: "/dashboard", label: "Back to App" },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-white">
        <Navbar links={navLinks} rightContent={<button onClick={logout} className="text-sm text-slate-400 hover:text-white transition">Logout</button>} />
        <div className="flex items-center justify-center py-32">
          <div className="text-center">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm text-slate-400">Loading admin dashboard…</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-950 text-white">
        <Navbar links={navLinks} rightContent={<button onClick={logout} className="text-sm text-slate-400 hover:text-white transition">Logout</button>} />
        <div className="max-w-4xl mx-auto px-4 py-16">
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6 text-center">
            <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-3" />
            <p className="text-red-400 font-medium">{error}</p>
            <p className="text-sm text-slate-400 mt-2">You may not have admin access.</p>
          </div>
        </div>
      </div>
    );
  }

  const statCards = [
    { label: "Total Users", value: stats?.total_users ?? 0, icon: Users, color: "text-indigo-400", bg: "bg-indigo-500/10" },
    { label: "Verified Users", value: stats?.verified_users ?? 0, icon: Shield, color: "text-emerald-400", bg: "bg-emerald-500/10" },
    { label: "Paying Users", value: stats?.paying_users ?? 0, icon: TrendingUp, color: "text-amber-400", bg: "bg-amber-500/10" },
    { label: "New Today", value: stats?.users_today ?? 0, icon: Clock, color: "text-sky-400", bg: "bg-sky-500/10" },
    { label: "Total Findings", value: stats?.total_findings ?? 0, icon: FileText, color: "text-purple-400", bg: "bg-purple-500/10" },
    { label: "Total Disputes", value: stats?.total_disputes ?? 0, icon: AlertTriangle, color: "text-orange-400", bg: "bg-orange-500/10" },
    { label: "Pending Disputes", value: stats?.pending_disputes ?? 0, icon: Activity, color: "text-red-400", bg: "bg-red-500/10" },
    { label: "Avg Score", value: stats?.avg_score ?? 0, icon: BarChart3, color: "text-teal-400", bg: "bg-teal-500/10" },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <Navbar links={navLinks} rightContent={<button onClick={logout} className="text-sm text-slate-400 hover:text-white transition">Logout</button>} />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold">Admin Dashboard</h1>
          <p className="text-slate-400 mt-1">Platform overview and management</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
          {statCards.map((card) => (
            <div key={card.label} className="bg-slate-900 border border-slate-800 rounded-xl p-4 sm:p-5">
              <div className="flex items-center gap-3 mb-3">
                <div className={`w-10 h-10 rounded-lg ${card.bg} flex items-center justify-center`}>
                  <card.icon className={`w-5 h-5 ${card.color}`} />
                </div>
              </div>
              <p className="text-2xl sm:text-3xl font-bold">{card.value}</p>
              <p className="text-xs sm:text-sm text-slate-400 mt-1">{card.label}</p>
            </div>
          ))}
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Link
            to="/admin/users"
            className="bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-indigo-500/50 transition group"
          >
            <Users className="w-8 h-8 text-indigo-400 mb-3" />
            <h3 className="font-semibold group-hover:text-indigo-400 transition">Manage Users</h3>
            <p className="text-sm text-slate-400 mt-1">View, edit, and manage all user accounts</p>
          </Link>

          <Link
            to="/admin/disputes"
            className="bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-orange-500/50 transition group"
          >
            <AlertTriangle className="w-8 h-8 text-orange-400 mb-3" />
            <h3 className="font-semibold group-hover:text-orange-400 transition">Review Disputes</h3>
            <p className="text-sm text-slate-400 mt-1">
              {(stats?.pending_disputes ?? 0) > 0
                ? `${stats?.pending_disputes} pending dispute${stats?.pending_disputes === 1 ? "" : "s"} to review`
                : "No pending disputes"}
            </p>
          </Link>

          <Link
            to="/dashboard"
            className="bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-emerald-500/50 transition group"
          >
            <Activity className="w-8 h-8 text-emerald-400 mb-3" />
            <h3 className="font-semibold group-hover:text-emerald-400 transition">Your Dashboard</h3>
            <p className="text-sm text-slate-400 mt-1">Switch back to the main application</p>
          </Link>
        </div>
      </div>
    </div>
  );
}
