"use client";
import { useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/card";
import { PLATFORMS, REPLY_MODES } from "@/lib/utils";
import { ExtensionInstallModal } from "@/components/layout/extension-banner";
import { syncExtensionConnection } from "@/components/layout/extension-token-bridge";
import { Plus, RefreshCw, Puzzle, Link2, CheckCircle2, AlertCircle, ShoppingBag, ExternalLink } from "lucide-react";

interface Platform { id: number; platform: string; display_name: string; default_reply_mode: string; is_active: boolean; last_synced_at?: string; }

const EXTENSION_OPTIONAL_PLATFORMS = ["amazon", "flipkart", "myntra", "meesho", "google_business"];

const AMAZON_DEFAULTS = {
  client_id: "",
  client_secret: "",
  refresh_token: "",
  marketplace_id: "A21TJRUUN4KGV",
  region: "eu",
  asins: "",
};

const FLIPKART_DEFAULTS = { client_id: "", client_secret: "", seller_id: "" };
const MYNTRA_DEFAULTS = { api_key: "", api_secret: "", seller_id: "" };

export default function PlatformsPage() {
  const searchParams = useSearchParams();
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [showExtensionModal, setShowExtensionModal] = useState(false);
  const [pendingExtensionPlatform, setPendingExtensionPlatform] = useState<string | null>(null);
  const [form, setForm] = useState({ platform: "amazon", display_name: "", default_reply_mode: "template" });
  const [amazonCreds, setAmazonCreds] = useState(AMAZON_DEFAULTS);
  const [flipkartCreds, setFlipkartCreds] = useState(FLIPKART_DEFAULTS);
  const [myntraCreds, setMyntraCreds] = useState(MYNTRA_DEFAULTS);
  const [validatingAmazon, setValidatingAmazon] = useState(false);
  const [validatingFlipkart, setValidatingFlipkart] = useState(false);
  const [validatingMyntra, setValidatingMyntra] = useState(false);
  const [amazonValid, setAmazonValid] = useState<string | null>(null);
  const [syncing, setSyncing] = useState<number | null>(null);
  const [googleConfigured, setGoogleConfigured] = useState(false);
  const [googleNeedsSetup, setGoogleNeedsSetup] = useState(false);
  const [finishingSetup, setFinishingSetup] = useState(false);
  const [connectingGoogle, setConnectingGoogle] = useState(false);
  const [showGoogleSection, setShowGoogleSection] = useState(false);
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const load = useCallback(() => {
    api<Platform[]>("/platforms").then(setPlatforms).catch(() => {});
    api<{ configured: boolean }>("/platforms/google/config").then(c => setGoogleConfigured(c.configured)).catch(() => {});
    api<{ connected: boolean; needs_setup: boolean }>("/platforms/google/status")
      .then(s => setGoogleNeedsSetup(s.needs_setup))
      .catch(() => setGoogleNeedsSetup(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const google = searchParams.get("google");
    const googleError = searchParams.get("google_error");
    if (google === "connected") {
      setToast({ type: "success", message: "Google Business connected successfully! Click Sync Reviews to import." });
      load();
      window.history.replaceState({}, "", "/platforms");
    } else if (google === "pending_setup") {
      setToast({
        type: "success",
        message: "Google signed in successfully. Rate limit was hit — wait 1–2 minutes, then click Finish Setup.",
      });
      load();
      window.history.replaceState({}, "", "/platforms");
    } else if (googleError) {
      setToast({ type: "error", message: `Google connect failed: ${decodeURIComponent(googleError)}` });
      window.history.replaceState({}, "", "/platforms");
    }
  }, [searchParams, load]);

  const finishGoogleSetup = async () => {
    setFinishingSetup(true);
    setToast(null);
    try {
      const result = await api<{ message: string; display_name: string }>("/platforms/google/finish-setup", { method: "POST" });
      setToast({ type: "success", message: `${result.message}: ${result.display_name}. You can now Sync Reviews.` });
      load();
    } catch (e: unknown) {
      setToast({ type: "error", message: e instanceof Error ? e.message : "Finish setup failed" });
    } finally {
      setFinishingSetup(false);
    }
  };

  const connectGoogle = async () => {
    setConnectingGoogle(true);
    try {
      const { auth_url } = await api<{ auth_url: string }>("/platforms/google/auth-url");
      window.location.href = auth_url;
    } catch (e: unknown) {
      setToast({ type: "error", message: e instanceof Error ? e.message : "Could not start Google OAuth" });
      setConnectingGoogle(false);
    }
  };

  const validateAmazon = async () => {
    setValidatingAmazon(true);
    setAmazonValid(null);
    try {
      const result = await api<{ valid: boolean; message: string }>("/platforms/amazon/validate", {
        method: "POST",
        body: JSON.stringify(amazonCreds),
      });
      setAmazonValid(result.message);
      setToast({ type: result.valid ? "success" : "error", message: result.message });
    } catch (e: unknown) {
      setToast({ type: "error", message: e instanceof Error ? e.message : "Validation failed" });
    } finally {
      setValidatingAmazon(false);
    }
  };

  const validateFlipkart = async () => {
    setValidatingFlipkart(true);
    try {
      const result = await api<{ valid: boolean; message: string }>("/platforms/flipkart/validate", {
        method: "POST", body: JSON.stringify(flipkartCreds),
      });
      setToast({ type: result.valid ? "success" : "error", message: result.message });
    } catch (e: unknown) {
      setToast({ type: "error", message: e instanceof Error ? e.message : "Validation failed" });
    } finally { setValidatingFlipkart(false); }
  };

  const validateMyntra = async () => {
    setValidatingMyntra(true);
    try {
      const result = await api<{ valid: boolean; message: string }>("/platforms/myntra/validate", {
        method: "POST", body: JSON.stringify(myntraCreds),
      });
      setToast({ type: result.valid ? "success" : "error", message: result.message });
    } catch (e: unknown) {
      setToast({ type: "error", message: e instanceof Error ? e.message : "Validation failed" });
    } finally { setValidatingMyntra(false); }
  };

  const connect = async () => {
    if (form.platform === "google_business") {
      await connectGoogle();
      return;
    }
    if (!form.display_name.trim()) {
      setToast({ type: "error", message: "Enter a display name for your store." });
      return;
    }
    let credentials: Record<string, string> = {};
    if (form.platform === "amazon") credentials = amazonCreds;
    else if (form.platform === "flipkart") credentials = flipkartCreds;
    else if (form.platform === "myntra") credentials = myntraCreds;

    const conn = await api<Platform>("/platforms", {
      method: "POST",
      body: JSON.stringify({ ...form, credentials }),
    });
    syncExtensionConnection(conn.id);
    setShowForm(false);
    setAmazonCreds(AMAZON_DEFAULTS);
    setFlipkartCreds(FLIPKART_DEFAULTS);
    setMyntraCreds(MYNTRA_DEFAULTS);
    setAmazonValid(null);
    setToast({
      type: "success",
      message: `${conn.display_name} connected via API. Click Sync Reviews. Extension is optional for AI reply on seller portal.`,
    });
    load();
  };

  const sync = async (id: number) => {
    setSyncing(id);
    setToast(null);
    try {
      const result = await api<{ imported: number; message?: string }>(`/platforms/${id}/sync`, { method: "POST" });
      const msg = result.message
        ? `Synced ${result.imported} review(s). ${result.message}`
        : `Synced ${result.imported} new review(s).`;
      setToast({ type: "success", message: msg });
      load();
    } catch (e: unknown) {
      setToast({ type: "error", message: e instanceof Error ? e.message : "Sync failed" });
    } finally { setSyncing(null); }
  };

  const hasGoogle = platforms.some(p => p.platform === "google_business");
  const hasAmazon = platforms.some(p => p.platform === "amazon");
  const hasFlipkart = platforms.some(p => p.platform === "flipkart");
  const hasMyntra = platforms.some(p => p.platform === "myntra");

  const quickConnect = (platform: string) => {
    setForm(f => ({ ...f, platform }));
    setShowForm(true);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Platform Connections</h1>
          <p className="text-gray-500 text-sm">Each company has its own Amazon, Flipkart & Myntra stores. Switch company in the header.</p>
        </div>
        <Button onClick={() => setShowForm(true)}><Plus className="w-4 h-4 mr-1" />Add Platform</Button>
      </div>

      {toast && (
        <div className={`flex items-center gap-2 p-3 rounded-lg text-sm ${toast.type === "success" ? "bg-green-50 text-green-800 border border-green-200" : "bg-red-50 text-red-800 border border-red-200"}`}>
          {toast.type === "success" ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
          {toast.message}
        </div>
      )}

      {/* Optional extension — works on all platforms */}
      <Card className="border-blue-200 bg-blue-50/30">
        <CardContent className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
          <div>
            <h2 className="font-semibold flex items-center gap-2">
              <Puzzle className="w-4 h-4 text-blue-600" />
              Chrome Extension (optional add-on)
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              Works on Amazon, Flipkart, Myntra, and more. Import reviews or apply AI replies on seller portals when API posting is limited.
            </p>
          </div>
          <Button variant="outline" onClick={() => setShowExtensionModal(true)}>Install Extension</Button>
        </CardContent>
      </Card>

      {/* Amazon quick setup */}
      <Card className="border-orange-200 bg-orange-50/40">
        <CardContent className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
          <div>
            <h2 className="font-semibold flex items-center gap-2">
              <ShoppingBag className="w-4 h-4 text-orange-600" />
              Amazon Seller (SP-API)
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              Primary: SP-API sync. Optional: Chrome extension on Seller Central for AI reply assist.
            </p>
          </div>
          <Button
            variant={hasAmazon ? "outline" : "default"}
            onClick={() => quickConnect("amazon")}
          >
            {hasAmazon ? "Add Another Amazon Store" : "Connect Amazon"}
          </Button>
        </CardContent>
      </Card>

      {/* Flipkart + Myntra extension setup */}
      <div className="grid md:grid-cols-2 gap-4">
        <Card className="border-blue-200 bg-blue-50/40">
          <CardContent className="py-4 space-y-3">
            <h2 className="font-semibold flex items-center gap-2">
              <Puzzle className="w-4 h-4 text-blue-600" />
              Flipkart Seller Hub
            </h2>
            <p className="text-sm text-gray-600">
              Primary: Flipkart Seller API sync. Optional: extension on seller.flipkart.com.
            </p>
            <Button size="sm" onClick={() => quickConnect("flipkart")}>
              {hasFlipkart ? "Add Flipkart Store" : "Connect Flipkart"}
            </Button>
          </CardContent>
        </Card>

        <Card className="border-pink-200 bg-pink-50/40">
          <CardContent className="py-4 space-y-3">
            <h2 className="font-semibold flex items-center gap-2">
              <Puzzle className="w-4 h-4 text-pink-600" />
              Myntra Seller Portal
            </h2>
            <p className="text-sm text-gray-600">
              Primary: Myntra Seller API sync. Optional: extension on Myntra seller portal.
            </p>
            <Button size="sm" onClick={() => quickConnect("myntra")}>
              {hasMyntra ? "Add Myntra Store" : "Connect Myntra"}
            </Button>
          </CardContent>
        </Card>
      </div>

      <div className="text-sm">
        <button
          type="button"
          className="text-gray-500 hover:text-gray-700 underline"
          onClick={() => setShowGoogleSection(v => !v)}
        >
          {showGoogleSection ? "Hide" : "Show"} Google Business setup (paused)
        </button>
      </div>

      {showGoogleSection && googleNeedsSetup && (
        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
            <div>
              <h2 className="font-semibold text-amber-900">Finish Google Business setup</h2>
              <p className="text-sm text-amber-800 mt-1">
                Signed in with Google but location discovery hit a rate limit. Wait 1–2 minutes, then Finish Setup.
              </p>
            </div>
            <Button onClick={finishGoogleSetup} disabled={finishingSetup} variant="outline" className="border-amber-400">
              {finishingSetup ? "Linking…" : "Finish Setup"}
            </Button>
          </CardContent>
        </Card>
      )}

      {showGoogleSection && googleConfigured && (
        <Card className="border-green-200 bg-green-50/50">
          <CardContent className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
            <div>
              <h2 className="font-semibold flex items-center gap-2">
                <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-800">Google Business</span>
                {hasGoogle ? "Reconnect or add another location" : "Connect with OAuth"}
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                Requires Google API allowlisting. Paused until Google approves your project.
              </p>
            </div>
            <Button onClick={connectGoogle} disabled={connectingGoogle} variant="outline">
              <Link2 className="w-4 h-4 mr-1" />
              {connectingGoogle ? "Redirecting…" : hasGoogle ? "Reconnect Google" : "Connect Google Business"}
            </Button>
          </CardContent>
        </Card>
      )}

      {showForm && (
        <Card>
          <CardContent className="space-y-4">
            <h2 className="font-semibold">Connect Platform</h2>
            <Select value={form.platform} onChange={e => setForm({ ...form, platform: e.target.value })}>
              {PLATFORMS.filter(p => p.id !== "google_business").map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              <option value="meesho">Meesho</option>
            </Select>
            <Input placeholder="Display name (e.g. My Amazon Store)" value={form.display_name} onChange={e => setForm({ ...form, display_name: e.target.value })} />
            <Select value={form.default_reply_mode} onChange={e => setForm({ ...form, default_reply_mode: e.target.value })}>
              {REPLY_MODES.map(m => <option key={m.id} value={m.id}>{m.name} — {m.description}</option>)}
            </Select>

            {form.platform === "amazon" && (
              <div className="space-y-3 p-4 bg-orange-50 rounded-lg border border-orange-100">
                <p className="text-sm font-medium text-orange-900">Amazon SP-API credentials</p>
                <Input placeholder="LWA Client ID" value={amazonCreds.client_id} onChange={e => setAmazonCreds({ ...amazonCreds, client_id: e.target.value })} />
                <Input placeholder="LWA Client Secret" type="password" value={amazonCreds.client_secret} onChange={e => setAmazonCreds({ ...amazonCreds, client_secret: e.target.value })} />
                <Input placeholder="Refresh Token" type="password" value={amazonCreds.refresh_token} onChange={e => setAmazonCreds({ ...amazonCreds, refresh_token: e.target.value })} />
                <div className="grid grid-cols-2 gap-2">
                  <Select value={amazonCreds.marketplace_id} onChange={e => setAmazonCreds({ ...amazonCreds, marketplace_id: e.target.value })}>
                    <option value="A21TJRUUN4KGV">Amazon India</option>
                    <option value="ATVPDKIKX0DER">Amazon US</option>
                    <option value="A1F83G8C2ARO7P">Amazon UK</option>
                  </Select>
                  <Select value={amazonCreds.region} onChange={e => setAmazonCreds({ ...amazonCreds, region: e.target.value })}>
                    <option value="eu">Region: EU</option>
                    <option value="na">Region: NA</option>
                    <option value="fe">Region: FE</option>
                  </Select>
                </div>
                <Input placeholder="Product ASINs (comma-separated, e.g. B0XXXXX,B0YYYYY)" value={amazonCreds.asins} onChange={e => setAmazonCreds({ ...amazonCreds, asins: e.target.value })} />
                <div className="flex gap-2 items-center">
                  <Button type="button" variant="outline" size="sm" onClick={validateAmazon} disabled={validatingAmazon}>
                    {validatingAmazon ? "Validating…" : "Test Connection"}
                  </Button>
                  {amazonValid && <span className="text-xs text-gray-600">{amazonValid}</span>}
                </div>
                <p className="text-xs text-gray-500">
                  Get credentials from{" "}
                  <a href="https://sellercentral.amazon.in/apps/develop/home" target="_blank" rel="noopener noreferrer" className="text-blue-600 inline-flex items-center gap-0.5">
                    Seller Central → Develop Apps <ExternalLink className="w-3 h-3" />
                  </a>
                </p>
              </div>
            )}

            {form.platform === "flipkart" && (
              <div className="space-y-3 p-4 bg-blue-50 rounded-lg border border-blue-100">
                <p className="text-sm font-medium text-blue-900">Flipkart Seller API (primary sync)</p>
                <Input placeholder="Client ID" value={flipkartCreds.client_id} onChange={e => setFlipkartCreds({ ...flipkartCreds, client_id: e.target.value })} />
                <Input placeholder="Client Secret" type="password" value={flipkartCreds.client_secret} onChange={e => setFlipkartCreds({ ...flipkartCreds, client_secret: e.target.value })} />
                <Input placeholder="Seller ID" value={flipkartCreds.seller_id} onChange={e => setFlipkartCreds({ ...flipkartCreds, seller_id: e.target.value })} />
                <Button type="button" variant="outline" size="sm" onClick={validateFlipkart} disabled={validatingFlipkart}>
                  {validatingFlipkart ? "Validating…" : "Test Connection"}
                </Button>
              </div>
            )}

            {form.platform === "myntra" && (
              <div className="space-y-3 p-4 bg-pink-50 rounded-lg border border-pink-100">
                <p className="text-sm font-medium text-pink-900">Myntra Seller API (primary sync)</p>
                <Input placeholder="API Key" value={myntraCreds.api_key} onChange={e => setMyntraCreds({ ...myntraCreds, api_key: e.target.value })} />
                <Input placeholder="API Secret" type="password" value={myntraCreds.api_secret} onChange={e => setMyntraCreds({ ...myntraCreds, api_secret: e.target.value })} />
                <Input placeholder="Seller ID" value={myntraCreds.seller_id} onChange={e => setMyntraCreds({ ...myntraCreds, seller_id: e.target.value })} />
                <Button type="button" variant="outline" size="sm" onClick={validateMyntra} disabled={validatingMyntra}>
                  {validatingMyntra ? "Validating…" : "Test Connection"}
                </Button>
              </div>
            )}

            {EXTENSION_OPTIONAL_PLATFORMS.includes(form.platform) && (
              <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg text-sm text-gray-600">
                <Puzzle className="w-4 h-4" />
                Chrome extension is optional — use it on seller portal for AI reply assist
              </div>
            )}

            <div className="flex gap-2">
              <Button onClick={connect}>Connect</Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        {platforms.map(p => {
          const platInfo = PLATFORMS.find(pl => pl.id === p.platform);
          const supportsExtension = EXTENSION_OPTIONAL_PLATFORMS.includes(p.platform);
          return (
            <Card key={p.id}>
              <CardContent>
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="font-semibold">{p.display_name}</h3>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${platInfo?.color || "bg-gray-100"}`}>{p.platform}</span>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${p.is_active ? "bg-green-100 text-green-700" : "bg-gray-100"}`}>
                    {p.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
                <div className="text-sm text-gray-500 mb-3">Reply mode: <span className="capitalize font-medium text-gray-700">{p.default_reply_mode}</span></div>
                {p.last_synced_at && <div className="text-xs text-gray-400 mb-3">Last synced: {new Date(p.last_synced_at).toLocaleString()}</div>}
                <p className="text-xs text-gray-500 mb-2">Primary: API Sync · Optional: Chrome extension</p>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => sync(p.id)} disabled={syncing === p.id}>
                    <RefreshCw className={`w-3 h-3 mr-1 ${syncing === p.id ? "animate-spin" : ""}`} />
                    Sync Reviews (API)
                  </Button>
                  {supportsExtension && (
                    <Button size="sm" variant="outline" onClick={() => syncExtensionConnection(p.id)}>
                      Link Extension
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
        {platforms.length === 0 && !showForm && (
          <div className="col-span-2 text-center py-12 text-gray-500">No platforms connected yet. Start with Amazon, Flipkart, or Myntra above.</div>
        )}
      </div>

      <ExtensionInstallModal
        open={showExtensionModal}
        onClose={() => { setShowExtensionModal(false); setPendingExtensionPlatform(null); }}
      />
    </div>
  );
}
