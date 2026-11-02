"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Bell } from "lucide-react";

interface Notif { id: number; type: string; title: string; body: string; action_url?: string; read_at?: string; created_at: string; }

export default function NotificationBell() {
  const [notifications, setNotifications] = useState<Notif[]>([]);
  const [open, setOpen] = useState(false);
  const unread = notifications.filter(n => !n.read_at).length;

  useEffect(() => {
    api<Notif[]>("/notifications").then(setNotifications).catch(() => {});
  }, []);

  const markRead = async (id: number) => {
    await api(`/notifications/${id}/read`, { method: "POST" });
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read_at: new Date().toISOString() } : n));
  };

  return (
    <div className="relative">
      <button onClick={() => setOpen(!open)} className="relative p-2 rounded-lg hover:bg-gray-100">
        <Bell className="w-5 h-5 text-gray-600" />
        {unread > 0 && <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">{unread}</span>}
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-white rounded-xl shadow-lg border border-gray-200 z-50 max-h-96 overflow-y-auto">
          <div className="px-4 py-3 border-b font-medium text-sm">Notifications</div>
          {notifications.length === 0 ? (
            <div className="p-4 text-sm text-gray-500 text-center">No notifications</div>
          ) : notifications.map(n => (
            <div key={n.id} className={`px-4 py-3 border-b hover:bg-gray-50 cursor-pointer ${!n.read_at ? "bg-blue-50/50" : ""}`}
              onClick={() => { markRead(n.id); if (n.action_url) window.location.href = n.action_url; }}>
              <div className="text-sm font-medium">{n.title}</div>
              <div className="text-xs text-gray-500 mt-0.5">{n.body.slice(0, 80)}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
