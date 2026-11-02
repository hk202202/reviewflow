import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const PLATFORMS = [
  { id: "amazon", name: "Amazon", color: "bg-orange-100 text-orange-800" },
  { id: "flipkart", name: "Flipkart", color: "bg-blue-100 text-blue-800" },
  { id: "myntra", name: "Myntra", color: "bg-pink-100 text-pink-800" },
  { id: "google_business", name: "Google Business", color: "bg-green-100 text-green-800" },
];

export const REPLY_MODES = [
  { id: "template", name: "Template", description: "Use saved reply templates" },
  { id: "ai", name: "AI Reply", description: "GPT-4o generates personalized replies" },
  { id: "manual", name: "Manual", description: "Write replies yourself" },
];

export const TEMPLATE_CATEGORIES = [
  "thank_you", "apology", "issue_resolution", "follow_up", "neutral",
];

export function stars(rating: number) {
  return "★".repeat(rating) + "☆".repeat(5 - rating);
}

export function sentimentColor(s: string) {
  if (s === "positive") return "text-green-600 bg-green-50";
  if (s === "negative") return "text-red-600 bg-red-50";
  return "text-yellow-600 bg-yellow-50";
}

export function statusColor(s: string) {
  const map: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    draft: "bg-blue-100 text-blue-800",
    published: "bg-green-100 text-green-800",
    escalated: "bg-red-100 text-red-800",
    skipped: "bg-gray-100 text-gray-800",
  };
  return map[s] || "bg-gray-100 text-gray-800";
}
