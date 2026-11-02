"use client";
import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { api } from "@/lib/api";

const ALLOWED_WHEN_EXPIRED = ["/settings/billing", "/settings/security"];

export default function TrialGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (ALLOWED_WHEN_EXPIRED.some(p => pathname.startsWith(p))) return;
    api<{ access: string; has_access: boolean }>("/billing/status")
      .then(s => {
        if (!s.has_access) router.replace("/settings/billing");
      })
      .catch(() => {});
  }, [pathname, router]);

  return <>{children}</>;
}
