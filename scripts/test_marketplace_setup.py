#!/usr/bin/env python3
"""Test Amazon, Flipkart, and Myntra marketplace setup endpoints."""
import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://localhost:8000/api"
EMAIL = "ui-trial-2026@example.com"
PASSWORD = "TestPass123!"


def req(method, path, token=None, data=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(f"{BASE}{path}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=15) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def main():
    passed = 0
    failed = 0

    def check(name, ok, detail=""):
        nonlocal passed, failed
        if ok:
            passed += 1
            print(f"  ✓ {name}" + (f" — {detail}" if detail else ""))
        else:
            failed += 1
            print(f"  ✗ {name}" + (f" — {detail}" if detail else ""))

    print("ReviewFlow Marketplace Setup Tests\n")

    code, login = req("POST", "/auth/login", data={"email": EMAIL, "password": PASSWORD})
    check("Login", code == 200 and "access_token" in login, login.get("user", {}).get("email", ""))
    if code != 200:
        print("\nCannot continue without auth.")
        sys.exit(1)
    token = login["access_token"]

    code, cfg = req("GET", "/platforms/amazon/config", token=token)
    check("Amazon config", code == 200 and cfg.get("configured"), f"{len(cfg.get('marketplaces', []))} marketplaces")

    code, val = req("POST", "/platforms/amazon/validate", token=token, data={
        "client_id": "demo", "client_secret": "demo", "refresh_token": "demo", "asins": "B0DEMO123",
    })
    check("Amazon validate (invalid creds)", code == 200 and val.get("valid") is False)

    # Connect Amazon (demo creds)
    code, amz = req("POST", "/platforms", token=token, data={
        "platform": "amazon",
        "display_name": f"Test Amazon {int(time.time())}",
        "default_reply_mode": "template",
        "credentials": {"asins": "B0TEST123", "marketplace_id": "A21TJRUUN4KGV", "region": "eu"},
    })
    check("Connect Amazon", code == 200 and amz.get("platform") == "amazon")
    amz_id = amz.get("id")

    if amz_id:
        code, sync = req("POST", f"/platforms/{amz_id}/sync", token=token)
        check("Amazon sync", code == 200 and sync.get("imported", 0) >= 0, sync.get("message", "")[:60])

    # Connect Flipkart + extension import
    code, fk = req("POST", "/platforms", token=token, data={
        "platform": "flipkart",
        "display_name": f"Test Flipkart {int(time.time())}",
        "default_reply_mode": "ai",
        "credentials": {"setup_via": "extension"},
    })
    check("Connect Flipkart", code == 200 and fk.get("platform") == "flipkart")
    fk_id = fk.get("id")

    code, ext = req("GET", "/extension/connections", token=token)
    check("Extension connections list", code == 200 and any(c["id"] == fk_id for c in ext if fk_id))

    if fk_id:
        code, imp = req("POST", "/extension/import-reviews", token=token, data={
            "platform": "flipkart",
            "platform_connection_id": fk_id,
            "reviews": [
                {
                    "external_review_id": f"fk-test-{int(time.time())}",
                    "reviewer_name": "Test Buyer",
                    "rating": 4,
                    "title": "Good product",
                    "body": "Works as expected, happy with the purchase quality.",
                    "product_name": "Test SKU",
                }
            ],
        })
        check("Extension import Flipkart", code == 200 and imp.get("imported") == 1, f"imported={imp.get('imported')}")

        code, sync_fk = req("POST", f"/platforms/{fk_id}/sync", token=token)
        check("Flipkart sync (extension hint)", code == 200 and "message" in sync_fk)

    # Connect Myntra
    code, my = req("POST", "/platforms", token=token, data={
        "platform": "myntra",
        "display_name": f"Test Myntra {int(time.time())}",
        "default_reply_mode": "template",
        "credentials": {"setup_via": "extension"},
    })
    check("Connect Myntra", code == 200 and my.get("platform") == "myntra")
    my_id = my.get("id")

    if my_id:
        code, imp2 = req("POST", "/extension/import-reviews", token=token, data={
            "platform": "myntra",
            "platform_connection_id": my_id,
            "reviews": [
                {
                    "external_review_id": f"my-test-{int(time.time())}",
                    "reviewer_name": "Fashion Buyer",
                    "rating": 2,
                    "body": "Size did not match the chart, disappointed with fit.",
                    "product_name": "Test Dress",
                }
            ],
        })
        check("Extension import Myntra", code == 200 and imp2.get("imported") == 1)

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
