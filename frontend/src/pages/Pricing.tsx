import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle, AlertTriangle, Loader2 } from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { useToast } from "@/components/Toast";

export default function Pricing() {
  useDocumentTitle("Pricing");
  const { user } = useAuth();
  const { toast } = useToast();
  const [searchParams] = useSearchParams();
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);

  const paymentStatus = searchParams.get("payment");

  const handleCheckout = async (priceType: "lookup" | "unlimited") => {
    if (!user) return;
    setCheckoutLoading(priceType);
    try {
      const data = await api.createCheckout(priceType);
      window.location.href = data.checkout_url;
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Payment processing unavailable";
      toast("error", msg);
    } finally {
      setCheckoutLoading(null);
    }
  };

  const publicNavLinks = [
    { to: "/search", label: "Search" },
    { to: "/pricing", label: "Pricing" },
    { to: "/login", label: "Log in" },
  ];

  const authedNavLinks = [
    { to: "/dashboard", label: "Dashboard" },
    { to: "/findings", label: "Findings" },
    { to: "/disputes", label: "Disputes" },
    { to: "/settings", label: "Settings" },
    ...(user?.is_admin ? [{ to: "/admin", label: "Admin" }] : []),
  ];

  const navLinks = user ? authedNavLinks : publicNavLinks;

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
    <div className="min-h-screen bg-slate-950 text-white">
      <Navbar links={navLinks} rightContent={navRight} variant={user ? undefined : "public"} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
        {paymentStatus === "cancelled" && (
          <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 mb-8 max-w-2xl mx-auto flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
            <p className="text-sm text-amber-300">Payment was cancelled. You can try again anytime.</p>
          </div>
        )}

        <div className="text-center mb-16">
          <h1 className="text-4xl font-bold">Simple, Transparent Pricing</h1>
          <p className="mt-4 text-slate-400 text-lg">No hidden fees. Cancel anytime.</p>
        </div>

        <div className="grid md:grid-cols-2 gap-8 max-w-3xl mx-auto">
          {/* Single Lookup */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-8">
            <h3 className="font-semibold text-lg">Single Report</h3>
            <div className="mt-4">
              <span className="text-4xl font-bold">$8</span>
              <span className="text-slate-500 ml-1">per lookup</span>
            </div>
            <ul className="mt-6 space-y-3 text-sm text-slate-400">
              <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400" /> Full reputation score</li>
              <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400" /> Detailed findings report</li>
              <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400" /> Evidence &amp; sources</li>
              <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400" /> 30-day access to report</li>
            </ul>
            {user ? (
              <Link
                to="/search"
                className="mt-8 block text-center bg-slate-800 hover:bg-slate-700 text-white py-2.5 rounded-lg text-sm font-medium transition"
              >
                Search &amp; Pay Per Report
              </Link>
            ) : (
              <Link to="/register" className="mt-8 block text-center bg-slate-800 hover:bg-slate-700 text-white py-2.5 rounded-lg text-sm font-medium transition">
                Get Started
              </Link>
            )}
          </div>

          {/* Unlimited Subscription — Best Value */}
          <div className="bg-slate-900 border-2 border-indigo-500 rounded-xl p-8 relative">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-indigo-500 text-xs font-medium px-3 py-1 rounded-full">
              Best Value
            </div>
            <h3 className="font-semibold text-lg">Unlimited Reports</h3>
            <div className="mt-4">
              <span className="text-4xl font-bold">$49</span>
              <span className="text-slate-500 ml-1">/month</span>
            </div>
            <ul className="mt-6 space-y-3 text-sm text-slate-400">
              <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400" /> Unlimited searches</li>
              <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400" /> Full reports with evidence</li>
              <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400" /> Score breakdowns</li>
              <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400" /> Cancel anytime</li>
            </ul>
            {user ? (
              <button
                onClick={() => handleCheckout("unlimited")}
                disabled={checkoutLoading !== null}
                className="mt-8 w-full flex items-center justify-center gap-2 bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white py-2.5 rounded-lg text-sm font-medium transition"
              >
                {checkoutLoading === "unlimited" ? <><Loader2 className="w-4 h-4 animate-spin" /> Processing…</> : "Subscribe Now"}
              </button>
            ) : (
              <Link to="/register" className="mt-8 block text-center bg-indigo-500 hover:bg-indigo-600 text-white py-2.5 rounded-lg text-sm font-medium transition">
                Get Started
              </Link>
            )}
          </div>
        </div>

        <p className="text-xs text-slate-600 text-center mt-16 max-w-2xl mx-auto">
          Cloak Haven scores are not consumer reports under the Fair Credit Reporting Act (FCRA)
          and are not intended as the sole basis for employment, housing, or credit decisions.
        </p>
      </main>

      <Footer />
    </div>
  );
}
