"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/card";
import { Shield, Smartphone } from "lucide-react";

export default function SecurityPage() {
  const [totpSetup, setTotpSetup] = useState<{ secret: string; qr_uri: string; backup_codes: string[] } | null>(null);
  const [totpCode, setTotpCode] = useState("");
  const [ssoForm, setSsoForm] = useState({ provider: "google_workspace", protocol: "oidc", client_id: "", is_active: false });

  const setup2FA = async () => {
    const data = await api<typeof totpSetup>("/auth/2fa/setup", { method: "POST" });
    setTotpSetup(data);
  };

  const verify2FA = async () => {
    await api("/auth/2fa/verify", { method: "POST", body: JSON.stringify({ code: totpCode }) });
    alert("2FA enabled successfully!");
  };

  const saveSSO = async () => {
    await api("/auth/sso/config", { method: "POST", body: JSON.stringify(ssoForm) });
    alert("SSO configuration saved");
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold">Security Settings</h1>
        <p className="text-gray-500 text-sm">Manage 2FA and SSO configuration</p>
      </div>

      <Card>
        <CardContent className="space-y-4">
          <h2 className="font-semibold flex items-center gap-2"><Smartphone className="w-4 h-4" />Two-Factor Authentication</h2>
          {!totpSetup ? (
            <Button onClick={setup2FA}>Enable 2FA</Button>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-gray-600">Scan this secret in your authenticator app: <code className="bg-gray-100 px-2 py-0.5 rounded">{totpSetup.secret}</code></p>
              <Input placeholder="Enter 6-digit code" value={totpCode} onChange={e => setTotpCode(e.target.value)} />
              <Button onClick={verify2FA}>Verify & Enable</Button>
              <div className="text-xs text-gray-500">
                Backup codes: {totpSetup.backup_codes.join(", ")}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-4">
          <h2 className="font-semibold flex items-center gap-2"><Shield className="w-4 h-4" />SSO Configuration (Enterprise)</h2>
          <Select value={ssoForm.provider} onChange={e => setSsoForm({ ...ssoForm, provider: e.target.value })}>
            <option value="google_workspace">Google Workspace</option>
            <option value="microsoft_entra">Microsoft Entra ID</option>
            <option value="okta">Okta</option>
            <option value="saml_generic">Custom SAML</option>
            <option value="oidc_generic">Custom OIDC</option>
          </Select>
          <Select value={ssoForm.protocol} onChange={e => setSsoForm({ ...ssoForm, protocol: e.target.value })}>
            <option value="oidc">OIDC</option>
            <option value="saml">SAML 2.0</option>
          </Select>
          <Input placeholder="Client ID" value={ssoForm.client_id} onChange={e => setSsoForm({ ...ssoForm, client_id: e.target.value })} />
          <Button onClick={saveSSO}>Save SSO Config</Button>
        </CardContent>
      </Card>
    </div>
  );
}
