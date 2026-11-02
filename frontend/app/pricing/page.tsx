"use client";
import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Check, Building2, Store } from "lucide-react";
import { PLANS, type AccountType } from "@/lib/plans";

type Cycle = "monthly" | "biannual" | "annual";

export default function PricingPage() {
  const [cycle, setCycle] = useState<Cycle>("monthly");
  const [segment, setSegment] = useState<AccountType | "all">("all");

  const cycleLabel = { monthly: "Monthly", biannual: "6 Months (save 15%)", annual: "Annual (save 25%)" };

  const visible = PLANS.filter(p => {
    if (segment === "all") return true;
    return p.segment === segment;
  });

  return (
    <div className="min-h-screen bg-gray-50 py-16 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold mb-3">Plans for sellers & agencies</h1>
          <p className="text-gray-600 text-lg">Same product — pick the path that fits how you work</p>
          <p className="text-sm text-blue-600 mt-2 font-medium">5-day free trial on all plans — no credit card required</p>

          <div className="flex justify-center gap-2 mt-6 flex-wrap">
            {(["all", "seller", "agency"] as const).map(s => (
              <button
                key={s}
                onClick={() => setSegment(s)}
                className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-1.5 ${segment === s ? "bg-blue-600 text-white" : "bg-white border border-gray-200 text-gray-600"}`}
              >
                {s === "seller" && <Store className="w-3.5 h-3.5" />}
                {s === "agency" && <Building2 className="w-3.5 h-3.5" />}
                {s === "all" ? "All plans" : s === "seller" ? "Direct sellers" : "Agencies"}
              </button>
            ))}
          </div>

          <div className="flex justify-center gap-2 mt-4">
            {(Object.keys(cycleLabel) as Cycle[]).map(c => (
              <button key={c} onClick={() => setCycle(c)}
                className={`px-4 py-2 rounded-lg text-sm font-medium ${cycle === c ? "bg-gray-900 text-white" : "bg-white border border-gray-200 text-gray-600"}`}>
                {cycleLabel[c]}
              </button>
            ))}
          </div>
        </div>

        <div className={`grid gap-6 ${visible.length >= 3 ? "md:grid-cols-2 lg:grid-cols-4" : "md:grid-cols-2 max-w-3xl mx-auto"}`}>
          {visible.map(plan => (
            <div key={plan.id} className={`bg-white rounded-2xl border p-6 flex flex-col ${plan.popular ? "border-blue-500 shadow-lg ring-2 ring-blue-500" : "border-gray-200"}`}>
              <div className="text-xs font-semibold text-gray-500 mb-1">{plan.audience}</div>
              {plan.popular && <div className="text-xs font-semibold text-blue-600 mb-2">MOST POPULAR</div>}
              <h2 className="text-xl font-bold">{plan.name}</h2>
              <p className="text-sm text-gray-500 mt-1 mb-3">{plan.description}</p>
              <div className="mb-6">
                <span className="text-3xl font-bold">₹{plan.prices[cycle].toLocaleString("en-IN")}</span>
                <span className="text-gray-500 text-sm">/mo</span>
              </div>
              <ul className="space-y-2 flex-1 mb-6">
                {plan.highlights.map(f => (
                  <li key={f} className="flex items-start gap-2 text-sm text-gray-600">
                    <Check className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />{f}
                  </li>
                ))}
              </ul>
              <Link href={`/register?type=${plan.segment}`}>
                <Button className="w-full" variant={plan.popular ? "default" : "outline"}>
                  {plan.segment === "agency" ? "Start as agency" : "Start as seller"}
                </Button>
              </Link>
            </div>
          ))}
        </div>

        <div className="mt-16 grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
          <div className="bg-white rounded-xl p-6 border">
            <Store className="w-8 h-8 text-blue-600 mb-3" />
            <h3 className="font-bold mb-2">Direct seller</h3>
            <p className="text-sm text-gray-600">One company, your own Amazon/Flipkart/Myntra stores. Connect via API, AI replies, optional Chrome extension.</p>
          </div>
          <div className="bg-white rounded-xl p-6 border">
            <Building2 className="w-8 h-8 text-blue-600 mb-3" />
            <h3 className="font-bold mb-2">Agency</h3>
            <p className="text-sm text-gray-600">Multiple client companies from one login. Switch brands in the header. Invite clients to their company only.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
