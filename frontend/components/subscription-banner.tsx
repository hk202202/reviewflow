"use client";
import Link from "next/link";
import { Clock, CreditCard, AlertTriangle, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface SubscriptionStatus {
  access: "trialing" | "active" | "expired";
  plan: string;
  days_left: number | null;
  trial_ends_at?: string | null;
  period_ends_at?: string | null;
  billing_cycle?: string;
  has_access: boolean;
}

interface Props {
  status: SubscriptionStatus | null;
  variant?: "dashboard" | "compact";
}

export default function SubscriptionBanner({ status, variant = "dashboard" }: Props) {
  if (!status) return null;

  if (status.access === "active" && status.days_left != null) {
    const pct = Math.min(100, Math.max(5, (status.days_left / 30) * 100));
    return (
      <div className="rounded-xl border border-green-200 bg-gradient-to-r from-green-50 to-emerald-50 p-4 flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="flex items-start gap-3 flex-1">
          <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center flex-shrink-0">
            <CheckCircle className="w-5 h-5 text-green-600" />
          </div>
          <div className="flex-1">
            <p className="font-semibold text-green-900 capitalize">{status.plan} plan active</p>
            <p className="text-sm text-green-700 mt-0.5">
              <strong>{status.days_left}</strong> day{status.days_left === 1 ? "" : "s"} remaining in your billing period
              {status.period_ends_at && (
                <span className="text-green-600"> · Renews {new Date(status.period_ends_at).toLocaleDateString()}</span>
              )}
            </p>
            {variant === "dashboard" && (
              <div className="mt-2 h-1.5 bg-green-200 rounded-full overflow-hidden max-w-xs">
                <div className="h-full bg-green-500 rounded-full transition-all" style={{ width: `${pct}%` }} />
              </div>
            )}
          </div>
        </div>
        <Link href="/settings/billing"><Button variant="outline" size="sm">Manage Billing</Button></Link>
      </div>
    );
  }

  if (status.access === "trialing" && status.days_left != null) {
    const urgent = status.days_left <= 2;
    if (variant === "compact") {
      return (
        <div className={`px-6 py-2.5 flex items-center justify-between gap-4 text-sm ${urgent ? "bg-amber-500 text-white" : "bg-blue-600 text-white"}`}>
          <span>Trial: <strong>{status.days_left}</strong> day{status.days_left === 1 ? "" : "s"} left — subscribe to keep access</span>
          <a href="/settings/billing" className="underline font-medium flex-shrink-0">Subscribe</a>
        </div>
      );
    }
    const pct = Math.min(100, (status.days_left / 5) * 100);
    return (
      <div className={`rounded-xl border p-4 flex flex-col sm:flex-row sm:items-center gap-4 ${urgent ? "border-amber-400 bg-gradient-to-r from-amber-50 to-orange-50" : "border-blue-200 bg-gradient-to-r from-blue-50 to-indigo-50"}`}>
        <div className="flex items-start gap-3 flex-1">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${urgent ? "bg-amber-100" : "bg-blue-100"}`}>
            <Clock className={`w-5 h-5 ${urgent ? "text-amber-600" : "text-blue-600"}`} />
          </div>
          <div>
            <p className={`font-semibold ${urgent ? "text-amber-900" : "text-blue-900"}`}>
              Free trial — {status.days_left} day{status.days_left === 1 ? "" : "s"} left
            </p>
            <p className={`text-sm mt-0.5 ${urgent ? "text-amber-700" : "text-blue-700"}`}>
              {urgent
                ? "Your trial is ending soon. Subscribe now to keep access to all features."
                : "Enjoy full access during your 5-day trial. Subscribe anytime to continue after it ends."}
              {status.trial_ends_at && (
                <span> Trial ends {new Date(status.trial_ends_at).toLocaleDateString()}.</span>
              )}
            </p>
            <div className="mt-2 h-1.5 bg-blue-200 rounded-full overflow-hidden max-w-xs">
              <div className={`h-full rounded-full transition-all ${urgent ? "bg-amber-500" : "bg-blue-500"}`} style={{ width: `${pct}%` }} />
            </div>
          </div>
        </div>
        <Link href="/settings/billing">
          <Button size="sm" className={urgent ? "bg-amber-600 hover:bg-amber-700" : ""}>
            <CreditCard className="w-4 h-4 mr-1" />Subscribe
          </Button>
        </Link>
      </div>
    );
  }

  if (status.access === "expired") {
    if (variant === "compact") {
      return (
        <div className="bg-red-600 text-white px-6 py-2.5 flex items-center justify-between gap-4 text-sm">
          <span>Trial expired — subscribe via Razorpay to restore access</span>
          <a href="/settings/billing" className="bg-white text-red-600 px-3 py-1 rounded-lg font-medium flex-shrink-0">Pay Now</a>
        </div>
      );
    }
    return (
      <div className="rounded-xl border border-red-300 bg-gradient-to-r from-red-50 to-rose-50 p-4 flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="flex items-start gap-3 flex-1">
          <div className="w-10 h-10 rounded-lg bg-red-100 flex items-center justify-center flex-shrink-0">
            <AlertTriangle className="w-5 h-5 text-red-600" />
          </div>
          <div>
            <p className="font-semibold text-red-900">Trial expired — features disabled</p>
            <p className="text-sm text-red-700 mt-0.5">Subscribe via Razorpay to restore access to reviews, AI replies, and all platforms.</p>
          </div>
        </div>
        <Link href="/settings/billing">
          <Button size="sm" className="bg-red-600 hover:bg-red-700">Pay & Restore Access</Button>
        </Link>
      </div>
    );
  }

  return null;
}
