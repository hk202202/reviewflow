"use client";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { X, Puzzle } from "lucide-react";

const EXTENSION_PING = "reviewflow-ping";
const EXTENSION_PONG = "reviewflow-pong";

export function useExtensionInstalled() {
  const [installed, setInstalled] = useState<boolean | null>(null);

  useEffect(() => {
    const handler = (e: MessageEvent) => {
      if (e.data?.type === EXTENSION_PONG) setInstalled(true);
    };
    window.addEventListener("message", handler);
    window.postMessage({ type: EXTENSION_PING }, "*");
    const timer = setTimeout(() => setInstalled(prev => prev === null ? false : prev), 600);
    return () => { window.removeEventListener("message", handler); clearTimeout(timer); };
  }, []);

  return installed;
}

export default function ExtensionBanner() {
  const installed = useExtensionInstalled();
  const [dismissed, setDismissed] = useState(false);

  if (installed !== false || dismissed) return null;

  return (
    <div className="bg-blue-600 text-white px-6 py-2.5 flex items-center gap-3 text-sm">
      <Puzzle className="w-4 h-4 flex-shrink-0" />
      <span className="flex-1">Optional: Install the ReviewFlow Chrome extension for AI reply assist on any seller portal</span>
      <Button variant="secondary" size="sm" onClick={() => window.open("https://chrome.google.com/webstore", "_blank")}>
        Install Extension
      </Button>
      <button onClick={() => setDismissed(true)}><X className="w-4 h-4" /></button>
    </div>
  );
}

export function ExtensionInstallModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const installed = useExtensionInstalled();

  useEffect(() => {
    if (installed) { onClose(); }
  }, [installed, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-md w-full p-8 shadow-xl">
        <h2 className="text-xl font-bold mb-2">Install ReviewFlow Extension</h2>
        <p className="text-gray-600 text-sm mb-6">Optional add-on for all platforms — import reviews and apply AI replies on Amazon, Flipkart, Myntra seller portals. Works alongside API sync.</p>
        <ol className="space-y-4 mb-6">
          {[
            "In Chrome go to chrome://extensions → Enable Developer mode",
            "Click Load unpacked → select the reviewflow/extension folder",
            "Return here — we'll detect it automatically",
          ].map((step, i) => (
            <li key={i} className="flex gap-3 text-sm">
              <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-medium flex-shrink-0">{i + 1}</span>
              {step}
            </li>
          ))}
        </ol>
        <div className="flex gap-3">
          <Button className="flex-1" onClick={() => window.open("chrome://extensions", "_blank")}>Open chrome://extensions</Button>
          <Button variant="outline" onClick={onClose}>Skip for now</Button>
        </div>
        <p className="text-xs text-gray-400 mt-4 text-center">Works on: Amazon, Flipkart, Myntra, Meesho, Google Business</p>
      </div>
    </div>
  );
}
