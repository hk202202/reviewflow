"use client";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { AccountType } from "@/lib/plans";
import { ExtensionInstallModal } from "@/components/layout/extension-banner";
import { CheckCircle, Building2, Store } from "lucide-react";

const SELLER_STEPS = [
  { title: "Connect your first marketplace", key: "platform" },
  { title: "Choose reply mode", key: "reply_mode" },
  { title: "You're all set!", key: "done" },
];

const AGENCY_STEPS = [
  { title: "Add your first client company", key: "client" },
  { title: "Connect a platform for this client", key: "platform" },
  { title: "Invite client (optional)", key: "invite" },
  { title: "You're all set!", key: "done" },
];

export default function OnboardingPage() {
  const [accountType, setAccountType] = useState<AccountType>("seller");
  const [step, setStep] = useState(0);
  const [form, setForm] = useState({
    client_name: "",
    platform: "amazon",
    reply_mode: "template",
    invite_email: "",
  });
  const [showExtension, setShowExtension] = useState(false);

  useEffect(() => {
    api<{ account: { account_type: AccountType } }>("/auth/me")
      .then(d => setAccountType(d.account?.account_type || "seller"))
      .catch(() => {});
  }, []);

  const steps = accountType === "agency" ? AGENCY_STEPS : SELLER_STEPS;

  const next = async () => {
    try {
      if (accountType === "agency") {
        if (step === 0 && form.client_name.trim()) {
          await api("/auth/organizations", {
            method: "POST",
            body: JSON.stringify({ org_name: form.client_name.trim() }),
          });
        }
        if (step === 1 && form.platform) {
          await api("/platforms", {
            method: "POST",
            body: JSON.stringify({
              platform: form.platform,
              display_name: `${form.client_name || "Client"} — ${form.platform}`,
              default_reply_mode: form.reply_mode,
            }),
          }).catch(() => {});
        }
        if (step === 2 && form.invite_email.trim()) {
          await api("/auth/invite", {
            method: "POST",
            body: JSON.stringify({ email: form.invite_email.trim(), role: "member" }),
          }).catch(() => {});
        }
      } else {
        if (step === 0 && form.platform) {
          await api("/platforms", {
            method: "POST",
            body: JSON.stringify({
              platform: form.platform,
              display_name: `My ${form.platform}`,
              default_reply_mode: form.reply_mode,
            }),
          }).catch(() => {});
        }
      }
    } catch {
      /* continue onboarding even if optional steps fail */
    }

    if (step === steps.length - 1) {
      await api("/auth/onboarding/complete", { method: "POST" });
      window.location.href = "/dashboard";
      return;
    }
    setStep(s => s + 1);
  };

  const skip = () => {
    if (step === steps.length - 1) {
      api("/auth/onboarding/complete", { method: "POST" }).finally(() => {
        window.location.href = "/dashboard";
      });
      return;
    }
    setStep(s => s + 1);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-lg">
        <div className="flex items-center gap-2 mb-4 text-sm text-gray-600">
          {accountType === "agency" ? <Building2 className="w-4 h-4" /> : <Store className="w-4 h-4" />}
          {accountType === "agency" ? "Agency setup" : "Seller setup"}
        </div>

        <div className="flex gap-2 mb-8">
          {steps.map((_, i) => (
            <div key={i} className={`flex-1 h-1.5 rounded-full ${i <= step ? "bg-blue-600" : "bg-gray-200"}`} />
          ))}
        </div>

        <h2 className="text-xl font-bold mb-2">{steps[step].title}</h2>
        <p className="text-gray-500 text-sm mb-6">Step {step + 1} of {steps.length}</p>

        {accountType === "agency" && step === 0 && (
          <>
            <p className="text-sm text-gray-600 mb-3">Each client is a separate company. You can switch between them in the header.</p>
            <Input placeholder="Client company name (e.g. Sharma Electronics)" value={form.client_name} onChange={e => setForm({ ...form, client_name: e.target.value })} />
          </>
        )}

        {((accountType === "seller" && step === 0) || (accountType === "agency" && step === 1)) && (
          <>
            <p className="text-sm text-gray-600 mb-3">Connect via API — extension is optional for AI reply on seller portals.</p>
            <Select value={form.platform} onChange={e => setForm({ ...form, platform: e.target.value })} className="mb-3">
              <option value="amazon">Amazon</option>
              <option value="flipkart">Flipkart</option>
              <option value="myntra">Myntra</option>
            </Select>
            <Select value={form.reply_mode} onChange={e => setForm({ ...form, reply_mode: e.target.value })}>
              <option value="template">Template replies</option>
              <option value="ai">AI replies</option>
              <option value="manual">Manual replies</option>
            </Select>
          </>
        )}

        {accountType === "agency" && step === 2 && (
          <>
            <p className="text-sm text-gray-600 mb-3">Invite your client to view and approve replies on their company only.</p>
            <Input type="email" placeholder="client@example.com (optional)" value={form.invite_email} onChange={e => setForm({ ...form, invite_email: e.target.value })} />
          </>
        )}

        {accountType === "seller" && step === 1 && (
          <Select value={form.reply_mode} onChange={e => setForm({ ...form, reply_mode: e.target.value })}>
            <option value="template">Template — saved reply templates</option>
            <option value="ai">AI Reply — GPT generates replies</option>
            <option value="manual">Manual — write yourself</option>
          </Select>
        )}

        {steps[step].key === "done" && (
          <div className="text-center py-6">
            <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <p className="text-gray-600">
              {accountType === "agency"
                ? "Your agency workspace is ready. Add more client companies anytime from the header switcher."
                : "Your store is ready. Connect more platforms from the Platforms page."}
            </p>
            <button type="button" className="text-sm text-blue-600 mt-3 underline" onClick={() => setShowExtension(true)}>
              Optional: install Chrome extension for seller-portal AI reply
            </button>
          </div>
        )}

        <div className="flex gap-3 mt-6">
          {step > 0 && step < steps.length - 1 && (
            <Button variant="outline" onClick={() => setStep(s => s - 1)}>Back</Button>
          )}
          {(accountType === "agency" && step === 2) || (accountType === "seller" && step < steps.length - 1 && step !== steps.length - 2) ? (
            <Button variant="outline" onClick={skip}>Skip</Button>
          ) : null}
          <Button className="flex-1" onClick={next}>
            {step === steps.length - 1 ? "Go to Dashboard" : "Continue"}
          </Button>
        </div>
      </div>
      <ExtensionInstallModal open={showExtension} onClose={() => setShowExtension(false)} />
    </div>
  );
}
