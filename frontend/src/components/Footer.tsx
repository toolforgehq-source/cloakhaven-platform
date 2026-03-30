import { Link } from "react-router-dom";
import { Shield } from "lucide-react";

export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="bg-slate-950 border-t border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-indigo-400" />
            <span className="text-white font-semibold">Cloak Haven</span>
          </div>

          <nav className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
            <Link to="/privacy" className="text-slate-400 hover:text-white transition">
              Privacy Policy
            </Link>
            <Link to="/terms" className="text-slate-400 hover:text-white transition">
              Terms of Service
            </Link>
            <Link to="/pricing" className="text-slate-400 hover:text-white transition">
              Pricing
            </Link>
            <Link to="/search" className="text-slate-400 hover:text-white transition">
              Search
            </Link>
          </nav>

          <p className="text-xs text-slate-500">
            &copy; {year} Cloak Haven. All rights reserved.
          </p>
        </div>

        <div className="mt-6 pt-6 border-t border-slate-800/50">
          <p className="text-xs text-slate-600 leading-relaxed max-w-3xl">
            Cloak Haven is not a consumer reporting agency as defined by the Fair Credit Reporting Act (FCRA).
            Scores and findings are for informational purposes only and should not be used as a factor in
            establishing eligibility for credit, insurance, employment, or any other purpose covered by the FCRA.
          </p>
        </div>
      </div>
    </footer>
  );
}
