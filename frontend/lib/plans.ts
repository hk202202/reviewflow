export type AccountType = "seller" | "agency";
export type PlanId = "solo" | "growth" | "professional" | "enterprise";

export interface PlanDef {
  id: PlanId;
  name: string;
  audience: string;
  segment: AccountType | "both";
  description: string;
  highlights: string[];
  popular?: boolean;
  prices: { monthly: number; biannual: number; annual: number };
}

export const PLANS: PlanDef[] = [
  {
    id: "solo",
    name: "Solo",
    audience: "Direct seller",
    segment: "seller",
    description: "One brand, one login — for individual Amazon/Flipkart sellers.",
    highlights: ["1 company", "2 platforms", "500 reviews/mo", "100 AI replies/mo"],
    prices: { monthly: 999, biannual: 849, annual: 749 },
  },
  {
    id: "growth",
    name: "Business",
    audience: "Direct seller",
    segment: "seller",
    description: "Growing stores with more marketplaces and a small team.",
    highlights: ["1 company", "5 platforms", "500 reviews/mo", "2 team members"],
    prices: { monthly: 1499, biannual: 1274, annual: 1124 },
  },
  {
    id: "professional",
    name: "Agency",
    audience: "Agency",
    segment: "agency",
    description: "Manage multiple client brands from one login.",
    highlights: ["10 companies", "20 platforms each", "5 team seats", "Client invites"],
    popular: true,
    prices: { monthly: 3999, biannual: 3399, annual: 2999 },
  },
  {
    id: "enterprise",
    name: "Agency Pro",
    audience: "Agency",
    segment: "agency",
    description: "Unlimited clients, SSO, and dedicated support.",
    highlights: ["Unlimited companies", "Unlimited platforms", "SSO", "Dedicated CSM"],
    prices: { monthly: 9999, biannual: 8499, annual: 7499 },
  },
];

export function plansForAccountType(accountType: AccountType): PlanDef[] {
  if (accountType === "agency") {
    return PLANS.filter(p => p.segment === "agency");
  }
  return PLANS.filter(p => p.segment === "seller");
}

export interface AccountContext {
  account_type: AccountType;
  effective_plan: string;
  plan_label: string;
  can_add_company: boolean;
  can_add_platform: boolean;
  can_invite_member: boolean;
  show_company_switcher: boolean;
  owned_companies: number;
  platform_count: number;
  team_count: number;
  limits: {
    max_companies: number | null;
    max_platforms_per_org: number | null;
    max_team_members: number | null;
    label: string;
  };
  organizations: Array<{
    id: number;
    name: string;
    role: string;
    platform_count: number;
    is_current: boolean;
  }>;
}
