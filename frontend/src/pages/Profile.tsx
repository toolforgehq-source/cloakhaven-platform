import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { api, PublicProfile, Scorecard } from "@/lib/api";
import { User, Shield, AlertTriangle } from "lucide-react";
import Navbar from "@/components/Navbar";

export default function Profile() {
  const { username } = useParams<{ username: string }>();
  const [profile, setProfile] = useState<PublicProfile | null>(null);
  const [scorecard, setScorecard] = useState<Scorecard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!username) return;
    loadProfile();
  }, [username]);

  const loadProfile = async () => {
    setLoading(true);
    try {
      const data = await api.getPublicProfile(username!);
      setProfile(data);
      if (data.id) {
        try {
          const sc = await api.getScorecard(data.id);
          setScorecard(sc);
        } catch {
          // Scorecard may not be available
        }
      }
    } catch {
      setError("Profile not found");
    } finally {
      setLoading(false);
    }
  };

  const navLinks = [
    { to: "/search", label: "Search" },
    { to: "/pricing", label: "Pricing" },
    { to: "/login", label: "Log in" },
  ];

  const navRight = (
    <Link to="/register" className="bg-indigo-500 hover:bg-indigo-600 text-white text-sm px-4 py-2 rounded-lg transition font-medium">
      Get Your Score
    </Link>
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950">
        <Navbar links={navLinks} rightContent={navRight} variant="public" />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center justify-center h-96">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          </div>
        </main>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="min-h-screen bg-slate-950">
        <Navbar links={navLinks} rightContent={navRight} variant="public" />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-16 text-center">
            <User className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-white mb-2">Profile Not Found</h2>
            <p className="text-slate-400 mb-6">We couldn't find a profile for @{username}.</p>
            <Link to="/search" className="text-indigo-400 hover:text-indigo-300 text-sm">
              Try searching instead
            </Link>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950">
      <Navbar links={navLinks} rightContent={navRight} variant="public" />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="max-w-3xl mx-auto">
        {/* Profile Header */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 mb-6">
          <div className="flex items-start gap-6">
            <div className="w-20 h-20 bg-slate-800 rounded-full flex items-center justify-center shrink-0">
              <User className="w-10 h-10 text-slate-500" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-1">
                <h1 className="text-2xl font-bold text-white">{profile.lookup_name}</h1>
                {profile.is_claimed ? (
                  <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                    Claimed
                  </span>
                ) : (
                  <span className="text-xs bg-slate-700 text-slate-400 px-2 py-0.5 rounded-full">
                    Unclaimed
                  </span>
                )}
              </div>
              {profile.lookup_username && (
                <p className="text-slate-400 mb-3">@{profile.lookup_username}</p>
              )}
              {!profile.is_claimed && (
                <div className="bg-indigo-500/5 border border-indigo-500/20 rounded-lg p-3 mt-3">
                  <p className="text-sm text-indigo-300">
                    Is this you? <Link to="/register" className="underline font-medium">Claim your profile</Link> to get a verified score and dispute any findings.
                  </p>
                </div>
              )}
            </div>
            {profile.public_score !== null && (
              <div className="text-center shrink-0">
                <div className="w-24 h-24 rounded-full border-4 flex items-center justify-center" style={{ borderColor: profile.score_color || "#6366F1" }}>
                  <div>
                    <p className="text-3xl font-bold text-white">{profile.public_score}</p>
                  </div>
                </div>
                <p className="text-sm font-medium mt-2" style={{ color: profile.score_color || "#6366F1" }}>
                  {profile.score_label}
                </p>
                {!profile.is_claimed && (
                  <p className="text-xs text-slate-500 mt-1">Unverified</p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Score Accuracy */}
        {profile.score_accuracy_pct !== null && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold text-white flex items-center gap-2">
                <Shield className="w-5 h-5 text-indigo-400" />
                Score Accuracy
              </h2>
              <span className="text-sm text-slate-400">{profile.score_accuracy_pct.toFixed(0)}%</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-2">
              <div
                className="h-2 rounded-full bg-indigo-500 transition-all"
                style={{ width: `${profile.score_accuracy_pct}%` }}
              />
            </div>
            <p className="text-xs text-slate-500 mt-2">
              {profile.is_claimed
                ? "This profile has been claimed and verified by the owner."
                : "This score is based on public data only. The owner can claim this profile for a more accurate score."}
            </p>
          </div>
        )}

        {/* Scorecard Details */}
        {scorecard && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-6">
            <h2 className="font-semibold text-white mb-4">Score Breakdown</h2>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-slate-800/50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-white">{scorecard.social_media_score}</p>
                <p className="text-xs text-slate-400 mt-1">Social Media (40%)</p>
              </div>
              <div className="bg-slate-800/50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-white">{scorecard.web_presence_score}</p>
                <p className="text-xs text-slate-400 mt-1">Web Presence (35%)</p>
              </div>
              <div className="bg-slate-800/50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-white">{scorecard.posting_behavior_score}</p>
                <p className="text-xs text-slate-400 mt-1">Behavior (25%)</p>
              </div>
            </div>
            <div className="mt-4 pt-4 border-t border-slate-800">
              <p className="text-xs text-slate-500">
                Platforms analyzed: {scorecard.platforms_analyzed.join(", ") || "None yet"} · 
                Total findings: {scorecard.total_findings}
              </p>
            </div>
          </div>
        )}

        {/* Public Findings Summary */}
        {scorecard && scorecard.total_findings > 0 && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-6">
            <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
              Findings Summary
            </h2>
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(scorecard.category_breakdown).map(([cat, count]) => (
                <div key={cat} className="flex items-center justify-between bg-slate-800/50 rounded-lg p-3">
                  <span className="text-sm text-slate-300 capitalize">{cat.replace(/_/g, " ")}</span>
                  <span className="text-sm font-medium text-white">{count as number}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* FCRA Disclaimer */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 text-center">
          <p className="text-xs text-slate-500">
            Cloak Haven scores are informational only and are not consumer reports under the FCRA.
            Scores should not be used as the sole basis for employment, housing, credit, or insurance decisions.
            <Link to="/terms" className="text-indigo-400 hover:underline ml-1">Learn more</Link>
          </p>
        </div>
      </div>
      </main>
    </div>
  );
}
