"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/card";
import { stars, statusColor } from "@/lib/utils";
import { AlertTriangle } from "lucide-react";

interface Review {
  id: number; reviewer_name: string; rating: number; body: string;
  flag_reason?: string; reply_status: string; platform?: string;
}

export default function EscalatedPage() {
  const [reviews, setReviews] = useState<Review[]>([]);

  useEffect(() => {
    api<Review[]>("/reviews/escalated").then(setReviews).catch(() => {});
  }, []);

  const resolve = async (id: number, action: string) => {
    await api(`/reviews/${id}/resolve-flag?action=${action}`, { method: "POST" });
    setReviews(prev => prev.filter(r => r.id !== id));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2"><AlertTriangle className="text-red-500" />Escalated Reviews</h1>
        <p className="text-gray-500 text-sm">Reviews flagged for human review before auto-reply</p>
      </div>
      {reviews.length === 0 ? (
        <Card><CardContent className="py-12 text-center text-gray-500">No escalated reviews. Great job!</CardContent></Card>
      ) : reviews.map(review => (
        <Card key={review.id} className="border-red-200">
          <CardContent className="py-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="font-medium">{review.reviewer_name}</span>
                  <span className="text-yellow-500 text-sm">{stars(review.rating)}</span>
                  <Badge className="bg-red-100 text-red-700">{review.flag_reason}</Badge>
                </div>
                <p className="text-sm text-gray-700">{review.body}</p>
              </div>
              <div className="flex gap-2 flex-shrink-0">
                <Button size="sm" onClick={() => resolve(review.id, "approve")}>Approve for AI</Button>
                <Button size="sm" variant="outline" onClick={() => resolve(review.id, "dismiss")}>Dismiss</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
