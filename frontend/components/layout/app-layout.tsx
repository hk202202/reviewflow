"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { clearToken } from "@/lib/api";
import {
  LayoutDashboard, MessageSquare, FileText, Globe, BarChart3,
  Users, Shield, Bell, AlertTriangle, Sparkles, LogOut, Menu, X, CreditCard,
  ChevronLeft, ChevronRight,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import NotificationBell from "./notification-bell";
import ExtensionBanner from "./extension-banner";
import ExtensionTokenBridge from "./extension-token-bridge";
import TrialBanner from "./trial-banner";
import OrgSwitcher from "./org-switcher";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/reviews", label: "Reviews", icon: MessageSquare },
  { href: "/reviews/escalated", label: "Escalated", icon: AlertTriangle },
  { href: "/templates", label: "Templates", icon: FileText },
  { href: "/platforms", label: "Platforms", icon: Globe },
  { href: "/generate", label: "AI Generate", icon: Sparkles },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/settings/team", label: "Team", icon: Users },
  { href: "/settings/billing", label: "Billing", icon: CreditCard },
  { href: "/settings/security", label: "Security", icon: Shield },
  { href: "/settings/audit-log", label: "Audit Log", icon: Bell },
];

const XL_QUERY = "(min-width: 1280px)";

function useIsXl() {
  const [isXl, setIsXl] = useState(true);

  useEffect(() => {
    const mq = window.matchMedia(XL_QUERY);
    const update = () => setIsXl(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  return isXl;
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isXl = useIsXl();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [userCollapsed, setUserCollapsed] = useState<boolean | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem("sidebar-collapsed");
    if (saved === "true") setUserCollapsed(true);
    else if (saved === "false") setUserCollapsed(false);
  }, []);

  // Auto-responsive: mini rail on tablet, full sidebar on xl+ unless user collapsed
  const collapsed = isXl ? (userCollapsed ?? false) : (userCollapsed ?? true);

  const toggleCollapsed = useCallback(() => {
    setUserCollapsed((prev) => {
      const currentlyCollapsed = isXl ? (prev ?? false) : (prev ?? true);
      const next = !currentlyCollapsed;
      localStorage.setItem("sidebar-collapsed", String(next));
      return next;
    });
  }, [isXl]);

  const logout = () => {
    clearToken();
    router.push("/login");
  };

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + "/");

  const navLinkClass = (href: string) =>
    cn(
      "flex items-center rounded-lg font-medium transition-colors",
      collapsed
        ? "justify-center gap-0 px-0 py-3 md:py-3"
        : "gap-3 px-3 py-2 text-sm",
      isActive(href) ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-gray-50",
    );

  const iconClass = cn("shrink-0", collapsed ? "w-5 h-5 md:w-[1.375rem] md:h-[1.375rem]" : "w-4 h-4");

  return (
    <div className="flex h-screen bg-gray-50">
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close sidebar"
          className="fixed inset-0 z-40 bg-black/30 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex flex-col bg-white border-r border-gray-200 transition-[width,transform] duration-200 ease-in-out",
          mobileOpen ? "translate-x-0 w-64" : "-translate-x-full w-64",
          "md:translate-x-0 md:static",
          collapsed ? "md:w-20" : "md:w-64",
        )}
      >
        {/* Header: logo + optional name + toggle */}
        <div
          className={cn(
            "flex shrink-0 items-center border-b",
            collapsed ? "flex-col gap-2 px-2 py-4 md:px-2 md:py-4" : "gap-2 px-4 py-4 md:px-5 md:py-5",
          )}
        >
          <div
            className={cn(
              "shrink-0 bg-blue-600 rounded-xl flex items-center justify-center text-white font-bold",
              collapsed ? "w-10 h-10 text-sm" : "w-8 h-8 text-sm",
            )}
          >
            RF
          </div>

          {!collapsed && (
            <span className="flex-1 font-semibold text-lg whitespace-nowrap truncate">
              ReviewFlow
            </span>
          )}

          <button
            type="button"
            className={cn(
              "hidden md:flex items-center justify-center rounded-lg hover:bg-gray-100 text-gray-500 shrink-0 transition-colors",
              collapsed ? "w-10 h-8" : "w-8 h-8 ml-auto",
            )}
            aria-label={collapsed ? "Show menu names" : "Hide menu names"}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            onClick={toggleCollapsed}
          >
            {collapsed ? (
              <ChevronRight className="w-5 h-5" />
            ) : (
              <ChevronLeft className="w-4 h-4" />
            )}
          </button>

          <button
            type="button"
            className="ml-auto md:hidden p-1 rounded-md hover:bg-gray-100"
            aria-label="Close sidebar"
            onClick={() => setMobileOpen(false)}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {collapsed && (
          <p className="hidden md:block text-[10px] font-medium text-center text-gray-400 uppercase tracking-wide pb-1">
            Menu
          </p>
        )}

        <nav className={cn("flex-1 overflow-y-auto space-y-0.5", collapsed ? "px-2 py-1" : "p-3 md:p-4")}>
          {NAV.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              title={collapsed ? label : undefined}
              onClick={() => setMobileOpen(false)}
              className={navLinkClass(href)}
            >
              <Icon className={iconClass} />
              {!collapsed && <span className="whitespace-nowrap truncate">{label}</span>}
            </Link>
          ))}
        </nav>

        <div className={cn("shrink-0 border-t", collapsed ? "p-2" : "p-3 md:p-4")}>
          <button
            type="button"
            onClick={logout}
            title={collapsed ? "Sign Out" : undefined}
            className={cn(
              "flex items-center w-full text-gray-600 hover:bg-gray-50 rounded-lg transition-colors",
              collapsed
                ? "justify-center px-0 py-3 md:py-3"
                : "gap-3 px-3 py-2 text-sm",
            )}
          >
            <LogOut className={iconClass} />
            {!collapsed && <span className="whitespace-nowrap">Sign Out</span>}
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <header className="bg-white border-b border-gray-200 px-4 md:px-6 py-3 flex items-center gap-4">
          <button
            type="button"
            className="md:hidden p-1.5 rounded-md hover:bg-gray-100"
            aria-label="Open sidebar"
            onClick={() => setMobileOpen(true)}
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="flex-1" />
          <OrgSwitcher />
          <NotificationBell />
          <Link href="/settings/billing" className="text-sm text-blue-600 hover:underline">
            Upgrade
          </Link>
        </header>
        <TrialBanner />
        <ExtensionTokenBridge />
        <ExtensionBanner />
        <main className="flex-1 overflow-y-auto p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
