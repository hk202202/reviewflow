#!/usr/bin/env python3
"""Test hybrid seller vs agency account flows."""
import json
import time
import urllib.error
import urllib.request

BASE = "http://localhost:8000/api"


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
        body = e.read().decode() or "{}"
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {"detail": body}


def main():
    passed = failed = 0
    ts = int(time.time())

    def check(name, ok, detail=""):
        nonlocal passed, failed
        if ok:
            passed += 1
            print(f"  ✓ {name}" + (f" — {detail}" if detail else ""))
        else:
            failed += 1
            print(f"  ✗ {name}" + (f" — {detail}" if detail else ""))

    print("Hybrid Seller / Agency Tests\n")

    _, seller = req("POST", "/auth/register", data={
        "email": f"seller-{ts}@example.com", "password": "TestPass123!",
        "full_name": "Seller User", "org_name": "My Store", "account_type": "seller",
    })
    check("Register seller", seller.get("org_id"), f"account_type in me next")
    seller_token = seller["access_token"]

    _, me_s = req("GET", "/auth/me", token=seller_token)
    check("Seller account_type", me_s.get("account", {}).get("account_type") == "seller")
    check("Seller no company switcher UI flag", me_s.get("account", {}).get("show_company_switcher") is False)

    code, blocked = req("POST", "/auth/organizations", token=seller_token, data={"org_name": "Second Co"})
    check("Seller blocked from 2nd company", code == 402, str(blocked.get("detail", ""))[:50])

    _, agency = req("POST", "/auth/register", data={
        "email": f"agency-{ts}@example.com", "password": "TestPass123!",
        "full_name": "Agency Owner", "org_name": "ReviewPro Agency", "account_type": "agency",
    })
    agency_token = agency["access_token"]
    check("Register agency", agency.get("org_id"))

    _, me_a = req("GET", "/auth/me", token=agency_token)
    check("Agency account_type", me_a.get("account", {}).get("account_type") == "agency")
    check("Agency shows switcher", me_a.get("account", {}).get("show_company_switcher") is True)

    _, client = req("POST", "/auth/organizations", token=agency_token, data={"org_name": "Client Brand A"})
    check("Agency adds client company", client.get("org_id"))

    _, ctx = req("GET", "/auth/account-context", token=client["access_token"])
    check("Agency owned companies", ctx.get("owned_companies", 0) >= 2, str(ctx.get("owned_companies")))

    _, plans = req("GET", "/billing/plans")
    check("Billing plans API", len(plans.get("plans", [])) >= 4)

    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
