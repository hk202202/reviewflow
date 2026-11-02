"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { MessageSquare, Clock, CheckCircle, AlertTriangle, TrendingUp } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import SubscriptionBanner, { SubscriptionStatus } from "@/components/subscription-banner";

interface Analytics {
  total_reviews: number; pending_replies: number; published_replies: number;
  positive: number; negative: number; flagged: number; reply_rate: number;
  by_platform: Record<string, number>; by_rating: Record<number, number>;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Analytics | null>(null);
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [recentReviews, setRecentReviews] = useState<Array<{ id: number; reviewer_name: string; rating: number; body: string; reply_status: string; platform?: string }>>([]);

  useEffect(() => {
    api<SubscriptionStatus>("/billing/status").then(setSubscription).catch(() => {});
    api<Analytics>("/analytics").then(setStats).catch(() => {});
    api<{ items: typeof recentReviews }>("/reviews?page_size=5").then(d => setRecentReviews(d.items)).catch(() => {});
  }, []);

  const cards = stats ? [
    { label: "Total Reviews", value: stats.total_reviews, icon: MessageSquare, color: "text-blue-600 bg-blue-50" },
    { label: "Pending Replies", value: stats.pending_replies, icon: Clock, color: "text-yellow-600 bg-yellow-50" },
    { label: "Published", value: stats.published_replies, icon: CheckCircle, color: "text-green-600 bg-green-50" },
    { label: "Flagged", value: stats.flagged, icon: AlertTriangle, color: "text-red-600 bg-red-50" },
    { label: "Reply Rate", value: `${stats.reply_rate}%`, icon: TrendingUp, color: "text-purple-600 bg-purple-50" },
  ] : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-gray-500 text-sm">Overview of your review management</p>
        </div>
        <Link href="/reviews"><Button>View All Reviews</Button></Link>
      </div>

      <SubscriptionBanner status={subscription} variant="dashboard" />

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {cards.map(c => (
          <Card key={c.label}>
            <CardContent className="pt-4">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${c.color} mb-3`}>
                <c.icon className="w-5 h-5" />
              </div>
              <div className="text-2xl font-bold">{c.value}</div>
              <div className="text-sm text-gray-500">{c.label}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {stats && Object.keys(stats.by_platform).length > 0 && (
        <Card>
          <CardContent>
            <h2 className="font-semibold mb-4">Reviews by Platform</h2>
            <div className="flex gap-4 flex-wrap">
              {Object.entries(stats.by_platform).map(([platform, count]) => (
                <div key={platform} className="text-center">
                  <div className="text-2xl font-bold">{count}</div>
                  <div className="text-sm text-gray-500 capitalize">{platform}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Recent Reviews</h2>
            <Link href="/reviews" className="text-sm text-blue-600 hover:underline">View all</Link>
          </div>
          {recentReviews.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <p>No reviews yet.</p>
              <Link href="/platforms"><Button variant="outline" className="mt-3">Connect a Platform</Button></Link>
            </div>
          ) : recentReviews.map(r => (
            <div key={r.id} className="flex items-start gap-4 py-3 border-b last:border-0">
              <div className="text-yellow-500 text-sm">{"★".repeat(r.rating)}</div>
              <div className="flex-1">
                <div className="font-medium text-sm">{r.reviewer_name}</div>
                <div className="text-sm text-gray-600 line-clamp-1">{r.body}</div>
              </div>
              <span className="text-xs px-2 py-1 rounded-full bg-gray-100 capitalize">{r.reply_status}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
