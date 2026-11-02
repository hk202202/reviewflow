"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Select, Badge } from "@/components/ui/card";
import { stars, sentimentColor, statusColor, PLATFORMS } from "@/lib/utils";
import { Sparkles, FileText, Send, CheckSquare } from "lucide-react";

interface Review {
  id: number; reviewer_name: string; rating: number; title?: string; body: string;
  sentiment: string; reply_status: string; platform?: string; product_name?: string;
  is_flagged: boolean; flag_reason?: string; published_reply_text?: string;
}

interface Template {
  id: number; name: string; body: string; star_rating_filter: string;
}

export default function ReviewsPage() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState({ platform: "", rating: "", sentiment: "", reply_status: "", search: "" });
  const [selected, setSelected] = useState<number[]>([]);
  const [replyDraft, setReplyDraft] = useState<{ reviewId: number; replyId: number; body: string } | null>(null);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [templatePickerReviewId, setTemplatePickerReviewId] = useState<number | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [loading, setLoading] = useState(false);

  const load = () => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => { if (v) params.set(k, v); });
    api<{ items: Review[]; total: number }>(`/reviews?${params}`).then(d => { setReviews(d.items); setTotal(d.total); });
  };

  useEffect(() => { load(); }, [filters]);
  useEffect(() => { api<Template[]>("/templates").then(setTemplates).catch(() => {}); }, []);

  const generateAI = async (reviewId: number) => {
    setLoading(true);
    setTemplatePickerReviewId(null);
    try {
      const reply = await api<{ body: string; id: number }>("/ai/reply", { method: "POST", body: JSON.stringify({ review_id: reviewId }) });
      setReplyDraft({ reviewId, replyId: reply.id, body: reply.body });
    } finally { setLoading(false); }
  };

  const applyTemplate = async (reviewId: number, templateId: number) => {
    setLoading(true);
    setTemplatePickerReviewId(null);
    try {
      const reply = await api<{ body: string; id: number }>(
        `/replies/apply-template?review_id=${reviewId}&template_id=${templateId}`,
        { method: "POST" },
      );
      setReplyDraft({ reviewId, replyId: reply.id, body: reply.body });
      setSelectedTemplateId("");
    } finally { setLoading(false); }
  };

  const publishReply = async () => {
    if (!replyDraft) return;
    await api(`/replies/publish?review_id=${replyDraft.reviewId}&reply_id=${replyDraft.replyId}`, { method: "POST" });
    load();
    setReplyDraft(null);
  };

  const templatesForReview = (rating: number) =>
    templates.filter(t => t.star_rating_filter === "any" || t.star_rating_filter === String(rating));

  const toggleSelect = (id: number) => {
    setSelected(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Reviews</h1>
          <p className="text-gray-500 text-sm">{total} total reviews</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => {
            const input = document.createElement("input");
            input.type = "file"; input.accept = ".csv";
            input.onchange = async (e) => {
              const file = (e.target as HTMLInputElement).files?.[0];
              if (!file) return;
              const form = new FormData(); form.append("file", file);
              const token = localStorage.getItem("token");
              await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/reviews/import-csv`, {
                method: "POST", headers: { Authorization: `Bearer ${token}` }, body: form,
              });
              load();
            };
            input.click();
          }}>Import CSV</Button>
          <a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/reviews/export-csv`} target="_blank">
            <Button variant="outline">Export CSV</Button>
          </a>
        </div>
      </div>

      <div className="flex gap-3 flex-wrap">
        <Input placeholder="Search reviews..." value={filters.search} onChange={e => setFilters({ ...filters, search: e.target.value })} className="w-48" />
        <Select value={filters.platform} onChange={e => setFilters({ ...filters, platform: e.target.value })}>
          <option value="">All Platforms</option>
          {PLATFORMS.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </Select>
        <Select value={filters.rating} onChange={e => setFilters({ ...filters, rating: e.target.value })}>
          <option value="">All Ratings</option>
          {[5,4,3,2,1].map(r => <option key={r} value={r}>{r} stars</option>)}
        </Select>
        <Select value={filters.reply_status} onChange={e => setFilters({ ...filters, reply_status: e.target.value })}>
          <option value="">All Status</option>
          {["pending","draft","published","escalated"].map(s => <option key={s} value={s}>{s}</option>)}
        </Select>
      </div>

      {selected.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-2 flex items-center gap-3 text-sm">
          <CheckSquare className="w-4 h-4" />
          {selected.length} selected
          <Button size="sm" variant="outline">Bulk Apply Template</Button>
        </div>
      )}

      <div className="space-y-3">
        {reviews.map(review => (
          <Card key={review.id}>
            <CardContent className="py-4">
              <div className="flex items-start gap-3">
                <input type="checkbox" checked={selected.includes(review.id)} onChange={() => toggleSelect(review.id)} className="mt-1" />
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="font-medium">{review.reviewer_name}</span>
                    <span className="text-yellow-500 text-sm">{stars(review.rating)}</span>
                    <Badge className={sentimentColor(review.sentiment)}>{review.sentiment}</Badge>
                    <Badge className={statusColor(review.reply_status)}>{review.reply_status}</Badge>
                    {review.platform && <Badge className="bg-gray-100 text-gray-700 capitalize">{review.platform}</Badge>}
                    {review.is_flagged && <Badge className="bg-red-100 text-red-700">Flagged</Badge>}
                  </div>
                  {review.title && <div className="font-medium text-sm mb-1">{review.title}</div>}
                  <p className="text-sm text-gray-700">{review.body}</p>
                  {review.published_reply_text && (
                    <div className="mt-2 p-3 bg-green-50 rounded-lg text-sm border border-green-100">
                      <div className="text-xs text-green-600 font-medium mb-1">Published Reply</div>
                      {review.published_reply_text}
                    </div>
                  )}
                  {replyDraft?.reviewId === review.id && (
                    <div className="mt-3">
                      <textarea className="w-full border rounded-lg p-3 text-sm" rows={3} value={replyDraft.body}
                        onChange={e => setReplyDraft({ ...replyDraft, body: e.target.value })} />
                      <div className="flex gap-2 mt-2">
                        <Button size="sm" onClick={publishReply}>Publish</Button>
                        <Button size="sm" variant="outline" onClick={() => setReplyDraft(null)}>Cancel</Button>
                      </div>
                    </div>
                  )}
                </div>
                {review.reply_status === "pending" && !replyDraft && templatePickerReviewId !== review.id && (
                  <div className="flex gap-2 flex-shrink-0">
                    <Button size="sm" variant="outline" onClick={() => generateAI(review.id)} disabled={loading}>
                      <Sparkles className="w-3 h-3 mr-1" />AI Reply
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => { setTemplatePickerReviewId(review.id); setSelectedTemplateId(""); }} disabled={loading}>
                      <FileText className="w-3 h-3 mr-1" />Template
                    </Button>
                  </div>
                )}
                {templatePickerReviewId === review.id && !replyDraft && (
                  <div className="flex flex-col gap-2 flex-shrink-0 min-w-[200px]">
                    <Select value={selectedTemplateId} onChange={e => setSelectedTemplateId(e.target.value)}>
                      <option value="">Choose template...</option>
                      {templatesForReview(review.rating).map(t => (
                        <option key={t.id} value={t.id}>{t.name}</option>
                      ))}
                    </Select>
                    <div className="flex gap-2">
                      <Button size="sm" disabled={!selectedTemplateId || loading} onClick={() => applyTemplate(review.id, Number(selectedTemplateId))}>
                        Apply
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setTemplatePickerReviewId(null)}>Cancel</Button>
                    </div>
                    {templatesForReview(review.rating).length === 0 && (
                      <p className="text-xs text-gray-500">No templates for {review.rating}★. Create one in Templates.</p>
                    )}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
        {reviews.length === 0 && (
          <div className="text-center py-12 text-gray-500">No reviews found. Connect a platform to import reviews.</div>
        )}
      </div>
    </div>
  );
}
