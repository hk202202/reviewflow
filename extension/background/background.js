const DEFAULT_API_URL = "http://localhost:8000";

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "SET_TOKEN") {
    const data = { token: message.token };
    if (message.apiUrl) data.api_url = message.apiUrl;
    if (message.platformConnectionId) data.platform_connection_id = message.platformConnectionId;
    chrome.storage.local.set(data, () => sendResponse({ ok: true }));
    return true;
  }

  if (message.type === "GENERATE_REPLY") {
    chrome.storage.local.get(["token", "api_url"], async ({ token, api_url }) => {
      try {
        const res = await fetch(`${api_url || DEFAULT_API_URL}/api/ai/reply`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({
            review_id: message.reviewId,
            review_text: message.reviewText,
            rating: message.rating,
          }),
        });
        const data = await res.json();
        sendResponse({ success: true, reply: data.body });
      } catch (e) {
        sendResponse({ success: false, error: String(e) });
      }
    });
    return true;
  }
});
