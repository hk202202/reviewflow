"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import SubscriptionBanner, { SubscriptionStatus } from "@/components/subscription-banner";

export default function TrialBanner() {
  const [status, setStatus] = useState<SubscriptionStatus | null>(null);

  useEffect(() => {
    api<SubscriptionStatus>("/billing/status").then(setStatus).catch(() => {});
  }, []);

  if (!status || status.access === "active") return null;

  return (
    <div className="border-b">
      <SubscriptionBanner status={status} variant="compact" />
    </div>
  );
}
