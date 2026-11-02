#!/usr/bin/env python3
"""Test Google OAuth config and auth-url endpoint."""
import json
import sys
import time
import urllib.request
import urllib.error

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
    print("\n=== Google Business OAuth Tests ===\n")

    status, health = req("GET", "/../health".replace("/api/../", "/"))
    # health is at /health not /api/health
    try:
        with urllib.request.urlopen("http://localhost:8000/health", timeout=5) as r:
            test("Backend health", r.status == 200)
    except Exception as e:
        test("Backend health", False, str(e))
        return 1

    status, cfg = req("GET", "/platforms/google/config")
    test("Google config endpoint", status == 200, str(cfg))
    test("Google OAuth configured", cfg.get("configured") is True, str(cfg))
    test("Redirect URI set", "callback" in (cfg.get("redirect_uri") or ""), str(cfg.get("redirect_uri")))

    email = f"google-oauth-{int(time.time())}@example.com"
    status, reg = req("POST", "/auth/register", data={
        "email": email, "password": "TestPass123!", "full_name": "Google Test", "org_name": "Google Org",
    })
    test("Register test user", status == 200, str(reg))
    token = reg.get("access_token", "")

    status, auth = req("GET", "/platforms/google/auth-url", token=token)
    test("Auth URL endpoint", status == 200, str(auth))
    auth_url = auth.get("auth_url", "")
    test("Auth URL contains accounts.google.com", "accounts.google.com" in auth_url, auth_url[:80])
    test("Auth URL contains client_id", "client_id=" in auth_url)
    test("Auth URL contains business.manage scope", "business.manage" in auth_url)

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"\nManual UI test:")
    print(f"  1. Login: {email} / TestPass123!")
    print(f"  2. Go to http://localhost:3000/platforms")
    print(f"  3. Click 'Connect Google Business'")
    print(f"  4. Sign in with your test Google account")
    print(f"  5. Click 'Sync Reviews' on the connected platform")
    print(f"{'='*50}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
