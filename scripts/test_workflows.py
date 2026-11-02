#!/usr/bin/env python3
"""End-to-end workflow tests for ReviewFlow API."""
import json
import sys
import urllib.request
import urllib.error
from io import BytesIO
from urllib.parse import urlencode

BASE = "http://localhost:8000/api"
passed = 0
failed = 0
errors = []


def req(method, path, token=None, data=None, form_data=None):
    url = f"{BASE}{path}" if path.startswith("/") else f"{BASE}/{path}"
    headers = {}
    body = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if form_data:
        boundary = "----ReviewFlowTest"
        parts = []
        for key, val in form_data.items():
            if hasattr(val, "read"):
                content = val.read()
                parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"; filename=\"test.csv\"\r\nContent-Type: text/csv\r\n\r\n".encode() + content + b"\r\n")
            else:
                parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{val}\r\n".encode())
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
            detail = json.loads(raw)
        except Exception:
            detail = {"detail": raw}
        return e.code, detail


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        msg = f"  FAIL  {name}" + (f" — {detail}" if detail else "")
        print(msg)
        errors.append(msg)


def main():
    print("\n=== ReviewFlow Workflow Tests ===\n")

    # 1. Health
    print("[1] Health Check")
    import urllib.request
    with urllib.request.urlopen("http://localhost:8000/health") as r:
        health = json.loads(r.read())
    test("Health endpoint", health.get("status") == "ok", str(health))

    # 2. Register
    print("\n[2] Auth — Register")
    email = f"workflow{int(__import__('time').time())}@example.com"
    status, reg = req("POST", "/auth/register", data={
        "email": email, "password": "TestPass123!", "full_name": "Workflow Tester", "org_name": "Workflow Org"
    })
    test("Register returns 200", status == 200, str(reg))
    token = reg.get("access_token")
    org_id = reg.get("org_id")
    user_id = reg.get("user_id")

    # 3. Login
    print("\n[3] Auth — Login")
    status, login = req("POST", "/auth/login", data={"email": email, "password": "TestPass123!"})
    test("Login returns 200", status == 200, str(login))
    test("Login returns token", bool(login.get("access_token")))

    # 4. Get me
    print("\n[4] Auth — Get Profile")
    status, me = req("GET", "/auth/me", token=token)
    test("Get me returns 200", status == 200, str(me))
    test("Org name correct", me.get("org", {}).get("name") == "Workflow Org")

    # 5. Onboarding complete
    print("\n[5] Onboarding")
    status, onboarding = req("POST", "/auth/onboarding/complete", token=token)
    test("Onboarding complete", status == 200, str(onboarding))

    # 6. Team invite
    print("\n[6] Team Management — Invite")
    status, invite = req("POST", "/auth/invite", token=token, data={"email": "member@example.com", "role": "member"})
    test("Invite sent", status == 200, str(invite))
    status, invitations = req("GET", "/auth/invitations", token=token)
    test("Invitations listed", status == 200 and len(invitations) >= 1, str(invitations))

    # 7. Team list
    print("\n[7] Team Management — List Members")
    status, team = req("GET", "/auth/team", token=token)
    test("Team listed", status == 200 and len(team) >= 1, str(team))

    # 8. SSO config
    print("\n[8] SSO Configuration")
    status, sso = req("POST", "/auth/sso/config", token=token, data={
        "provider": "google_workspace", "protocol": "oidc", "client_id": "test-client", "is_active": False
    })
    test("SSO config saved", status == 200, str(sso))
    slug = me.get("org", {}).get("slug", "workflow-org")
    try:
        with urllib.request.urlopen(f"http://localhost:8000/api/auth/sso/{slug}") as r:
            sso_get = json.loads(r.read())
        test("SSO slug lookup", "org_name" in sso_get or "sso_enabled" in sso_get, str(sso_get))
    except urllib.error.HTTPError as e:
        test("SSO slug lookup", False, f"HTTP {e.code}")

    # 9. 2FA setup
    print("\n[9] 2FA Setup")
    status, totp = req("POST", "/auth/2fa/setup", token=token)
    test("2FA setup returns secret", status == 200 and "secret" in totp, str(totp))

    # 10. Platform connection
    print("\n[10] Platform Connection")
    status, platform = req("POST", "/platforms", token=token, data={
        "platform": "amazon", "display_name": "Test Amazon Store", "default_reply_mode": "ai"
    })
    test("Platform created", status == 200, str(platform))
    platform_id = platform.get("id")

    # 11. Sync platform
    print("\n[11] Platform Sync (Import Reviews)")
    status, sync = req("POST", f"/platforms/{platform_id}/sync", token=token)
    test("Sync imported reviews", status == 200 and sync.get("imported", 0) >= 0, str(sync))

    # 12. List reviews
    print("\n[12] Review Dashboard")
    status, reviews = req("GET", "/reviews", token=token)
    test("Reviews listed", status == 200 and "items" in reviews, str(reviews.get("total")))
    review_id = reviews["items"][0]["id"] if reviews.get("items") else None

    # 13. Create review manually (negative for flagging)
    print("\n[13] Create Review + Flagging")
    status, new_review = req("POST", "/reviews", token=token, data={
        "reviewer_name": "Angry Customer", "rating": 1,
        "body": "Terrible product! I want a refund and will file a consumer court complaint lawsuit!",
        "platform": "amazon", "product_name": "Test Widget"
    })
    test("Review created", status == 200, str(new_review))
    flagged_id = new_review.get("id")
    status, escalated = req("GET", "/reviews/escalated", token=token)
    test("Escalated queue has flagged review", status == 200 and any(r["id"] == flagged_id for r in escalated), str(len(escalated)))

    # 14. Resolve flag
    if flagged_id:
        status, resolved = req("POST", f"/reviews/{flagged_id}/resolve-flag?action=approve", token=token)
        test("Flag resolved (approve)", status == 200, str(resolved))

    # 15. Templates
    print("\n[15] Template Library")
    status, template = req("POST", "/templates", token=token, data={
        "name": "Thank You 5 Star", "body": "Thank you {{reviewer_name}} for your {{rating}}-star review of {{product_name}}! — {{brand_name}}",
        "category": "thank_you", "star_rating_filter": "5"
    })
    test("Template created", status == 200, str(template))
    template_id = template.get("id")
    status, templates = req("GET", "/templates", token=token)
    test("Templates listed", status == 200 and len(templates) >= 1)

    # 16. Reply mode
    print("\n[16] Reply Mode Settings")
    status, mode = req("POST", "/reply-modes", token=token, data={
        "scope": "platform", "platform_connection_id": platform_id, "reply_mode": "template", "template_id": template_id
    })
    test("Reply mode set", status == 200, str(mode))

    # 17. Apply template
    print("\n[17] Apply Template Reply")
    if review_id and template_id:
        status, applied = req("POST", f"/replies/apply-template?review_id={review_id}&template_id={template_id}", token=token)
        test("Template applied", status == 200 and "body" in applied, str(applied.get("body", "")[:80]))
        reply_id = applied.get("id")
        if reply_id:
            status, published = req("POST", f"/replies/publish?review_id={review_id}&reply_id={reply_id}", token=token)
            test("Reply published", status == 200, str(published))

    # 18. AI Reply
    print("\n[18] AI Reply Engine")
    if review_id:
        status, ai_reply = req("POST", "/ai/reply", token=token, data={"review_id": review_id})
        test("AI reply generated", status == 200 and "body" in ai_reply, str(ai_reply.get("body", "")[:80]))

    # 19. AI Review Generator
    print("\n[19] AI Review Generator")
    status, gen_review = req("POST", "/ai/generate-review", token=token, data={
        "product_title": "Premium Wireless Earbuds", "product_features": "Noise cancelling, 30hr battery", "rating_target": 5
    })
    test("AI review generated", status == 200 and "body" in gen_review, str(gen_review.get("body", "")[:80]))

    # 20. Personas
    print("\n[20] Personas")
    status, persona = req("POST", "/personas", token=token, data={
        "name": "Casual Mumbai Buyer", "age_range": "25-35", "location": "Mumbai", "writing_style": "terse"
    })
    test("Persona created", status == 200, str(persona))
    status, personas = req("GET", "/personas", token=token)
    test("Personas listed", status == 200 and len(personas) >= 1)

    # 21. Notifications
    print("\n[21] Notifications")
    status, notifs = req("GET", "/notifications", token=token)
    test("Notifications listed", status == 200, str(len(notifs)))

    # 22. Audit log
    print("\n[22] Audit Log")
    status, audit = req("GET", "/audit-log", token=token)
    test("Audit log listed", status == 200, str(len(audit)))

    # 23. Webhooks
    print("\n[23] Webhooks")
    status, webhook = req("POST", "/webhooks?" + urlencode({"name": "Test Hook", "url": "https://example.com/hook", "events": "review.created,review.reply_published"}), token=token)
    test("Webhook created", status == 200, str(webhook))
    status, webhooks = req("GET", "/webhooks", token=token)
    test("Webhooks listed", status == 200 and len(webhooks) >= 1)

    # 24. Review requests
    print("\n[24] Review Requests")
    status, rr = req("POST", "/review-requests?recipient_email=buyer@test.com&product_title=Test+Product&send_after_days=3", token=token)
    test("Review request scheduled", status == 200, str(rr))

    # 25. Analytics
    print("\n[25] Analytics")
    status, analytics = req("GET", "/analytics", token=token)
    test("Analytics returned", status == 200 and "total_reviews" in analytics, str(analytics))

    # 26. CSV Import
    print("\n[26] CSV Import")
    csv_content = b"reviewer_name,rating,body,platform,product_name\nCSV User,4,Great product from CSV,flipkart,CSV Product\n"
    status, csv_import = req("POST", "/reviews/import-csv", token=token, form_data={"file": BytesIO(csv_content)})
    test("CSV imported", status == 200 and csv_import.get("imported", 0) >= 1, str(csv_import))

    # Summary
    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
    if errors:
        print("\nFailures:")
        for e in errors:
            print(e)
    print(f"{'='*40}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
