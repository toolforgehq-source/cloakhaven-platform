import { useState, useEffect, useRef, useCallback } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, PublicProfile } from "@/lib/api";
import { Search as SearchIcon, User, Shield, ChevronDown, ChevronUp, ExternalLink, Scale, Newspaper, Award, AlertTriangle, FileText, Clock, Lock, Loader2, SlidersHorizontal } from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { useAuth } from "@/lib/auth";
import { useToast } from "@/components/Toast";

interface PublicFinding {
  source: string;
  category: string;
  severity: string;
  title: string;
  description: string;
  evidence_url: string | null;
  confidence: number;
  corroboration_count: number;
  base_score_impact: number;
}

const CATEGORY_LABELS: Record<string, string> = {
  court_records: "Court Records",
  negative_press: "Press Coverage (Informational)",
  controversial_opinions: "Opinions (Informational)",
  positive_press: "Positive Press",
  professional_achievement: "Professional Achievements",
  community_involvement: "Community Involvement",
  constructive_content: "Constructive Content",
  verified_credentials: "Verified Credentials",
  misinformation: "Misinformation",
  harassment: "Harassment",
  hate_speech: "Hate Speech",
  threats: "Threats",
  illegal_activity: "Illegal Activity",
  discriminatory: "Discriminatory Content",
  substance_abuse: "Substance Abuse",
  profanity: "Profanity",
  unprofessional: "Unprofessional",
  negative_reviews: "Negative Reviews",
  neutral: "Neutral",
};

const CATEGORY_ICONS: Record<string, typeof Scale> = {
  court_records: Scale,
  negative_press: Newspaper,
  controversial_opinions: Newspaper,
  positive_press: Award,
  professional_achievement: Award,
  community_involvement: Award,
  constructive_content: FileText,
  verified_credentials: Award,
  misinformation: AlertTriangle,
};

function getCategoryColor(_category: string, impact: number): string {
  if (impact === 0) return "text-slate-400"; // Informational only
  if (impact > 0) return "text-emerald-400";
  return "text-red-400";
}

function getCategoryBg(_category: string, impact: number): string {
  if (impact === 0) return "bg-slate-800/50 border-slate-700";
  if (impact > 0) return "bg-emerald-950/30 border-emerald-800/30";
  return "bg-red-950/30 border-red-800/30";
}

function getImpactLabel(impact: number): string {
  if (impact === 0) return "No impact";
  if (impact > 0) return `+${impact.toFixed(0)} pts`;
  return `${impact.toFixed(0)} pts`;
}

function getSourceLabel(source: string): string {
  const labels: Record<string, string> = {
    serpapi: "Web Search",
    twitter: "Twitter/X",
    youtube: "YouTube",
    courtlistener: "Court Records",
    sec_edgar: "SEC Filings",
    github: "GitHub",
    wikipedia: "Wikipedia",
    patents: "Patents",
    scholar: "Academic",
    opencorporates: "Corporate Records",
  };
  return labels[source] || source;
}

const POLL_INTERVAL_MS = 2000;
const POLL_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes

