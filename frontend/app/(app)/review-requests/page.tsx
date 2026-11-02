"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/card";
import { Mail } from "lucide-react";

export default function ReviewRequestsPage() {
  const [form, setForm] = useState({ recipient_email: "", product_title: "", send_after_days: 7 });
  const [sent, setSent] = useState(false);

  const submit = async () => {
    await api(`/review-requests?recipient_email=${encodeURIComponent(form.recipient_email)}&product_title=${encodeURIComponent(form.product_title)}&send_after_days=${form.send_after_days}`, { method: "POST" });
    setSent(true);
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold">Review Requests</h1>
        <p className="text-gray-500 text-sm">Send post-purchase emails asking buyers to leave a review</p>
      </div>
      <Card>
        <CardContent className="space-y-4">
          <Input type="email" placeholder="Buyer email" value={form.recipient_email} onChange={e => setForm({ ...form, recipient_email: e.target.value })} />
          <Input placeholder="Product title" value={form.product_title} onChange={e => setForm({ ...form, product_title: e.target.value })} />
          <Input type="number" placeholder="Send after days" value={form.send_after_days} onChange={e => setForm({ ...form, send_after_days: Number(e.target.value) })} />
          <Button onClick={submit}><Mail className="w-4 h-4 mr-1" />Schedule Request</Button>
          {sent && <p className="text-green-600 text-sm">Review request scheduled!</p>}
        </CardContent>
      </Card>
    </div>
  );
}
