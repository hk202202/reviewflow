"use client";
import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Check, Building2, User, Loader2, CheckCircle2, XCircle } from "lucide-react";
import SubscriptionBanner, { SubscriptionStatus } from "@/components/subscription-banner";
import { openRazorpayCheckout, RazorpaySuccessResponse } from "@/lib/razorpay";
import { PLANS, plansForAccountType, type AccountType } from "@/lib/plans";

const CYCLE_MULT: Record<string, number> = { monthly: 1, biannual: 6, annual: 12 };

type PaymentStep = "idle" | "creating_order" | "checkout_open" | "verifying" | "success" | "error";

interface PaymentCallback {
  order_id: string;
  payment_id: string;
  verified_at: string;
  plan: string;
}

export default function BillingPage() {
  const [status, setStatus] = useState<SubscriptionStatus | null>(null);
  const [razorpayEnabled, setRazorpayEnabled] = useState(false);
  const [plan, setPlan] = useState("growth");
  const [cycle, setCycle] = useState("monthly");
  const [payerType, setPayerType] = useState<"org" | "user">("org");
  const [role, setRole] = useState("");
  const [accountType, setAccountType] = useState<AccountType>("seller");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [paymentStep, setPaymentStep] = useState<PaymentStep>("idle");
  const [callback, setCallback] = useState<PaymentCallback | null>(null);

  const load = useCallback(() => {
    api<SubscriptionStatus>("/billing/status").then(setStatus).catch(() => {});
    api<{ role: string; account?: { account_type: AccountType } }>("/auth/me")
      .then(d => { setRole(d.role); setAccountType(d.account?.account_type || "seller"); })
      .catch(() => {});
    api<{ razorpay_enabled: boolean }>("/billing/config").then(c => setRazorpayEnabled(c.razorpay_enabled)).catch(() => {});
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    setPlan(accountType === "agency" ? "professional" : "solo");
  }, [accountType]);

  const availablePlans = plansForAccountType(accountType);
  const selectedPlan = availablePlans.find(p => p.id === plan) ?? availablePlans[0];
  const monthlyRate = selectedPlan?.prices[cycle as keyof typeof selectedPlan.prices] ?? 0;
  const totalAmount = monthlyRate * (CYCLE_MULT[cycle] ?? 1);

  const verifyPayment = async (response: RazorpaySuccessResponse) => {
    setPaymentStep("verifying");
    setError("");
    try {
      const result = await api<{ message: string; subscription: SubscriptionStatus }>("/billing/verify-payment", {
        method: "POST",
        body: JSON.stringify({
          razorpay_order_id: response.razorpay_order_id,
          razorpay_payment_id: response.razorpay_payment_id,
          razorpay_signature: response.razorpay_signature,
        }),
      });
      setCallback({
        order_id: response.razorpay_order_id,
        payment_id: response.razorpay_payment_id,
        verified_at: new Date().toISOString(),
        plan,
      });
      setStatus(result.subscription);
      setSuccess("Payment verified — subscription activated.");
      setPaymentStep("success");
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Payment verification failed");
      setPaymentStep("error");
    } finally {
      setLoading(false);
    }
  };

  const payWithRazorpay = async () => {
    setLoading(true);
    setError("");
    setSuccess("");
    setCallback(null);
    setPaymentStep("creating_order");
    try {
      const order = await api<{
        order_id: string; amount: number; currency: string; key_id: string;
        prefill: { email: string; name: string }; description: string;
      }>("/billing/create-order", {
        method: "POST",
        body: JSON.stringify({ plan, billing_cycle: cycle, payer_type: payerType }),
      });

      setPaymentStep("checkout_open");
      await openRazorpayCheckout({
        key: order.key_id,
        amount: order.amount,
        currency: order.currency,
        name: "ReviewFlow",
        description: order.description,
        order_id: order.order_id,
        prefill: order.prefill,
        theme: { color: "#2563eb" },
        handler: verifyPayment,
        modal: {
          ondismiss: () => {
            setPaymentStep((step) => {
              if (step === "verifying" || step === "success") return step;
              setLoading(false);
              setError("Payment cancelled.");
              return "idle";
            });
          },
        },
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Could not start payment");
      setPaymentStep("error");
      setLoading(false);
    }
  };

  const payDemo = async () => {
    setLoading(true);
    setError("");
    setSuccess("");
    setCallback(null);
    setPaymentStep("verifying");
    try {
      await api("/billing/activate", {
        method: "POST",
        body: JSON.stringify({ plan, billing_cycle: cycle, payer_type: payerType }),
      });
      setSuccess("Subscription activated (demo mode).");
      setPaymentStep("success");
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Activation failed");
      setPaymentStep("error");
    } finally {
      setLoading(false);
    }
  };

  const active = status?.access === "active";

  const stepLabel: Record<PaymentStep, string> = {
    idle: "",
    creating_order: "Creating Razorpay order…",
    checkout_open: "Complete payment in Razorpay checkout…",
    verifying: "Verifying payment signature…",
    success: "Payment verified",
    error: "Payment failed",
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Billing & Subscription</h1>
        <p className="text-gray-500 text-sm mt-1">
          {accountType === "agency" ? "Agency plans — manage multiple client companies" : "Seller plans — one company, multiple marketplaces"}
        </p>
      </div>

      <SubscriptionBanner status={status} />

      {paymentStep !== "idle" && (
        <Card className={paymentStep === "success" ? "border-green-200 bg-green-50" : paymentStep === "error" ? "border-red-200 bg-red-50" : "border-blue-200 bg-blue-50"}>
          <CardContent className="py-4 space-y-3">
            <div className="flex items-center gap-2 text-sm font-medium">
              {paymentStep === "success" ? (
                <CheckCircle2 className="w-5 h-5 text-green-600" />
              ) : paymentStep === "error" ? (
                <XCircle className="w-5 h-5 text-red-600" />
              ) : (
                <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
              )}
              <span>{stepLabel[paymentStep]}</span>
            </div>
            {callback && (
              <div className="rounded-lg bg-white/80 border border-green-200 p-3 text-xs font-mono space-y-1">
                <p className="font-sans font-semibold text-green-800 text-sm mb-2">Razorpay callback received</p>
                <p><span className="text-gray-500">order_id:</span> {callback.order_id}</p>
                <p><span className="text-gray-500">payment_id:</span> {callback.payment_id}</p>
                <p><span className="text-gray-500">plan:</span> {callback.plan}</p>
                <p><span className="text-gray-500">verified:</span> {new Date(callback.verified_at).toLocaleString()}</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {!active && (
        <>
          <div className={`grid gap-4 ${availablePlans.length > 2 ? "md:grid-cols-2 lg:grid-cols-4" : "md:grid-cols-2"}`}>
            {availablePlans.map(p => (
              <button key={p.id} type="button" onClick={() => setPlan(p.id)}
                className={`text-left rounded-xl border p-4 transition-colors ${plan === p.id ? "border-blue-500 ring-2 ring-blue-500 bg-blue-50" : "border-gray-200 bg-white hover:border-gray-300"}`}>
                {p.popular && <div className="text-xs font-semibold text-blue-600 mb-1">RECOMMENDED</div>}
                <div className="text-xs text-gray-500 mb-1">{p.audience}</div>
                <div className="font-bold">{p.name}</div>
                <div className="text-2xl font-bold mt-1">
                  ₹{p.prices[cycle as keyof typeof p.prices].toLocaleString("en-IN")}
                  <span className="text-sm font-normal text-gray-500">/mo</span>
                </div>
                <ul className="mt-3 space-y-1">
                  {p.highlights.map(f => <li key={f} className="text-xs text-gray-600 flex gap-1"><Check className="w-3 h-3 text-green-500 shrink-0" />{f}</li>)}
                </ul>
              </button>
            ))}
          </div>

          <Card>
            <CardContent className="space-y-4 py-4">
              <h2 className="font-semibold">Billing cycle</h2>
              <div className="flex gap-2 flex-wrap">
                {[{ id: "monthly", label: "Monthly" }, { id: "biannual", label: "6 Months (−15%)" }, { id: "annual", label: "Annual (−25%)" }].map(c => (
                  <button key={c.id} type="button" onClick={() => setCycle(c.id)}
                    className={`px-4 py-2 rounded-lg text-sm ${cycle === c.id ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"}`}>
                    {c.label}
                  </button>
                ))}
              </div>

              <div className="bg-gray-50 rounded-lg p-3 text-sm">
                Total due: <strong>₹{totalAmount.toLocaleString("en-IN")}</strong>
                {cycle !== "monthly" && <span className="text-gray-500"> ({CYCLE_MULT[cycle]} months at ₹{monthlyRate.toLocaleString("en-IN")}/mo)</span>}
              </div>

              <h2 className="font-semibold pt-2">Pay with</h2>
              <div className="grid sm:grid-cols-2 gap-3">
                <button type="button" onClick={() => setPayerType("org")} disabled={role !== "owner" && role !== "admin"}
                  className={`flex items-start gap-3 p-4 rounded-xl border text-left ${payerType === "org" ? "border-blue-500 bg-blue-50" : "border-gray-200"} ${role !== "owner" && role !== "admin" ? "opacity-50 cursor-not-allowed" : ""}`}>
                  <Building2 className="w-5 h-5 text-blue-600 mt-0.5" />
                  <div>
                    <div className="font-medium">Organization account</div>
                    <div className="text-xs text-gray-500">Billed to your company. Owners/admins only.</div>
                  </div>
                </button>
                <button type="button" onClick={() => setPayerType("user")}
                  className={`flex items-start gap-3 p-4 rounded-xl border text-left ${payerType === "user" ? "border-blue-500 bg-blue-50" : "border-gray-200"}`}>
                  <User className="w-5 h-5 text-blue-600 mt-0.5" />
                  <div>
                    <div className="font-medium">Personal account</div>
                    <div className="text-xs text-gray-500">Pay with your individual account (any team member).</div>
                  </div>
                </button>
              </div>

              {error && <p className="text-red-600 text-sm">{error}</p>}
              {success && <p className="text-green-600 text-sm">{success}</p>}

              <Button className="w-full" onClick={razorpayEnabled ? payWithRazorpay : payDemo} disabled={loading}>
                {loading ? "Processing..." : razorpayEnabled ? `Pay ₹${totalAmount.toLocaleString("en-IN")} with Razorpay` : "Activate (Demo — no Razorpay keys)"}
              </Button>
              {razorpayEnabled ? (
                <div className="text-xs text-gray-500 text-center space-y-1">
                  <p>Secured by Razorpay · UPI, Cards, Netbanking, Wallets</p>
                  <p className="text-gray-400">Test card: 4111 1111 1111 1111 · Test UPI: success@razorpay</p>
                </div>
              ) : (
                <p className="text-xs text-amber-600 text-center">Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to .env, then restart backend</p>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

