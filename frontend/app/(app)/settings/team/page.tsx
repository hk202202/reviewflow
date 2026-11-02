"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/card";
import { UserPlus, Mail } from "lucide-react";

interface Member { id: number; user_id: number; email: string; full_name: string; role: string; is_active: boolean; joined_at: string; }
interface Invite { id: number; email: string; role: string; created_at: string; }

export default function TeamPage() {
  const [members, setMembers] = useState<Member[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [showInvite, setShowInvite] = useState(false);
  const [inviteForm, setInviteForm] = useState({ email: "", role: "member" });

  const load = () => {
    api<Member[]>("/auth/team").then(setMembers).catch(() => {});
    api<Invite[]>("/auth/invitations").then(setInvites).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  const invite = async () => {
    await api("/auth/invite", { method: "POST", body: JSON.stringify(inviteForm) });
    setShowInvite(false);
    setInviteForm({ email: "", role: "member" });
    load();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Team Members</h1>
          <p className="text-gray-500 text-sm">{members.filter(m => m.is_active).length} active members</p>
        </div>
        <Button onClick={() => setShowInvite(true)}><UserPlus className="w-4 h-4 mr-1" />Invite Member</Button>
      </div>

      {showInvite && (
        <Card><CardContent className="space-y-4">
          <h2 className="font-semibold">Invite Team Member</h2>
          <Input type="email" placeholder="Email address" value={inviteForm.email} onChange={e => setInviteForm({ ...inviteForm, email: e.target.value })} />
          <Select value={inviteForm.role} onChange={e => setInviteForm({ ...inviteForm, role: e.target.value })}>
            <option value="admin">Admin</option>
            <option value="member">Member</option>
            <option value="viewer">Viewer</option>
          </Select>
          <div className="flex gap-2">
            <Button onClick={invite}>Send Invitation</Button>
            <Button variant="outline" onClick={() => setShowInvite(false)}>Cancel</Button>
          </div>
        </CardContent></Card>
      )}

      <Card>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead><tr className="border-b bg-gray-50">
              {["Name", "Email", "Role", "Status", "Joined"].map(h => (
                <th key={h} className="text-left px-4 py-3 font-medium text-gray-600">{h}</th>
              ))}
            </tr></thead>
            <tbody>
              {members.map(m => (
                <tr key={m.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{m.full_name}</td>
                  <td className="px-4 py-3 text-gray-600">{m.email}</td>
                  <td className="px-4 py-3 capitalize">{m.role}</td>
                  <td className="px-4 py-3"><span className={`px-2 py-0.5 rounded-full text-xs ${m.is_active ? "bg-green-100 text-green-700" : "bg-gray-100"}`}>{m.is_active ? "Active" : "Inactive"}</span></td>
                  <td className="px-4 py-3 text-gray-500">{new Date(m.joined_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {invites.length > 0 && (
        <Card>
          <CardContent>
            <h2 className="font-semibold mb-3 flex items-center gap-2"><Mail className="w-4 h-4" />Pending Invitations</h2>
            {invites.map(i => (
              <div key={i.id} className="flex items-center justify-between py-2 border-b last:border-0 text-sm">
                <span>{i.email}</span>
                <span className="capitalize text-gray-500">{i.role}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
