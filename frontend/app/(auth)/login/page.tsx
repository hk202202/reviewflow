"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/card";
import { api, setToken, setActiveOrgId, getActiveOrgId } from "@/lib/api";
import Link from "next/link";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [needs2fa, setNeeds2fa] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const data = await api<{ access_token: string; requires_2fa: boolean; user_id: number; org_id: number }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email, password,
          totp_code: totp || undefined,
          org_id: getActiveOrgId() || undefined,
        }),
      });
      if (data.requires_2fa) { setNeeds2fa(true); return; }
      setToken(data.access_token);
      setActiveOrgId(data.org_id);
      window.location.href = "/dashboard";
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
        <div className="flex items-center gap-2 mb-8">
          <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center text-white font-bold">RF</div>
          <div>
            <h1 className="text-xl font-bold">ReviewFlow</h1>
            <p className="text-sm text-gray-500">Sign in to your account</p>
          </div>
        </div>
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="text-sm font-medium text-gray-700">Email</label>
            <Input type="email" value={email} onChange={e => setEmail(e.target.value)} required className="mt-1" />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">Password</label>
            <Input type="password" value={password} onChange={e => setPassword(e.target.value)} required className="mt-1" />
          </div>
          {needs2fa && (
            <div>
              <label className="text-sm font-medium text-gray-700">2FA Code</label>
              <Input type="text" value={totp} onChange={e => setTotp(e.target.value)} placeholder="6-digit code" className="mt-1" />
            </div>
          )}
          {error && <p className="text-red-600 text-sm">{error}</p>}
          <Button type="submit" className="w-full" disabled={loading}>{loading ? "Signing in..." : "Sign In"}</Button>
        </form>
        <p className="text-center text-sm text-gray-500 mt-4">
          No account? <Link href="/register" className="text-blue-600 hover:underline">Create one</Link>
        </p>
      </div>
    </div>
  );
}
