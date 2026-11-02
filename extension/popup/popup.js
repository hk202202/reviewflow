const DEFAULT_API_URL = "http://localhost:8000";

async function getConfig() {
  const stored = await chrome.storage.local.get(["token", "api_url", "platform_connection_id"]);
  return {
    token: stored.token,
    apiUrl: stored.api_url || DEFAULT_API_URL,
    connectionId: stored.platform_connection_id,
  };
}

async function init() {
  const { token, apiUrl } = await getConfig();
  const userInfo = document.getElementById("user-info");
  const platformInfo = document.getElementById("platform-info");
  const connectionSelect = document.getElementById("connection-select");
  const importBtn = document.getElementById("import-btn");
  const importStatus = document.getElementById("import-status");

  if (!token) {
    userInfo.textContent = "Not logged in. Open ReviewFlow dashboard to sign in.";
    return;
  }

  try {
    const res = await fetch(`${apiUrl}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    userInfo.textContent = `${data.user.full_name} · ${data.org.name}`;

    const analytics = await fetch(`${apiUrl}/api/analytics`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then(r => r.json());
    document.getElementById("pending").textContent = analytics.pending_replies || 0;
    document.getElementById("published").textContent = analytics.published_replies || 0;

    const connections = await fetch(`${apiUrl}/api/extension/connections`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then(r => r.json());

    if (connections.length) {
      connectionSelect.innerHTML = connections
        .map(c => `<option value="${c.id}">${c.display_name} (${c.platform})</option>`)
        .join("");
      connectionSelect.style.display = "block";
      const stored = await chrome.storage.local.get(["platform_connection_id"]);
      if (stored.platform_connection_id) {
        connectionSelect.value = String(stored.platform_connection_id);
      }
      connectionSelect.onchange = () => {
        chrome.storage.local.set({ platform_connection_id: connectionSelect.value });
      };
    }
  } catch {
    userInfo.textContent = "Could not connect to ReviewFlow";
  }

  chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
    if (!tab?.url) return;
    const url = tab.url;
    if (url.includes("sellercentral.amazon")) {
      platformInfo.style.display = "block";
      platformInfo.textContent = "📦 Amazon Seller Central — optional import + AI reply";
    } else if (url.includes("flipkart")) {
      platformInfo.style.display = "block";
      platformInfo.textContent = "📦 Flipkart Seller Hub — optional import + AI reply";
    } else if (url.includes("myntra")) {
      platformInfo.style.display = "block";
      platformInfo.textContent = "👗 Myntra Seller Portal — optional import + AI reply";
    }
  });

  importBtn.onclick = async () => {
    importStatus.textContent = "Sending import to active tab…";
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) return;
    if (connectionSelect.value) {
      await chrome.storage.local.set({ platform_connection_id: connectionSelect.value });
    }
    try {
      await chrome.tabs.sendMessage(tab.id, { type: "RF_IMPORT_REVIEWS" });
      importStatus.textContent = "Check the page toolbar for import status.";
    } catch {
      importStatus.textContent = "Open Flipkart/Myntra seller reviews page first.";
    }
  };
}

init();