export default function Search() {
  useDocumentTitle("Search");
  const { user } = useAuth();
  const { toast } = useToast();
  const [searchParams] = useSearchParams();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PublicProfile[]>([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
  const [showContext, setShowContext] = useState(false);
  const [company, setCompany] = useState("");
  const [location, setLocation] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollStartRef = useRef<number>(0);

  const paymentStatus = searchParams.get("payment");
  const sessionId = searchParams.get("session_id");
  const returnedProfileId = searchParams.get("profile_id");
  const [verifying, setVerifying] = useState(false);
  const [paymentVerified, setPaymentVerified] = useState(false);

  // Verify payment session when returning from Stripe checkout
  useEffect(() => {
    if (paymentStatus !== "success" || !sessionId || !user) return;
    let cancelled = false;

    const verify = async () => {
      setVerifying(true);
      try {
        const result = await api.verifyPaymentSession(sessionId);
        if (cancelled) return;
        if (result.verified) {
          setPaymentVerified(true);
          toast("success", result.message || "Payment verified! Report unlocked.");
          // Re-fetch the profile to show unlocked results
          if (returnedProfileId) {
            try {
              const data = await api.searchPublic(returnedProfileId);
              if (!cancelled && data.results.length > 0) {
                setResults(data.results);
                setSearched(true);
              }
            } catch {
              // Profile ID search might not work — user can re-search manually
            }
          }
        } else {
          toast("error", result.message || "Payment verification failed. Please try again.");
        }
      } catch {
        if (!cancelled) {
          toast("error", "Could not verify payment. Please refresh or search again.");
        }
      } finally {
        if (!cancelled) setVerifying(false);
      }
    };

    verify();
    return () => { cancelled = true; };
  }, [paymentStatus, sessionId, user]); // eslint-disable-line react-hooks/exhaustive-deps

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    setScanning(false);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const getSearchContext = useCallback(() => {
    const ctx: { company?: string; location?: string; linkedin_url?: string } = {};
    if (company.trim()) ctx.company = company.trim();
    if (location.trim()) ctx.location = location.trim();
    if (linkedinUrl.trim()) ctx.linkedin_url = linkedinUrl.trim();
    return Object.keys(ctx).length > 0 ? ctx : undefined;
  }, [company, location, linkedinUrl]);

  const startPolling = useCallback((searchQuery: string) => {
    stopPolling();
    setScanning(true);
    pollStartRef.current = Date.now();

    pollRef.current = setInterval(async () => {
      // Timeout after 5 minutes
      if (Date.now() - pollStartRef.current > POLL_TIMEOUT_MS) {
        stopPolling();
        return;
      }
      try {
        const data = await api.searchPublic(searchQuery, getSearchContext());
        if (data.results.length > 0) {
          setResults(data.results);
          stopPolling();
        }
      } catch {
        // Keep polling on transient errors
      }
    }, POLL_INTERVAL_MS);
  }, [stopPolling, getSearchContext]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (query.length < 2) return;
    setLoading(true);
    setExpandedId(null);
    setErrorMessage(null);
    stopPolling();
    try {
      const data = await api.searchPublic(query, getSearchContext());
      setResults(data.results);

      if (data.scan_pending && data.results.length === 0) {
        setScanning(true);
        setSearched(true);
        startPolling(query);
      } else {
        setSearched(true);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Request failed";
      if (message.toLowerCase().includes("rate limit") || message.toLowerCase().includes("too many")) {
        setErrorMessage("You've made too many searches. Please wait a few minutes before trying again.");
      } else if (message.toLowerCase().includes("daily") && message.toLowerCase().includes("limit")) {
        setErrorMessage("You've reached the daily search limit. Please try again tomorrow.");
      } else {
        setErrorMessage(null);
      }
      setResults([]);
      setSearched(true);
    } finally {
      setLoading(false);
    }
  };

  const handleUnlockReport = async (profileId: string) => {
    setCheckoutLoading(profileId);
    try {
      const data = await api.createCheckout("lookup", profileId);
      window.location.href = data.checkout_url;
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Payment processing unavailable";
      toast("error", msg);
    } finally {
      setCheckoutLoading(null);
    }
  };

  const handleSubscribe = async () => {
    setCheckoutLoading("subscribe");
    try {
      const data = await api.createCheckout("unlimited");
      window.location.href = data.checkout_url;
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Payment processing unavailable";
      toast("error", msg);
    } finally {
      setCheckoutLoading(null);
    }
  };

  const navLinks = user ? [
    { to: "/dashboard", label: "Dashboard" },
    { to: "/search", label: "Search" },
    { to: "/pricing", label: "Pricing" },
    { to: "/settings", label: "Settings" },
  ] : [
    { to: "/search", label: "Search" },
    { to: "/pricing", label: "Pricing" },
    { to: "/login", label: "Log in" },
  ];

  const navRight = user ? (
    <Link to="/dashboard" className="bg-indigo-500 hover:bg-indigo-600 text-white text-sm px-4 py-2 rounded-lg transition font-medium">
      Dashboard
    </Link>
  ) : (
    <Link to="/register" className="bg-indigo-500 hover:bg-indigo-600 text-white text-sm px-4 py-2 rounded-lg transition font-medium">
      Get Your Score
    </Link>
  );

  return (
    <div className="min-h-screen bg-slate-950">
      <Navbar links={navLinks} rightContent={navRight} variant={user ? undefined : "public"} />

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {paymentStatus === "success" && (
          <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4 mb-8 flex items-center gap-3">
            {verifying ? (
              <>
                <Loader2 className="w-5 h-5 text-emerald-400 shrink-0 animate-spin" />
                <p className="text-sm text-emerald-300">Verifying payment and unlocking your report...</p>
              </>
            ) : paymentVerified ? (
              <>
                <Shield className="w-5 h-5 text-emerald-400 shrink-0" />
                <p className="text-sm text-emerald-300">Payment verified! Your report is now unlocked. Search the name again to view it.</p>
              </>
            ) : (
              <>
                <Shield className="w-5 h-5 text-emerald-400 shrink-0" />
                <p className="text-sm text-emerald-300">Payment successful! Search the name again to view your unlocked report.</p>
              </>
            )}
          </div>
        )}

        {paymentStatus === "cancelled" && (
          <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 mb-8 flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
            <p className="text-sm text-amber-300">Payment was cancelled. You can try again anytime.</p>
          </div>
        )}

        <div className="text-center mb-12">
          <h1 className="text-3xl font-bold text-white mb-3">Search Anyone's Digital Reputation</h1>
          <p className="text-slate-400">
            Every person has a digital footprint. Find out what it says about someone.
          </p>
        </div>

        {!user ? (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
            <Lock className="w-10 h-10 text-indigo-400 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-3">Sign in to search</h2>
            <p className="text-sm text-slate-400 mb-6">
              Create an account or log in to search anyone's digital reputation.
            </p>
            <div className="flex gap-3 justify-center">
              <Link to="/login" className="bg-slate-800 hover:bg-slate-700 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition">
                Log in
              </Link>
              <Link to="/register" className="bg-indigo-500 hover:bg-indigo-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition">
                Create Account
              </Link>
            </div>
          </div>
        ) : (
          <>
            <form onSubmit={handleSearch} className="mb-8">
              <div className="flex gap-3">
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
              </div>

              <button
                type="button"
                onClick={() => setShowContext(!showContext)}
                className="flex items-center gap-1.5 mt-3 text-xs text-slate-500 hover:text-slate-300 transition"
              >
                <SlidersHorizontal className="w-3.5 h-3.5" />
                {showContext ? "Hide" : "Refine search"} — add context for better accuracy
                {(company || location || linkedinUrl) && (
                  <span className="bg-indigo-500/20 text-indigo-400 px-1.5 py-0.5 rounded text-[10px] font-medium">
                    {[company, location, linkedinUrl].filter(Boolean).length} added
                  </span>
                )}
              </button>

              {showContext && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3 p-4 bg-slate-900/50 border border-slate-800 rounded-xl">
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">Company</label>
                    <input
                      type="text"
                      value={company}
                      onChange={(e) => setCompany(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                      placeholder="e.g. Google"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">City / State</label>
                    <input
                      type="text"
                      value={location}
                      onChange={(e) => setLocation(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                      placeholder="e.g. San Francisco, CA"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">LinkedIn URL</label>
                    <input
                      type="text"
                      value={linkedinUrl}
                      onChange={(e) => setLinkedinUrl(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                      placeholder="linkedin.com/in/..."
                    />
                  </div>
                  <p className="col-span-full text-[11px] text-slate-600">
                    Optional — adding context helps us find the right person, especially for common names.
                  </p>
                </div>
              )}
            </form>

            {scanning && results.length === 0 && (
              <div className="bg-slate-900 border border-indigo-800/40 rounded-xl p-12 text-center">
                <div className="w-10 h-10 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mx-auto mb-4" />
                <p className="text-white font-medium">Scanning public records...</p>
                <p className="text-sm text-slate-400 mt-2">
                  We're searching public data sources for "{query}". This usually takes 30–60 seconds.
                </p>
              </div>
            )}

            {searched && !scanning && results.length === 0 && errorMessage && (
              <div className="bg-slate-900 border border-amber-800/40 rounded-xl p-12 text-center">
                <Clock className="w-10 h-10 text-amber-400 mx-auto mb-3" />
                <p className="text-amber-300 font-medium">{errorMessage}</p>
                <p className="text-sm text-slate-400 mt-2">
                  Rate limits help protect the service from abuse.
                </p>
              </div>
            )}

            {searched && !scanning && results.length === 0 && !errorMessage && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
                <User className="w-10 h-10 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-400">No profiles found for "{query}"</p>
                <p className="text-sm text-slate-500 mt-2">
                  Try searching with a full name (first and last).
                </p>
              </div>
            )}

            {results.length > 0 && (
              <div className="space-y-3">
                {results.map((profile) => {
                  const isExpanded = expandedId === profile.id;
                  const isLocked = profile.is_locked;

                  if (isLocked) {
                    // ── LOCKED TEASER ──
                    return (
                      <div key={profile.id} className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                        <div className="p-5">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                              <div className="w-12 h-12 bg-slate-800 rounded-full flex items-center justify-center">
                                <User className="w-6 h-6 text-slate-500" />
                              </div>
                              <div>
                                <h3 className="text-white font-medium">{profile.lookup_name}</h3>
                                <div className="flex items-center gap-2 mt-1">
                                  {profile.sources_scanned_count > 0 && (
                                    <span className="text-xs text-slate-500">{profile.sources_scanned_count} sources scanned</span>
                                  )}
                                  {profile.total_findings_count > 0 && (
                                    <span className="text-xs text-slate-500">{profile.total_findings_count} findings</span>
                                  )}
                                </div>
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="w-16 h-10 bg-slate-800 rounded-lg flex items-center justify-center">
                                <Lock className="w-5 h-5 text-slate-500" />
                              </div>
                            </div>
                          </div>

                          {/* Paywall CTA */}
                          <div className="mt-4 bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                            <div className="flex items-center gap-2 mb-2">
                              <Lock className="w-4 h-4 text-indigo-400" />
                              <p className="text-sm font-medium text-white">Report ready</p>
                            </div>
                            <p className="text-xs text-slate-400 mb-4">
                              We found {profile.total_findings_count > 0 ? profile.total_findings_count : ""} finding{profile.total_findings_count !== 1 ? "s" : ""} across {profile.sources_scanned_count > 0 ? profile.sources_scanned_count : "multiple"} sources for {profile.lookup_name}. Unlock to see the full score, findings, and evidence.
                            </p>
                            <div className="flex gap-2">
                              <button
                                onClick={() => handleUnlockReport(profile.id)}
                                disabled={checkoutLoading !== null}
                                className="flex-1 flex items-center justify-center gap-2 bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white py-2.5 rounded-lg text-sm font-medium transition"
                              >
                                {checkoutLoading === profile.id ? (
                                  <><Loader2 className="w-4 h-4 animate-spin" /> Processing...</>
                                ) : (
                                  "Unlock Report — $8"
                                )}
                              </button>
                              <button
                                onClick={handleSubscribe}
                                disabled={checkoutLoading !== null}
                                className="flex-1 flex items-center justify-center gap-2 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-white py-2.5 rounded-lg text-sm font-medium transition"
                              >
                                {checkoutLoading === "subscribe" ? (
                                  <><Loader2 className="w-4 h-4 animate-spin" /> Processing...</>
                                ) : (
                                  "Unlimited — $49/mo"
                                )}
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  }

                  // ── UNLOCKED FULL REPORT ──
                  const findings: PublicFinding[] = (profile.public_findings_summary as unknown as { findings?: PublicFinding[] })?.findings || [];
                  const grouped: Record<string, PublicFinding[]> = {};
                  for (const f of findings) {
                    if (!grouped[f.category]) grouped[f.category] = [];
                    grouped[f.category].push(f);
                  }
                  const sortedCategories = Object.keys(grouped).sort((a, b) => {
                    const aImpact = grouped[a][0]?.base_score_impact || 0;
                    const bImpact = grouped[b][0]?.base_score_impact || 0;
                    if (aImpact < 0 && bImpact >= 0) return -1;
                    if (aImpact >= 0 && bImpact < 0) return 1;
                    if (aImpact === 0 && bImpact > 0) return -1;
                    if (aImpact > 0 && bImpact === 0) return 1;
                    return 0;
                  });

                  return (
                    <div key={profile.id} className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                      <button
                        onClick={() => setExpandedId(isExpanded ? null : profile.id)}
                        className="w-full p-5 hover:bg-slate-800/30 transition text-left"
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
                                {findings.length > 0 && (
                                  <span className="text-xs text-slate-500">{findings.length} findings</span>
                                )}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-3">
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
                            {findings.length > 0 && (
                              isExpanded
                                ? <ChevronUp className="w-5 h-5 text-slate-500" />
                                : <ChevronDown className="w-5 h-5 text-slate-500" />
                            )}
                          </div>
                        </div>
                      </button>

                      {isExpanded && findings.length > 0 && (
                        <div className="border-t border-slate-800 px-5 py-4">
                          <h4 className="text-sm font-semibold text-slate-300 mb-3">What affected this score</h4>

                          <div className="flex gap-3 mb-4 text-xs">
                            {(() => {
                              const actionableNeg = findings.filter(f => f.base_score_impact < 0).length;
                              const positiveCount = findings.filter(f => f.base_score_impact > 0).length;
                              const infoCount = findings.filter(f => f.base_score_impact === 0).length;
                              return (
                                <>
                                  {actionableNeg > 0 && (
                                    <span className="bg-red-950/40 text-red-400 border border-red-800/30 px-2.5 py-1 rounded-full">
                                      {actionableNeg} negative
                                    </span>
                                  )}
                                  {positiveCount > 0 && (
                                    <span className="bg-emerald-950/40 text-emerald-400 border border-emerald-800/30 px-2.5 py-1 rounded-full">
                                      {positiveCount} positive
                                    </span>
                                  )}
                                  {infoCount > 0 && (
                                    <span className="bg-slate-800 text-slate-400 border border-slate-700 px-2.5 py-1 rounded-full">
                                      {infoCount} informational
                                    </span>
                                  )}
                                </>
                              );
                            })()}
                          </div>

                          <div className="space-y-3">
                            {sortedCategories.map((category) => {
                              const catFindings = grouped[category];
                              const sampleImpact = catFindings[0]?.base_score_impact || 0;
                              const IconComponent = CATEGORY_ICONS[category] || FileText;
                              return (
                                <div key={category} className={`border rounded-lg p-3 ${getCategoryBg(category, sampleImpact)}`}>
                                  <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-2">
                                      <IconComponent className={`w-4 h-4 ${getCategoryColor(category, sampleImpact)}`} />
                                      <span className={`text-sm font-medium ${getCategoryColor(category, sampleImpact)}`}>
                                        {CATEGORY_LABELS[category] || category}
                                      </span>
                                      <span className="text-xs text-slate-500">({catFindings.length})</span>
                                    </div>
                                    <span className={`text-xs font-mono ${getCategoryColor(category, sampleImpact)}`}>
                                      {sampleImpact === 0 ? "No impact" : `${getImpactLabel(sampleImpact)} each`}
                                    </span>
                                  </div>
                                  <div className="space-y-1.5">
                                    {catFindings.slice(0, 5).map((finding, idx) => (
                                      <div key={idx} className="flex items-start gap-2 text-xs">
                                        <span className="text-slate-500 shrink-0 mt-0.5">{getSourceLabel(finding.source)}</span>
                                        <span className="text-slate-300 flex-1 line-clamp-1">{finding.title}</span>
                                        {finding.evidence_url && (
                                          <a
                                            href={finding.evidence_url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="text-indigo-400 hover:text-indigo-300 shrink-0"
                                            onClick={(e) => e.stopPropagation()}
                                          >
                                            <ExternalLink className="w-3 h-3" />
                                          </a>
                                        )}
                                      </div>
                                    ))}
                                    {catFindings.length > 5 && (
                                      <p className="text-xs text-slate-500 mt-1">
                                        +{catFindings.length - 5} more {CATEGORY_LABELS[category]?.toLowerCase() || category} findings
                                      </p>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>

                          <p className="text-xs text-slate-600 mt-3">
                            Scores are based only on public information. Opinions and press coverage are shown for transparency but do not affect the score.
                          </p>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}
      </main>

      <Footer />
    </div>
  );
}
