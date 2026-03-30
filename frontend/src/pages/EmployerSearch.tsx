import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { api, PublicProfile, EmployerSearchHistoryItem } from "@/lib/api";
import { Search, Building2, User, Shield, Lock, Clock } from "lucide-react";
import Navbar from "@/components/Navbar";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

export default function EmployerSearch() {
  useDocumentTitle("Employer Search");
  const { user, logout } = useAuth();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PublicProfile[]>([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<EmployerSearchHistoryItem[]>([]);

  const isEmployer = user?.subscription_tier === "employer";

  useEffect(() => {
    if (isEmployer) loadHistory();
  }, [isEmployer]);

  const loadHistory = async () => {
    try {
      const data = await api.getEmployerSearchHistory();
      setHistory(data.searches);
    } catch {
      // Silently ignore — history is non-critical
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isEmployer || query.length < 2) return;
    setLoading(true);
    try {
      const data = await api.employerSearch(query);
      setResults(data.results);
      setSearched(true);
    } catch {
      setResults([]);
      setSearched(true);
    } finally {
      setLoading(false);
    }
  };

  const navLinks = [
    { to: "/dashboard", label: "Dashboard" },
    { to: "/employer", label: "Employer Search" },
    { to: "/disputes", label: "Disputes" },
    { to: "/settings", label: "Settings" },
    ...(user?.is_admin ? [{ to: "/admin", label: "Admin" }] : []),
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

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="flex items-center gap-3 mb-8">
          <Building2 className="w-8 h-8 text-indigo-400" />
          <div>
            <h1 className="text-2xl font-bold text-white">Employer Search</h1>
            <p className="text-sm text-slate-400">Search candidate reputation scores for hiring decisions</p>
          </div>
        </div>

        {!isEmployer ? (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
            <Lock className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-white mb-2">Employer Tier Required</h2>
            <p className="text-slate-400 mb-6 max-w-md mx-auto">
              The employer search feature requires an active Employer subscription ($49/month).
              Get access to candidate reputation scores, detailed reports, and bulk search capabilities.
            </p>
            <Link
              to="/settings"
              className="inline-block bg-indigo-500 hover:bg-indigo-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition"
            >
              Upgrade to Employer Tier
            </Link>
          </div>
        ) : (
          <>
            {/* FCRA Warning */}
            <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-4 mb-6">
              <div className="flex items-start gap-3">
                <Shield className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm text-amber-300 font-medium">FCRA Compliance Notice</p>
                  <p className="text-xs text-slate-400 mt-1">
                    Cloak Haven scores are NOT consumer reports under the FCRA. These scores must not be used
                    as the sole basis for employment decisions. You agree to comply with all applicable federal,
                    state, and local laws regarding background checks and hiring.
                  </p>
                </div>
              </div>
            </div>

            <form onSubmit={handleSearch} className="flex gap-3 mb-8">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-11 pr-4 py-3 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  placeholder="Search by candidate name or username..."
                  minLength={2}
                />
              </div>
              <button
                type="submit"
                disabled={loading || query.length < 2}
                className="bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white px-6 py-3 rounded-xl text-sm font-medium transition"
              >
                {loading ? "Searching..." : "Search"}
              </button>
            </form>

            {searched && results.length === 0 && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
                <User className="w-10 h-10 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-400">No results found for "{query}"</p>
              </div>
            )}

            {results.length > 0 && (
              <div className="space-y-3">
                {results.map((profile) => (
                  <div
                    key={profile.id}
                    className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-slate-800 rounded-full flex items-center justify-center">
                          <User className="w-6 h-6 text-slate-500" />
                        </div>
                        <div>
                          <h3 className="text-white font-medium">{profile.lookup_name}</h3>
                          {profile.lookup_username && (
                            <p className="text-sm text-slate-400">@{profile.lookup_username}</p>
                          )}
                          <div className="flex items-center gap-2 mt-1">
                            {profile.is_claimed ? (
                              <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                                Verified
                              </span>
                            ) : (
                              <span className="text-xs bg-slate-700 text-slate-400 px-2 py-0.5 rounded-full">
                                Unverified
                              </span>
                            )}
                            {profile.score_accuracy_pct !== null && (
                              <span className="text-xs text-slate-500">{profile.score_accuracy_pct.toFixed(0)}% accuracy</span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        {profile.public_score !== null && (
                          <div className="text-right">
                            <p className="text-3xl font-bold" style={{ color: profile.score_color || "#6366F1" }}>
                              {profile.public_score}
                            </p>
                            <p className="text-sm" style={{ color: profile.score_color || "#6366F1" }}>
                              {profile.score_label}
                            </p>
                          </div>
                        )}
                        {profile.lookup_username && (
                          <Link
                            to={`/profile/${profile.lookup_username}`}
                            className="bg-slate-800 hover:bg-slate-700 text-white text-xs px-3 py-1.5 rounded-lg transition"
                          >
                            View Report
                          </Link>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Search History */}
            {!searched && history.length > 0 && (
              <div className="mt-8">
                <div className="flex items-center gap-2 mb-4">
                  <Clock className="w-4 h-4 text-slate-500" />
                  <h3 className="text-sm font-medium text-slate-400">Recent Searches</h3>
                </div>
                <div className="space-y-2">
                  {history.slice(0, 10).map((item) => (
                    <button
                      key={item.id}
                      onClick={() => { setQuery(item.searched_name); }}
                      className="w-full text-left bg-slate-900/50 border border-slate-800 rounded-lg px-4 py-3 hover:bg-slate-900 hover:border-slate-700 transition"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <span className="text-sm text-white">{item.searched_name}</span>
                          {item.searched_username && (
                            <span className="text-xs text-slate-500 ml-2">@{item.searched_username}</span>
                          )}
                        </div>
                        <span className="text-xs text-slate-600">
                          {new Date(item.searched_at).toLocaleDateString()}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
