"use client";
import { useEffect } from "react";
import { getToken, API_URL } from "@/lib/api";

export default function ExtensionTokenBridge() {
  useEffect(() => {
    const sync = () => {
      const token = getToken();
      if (token) {
        window.postMessage(
          { type: "reviewflow-set-token", token, apiUrl: API_URL },
          "*"
        );
      }
    };
    sync();
    window.addEventListener("storage", sync);
    const interval = setInterval(sync, 5000);
    return () => {
      window.removeEventListener("storage", sync);
      clearInterval(interval);
    };
  }, []);
  return null;
}

export function syncExtensionConnection(connectionId: number) {
  const token = getToken();
  if (token) {
    window.postMessage(
      {
        type: "reviewflow-set-token",
        token,
        apiUrl: API_URL,
        platformConnectionId: connectionId,
      },
      "*"
    );
  }
}
