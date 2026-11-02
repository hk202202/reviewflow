const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class TrialExpiredError extends Error {
  billingUrl: string;
  constructor(message: string, billingUrl = "/settings/billing") {
    super(message);
    this.name = "TrialExpiredError";
    this.billingUrl = billingUrl;
  }
}

export async function api<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}/api${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    if (res.status === 402 && typeof err.detail === "object" && err.detail?.code === "trial_expired") {
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/settings/billing")) {
        window.location.href = err.detail.billing_url || "/settings/billing";
      }
      throw new TrialExpiredError(err.detail.message || "Trial expired");
    }
    const detail = typeof err.detail === "string" ? err.detail : err.detail?.message || JSON.stringify(err.detail);
    throw new Error(detail || "Request failed");
  }
  return res.json();
}

export function setToken(token: string) {
  localStorage.setItem("token", token);
}

export function setActiveOrgId(orgId: number) {
  localStorage.setItem("active_org_id", String(orgId));
}

export function getActiveOrgId(): number | null {
  if (typeof window === "undefined") return null;
  const v = localStorage.getItem("active_org_id");
  return v ? parseInt(v, 10) : null;
}

export function clearToken() {
  localStorage.removeItem("token");
  localStorage.removeItem("active_org_id");
}

export function getToken() {
  return typeof window !== "undefined" ? localStorage.getItem("token") : null;
}

export { API_URL };
