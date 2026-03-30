import { Link } from "react-router-dom";
import { Shield, ArrowLeft } from "lucide-react";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

export default function NotFound() {
  useDocumentTitle("Page Not Found");
  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <Shield className="w-16 h-16 text-indigo-400 mx-auto mb-6" />
        <h1 className="text-6xl font-bold text-white mb-2">404</h1>
        <h2 className="text-xl font-semibold text-white mb-4">Page Not Found</h2>
        <p className="text-slate-400 mb-8">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="flex items-center justify-center gap-4">
          <Link
            to="/"
            className="bg-indigo-500 hover:bg-indigo-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Home
          </Link>
          <Link
            to="/search"
            className="bg-slate-800 hover:bg-slate-700 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition"
          >
            Search
          </Link>
        </div>
      </div>
    </div>
  );
}
