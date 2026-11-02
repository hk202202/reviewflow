const DEFAULT_API_URL = "http://localhost:8000";

async function getConfig() {
  const stored = await chrome.storage.local.get(["token", "api_url", "platform_connection_id"]);
  return {
    token: stored.token,
    apiUrl: stored.api_url || DEFAULT_API_URL,
    connectionId: stored.platform_connection_id,
  };
}

async function apiFetch(path, options = {}) {
  const { token, apiUrl } = await getConfig();
  if (!token) throw new Error("Not logged in to ReviewFlow. Open the dashboard and sign in.");
  const res = await fetch(`${apiUrl}/api${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

function hashReview(platform, body, reviewer, rating) {
  let h = 0;
  const s = `${platform}:${reviewer}:${rating}:${body.slice(0, 200)}`;
  for (let i = 0; i < s.length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0;
  return `${platform}-${Math.abs(h).toString(16).padStart(8, "0")}`;
}

function parseRating(text) {
  const starCount = (text.match(/★/g) || []).length;
  if (starCount >= 1 && starCount <= 5) return starCount;
  const m = text.match(/(\d)\s*(?:\/\s*5|star|★|out of)/i) || text.match(/rating[:\s]*(\d)/i);
  return m ? Math.min(5, Math.max(1, parseInt(m[1], 10))) : 3;
}

function extractReviewsFromPage(platform) {
  const reviews = [];
  const seen = new Set();

  const selectors = [
    "[class*='review' i]",
    "[class*='Review' i]",
    "[class*='feedback' i]",
    "[class*='rating' i]",
    "[data-testid*='review' i]",
    "article",
    ".review-card",
    ".customer-review",
  ];

  const candidates = new Set();
  selectors.forEach(sel => {
    try {
      document.querySelectorAll(sel).forEach(el => candidates.add(el));
    } catch (_) {}
  });

  candidates.forEach(el => {
    const text = (el.innerText || el.textContent || "").trim();
    if (!text || text.length < 25 || text.length > 3000) return;
    if (seen.has(text.slice(0, 120))) return;

    const rating = parseRating(text);
    const lines = text.split("\n").map(l => l.trim()).filter(Boolean);
    const bodyLine = lines.find(l => l.length > 30) || text.slice(0, 500);
    const nameLine = lines.find(l => l.length < 40 && l.length > 2 && !/\d\s*star/i.test(l));

    const review = {
      external_review_id: hashReview(platform, bodyLine, nameLine || "anon", rating),
      reviewer_name: nameLine || "Customer",
      rating,
      title: lines.find(l => l.length > 10 && l.length < 80 && l !== bodyLine) || null,
      body: bodyLine,
      product_name: document.title.replace(/\s*[-|].*$/, "").trim() || null,
    };

    if (review.body.length >= 20) {
      seen.add(text.slice(0, 120));
      reviews.push(review);
    }
  });

  return reviews.slice(0, 100);
}

async function importReviewsToReviewFlow(platform) {
  const { connectionId } = await getConfig();
  if (!connectionId) {
    throw new Error("No platform linked. Connect Flipkart/Myntra on the ReviewFlow Platforms page first.");
  }

  const reviews = extractReviewsFromPage(platform);
  if (!reviews.length) {
    throw new Error("No reviews found on this page. Open your seller reviews page and try again.");
  }

  return apiFetch("/extension/import-reviews", {
    method: "POST",
    body: JSON.stringify({
      platform,
      platform_connection_id: parseInt(connectionId, 10),
      reviews,
    }),
  });
}

function injectToolbar(platform) {
  if (document.getElementById("rf-toolbar")) return;

  const bar = document.createElement("div");
  bar.id = "rf-toolbar";
  bar.innerHTML = `
    <div class="rf-toolbar-inner">
      <span class="rf-toolbar-logo">RF</span>
      <span class="rf-toolbar-title">ReviewFlow</span>
      <button type="button" id="rf-import-btn">Import Reviews</button>
      <span id="rf-toolbar-status"></span>
    </div>
  `;
  document.body.appendChild(bar);

  const btn = bar.querySelector("#rf-import-btn");
  const status = bar.querySelector("#rf-toolbar-status");

  btn.onclick = async () => {
    btn.disabled = true;
    status.textContent = "Scanning…";
    try {
      const result = await importReviewsToReviewFlow(platform);
      status.textContent = `Imported ${result.imported} review(s)`;
      status.className = "rf-success";
    } catch (e) {
      status.textContent = e.message || "Import failed";
      status.className = "rf-error";
    } finally {
      btn.disabled = false;
    }
  };
}

async function generateAiReply(reviewEl, reviewText, rating) {
  const btn = reviewEl.querySelector(".rf-reply-btn");
  if (btn) {
    btn.textContent = "Generating...";
    btn.disabled = true;
  }
  try {
    const data = await apiFetch("/ai/reply", {
      method: "POST",
      body: JSON.stringify({ review_id: 0, review_text: reviewText, rating }),
    });
    const textarea = reviewEl.querySelector("textarea, input[type=text]");
    if (textarea) {
      textarea.value = data.body;
      textarea.dispatchEvent(new Event("input", { bubbles: true }));
    } else {
      await navigator.clipboard.writeText(data.body);
      alert("Reply copied to clipboard!");
    }
  } catch (e) {
    alert(e.message || "Failed to generate reply.");
  } finally {
    if (btn) {
      btn.textContent = "✨ AI Reply";
      btn.disabled = false;
    }
  }
}

function injectReplyButton(reviewEl, reviewText, rating) {
  if (reviewEl.querySelector(".rf-reply-btn")) return;
  const btn = document.createElement("button");
  btn.className = "rf-reply-btn";
  btn.textContent = "✨ AI Reply";
  btn.onclick = () => generateAiReply(reviewEl, reviewText, rating);
  reviewEl.appendChild(btn);
}

function detectPlatformFromHost() {
  const host = window.location.hostname;
  if (host.includes("sellercentral.amazon") || host.includes("amazon.in") && host.includes("seller")) return "amazon";
  if (host.includes("flipkart")) return "flipkart";
  if (host.includes("myntra")) return "myntra";
  if (host.includes("meesho")) return "meesho";
  if (host.includes("business.google")) return "google_business";
  return null;
}

function scanPageForReviews(platform) {
  document.querySelectorAll("[class*='review'], [class*='Review'], [class*='feedback'], [class*='rating']").forEach(el => {
    const text = el.textContent?.trim();
    if (text && text.length > 20) {
      ReviewFlowExt.injectReplyButton(el, text.slice(0, 500), parseRating(text));
    }
  });
}

window.ReviewFlowExt = {
  detectPlatformFromHost,
  extractReviewsFromPage,
  importReviewsToReviewFlow,
  injectToolbar,
  injectReplyButton,
  parseRating,
  scanPageForReviews,
};

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "RF_IMPORT_REVIEWS") {
    const platform = detectPlatformFromHost();
    if (!platform) {
      sendResponse({ ok: false, error: "Unsupported seller portal on this page." });
      return true;
    }
    importReviewsToReviewFlow(platform)
      .then(result => sendResponse({ ok: true, ...result }))
      .catch(err => sendResponse({ ok: false, error: err.message }));
    return true;
  }
});
