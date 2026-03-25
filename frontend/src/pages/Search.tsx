import { useState } from "react";
import { Link } from "react-router-dom";
import { api, PublicProfile } from "@/lib/api";
import { Search as SearchIcon, User, Shield } from "lucide-react";

export default function Search() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PublicProfile[]>([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (query.length < 2) return;
    setLoading(true);
    try {
      const data = await api.searchPublic(query);
      setResults(data.results);
      setSearched(true);
    } catch {
      setResults([]);
      setSearched(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950">
      <nav className="border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center font-bold text-sm text-white">CH</div>
            <span className="text-lg font-semibold text-white">Cloak Haven</span>
          </Link>
          <div className="flex items-center gap-6">
            <Link to="/search" className="text-sm text-white font-medium">Search</Link>
            <Link to="/pricing" className="text-sm text-slate-400 hover:text-white transition">Pricing</Link>
            <Link to="/login" className="text-sm text-slate-400 hover:text-white transition">Log in</Link>
            <Link to="/register" className="bg-indigo-500 hover:bg-indigo-600 text-white text-sm px-4 py-2 rounded-lg transition font-medium">
              Get Your Score
            </Link>
          </div>
        </div>
      </nav>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-12">
          <h1 className="text-3xl font-bold text-white mb-3">Search Anyone's Digital Reputation</h1>
          <p className="text-slate-400">
            Every person has a digital footprint. Find out what it says about someone.
          </p>
        </div>

        <form onSubmit={handleSearch} className="flex gap-3 mb-8">
          <div className="flex-1 relative">
            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-11 pr-4 py-3 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              placeholder="Search by name or username..."
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
            <p className="text-slate-400">No profiles found for "{query}"</p>
            <p className="text-sm text-slate-500 mt-2">
              This person may not have a Cloak Haven profile yet.
            </p>
          </div>
        )}

        {results.length > 0 && (
          <div className="space-y-3">
            {results.map((profile) => (
              <Link
                key={profile.id}
                to={profile.lookup_username ? `/profile/${profile.lookup_username}` : "#"}
                className="block bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition"
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
                            Claimed
                          </span>
                        ) : (
                          <span className="text-xs bg-slate-700 text-slate-400 px-2 py-0.5 rounded-full">
                            Unclaimed
                          </span>
                        )}
                        {profile.score_accuracy_pct !== null && (
                          <span className="text-xs text-slate-500">{profile.score_accuracy_pct.toFixed(0)}% accuracy</span>
                        )}
                      </div>
                    </div>
                  </div>
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
                </div>
              </Link>
            ))}
          </div>
        )}

        <div className="mt-16 bg-slate-900/50 border border-slate-800 rounded-xl p-8 text-center">
          <Shield className="w-8 h-8 text-indigo-400 mx-auto mb-3" />
          <h2 className="text-lg font-semibold text-white mb-2">Want to check your own score?</h2>
          <p className="text-sm text-slate-400 mb-4">
            Create a free account and start your reputation audit.
          </p>
          <Link
            to="/register"
            className="inline-block bg-indigo-500 hover:bg-indigo-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition"
          >
            Get Started Free
          </Link>
        </div>
      </main>
    </div>
  );
}
