#!/usr/bin/env python3
"""Test 5-day trial and payment activation workflow."""
import json
import sys
import time
import urllib.request
import urllib.error
import subprocess

BASE = "http://localhost:8000/api"
passed = failed = 0


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
        print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))


def main():
    print("\n=== Trial & Billing Workflow Tests ===\n")
    email = f"trial-{int(time.time())}@example.com"

    print("[1] Register → 5-day trial")
    status, reg = req("POST", "/auth/register", data={
        "email": email, "password": "TestPass123!", "full_name": "Trial User", "org_name": "Trial Org",
    })
    test("Register", status == 200)
    token = reg["access_token"]
    org_id = reg["org_id"]

    print("\n[2] Trial status")
    status, billing = req("GET", "/billing/status", token=token)
    test("Billing status", status == 200 and billing.get("access") == "trialing", str(billing))
    test("5 days left on new account", billing.get("days_left") == 5, str(billing.get("days_left")))
    test("Has feature access during trial", billing.get("has_access") is True)

    print("\n[3] Features work during trial")
    status, platform = req("POST", "/platforms", token=token, data={
        "platform": "amazon", "display_name": "Trial Store", "default_reply_mode": "ai",
    })
    test("Connect platform during trial", status == 200, str(platform))

    print("\n[4] Simulate trial expiry")
    subprocess.run([
        "docker", "exec", "reviewflow-postgres-1", "psql", "-U", "reviewflow", "-d", "reviewflow", "-c",
        f"UPDATE subscriptions SET trial_ends_at = NOW() - INTERVAL '1 day', status = 'expired' WHERE org_id = {org_id};",
    ], capture_output=True)

    status, billing = req("GET", "/billing/status", token=token)
    test("Status shows expired", billing.get("access") == "expired", str(billing))
    test("No feature access after expiry", billing.get("has_access") is False)

    print("\n[5] Features blocked after expiry")
    status, blocked = req("POST", "/platforms", token=token, data={
        "platform": "flipkart", "display_name": "Blocked", "default_reply_mode": "ai",
    })
    test("Platform connect returns 402", status == 402, str(blocked))
    detail = blocked.get("detail", {})
    if isinstance(detail, dict):
        test("402 has trial_expired code", detail.get("code") == "trial_expired", str(detail))

    print("\n[6] Billing still accessible")
    status, me = req("GET", "/auth/me", token=token)
    test("/auth/me works when expired", status == 200)
    status, billing = req("GET", "/billing/status", token=token)
    test("/billing/status works when expired", status == 200)

    print("\n[7] Activate subscription — org account")
    status, activated = req("POST", "/billing/activate", token=token, data={
        "plan": "growth", "billing_cycle": "monthly", "payer_type": "org",
    })
    test("Org payment activates subscription", status == 200, str(activated))

    print("\n[8] Features restored after payment")
    status, billing = req("GET", "/billing/status", token=token)
    test("Access active after payment", billing.get("access") == "active", str(billing))
    test("Payer type recorded", billing.get("payer_type") == "org", str(billing))

    status, platform2 = req("POST", "/platforms", token=token, data={
        "platform": "google_business", "display_name": "Restored", "default_reply_mode": "template",
    })
    test("Platform connect works after payment", status == 200, str(platform2))

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
    print(f"Test account: {email} / TestPass123!")
    print(f"{'='*50}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
