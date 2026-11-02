"use client";
import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { getToken } from "@/lib/api";
import AppLayout from "@/components/layout/app-layout";
import TrialGate from "@/components/layout/trial-gate";

const PUBLIC_PATHS = ["/login", "/register", "/accept-invite", "/pricing", "/"];

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (PUBLIC_PATHS.some(p => pathname === p || pathname.startsWith("/login/"))) return;
    if (!getToken()) router.push("/login");
  }, [pathname, router]);

  if (PUBLIC_PATHS.some(p => pathname === p)) return <>{children}</>;
  if (pathname.startsWith("/login/")) return <>{children}</>;
  if (pathname === "/onboarding") return <>{children}</>;

  return (
    <TrialGate>
      <AppLayout>{children}</AppLayout>
    </TrialGate>
  );
}
