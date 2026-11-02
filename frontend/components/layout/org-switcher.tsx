"use client";
import { useCallback, useEffect, useState } from "react";
import { api, setToken, setActiveOrgId } from "@/lib/api";
import type { AccountContext } from "@/lib/plans";
import { Building2, Check, ChevronDown, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/card";
import Link from "next/link";

interface OrgItem {
  id: number;
  name: string;
  role: string;
  platform_count: number;
  is_current: boolean;
}

export default function OrgSwitcher() {
  const [ctx, setCtx] = useState<AccountContext | null>(null);
  const [open, setOpen] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [newOrgName, setNewOrgName] = useState("");
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api<AccountContext>("/auth/account-context").then(setCtx).catch(() => {});
  }, []);

  useEffect(() => { load(); }, [load]);

  if (!ctx) return null;

  const orgs = ctx.organizations ?? [];
  const current = orgs.find(o => o.is_current);

  if (!current) return null;

  const switchOrg = async (orgId: number) => {
    if (orgId === current?.id) {
      setOpen(false);
      return;
    }
    setLoading(true);
    try {
      const result = await api<{ access_token: string; org_id: number }>("/auth/switch-org", {
        method: "POST",
        body: JSON.stringify({ org_id: orgId }),
      });
      setToken(result.access_token);
      setActiveOrgId(result.org_id);
      setOpen(false);
      window.location.href = "/dashboard";
    } catch {
      setLoading(false);
    }
  };

  const createOrg = async () => {
    if (!newOrgName.trim()) return;
    setCreating(true);
    setError("");
    try {
      const result = await api<{ access_token: string; org_id: number }>("/auth/organizations", {
        method: "POST",
        body: JSON.stringify({ org_name: newOrgName.trim() }),
      });
      setToken(result.access_token);
      setActiveOrgId(result.org_id);
      setNewOrgName("");
      setShowCreate(false);
      setOpen(false);
      window.location.href = "/platforms";
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Could not create company");
    } finally {
      setCreating(false);
    }
  };

  if (!ctx.show_company_switcher) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-gray-100 bg-gray-50 text-sm max-w-[220px]">
        <Building2 className="w-4 h-4 text-gray-500 shrink-0" />
        <span className="truncate font-medium text-gray-700">{current.name}</span>
      </div>
    );
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 text-sm max-w-[220px]"
        title="Switch company"
      >
        <Building2 className="w-4 h-4 text-blue-600 shrink-0" />
        <span className="truncate font-medium">{current.name}</span>
        <ChevronDown className="w-3.5 h-3.5 text-gray-400 shrink-0" />
      </button>

      {open && (
        <>
          <button
            type="button"
            className="fixed inset-0 z-40"
            aria-label="Close company menu"
            onClick={() => { setOpen(false); setShowCreate(false); setError(""); }}
          />
          <div className="absolute right-0 top-full mt-2 z-50 w-72 bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden">
            <div className="px-3 py-2 border-b bg-gray-50">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                {ctx.account_type === "agency" ? "Client companies" : "Your companies"}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                {ctx.owned_companies} company{ctx.owned_companies !== 1 ? "ies" : ""} · {ctx.plan_label} plan
              </p>
            </div>
            <ul className="max-h-64 overflow-y-auto py-1">
              {orgs.map(org => (
                <li key={org.id}>
                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => switchOrg(org.id)}
                    className="w-full flex items-start gap-2 px-3 py-2.5 hover:bg-blue-50 text-left disabled:opacity-50"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm truncate">{org.name}</div>
                      <div className="text-xs text-gray-500">
                        {org.platform_count} platform{org.platform_count !== 1 ? "s" : ""} · {org.role}
                      </div>
                    </div>
                    {org.is_current && <Check className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />}
                  </button>
                </li>
              ))}
            </ul>
            <div className="border-t p-2">
              {ctx.can_add_company ? (
                !showCreate ? (
                  <Button variant="outline" size="sm" className="w-full justify-start" onClick={() => setShowCreate(true)}>
                    <Plus className="w-3.5 h-3.5 mr-1" />
                    Add client company
                  </Button>
                ) : (
                  <div className="space-y-2">
                    <Input
                      placeholder="Company name (e.g. Client Brand Ltd)"
                      value={newOrgName}
                      onChange={e => setNewOrgName(e.target.value)}
                      onKeyDown={e => e.key === "Enter" && createOrg()}
                    />
                    {error && <p className="text-xs text-red-600">{error}</p>}
                    <div className="flex gap-2">
                      <Button size="sm" className="flex-1" onClick={createOrg} disabled={creating}>
                        {creating ? "Creating…" : "Create"}
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
                    </div>
                  </div>
                )
              ) : (
                <p className="text-xs text-gray-500 px-1">
                  Company limit reached.{" "}
                  <Link href="/settings/billing" className="text-blue-600 hover:underline">Upgrade to Agency</Link>
                </p>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
