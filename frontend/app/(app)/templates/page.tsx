"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Textarea, Select } from "@/components/ui/card";
import { TEMPLATE_CATEGORIES } from "@/lib/utils";
import { Plus, Trash2 } from "lucide-react";

interface Template {
  id: number; name: string; description?: string; body: string;
  category: string; star_rating_filter: string; usage_count: number;
}

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", body: "", category: "thank_you", star_rating_filter: "any" });

  const load = () => api<Template[]>("/templates").then(setTemplates).catch(() => {});
  useEffect(() => { load(); }, []);

  const create = async () => {
    await api("/templates", { method: "POST", body: JSON.stringify(form) });
    setShowForm(false);
    setForm({ name: "", description: "", body: "", category: "thank_you", star_rating_filter: "any" });
    load();
  };

  const remove = async (id: number) => {
    await api(`/templates/${id}`, { method: "DELETE" });
    load();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Reply Templates</h1>
          <p className="text-gray-500 text-sm">Save and reuse reply templates with smart placeholders</p>
        </div>
        <Button onClick={() => setShowForm(true)}><Plus className="w-4 h-4 mr-1" />New Template</Button>
      </div>

      {showForm && (
        <Card>
          <CardContent className="space-y-4">
            <h2 className="font-semibold">Create Template</h2>
            <Input placeholder="Template name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
            <div className="grid grid-cols-2 gap-4">
              <Select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>
                {TEMPLATE_CATEGORIES.map(c => <option key={c} value={c}>{c.replace("_", " ")}</option>)}
              </Select>
              <Select value={form.star_rating_filter} onChange={e => setForm({ ...form, star_rating_filter: e.target.value })}>
                <option value="any">Any Rating</option>
                {[5,4,3,2,1].map(r => <option key={r} value={String(r)}>{r} stars</option>)}
              </Select>
            </div>
            <Textarea placeholder="Template body. Use {{reviewer_name}}, {{product_name}}, {{rating}}, {{platform}}, {{issue_keyword}}, {{brand_name}}" rows={5} value={form.body} onChange={e => setForm({ ...form, body: e.target.value })} />
            <div className="flex gap-2">
              <Button onClick={create}>Save Template</Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        {templates.map(t => (
          <Card key={t.id}>
            <CardContent>
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h3 className="font-semibold">{t.name}</h3>
                  <div className="flex gap-2 mt-1">
                    <span className="text-xs px-2 py-0.5 bg-gray-100 rounded-full capitalize">{t.category.replace("_", " ")}</span>
                    <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full">{t.star_rating_filter === "any" ? "Any rating" : `${t.star_rating_filter}★`}</span>
                  </div>
                </div>
                <button onClick={() => remove(t.id)} className="text-gray-400 hover:text-red-500"><Trash2 className="w-4 h-4" /></button>
              </div>
              <p className="text-sm text-gray-600 line-clamp-3">{t.body}</p>
              <div className="text-xs text-gray-400 mt-2">Used {t.usage_count} times</div>
            </CardContent>
          </Card>
        ))}
        {templates.length === 0 && !showForm && (
          <div className="col-span-2 text-center py-12 text-gray-500">No templates yet. Create your first template.</div>
        )}
      </div>
    </div>
  );
}
