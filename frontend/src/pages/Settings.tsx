import { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { api, SocialAccount } from "@/lib/api";
import {
  Settings as SettingsIcon, Upload, CreditCard, Shield, CheckCircle, Eye, EyeOff,
  Twitter, Instagram, Facebook, Linkedin, Youtube, Github, Link2, X, Loader2
} from "lucide-react";
import Navbar from "@/components/Navbar";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

const PLATFORMS = [
  { key: "twitter", label: "X / Twitter", icon: Twitter, placeholder: "elonmusk" },
  { key: "instagram", label: "Instagram", icon: Instagram, placeholder: "natgeo" },
  { key: "facebook", label: "Facebook", icon: Facebook, placeholder: "zuck" },
  { key: "linkedin", label: "LinkedIn", icon: Linkedin, placeholder: "williamhgates" },
  { key: "tiktok", label: "TikTok", icon: Upload, placeholder: "khaby.lame" },
  { key: "youtube", label: "YouTube", icon: Youtube, placeholder: "MrBeast" },
  { key: "reddit", label: "Reddit", icon: Link2, placeholder: "spez" },
  { key: "github", label: "GitHub", icon: Github, placeholder: "torvalds" },
] as const;

export default function Settings() {
  useDocumentTitle("Settings");
  const { user, logout } = useAuth();
  const [uploadPlatform, setUploadPlatform] = useState("instagram");
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  // Account linking state
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [linkInputs, setLinkInputs] = useState<Record<string, string>>({});
  const [linkingPlatform, setLinkingPlatform] = useState<string | null>(null);
  const [disconnecting, setDisconnecting] = useState<string | null>(null);
  const [linkError, setLinkError] = useState("");
  const [linkSuccess, setLinkSuccess] = useState("");

  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    try {
      const data = await api.getAccounts();
      setAccounts(data.accounts);
    } catch {
      // silent
    }
  };

  const handleLink = async (platform: string) => {
    const username = linkInputs[platform]?.trim();
    if (!username) return;
    setLinkingPlatform(platform);
    setLinkError("");
    setLinkSuccess("");
    try {
      await api.linkAccount(platform, username);
      setLinkSuccess(`${platform} account linked successfully`);
      setLinkInputs((prev) => ({ ...prev, [platform]: "" }));
      await loadAccounts();
      setTimeout(() => setLinkSuccess(""), 3000);
    } catch (err) {
      setLinkError(err instanceof Error ? err.message : "Failed to link account");
    } finally {
      setLinkingPlatform(null);
    }
  };

  const handleDisconnect = async (accountId: string, platform: string) => {
    setDisconnecting(accountId);
    setLinkError("");
    try {
      await api.disconnectAccount(accountId);
      setLinkSuccess(`${platform} account disconnected`);
      await loadAccounts();
      setTimeout(() => setLinkSuccess(""), 3000);
    } catch (err) {
      setLinkError(err instanceof Error ? err.message : "Failed to disconnect");
    } finally {
      setDisconnecting(null);
    }
  };

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadMsg("");
    try {
      const result = await api.uploadArchive(uploadPlatform, file);
      setUploadMsg(result.message);
      if (fileRef.current) fileRef.current.value = "";
    } catch (err) {
      setUploadMsg(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const [checkoutError, setCheckoutError] = useState("");
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
  const [visibility, setVisibility] = useState(user?.profile_visibility || "public");
  const [visibilitySaving, setVisibilitySaving] = useState(false);

  const handleCheckout = async (type: "lookup" | "unlimited") => {
    setCheckoutError("");
    setCheckoutLoading(type);
    try {
      const result = await api.createCheckout(type);
      window.location.href = result.checkout_url;
    } catch (err) {
      setCheckoutError(err instanceof Error ? err.message : "Checkout failed");
    } finally {
      setCheckoutLoading(null);
    }
  };

  const handleVisibilityToggle = async () => {
    const newVisibility = visibility === "public" ? "private" : "public";
    setVisibilitySaving(true);
    try {
      await api.put("/api/v1/auth/me/visibility", { visibility: newVisibility });
      setVisibility(newVisibility);
    } catch {
      // revert on failure
    } finally {
      setVisibilitySaving(false);
    }
  };

  const navLinks = [
    { to: "/dashboard", label: "Dashboard" },
    { to: "/findings", label: "Findings" },
    { to: "/disputes", label: "Disputes" },
    { to: "/search", label: "Search" },
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

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <SettingsIcon className="w-6 h-6 text-indigo-400" />
          Settings
        </h1>

        {/* Profile */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h2 className="font-semibold text-white mb-4">Profile</h2>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400">Name</span>
              <span className="text-white">{user?.full_name || "—"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Email</span>
              <div className="flex items-center gap-2">
                <span className="text-white">{user?.email}</span>
                {user?.email_verified && <CheckCircle className="w-4 h-4 text-emerald-400" />}
              </div>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Profile Claimed</span>
              <span className="text-white">{user?.is_profile_claimed ? "Yes" : "No"}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Visibility</span>
              <button
                onClick={handleVisibilityToggle}
                disabled={visibilitySaving}
                className="flex items-center gap-2 text-sm text-white hover:text-indigo-400 transition disabled:opacity-50"
              >
                {visibility === "public" ? (
                  <><Eye className="w-4 h-4" /> Public</>
                ) : (
                  <><EyeOff className="w-4 h-4" /> Private</>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Connect Platforms */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h2 className="font-semibold text-white mb-2 flex items-center gap-2">
            <Link2 className="w-5 h-5 text-indigo-400" />
            Connect Platforms
          </h2>
          <p className="text-sm text-slate-400 mb-4">
            Link your social accounts to improve your score accuracy. More platforms = higher confidence.
          </p>

          {linkError && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-sm text-red-400 mb-4">
              {linkError}
            </div>
          )}
          {linkSuccess && (
            <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3 text-sm text-emerald-400 mb-4">
              {linkSuccess}
            </div>
          )}

          <div className="space-y-3">
            {PLATFORMS.map(({ key, label, icon: Icon, placeholder }) => {
              const connected = accounts.find((a) => a.platform === key);
              return (
                <div key={key} className="bg-slate-800/50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Icon className="w-5 h-5 text-slate-400" />
                      <div>
                        <p className="text-sm font-medium text-white">{label}</p>
                        {connected && connected.platform_username && (
                          <p className="text-xs text-slate-500">@{connected.platform_username}</p>
                        )}
                      </div>
                    </div>
                    {connected ? (
                      <div className="flex items-center gap-2">
                        <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                          Connected
                        </span>
                        <button
                          onClick={() => handleDisconnect(connected.id, label)}
                          disabled={disconnecting === connected.id}
                          className="text-slate-500 hover:text-red-400 transition p-1"
                          title="Disconnect"
                        >
                          {disconnecting === connected.id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <X className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          placeholder={placeholder}
                          value={linkInputs[key] || ""}
                          onChange={(e) => setLinkInputs((prev) => ({ ...prev, [key]: e.target.value }))}
                          onKeyDown={(e) => e.key === "Enter" && handleLink(key)}
                          className="w-36 sm:w-44 bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        />
                        <button
                          onClick={() => handleLink(key)}
                          disabled={linkingPlatform === key || !linkInputs[key]?.trim()}
                          className="bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed text-white px-3 py-1.5 rounded-lg text-sm font-medium transition whitespace-nowrap"
                        >
                          {linkingPlatform === key ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            "Connect"
                          )}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Subscription */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
            <CreditCard className="w-5 h-5 text-indigo-400" />
            Subscription
          </h2>
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-sm text-white">{(user?.subscription_tier || "free").charAt(0).toUpperCase() + (user?.subscription_tier || "free").slice(1)} Plan</p>
              <p className="text-xs text-slate-400 capitalize">Status: {user?.subscription_status || "inactive"}</p>
            </div>
          </div>
          {checkoutError && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-sm text-red-400 mb-4">
              {checkoutError}
            </div>
          )}
          <div className="grid sm:grid-cols-2 gap-3">
            <button
              onClick={() => handleCheckout("lookup")}
              disabled={checkoutLoading !== null}
              className="bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white py-2.5 rounded-lg text-sm font-medium transition"
            >
              {checkoutLoading === "lookup" ? "Processing..." : "Single Report — $8"}
            </button>
            <button
              onClick={() => handleCheckout("unlimited")}
              disabled={checkoutLoading !== null}
              className="bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white py-2.5 rounded-lg text-sm font-medium transition"
            >
              {checkoutLoading === "unlimited" ? "Processing..." : "Unlimited — $49/mo"}
            </button>
          </div>
        </div>

        {/* Data Upload */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
            <Upload className="w-5 h-5 text-indigo-400" />
            Upload Data Archive
          </h2>
          <p className="text-sm text-slate-400 mb-4">
            Upload your data export from social media platforms. We process the data and delete the raw files immediately — zero data retention.
          </p>
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="block text-xs text-slate-400 mb-1">Platform</label>
              <select
                value={uploadPlatform}
                onChange={(e) => setUploadPlatform(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="instagram">Instagram</option>
                <option value="tiktok">TikTok</option>
                <option value="facebook">Facebook</option>
                <option value="linkedin">LinkedIn</option>
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-xs text-slate-400 mb-1">File (.zip, .json, .html)</label>
              <input
                ref={fileRef}
                type="file"
                accept=".zip,.json,.html"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white file:mr-3 file:bg-slate-700 file:border-0 file:text-white file:text-xs file:px-2 file:py-1 file:rounded"
              />
            </div>
            <button
              onClick={handleUpload}
              disabled={uploading}
              className="bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium transition whitespace-nowrap"
            >
              {uploading ? "Uploading..." : "Upload"}
            </button>
          </div>
          {uploadMsg && (
            <p className="text-sm text-emerald-400 mt-3">{uploadMsg}</p>
          )}

          <div className="mt-6 space-y-3">
            <h3 className="text-sm font-medium text-slate-300">How to download your data:</h3>
            {[
              { platform: "Instagram", steps: "Settings → Accounts Center → Your information and permissions → Download your information" },
              { platform: "TikTok", steps: "Settings → Account → Download your data → Request data" },
              { platform: "Facebook", steps: "Settings → Your Facebook Information → Download Your Information" },
              { platform: "LinkedIn", steps: "Settings → Data Privacy → Get a copy of your data" },
            ].map((item) => (
              <div key={item.platform} className="bg-slate-800/50 rounded-lg p-3">
                <p className="text-sm text-white font-medium">{item.platform}</p>
                <p className="text-xs text-slate-400 mt-0.5">{item.steps}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Legal links */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
            <Shield className="w-5 h-5 text-indigo-400" />
            Legal
          </h2>
          <div className="space-y-2">
            <Link to="/privacy" className="block text-sm text-indigo-400 hover:text-indigo-300 transition">Privacy Policy</Link>
            <Link to="/terms" className="block text-sm text-indigo-400 hover:text-indigo-300 transition">Terms of Service</Link>
          </div>
        </div>
      </main>
    </div>
  );
}
