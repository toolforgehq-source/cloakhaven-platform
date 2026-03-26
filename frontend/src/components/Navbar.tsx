import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Menu, X } from "lucide-react";

interface NavLink {
  to: string;
  label: string;
  active?: boolean;
}

interface NavbarProps {
  links: NavLink[];
  rightContent?: React.ReactNode;
  variant?: "public" | "auth";
}

export default function Navbar({ links, rightContent, variant = "auth" }: NavbarProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  return (
    <nav className="border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link to={variant === "auth" ? "/dashboard" : "/"} className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center font-bold text-sm text-white">CH</div>
          <span className="text-lg font-semibold text-white">Cloak Haven</span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-6">
          {links.map((link) => {
            const isActive = link.active ?? location.pathname === link.to;
            return (
              <Link
                key={link.to}
                to={link.to}
                className={`text-sm transition ${isActive ? "text-white font-medium" : "text-slate-400 hover:text-white"}`}
              >
                {link.label}
              </Link>
            );
          })}
          {rightContent}
        </div>

        {/* Mobile hamburger */}
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="md:hidden text-slate-400 hover:text-white transition p-2"
          aria-label="Toggle menu"
        >
          {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Mobile menu overlay */}
      {mobileOpen && (
        <div className="md:hidden border-t border-slate-800 bg-slate-950">
          <div className="px-4 py-4 space-y-1">
            {links.map((link) => {
              const isActive = link.active ?? location.pathname === link.to;
              return (
                <Link
                  key={link.to}
                  to={link.to}
                  onClick={() => setMobileOpen(false)}
                  className={`block px-3 py-2.5 rounded-lg text-sm transition ${
                    isActive
                      ? "text-white font-medium bg-slate-800"
                      : "text-slate-400 hover:text-white hover:bg-slate-900"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
            <div className="pt-3 border-t border-slate-800 mt-3">
              {rightContent}
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
