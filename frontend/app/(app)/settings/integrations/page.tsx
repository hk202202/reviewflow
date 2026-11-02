"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/card";
import { Plus } from "lucide-react";

interface Webhook { id: number; name: string; url: string; events: string[]; is_active: boolean; failure_count: number; }

const EVENTS = ["review.created", "review.reply_published", "review.flagged", "sync.failed", "quota.warning"];

export default function IntegrationsPage() {
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", url: "", events: ["review.created"] as string[] });

  const load = () => api<Webhook[]>("/webhooks").then(setWebhooks).catch(() => {});
  useEffect(() => { load(); }, []);

  const create = async () => {
    await api(`/webhooks?name=${encodeURIComponent(form.name)}&url=${encodeURIComponent(form.url)}&events=${form.events.join(",")}`, { method: "POST" });
    setShowForm(false);
    load();
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Integrations</h1>
          <p className="text-gray-500 text-sm">Webhooks and Zapier connections</p>
        </div>
        <Button onClick={() => setShowForm(true)}><Plus className="w-4 h-4 mr-1" />Add Webhook</Button>
      </div>

      {showForm && (
        <Card><CardContent className="space-y-4">
          <Input placeholder="Webhook name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
          <Input placeholder="https://your-app.com/webhook" value={form.url} onChange={e => setForm({ ...form, url: e.target.value })} />
          <div className="space-y-2">
            <p className="text-sm font-medium">Events</p>
            {EVENTS.map(ev => (
              <label key={ev} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.events.includes(ev)}
                  onChange={e => setForm({ ...form, events: e.target.checked ? [...form.events, ev] : form.events.filter(x => x !== ev) })} />
                {ev}
              </label>
            ))}
          </div>
          <div className="flex gap-2">
            <Button onClick={create}>Save Webhook</Button>
            <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
          </div>
        </CardContent></Card>
      )}

      {webhooks.map(wh => (
        <Card key={wh.id}><CardContent>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold">{wh.name}</h3>
              <p className="text-sm text-gray-500">{wh.url}</p>
              <div className="flex gap-1 mt-1">{wh.events?.map(e => <span key={e} className="text-xs bg-gray-100 px-2 py-0.5 rounded">{e}</span>)}</div>
            </div>
            <span className={`text-xs px-2 py-0.5 rounded-full ${wh.is_active ? "bg-green-100 text-green-700" : "bg-gray-100"}`}>{wh.is_active ? "Active" : "Inactive"}</span>
          </div>
        </CardContent></Card>
      ))}
    </div>
  );
}
