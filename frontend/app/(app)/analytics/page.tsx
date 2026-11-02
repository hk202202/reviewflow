"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";

interface Analytics {
  total_reviews: number; pending_replies: number; published_replies: number;
  positive: number; negative: number; flagged: number; reply_rate: number;
  by_platform: Record<string, number>; by_rating: Record<number, number>;
}

const COLORS = ["#2563eb", "#16a34a", "#eab308", "#ef4444", "#8b5cf6"];

export default function AnalyticsPage() {
  const [stats, setStats] = useState<Analytics | null>(null);

  useEffect(() => {
    api<Analytics>("/analytics").then(setStats).catch(() => {});
  }, []);

  const platformData = stats ? Object.entries(stats.by_platform).map(([name, value]) => ({ name, value })) : [];
  const ratingData = stats ? Object.entries(stats.by_rating).map(([rating, count]) => ({ rating: `${rating}★`, count })) : [];
  const sentimentData = stats ? [
    { name: "Positive", value: stats.positive },
    { name: "Negative", value: stats.negative },
    { name: "Other", value: stats.total_reviews - stats.positive - stats.negative },
  ] : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Analytics</h1>
        <p className="text-gray-500 text-sm">Review performance and sentiment trends</p>
      </div>

      {stats && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "Total Reviews", value: stats.total_reviews },
              { label: "Reply Rate", value: `${stats.reply_rate}%` },
              { label: "Positive", value: stats.positive },
              { label: "Negative", value: stats.negative },
            ].map(s => (
              <Card key={s.label}><CardContent className="pt-4">
                <div className="text-2xl font-bold">{s.value}</div>
                <div className="text-sm text-gray-500">{s.label}</div>
              </CardContent></Card>
            ))}
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <Card>
              <CardContent>
                <h2 className="font-semibold mb-4">Reviews by Platform</h2>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={platformData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="value" fill="#2563eb" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardContent>
                <h2 className="font-semibold mb-4">Rating Distribution</h2>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={ratingData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="rating" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="count" fill="#16a34a" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardContent>
                <h2 className="font-semibold mb-4">Sentiment Breakdown</h2>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie data={sentimentData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                      {sentimentData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
