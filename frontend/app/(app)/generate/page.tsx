"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Textarea, Select } from "@/components/ui/card";
import { Sparkles } from "lucide-react";

export default function GeneratePage() {
  const [form, setForm] = useState({ product_title: "", product_features: "", rating_target: 5 });
  const [result, setResult] = useState<{ id: number; body: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    setLoading(true);
    try {
      const data = await api<{ id: number; body: string }>("/ai/generate-review", {
        method: "POST", body: JSON.stringify(form),
      });
      setResult(data);
    } finally { setLoading(false); }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold">AI Review Generator</h1>
        <p className="text-gray-500 text-sm">Generate authentic-sounding product reviews with unique personas</p>
      </div>

      <Card>
        <CardContent className="space-y-4">
          <Input placeholder="Product title" value={form.product_title} onChange={e => setForm({ ...form, product_title: e.target.value })} />
          <Textarea placeholder="Product features (optional)" rows={3} value={form.product_features} onChange={e => setForm({ ...form, product_features: e.target.value })} />
          <Select value={form.rating_target} onChange={e => setForm({ ...form, rating_target: Number(e.target.value) })}>
            {[5,4,3,2,1].map(r => <option key={r} value={r}>{r} stars</option>)}
          </Select>
          <Button onClick={generate} disabled={loading || !form.product_title}>
            <Sparkles className="w-4 h-4 mr-1" />{loading ? "Generating..." : "Generate Review"}
          </Button>
        </CardContent>
      </Card>

      {result && (
        <Card className="border-green-200">
          <CardContent>
            <h2 className="font-semibold mb-2 text-green-700">Generated Review</h2>
            <p className="text-sm text-gray-700 whitespace-pre-wrap">{result.body}</p>
            <div className="flex gap-2 mt-4">
              <Button size="sm" variant="outline" onClick={() => navigator.clipboard.writeText(result.body)}>Copy</Button>
              <Button size="sm" variant="outline" onClick={generate}>Regenerate</Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
