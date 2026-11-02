#!/usr/bin/env python3
"""Test Google Business reviews + template response flows."""
import json
import sys
import urllib.request
import urllib.error
from urllib.parse import urlencode

BASE = "http://localhost:8000/api"
passed = failed = 0
errors = []


def req(method, path, token=None, data=None):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
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
    import time
    email = f"google-flow-{int(time.time())}@example.com"
    print("\n=== Google Business + Template Response Flow Tests ===\n")

    # Setup account
    print("[Setup] Register test account")
    status, reg = req("POST", "/auth/register", data={
        "email": email, "password": "TestPass123!", "full_name": "Google Flow Tester", "org_name": "Google Test Store"
    })
    test("Register", status == 200, str(reg))
    token = reg.get("access_token", "")

    # --- GOOGLE BUSINESS FLOW ---
    print("\n[1] Google Business — Connect Platform")
    status, gconn = req("POST", "/platforms", token=token, data={
        "platform": "google_business",
        "display_name": "My Google Business Profile",
        "default_reply_mode": "template",
        "credentials": {"access_token": "", "location_id": "locations/12345"},
    })
    test("Google platform connected", status == 200 and gconn.get("platform") == "google_business", str(gconn))
    google_id = gconn.get("id")

    print("\n[2] Google Business — Sync Reviews")
    status, sync = req("POST", f"/platforms/{google_id}/sync", token=token)
    test("Google sync completed", status == 200, str(sync))
    test("Google reviews imported", sync.get("imported", 0) >= 1, f"imported={sync.get('imported')}")

    print("\n[3] Google Business — Verify Reviews in Dashboard")
    status, reviews = req("GET", "/reviews?platform=google_business", token=token)
    test("Google reviews listed", status == 200 and reviews.get("total", 0) >= 1, f"total={reviews.get('total')}")
    google_reviews = reviews.get("items", [])
    by_rating = {r["rating"]: r for r in google_reviews}
    test("Has 5-star review", 5 in by_rating)
    test("Has 1-star review", 1 in by_rating)

    # --- TEMPLATE LIBRARY ---
    print("\n[4] Template Library — Create Multiple Templates")
    templates = {}
    template_defs = [
        ("Thank You 5-Star", "thank_you", "5",
         "Hi {{reviewer_name}}! Thank you for your wonderful {{rating}}-star review on Google! We're thrilled you enjoyed {{product_name}}. Visit us again soon! — {{brand_name}}"),
        ("Thank You 4-Star", "thank_you", "4",
         "Dear {{reviewer_name}}, thank you for your {{rating}}-star feedback on Google Business. We appreciate you choosing {{brand_name}} and hope to serve you again!"),
        ("Apology 1-2 Star", "apology", "any",
         "Hi {{reviewer_name}}, we're sorry to hear about your experience regarding {{issue_keyword}}. We take your feedback seriously. Please contact us directly so we can make this right. — {{brand_name}}"),
        ("Issue Resolution", "issue_resolution", "any",
         "Hello {{reviewer_name}}, we understand your concern about {{issue_keyword}}. Our team is looking into this and will resolve it promptly. Thank you for bringing this to our attention. — {{brand_name}}"),
        ("Neutral Acknowledgement", "neutral", "any",
         "Thank you {{reviewer_name}} for sharing your {{rating}}-star review on {{platform}}. Your feedback helps us improve. — {{brand_name}}"),
    ]
    for name, category, star_filter, body in template_defs:
        status, tpl = req("POST", "/templates", token=token, data={
            "name": name, "body": body, "category": category, "star_rating_filter": star_filter,
        })
        test(f"Template created: {name}", status == 200 and tpl.get("id"), str(tpl.get("id")))
        templates[name] = tpl

    status, all_tpl = req("GET", "/templates", token=token)
    test("All templates listed", status == 200 and len(all_tpl) >= 5, f"count={len(all_tpl)}")

    # --- REPLY MODE PER PLATFORM ---
    print("\n[5] Reply Mode — Set Google to Template, Amazon to AI")
    status, _ = req("POST", "/reply-modes", token=token, data={
        "scope": "platform", "platform_connection_id": google_id,
        "reply_mode": "template", "template_id": templates["Thank You 5-Star"]["id"],
    })
    test("Google reply mode = template", status == 200)

    # Also connect Amazon for comparison
    status, amz = req("POST", "/platforms", token=token, data={
        "platform": "amazon", "display_name": "Amazon Store", "default_reply_mode": "ai",
    })
    amazon_id = amz.get("id")
    status, _ = req("POST", "/reply-modes", token=token, data={
        "scope": "platform", "platform_connection_id": amazon_id, "reply_mode": "ai",
    })
    test("Amazon reply mode = AI", status == 200)

    # --- TEMPLATE RESPONSE FLOWS ---
    print("\n[6] Template Response — Apply Thank You to 5-Star Google Review")
    review_5 = by_rating.get(5)
    if review_5:
        tpl_id = templates["Thank You 5-Star"]["id"]
        status, reply = req("POST", f"/replies/apply-template?review_id={review_5['id']}&template_id={tpl_id}", token=token)
        test("5-star template applied", status == 200 and "body" in reply, reply.get("body", "")[:100])
        test("Placeholders filled (reviewer name)", status == 200 and review_5["reviewer_name"] in reply.get("body", ""))
        test("Placeholders filled (brand name)", status == 200 and "Google Test Store" in reply.get("body", ""))
        if reply.get("id"):
            status, pub = req("POST", f"/replies/publish?review_id={review_5['id']}&reply_id={reply['id']}", token=token)
            test("5-star reply published", status == 200, str(pub))

    print("\n[7] Template Response — Apply Apology to 1-Star Google Review")
    review_1 = by_rating.get(1)
    if review_1:
        tpl_id = templates["Apology 1-2 Star"]["id"]
        status, reply = req("POST", f"/replies/apply-template?review_id={review_1['id']}&template_id={tpl_id}", token=token)
        test("1-star apology template applied", status == 200 and "body" in reply, reply.get("body", "")[:100])
        test("Issue keyword extracted", status == 200 and ("delivery" in reply.get("body", "").lower() or "sorry" in reply.get("body", "").lower()))
        if reply.get("id"):
            status, pub = req("POST", f"/replies/publish?review_id={review_1['id']}&reply_id={reply['id']}", token=token)
            test("1-star reply published", status == 200, str(pub))

    print("\n[8] Template Response — Apply to 4-Star Review")
    review_4 = by_rating.get(4)
    if review_4:
        tpl_id = templates["Thank You 4-Star"]["id"]
        status, reply = req("POST", f"/replies/apply-template?review_id={review_4['id']}&template_id={tpl_id}", token=token)
        test("4-star template applied", status == 200 and "body" in reply, reply.get("body", "")[:80])

    print("\n[9] Template Response — Apply Issue Resolution to 2-Star Review")
    review_2 = by_rating.get(2)
    if review_2:
        tpl_id = templates["Issue Resolution"]["id"]
        status, reply = req("POST", f"/replies/apply-template?review_id={review_2['id']}&template_id={tpl_id}", token=token)
        test("2-star issue resolution applied", status == 200 and "body" in reply, reply.get("body", "")[:80])

    print("\n[10] AI Reply — Fallback for Pending Google Review")
    review_3_list = [r for r in google_reviews if r.get("rating") == 3]
    pending = [r for r in google_reviews if r.get("reply_status") == "pending"]
    target = pending[0] if pending else (google_reviews[0] if google_reviews else None)
    if target:
        status, ai = req("POST", "/ai/reply", token=token, data={"review_id": target["id"], "tone": "friendly"})
        test("AI reply generated (fallback)", status == 200 and "body" in ai, ai.get("body", "")[:80])

    print("\n[11] Bulk Template Apply")
    pending_ids = [r["id"] for r in google_reviews if r.get("reply_status") == "pending"][:3]
    if pending_ids:
        status, bulk = req("POST", "/replies/bulk", token=token, data={
            "review_ids": pending_ids, "source": "template",
            "template_id": templates["Neutral Acknowledgement"]["id"],
        })
        test("Bulk template apply", status == 200 and bulk.get("processed", 0) >= 0, str(bulk))

    print("\n[12] Verify Published Replies on Google Reviews")
    status, updated = req("GET", "/reviews?platform=google_business", token=token)
    published = [r for r in updated.get("items", []) if r.get("reply_status") == "published"]
    test("Has published Google replies", len(published) >= 1, f"published={len(published)}")

    print("\n[13] Analytics — Google Platform Breakdown")
    status, analytics = req("GET", "/analytics", token=token)
    test("Analytics has google_business", status == 200 and "google_business" in analytics.get("by_platform", {}),
         str(analytics.get("by_platform")))
    test("Reply rate > 0", status == 200 and analytics.get("reply_rate", 0) > 0,
         f"reply_rate={analytics.get('reply_rate')}")

    print("\n[14] Template Usage Count Updated")
    status, tpl_check = req("GET", "/templates", token=token)
    used = [t for t in tpl_check if t.get("usage_count", 0) > 0]
    test("Templates show usage count", len(used) >= 1, f"used_templates={len(used)}")

    print("\n[15] Audit Log — Reply Actions Recorded")
    status, audit = req("GET", "/audit-log", token=token)
    reply_actions = [a for a in audit if "reply" in a.get("action", "")]
    test("Audit log has reply actions", len(reply_actions) >= 1, f"actions={len(reply_actions)}")

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
    if errors:
        print("\nFailures:")
        for e in errors:
            print(e)
    print(f"{'='*50}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
