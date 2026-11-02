#!/usr/bin/env python3
"""Test Razorpay test API: config, order creation, and verify-payment flow."""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://localhost:8000/api"
RAZORPAY_API = "https://api.razorpay.com/v1"
ROOT = Path(__file__).resolve().parent.parent
passed = failed = 0


def load_env_file(path: Path) -> dict:
    env = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def req(method, path, token=None, data=None):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"detail": raw}


def razorpay_req(method, path, key_id, key_secret, data=None):
    url = f"{RAZORPAY_API}{path}"
    auth = base64.b64encode(f"{key_id}:{key_secret}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
    body = json.dumps(data).encode() if data else None
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=20) as resp:
        return resp.status, json.loads(resp.read().decode())


def test(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))


def main():
    print("\n=== Razorpay Test API ===\n")

    env = {**load_env_file(ROOT / ".env"), **os.environ}
    key_id = env.get("RAZORPAY_KEY_ID", "")
    key_secret = env.get("RAZORPAY_KEY_SECRET", "")

    if not key_id or not key_secret or "your_key" in key_id:
        print("  Razorpay test keys not configured.\n")
        print("  1. Sign up at https://dashboard.razorpay.com")
        print("  2. Switch to Test Mode → Settings → API Keys")
        print("  3. Add to reviewflow/.env:")
        print("     RAZORPAY_KEY_ID=rzp_test_...")
        print("     RAZORPAY_KEY_SECRET=...")
        print("  4. Restart backend: docker compose restart backend")
        print("  5. Re-run: python3 scripts/test_razorpay.py\n")
        return 1

    print(f"[1] Keys loaded: {key_id[:12]}...")

    print("\n[2] Backend billing config")
    status, config = req("GET", "/billing/config")
    test("Config endpoint", status == 200, str(config))
    test("razorpay_enabled true", config.get("razorpay_enabled") is True, str(config))
    test("Key ID matches", config.get("razorpay_key_id") == key_id, str(config.get("razorpay_key_id")))

    if not config.get("razorpay_enabled"):
        print("\n  Backend still shows razorpay_enabled=false.")
        print("  Run: docker compose restart backend")
        return 1

    print("\n[3] Direct Razorpay API — create test order")
    try:
        code, order = razorpay_req("POST", "/orders", key_id, key_secret, {
            "amount": 10000,
            "currency": "INR",
            "receipt": f"test_{int(time.time())}",
        })
        test("Razorpay API reachable", code == 200, str(order))
        test("Order has id", bool(order.get("id")), str(order))
    except urllib.error.HTTPError as e:
        test("Razorpay API reachable", False, e.read().decode())
        return 1

    print("\n[4] App create-order endpoint")
    email = f"razorpay-{int(time.time())}@example.com"
    status, reg = req("POST", "/auth/register", data={
        "email": email, "password": "TestPass123!", "full_name": "Razorpay Test", "org_name": "Razorpay Org",
    })
    test("Register test user", status == 200, str(reg))
    token = reg["access_token"]
    org_id = reg["org_id"]

    subprocess.run([
        "docker", "exec", "reviewflow-postgres-1", "psql", "-U", "reviewflow", "-d", "reviewflow", "-c",
        f"UPDATE subscriptions SET trial_ends_at = NOW() - INTERVAL '1 day', status = 'expired' WHERE org_id = {org_id};",
    ], capture_output=True)

    status, order_resp = req("POST", "/billing/create-order", token=token, data={
        "plan": "growth", "billing_cycle": "monthly", "payer_type": "user",
    })
    test("Create order via app", status == 200, str(order_resp))
    test("Returns order_id", bool(order_resp.get("order_id")), str(order_resp))
    test("Returns key_id", order_resp.get("key_id") == key_id, str(order_resp.get("key_id")))
    test("Amount in paise", order_resp.get("amount") == 149900, str(order_resp.get("amount")))

    print("\n[5] Verify endpoint rejects bad signature")
    status, bad = req("POST", "/billing/verify-payment", token=token, data={
        "razorpay_order_id": order_resp.get("order_id", "order_x"),
        "razorpay_payment_id": "pay_test_fake",
        "razorpay_signature": "invalid_signature",
    })
    test("Bad signature returns 400", status == 400, str(bad))

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
    print(f"\nUI test account: {email} / TestPass123!")
    print("Open http://localhost:3000/settings/billing and pay with:")
    print("  Card: 4111 1111 1111 1111  |  Expiry: any future  |  CVV: any")
    print("  UPI:  success@razorpay")
    print(f"{'='*50}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
