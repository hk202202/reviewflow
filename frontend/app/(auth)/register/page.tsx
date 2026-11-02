"use client";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/card";
import { api, setToken, setActiveOrgId } from "@/lib/api";
import type { AccountType } from "@/lib/plans";
import Link from "next/link";
import { Building2, Store } from "lucide-react";

function RegisterForm() {
  const searchParams = useSearchParams();
  const initialType = searchParams.get("type") === "agency" ? "agency" : "seller";
  const [accountType, setAccountType] = useState<AccountType>(initialType);
  const [form, setForm] = useState({ email: "", password: "", full_name: "", org_name: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const t = searchParams.get("type");
    if (t === "agency" || t === "seller") setAccountType(t);
  }, [searchParams]);

  const orgLabel = accountType === "agency" ? "Agency / company name" : "Store / brand name";

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const data = await api<{ access_token: string; org_id: number }>("/auth/register", {
        method: "POST",
        body: JSON.stringify({ ...form, account_type: accountType }),
      });
      setToken(data.access_token);
      setActiveOrgId(data.org_id);
      window.location.href = "/onboarding";
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
        <div className="flex items-center gap-2 mb-6">
          <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center text-white font-bold">RF</div>
          <div>
            <h1 className="text-xl font-bold">Create Account</h1>
            <p className="text-sm text-gray-500">For sellers or review-management agencies</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 mb-6">
          <button
            type="button"
            onClick={() => setAccountType("seller")}
            className={`p-3 rounded-xl border text-left transition-colors ${accountType === "seller" ? "border-blue-500 bg-blue-50 ring-2 ring-blue-500" : "border-gray-200 hover:bg-gray-50"}`}
          >
            <Store className="w-5 h-5 text-blue-600 mb-1" />
            <div className="font-medium text-sm">Direct seller</div>
            <div className="text-xs text-gray-500">My own store</div>
          </button>
          <button
            type="button"
            onClick={() => setAccountType("agency")}
            className={`p-3 rounded-xl border text-left transition-colors ${accountType === "agency" ? "border-blue-500 bg-blue-50 ring-2 ring-blue-500" : "border-gray-200 hover:bg-gray-50"}`}
          >
            <Building2 className="w-5 h-5 text-blue-600 mb-1" />
            <div className="font-medium text-sm">Agency</div>
            <div className="text-xs text-gray-500">Multiple clients</div>
          </button>
        </div>

        <form onSubmit={handleRegister} className="space-y-4">
          {[
            { key: "full_name", label: "Full Name", type: "text" },
            { key: "org_name", label: orgLabel, type: "text" },
            { key: "email", label: "Email", type: "email" },
            { key: "password", label: "Password", type: "password" },
          ].map(({ key, label, type }) => (
            <div key={key}>
              <label className="text-sm font-medium text-gray-700">{label}</label>
              <Input type={type} value={form[key as keyof typeof form]} onChange={e => setForm({ ...form, [key]: e.target.value })} required className="mt-1" />
            </div>
          ))}
          {error && <p className="text-red-600 text-sm">{error}</p>}
          <Button type="submit" className="w-full" disabled={loading}>{loading ? "Creating..." : "Create Account"}</Button>
        </form>
        <p className="text-center text-sm text-gray-500 mt-4">
          Already have an account? <Link href="/login" className="text-blue-600 hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading...</div>}>
      <RegisterForm />
    </Suspense>
  );
}
