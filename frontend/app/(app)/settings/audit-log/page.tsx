"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";

interface AuditEntry { id: number; action: string; target_type?: string; target_id?: number; payload?: Record<string, unknown>; created_at: string; }

export default function AuditLogPage() {
  const [logs, setLogs] = useState<AuditEntry[]>([]);

  useEffect(() => {
    api<AuditEntry[]>("/audit-log").then(setLogs).catch(() => {});
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Audit Log</h1>
        <p className="text-gray-500 text-sm">Track all actions across your organization</p>
      </div>
      <Card>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead><tr className="border-b bg-gray-50">
              {["Action", "Target", "Details", "Time"].map(h => (
                <th key={h} className="text-left px-4 py-3 font-medium text-gray-600">{h}</th>
              ))}
            </tr></thead>
            <tbody>
              {logs.map(l => (
                <tr key={l.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium capitalize">{l.action.replace(/_/g, " ")}</td>
                  <td className="px-4 py-3 text-gray-600">{l.target_type} #{l.target_id}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{l.payload ? JSON.stringify(l.payload).slice(0, 60) : "—"}</td>
                  <td className="px-4 py-3 text-gray-500">{new Date(l.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {logs.length === 0 && <div className="text-center py-8 text-gray-500">No audit entries yet</div>}
        </CardContent>
      </Card>
    </div>
  );
}
