#!/usr/bin/env python3
"""Full live usage test — all platforms, reply flows, and core features."""
import json
import sys
import time
import urllib.request
import urllib.error
from io import BytesIO
from urllib.parse import urlencode

BASE = "http://localhost:8000/api"
passed = failed = 0
errors = []
PLATFORMS = ["amazon", "google_business", "flipkart", "myntra", "meesho"]


def req(method, path, token=None, data=None, form_data=None):
    url = f"{BASE}{path}" if path.startswith("/") else f"{BASE}/{path}"
    headers = {}
    body = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if form_data:
        boundary = "----LiveTest"
        parts = []
        for key, val in form_data.items():
            if hasattr(val, "read"):
                content = val.read()
                parts.append(
                    f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"; filename="test.csv"\r\n'
                    f"Content-Type: text/csv\r\n\r\n".encode() + content + b"\r\n"
                )
            else:
                parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{val}\r\n'.encode())
        parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(parts)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"detail": raw}


def test(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        msg = f"  FAIL  {name}" + (f" — {detail}" if detail else "")
        print(msg)
        errors.append(msg)


def main():
    print("\n=== ReviewFlow Full Live Usage Test ===\n")
    email = f"live-{int(time.time())}@example.com"
    password = "TestPass123!"

    # Health
    print("[1] Infrastructure")
    with urllib.request.urlopen("http://localhost:8000/health") as r:
        health = json.loads(r.read())
    test("Backend health", health.get("status") == "ok")
    try:
        with urllib.request.urlopen("http://localhost:3000/login", timeout=5) as r:
            test("Frontend reachable", r.status == 200)
    except Exception as e:
        test("Frontend reachable", False, str(e))

    # Register + login
    print("\n[2] Auth")
    status, reg = req("POST", "/auth/register", data={
        "email": email, "password": password, "full_name": "Live Tester", "org_name": "Live Test Org",
    })
    test("Register", status == 200, str(reg))
    token = reg.get("access_token")
    status, login = req("POST", "/auth/login", data={"email": email, "password": password})
    test("Login", status == 200 and login.get("access_token"))
    status, me = req("GET", "/auth/me", token=token)
    test("Profile", status == 200 and me.get("org", {}).get("name") == "Live Test Org")
    req("POST", "/auth/onboarding/complete", token=token)

    # All platforms connect + sync
    print("\n[3] All Platforms — Connect & Sync")
    platform_ids = {}
    total_imported = 0
    for p in PLATFORMS:
        status, conn = req("POST", "/platforms", token=token, data={
            "platform": p,
            "display_name": f"Live {p.replace('_', ' ').title()}",
            "default_reply_mode": "template" if p == "google_business" else "ai",
        })
        test(f"Connect {p}", status == 200 and conn.get("id"), str(conn))
        pid = conn.get("id")
        platform_ids[p] = pid
        status, sync = req("POST", f"/platforms/{pid}/sync", token=token)
        imported = sync.get("imported", 0)
        total_imported += imported
        test(f"Sync {p} ({imported} imported)", status == 200, str(sync))

    test("Total reviews imported across platforms", total_imported >= len(PLATFORMS), f"got {total_imported}")

    # Verify per-platform reviews
    print("\n[4] Per-Platform Review Counts")
    for p in PLATFORMS:
        status, reviews = req("GET", f"/reviews?platform={p}", token=token)
        count = reviews.get("total", 0)
        test(f"Reviews for {p}", status == 200 and count >= 1, f"total={count}")

    # Template library — one per category
    print("\n[5] Template Library")
    templates = {}
    tpl_defs = [
        ("Thank You 5★", "thank_you", "5", "Hi {{reviewer_name}}, thanks for your {{rating}}-star review on {{platform}}! — {{brand_name}}"),
        ("Thank You 4★", "thank_you", "4", "Dear {{reviewer_name}}, we appreciate your feedback on {{platform}}. — {{brand_name}}"),
        ("Apology 1-2★", "apology", "1", "Hi {{reviewer_name}}, sorry about {{issue_keyword}}. We want to make this right. — {{brand_name}}"),
        ("Issue Resolution", "issue_resolution", "2", "Hi {{reviewer_name}}, regarding {{issue_keyword}} — please contact us. — {{brand_name}}"),
        ("Neutral", "neutral", "any", "Thank you {{reviewer_name}} for sharing your experience on {{platform}}. — {{brand_name}}"),
    ]
    for name, cat, stars, body in tpl_defs:
        status, tpl = req("POST", "/templates", token=token, data={
            "name": name, "body": body, "category": cat, "star_rating_filter": stars,
        })
        test(f"Template: {name}", status == 200 and tpl.get("id"))
        templates[name] = tpl.get("id")

    # Reply modes per platform
    print("\n[6] Reply Mode Settings")
    for p, pid in platform_ids.items():
        mode = "template" if p in ("google_business", "amazon") else "ai"
        tpl_id = templates.get("Thank You 5★") if mode == "template" else None
        payload = {"scope": "platform", "platform_connection_id": pid, "reply_mode": mode}
        if tpl_id:
            payload["template_id"] = tpl_id
        status, rm = req("POST", "/reply-modes", token=token, data=payload)
        test(f"Reply mode {p} → {mode}", status == 200, str(rm))

    # Template + AI reply flows per platform
    print("\n[7] Reply Flows — Template Apply & Publish")
    published_by_platform = {}
    for p in PLATFORMS:
        status, reviews = req("GET", f"/reviews?platform={p}&reply_status=pending", token=token)
        items = reviews.get("items", [])
        if not items:
            test(f"{p}: has pending review for reply", False, "no pending reviews")
            continue
        review = items[0]
        rid = review["id"]
        rating = review["rating"]
        tpl_name = "Thank You 5★" if rating >= 5 else "Thank You 4★" if rating == 4 else "Apology 1-2★" if rating <= 1 else "Issue Resolution"
        tpl_id = templates.get(tpl_name) or templates.get("Neutral")
        status, applied = req("POST", f"/replies/apply-template?review_id={rid}&template_id={tpl_id}", token=token)
        test(f"{p}: template applied", status == 200 and applied.get("body"), str(applied.get("body", "")[:60]))
        reply_id = applied.get("id")
        if reply_id:
            status, pub = req("POST", f"/replies/publish?review_id={rid}&reply_id={reply_id}", token=token)
            test(f"{p}: reply published", status == 200, str(pub))
            published_by_platform[p] = True

    print("\n[8] Reply Flows — AI Fallback")
    for p in PLATFORMS:
        status, reviews = req("GET", f"/reviews?platform={p}&reply_status=pending", token=token)
        items = reviews.get("items", [])
        if not items:
            continue
        rid = items[0]["id"]
        status, ai = req("POST", "/ai/reply", token=token, data={"review_id": rid})
        test(f"{p}: AI reply generated", status == 200 and ai.get("body"), str(ai.get("body", "")[:60]))

    # Flagging + escalation
    print("\n[9] Flagging & Escalation")
    status, flagged = req("POST", "/reviews", token=token, data={
        "reviewer_name": "Legal Threat User", "rating": 1,
        "body": "I will file a lawsuit and consumer court complaint for this defective product!",
        "platform": "amazon", "product_name": "Test Item",
    })
    test("Sensitive review auto-flagged", status == 200 and flagged.get("is_flagged"), str(flagged))
    fid = flagged.get("id")
    status, escalated = req("GET", "/reviews/escalated", token=token)
    test("Escalated queue", status == 200 and any(r["id"] == fid for r in escalated))
    if fid:
        req("POST", f"/reviews/{fid}/resolve-flag?action=approve", token=token)

    # Bulk apply
    print("\n[10] Bulk Operations")
    status, pending = req("GET", "/reviews?reply_status=pending", token=token)
    pending_ids = [r["id"] for r in pending.get("items", [])[:3]]
    if pending_ids and templates.get("Neutral"):
        status, bulk = req("POST", "/replies/bulk", token=token, data={
            "review_ids": pending_ids, "template_id": templates["Neutral"],
        })
        test("Bulk template apply", status == 200, str(bulk))

    # AI review generator + personas
    print("\n[11] AI Generate & Personas")
    status, gen = req("POST", "/ai/generate-review", token=token, data={
        "product_title": "Wireless Earbuds Pro", "product_features": "ANC, 40hr battery", "rating_target": 5,
    })
    test("AI review generator", status == 200 and gen.get("body"))
    status, persona = req("POST", "/personas", token=token, data={
        "name": "Delhi Buyer", "age_range": "28-35", "location": "Delhi", "writing_style": "casual",
    })
    test("Persona created", status == 200 and persona.get("id"))

    # Team, SSO, 2FA
    print("\n[12] Team & Security")
    status, invite = req("POST", "/auth/invite", token=token, data={"email": "teammate@example.com", "role": "member"})
    test("Team invite", status == 200)
    status, totp = req("POST", "/auth/2fa/setup", token=token)
    test("2FA setup", status == 200 and totp.get("secret"))
    status, sso = req("POST", "/auth/sso/config", token=token, data={
        "provider": "google_workspace", "protocol": "oidc", "client_id": "live-test", "is_active": False,
    })
    test("SSO config", status == 200)

    # Notifications, webhooks, review requests, audit
    print("\n[13] Integrations & Notifications")
    status, notifs = req("GET", "/notifications", token=token)
    test("Notifications", status == 200)
    status, webhook = req("POST", "/webhooks?" + urlencode({
        "name": "Live Hook", "url": "https://example.com/hook", "events": "review.created,review.reply_published",
    }), token=token)
    test("Webhook created", status == 200 and webhook.get("id"))
    status, rr = req("POST", "/review-requests?" + urlencode({
        "recipient_email": "buyer@live.test", "product_title": "Live Product", "send_after_days": 7,
    }), token=token)
    test("Review request", status == 200)
    status, audit = req("GET", "/audit-log", token=token)
    test("Audit log has entries", status == 200 and len(audit) >= 1, f"count={len(audit)}")

    # Analytics breakdown
    print("\n[14] Analytics")
    status, analytics = req("GET", "/analytics", token=token)
    test("Analytics totals", status == 200 and analytics.get("total_reviews", 0) >= total_imported)
    breakdown = analytics.get("by_platform", {})
    for p in PLATFORMS:
        test(f"Analytics includes {p}", p in breakdown, str(list(breakdown.keys())))
    test("Reply rate > 0", analytics.get("reply_rate", 0) > 0, str(analytics.get("reply_rate")))

    # CSV import/export
    print("\n[15] CSV Import/Export")
    csv = b"reviewer_name,rating,body,platform,product_name\nCSV Live,5,Imported via CSV,flipkart,CSV Widget\n"
    status, imp = req("POST", "/reviews/import-csv", token=token, form_data={"file": BytesIO(csv)})
    test("CSV import", status == 200 and imp.get("imported", 0) >= 1, str(imp))
    try:
        exp_req = urllib.request.Request(
            f"{BASE}/reviews/export-csv", headers={"Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(exp_req) as r:
            export_ok = r.status == 200 and len(r.read()) > 50
        test("CSV export", export_ok)
    except Exception as e:
        test("CSV export", False, str(e))

    # Template usage counts
    print("\n[16] Template Usage")
    status, tpl_list = req("GET", "/templates", token=token)
    used = [t for t in tpl_list if t.get("usage_count", 0) > 0]
    test("Templates show usage", status == 200 and len(used) >= 1, f"{len(used)} used")

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
    if errors:
        print("\nFailures:")
        for e in errors:
            print(e)
    print(f"{'='*50}\n")
    print(f"Test account: {email} / {password}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
