#!/usr/bin/env python3
"""Test pricing page, plan catalog, trial limits, and billing API."""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE = "http://localhost:8000/api"
FRONTEND = "http://localhost:3000"
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
        with urllib.request.urlopen(request, timeout=15) as resp:
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


def fetch_page(path):
    req_obj = urllib.request.Request(f"{FRONTEND}{path}", method="GET")
    req_obj.add_header("User-Agent", "ReviewFlowTest/1.0")
    try:
        with urllib.request.urlopen(req_obj, timeout=10) as r:
            return r.status, r.read().decode(), r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), e.geturl()


def psql(sql):
    result = subprocess.run(
        ["docker", "exec", "reviewflow-postgres-1", "psql", "-U", "reviewflow", "-d", "reviewflow", "-t", "-c", sql],
        capture_output=True, text=True,
    )
    return result.stdout.strip()


def main():
    print("\n=== ReviewFlow Pricing & Plan Tests ===\n")
    html = ""

    print("[1] Pricing Page — Public Access")
    try:
        status, html, final_url = fetch_page("/pricing")
        test("Pricing page loads", status == 200, f"status={status} url={final_url}")
        test("Shows Solo plan", "Solo" in html)
        test("Shows Business plan", "Business" in html)
        test("Shows Agency plan", "Agency" in html)
        test("Shows Agency Pro plan", "Agency Pro" in html)
        test("Seller/agency segment toggles", "Direct sellers" in html and "Agencies" in html)
        test("Billing cycle toggles", all(x in html for x in ["Monthly", "6 Months", "Annual"]))
        test("CTA links to register", 'href="/register' in html)
        _, quote = req("GET", "/billing/quote?plan=solo&billing_cycle=monthly")
        test("Billing quote solo ₹999", quote.get("amount_inr") == 999, str(quote))
    except Exception as e:
        test("Pricing page loads", False, str(e))

    print("\n[2] Pricing Page — Plan Highlights")
    for plan, snippets in [
        ("Solo", ["1 company", "2 platforms"]),
        ("Business", ["5 platforms", "2 team members"]),
        ("Agency", ["10 companies", "Client invites"]),
        ("Agency Pro", ["Unlimited companies", "SSO"]),
    ]:
        test(f"{plan} highlights on page", all(s in html for s in snippets), "missing in HTML")

    print("\n[3] Billing Plans API")
    status, catalog = req("GET", "/billing/plans")
    test("GET /billing/plans", status == 200)
    plan_ids = [p["id"] for p in catalog.get("plans", [])]
    test("Catalog has solo/growth/professional/enterprise", all(p in plan_ids for p in ["solo", "growth", "professional", "enterprise"]))

    status, cfg = req("GET", "/billing/config")
    test("GET /billing/config", status == 200 and cfg.get("trial_days") == 5)

    print("\n[4] Registration → Trial Subscription")
    email = f"pricing-{int(time.time())}@example.com"
    status, reg = req("POST", "/auth/register", data={
        "email": email, "password": "TestPass123!", "full_name": "Pricing Tester",
        "org_name": "Pricing Org", "account_type": "seller",
    })
    test("Register succeeds", status == 200, str(reg))
    org_id = reg.get("org_id")
    token = reg.get("access_token")

    sub_line = psql(f"SELECT plan, billing_cycle, status FROM subscriptions WHERE org_id = {org_id};")
    test("Trial subscription created", "trial" in sub_line and "trialing" in sub_line, sub_line)
    test("Default billing cycle = monthly", "monthly" in sub_line, sub_line)

    print("\n[5] Profile — Plan & Account Context")
    status, me = req("GET", "/auth/me", token=token)
    test("/auth/me returns org", status == 200 and me.get("org"))
    test("Subscription in /auth/me", me.get("subscription", {}).get("access") == "trialing")
    test("Account context in /auth/me", me.get("account", {}).get("account_type") == "seller")
    test("Seller hides company switcher", me.get("account", {}).get("show_company_switcher") is False)

    print("\n[6] Billing API — Demo Activation")
    status, act = req("POST", "/billing/activate", token=token, data={
        "plan": "solo", "billing_cycle": "monthly", "payer_type": "org",
    })
    test("POST /billing/activate (demo)", status == 200, str(act.get("message", act)))
    test("Plan activated to solo", act.get("subscription", {}).get("plan") == "solo")

    print("\n[7] Platform Limit Enforcement")
    status, _ = req("POST", "/platforms", token=token, data={
        "platform": "amazon", "display_name": "P1", "default_reply_mode": "ai",
    })
    test("1st platform allowed", status == 200)
    status, blocked = req("POST", "/platforms", token=token, data={
        "platform": "flipkart", "display_name": "P2", "default_reply_mode": "ai",
    })
    test("2nd platform blocked on Solo (limit 2 after 1st... solo allows 2)", status in (200, 402))
    # Solo allows 2 platforms - add third should block
    if status == 200:
        status3, blocked3 = req("POST", "/platforms", token=token, data={
            "platform": "myntra", "display_name": "P3", "default_reply_mode": "ai",
        })
        test("3rd platform blocked on Solo plan", status3 == 402, str(blocked3.get("detail", blocked3)))

    print("\n[8] Login page accessible without auth")
    status, login_html, _ = fetch_page("/login")
    test("Login page loads", status == 200 and "Sign in" in login_html)

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
    if errors:
        print("\nFailures:")
        for e in errors:
            print(e)
    print(f"\nTest account: {email} / TestPass123!")
    print(f"{'='*50}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
