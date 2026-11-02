"use client";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/card";
import { api, setToken } from "@/lib/api";

export default function AcceptInviteForm() {
  const params = useSearchParams();
  const token = params.get("token") || "";
  const [form, setForm] = useState({ full_name: "", password: "" });
  const [error, setError] = useState("");

  const accept = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const data = await api<{ access_token: string }>("/auth/accept-invite", {
        method: "POST", body: JSON.stringify({ token, ...form }),
      });
      setToken(data.access_token);
      window.location.href = "/dashboard";
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to accept invite");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
        <h1 className="text-xl font-bold mb-6">Accept Invitation</h1>
        <form onSubmit={accept} className="space-y-4">
          <Input placeholder="Full name" value={form.full_name} onChange={e => setForm({ ...form, full_name: e.target.value })} required />
          <Input type="password" placeholder="Create password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} required />
          {error && <p className="text-red-600 text-sm">{error}</p>}
          <Button type="submit" className="w-full">Join Organization</Button>
        </form>
      </div>
    </div>
  );
}
