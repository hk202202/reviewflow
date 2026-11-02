#!/usr/bin/env python3
"""Test multi-company org switching with separate platform connections."""
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
        return e.code, json.loads(e.read().decode() or "{}")


def main():
    passed = failed = 0
    email = f"multi-org-{int(time.time())}@example.com"

    def check(name, ok, detail=""):
        nonlocal passed, failed
        if ok:
            passed += 1
            print(f"  ✓ {name}" + (f" — {detail}" if detail else ""))
        else:
            failed += 1
            print(f"  ✗ {name}" + (f" — {detail}" if detail else ""))

    print("Multi-Company Org Switch Tests\n")

    code, reg = req("POST", "/auth/register", data={
        "email": email, "password": "TestPass123!", "full_name": "Agency Owner",
        "org_name": "Company A", "account_type": "agency",
    })
    check("Register Company A", code == 200, f"org_id={reg.get('org_id')}")
    token_a = reg["access_token"]
    org_a = reg["org_id"]

    code, p1 = req("POST", "/platforms", token=token_a, data={
        "platform": "amazon", "display_name": "Company A Amazon", "default_reply_mode": "template",
        "credentials": {"asins": "B0COMPANYA"},
    })
    check("Company A: connect Amazon", code == 200)

    code, org2 = req("POST", "/auth/organizations", token=token_a, data={"org_name": "Company B"})
    check("Create Company B", code == 200, f"org_id={org2.get('org_id')}")
    token_b = org2["access_token"]
    org_b = org2["org_id"]

    code, p2 = req("POST", "/platforms", token=token_b, data={
        "platform": "flipkart", "display_name": "Company B Flipkart", "default_reply_mode": "ai",
        "credentials": {"client_id": "demo"},
    })
    check("Company B: connect Flipkart", code == 200)

    code, platforms_b = req("GET", "/platforms", token=token_b)
    check("Company B sees only its platforms", code == 200 and len(platforms_b) == 1 and platforms_b[0]["platform"] == "flipkart")

    code, switch = req("POST", "/auth/switch-org", token=token_b, data={"org_id": org_a})
    check("Switch back to Company A", code == 200 and switch.get("org_id") == org_a)
    token_a2 = switch["access_token"]

    code, platforms_a = req("GET", "/platforms", token=token_a2)
    check("Company A sees Amazon only", code == 200 and any(p["platform"] == "amazon" for p in platforms_a))
    check("Company A isolated from Flipkart", not any(p["platform"] == "flipkart" for p in platforms_a))

    code, orgs = req("GET", "/auth/organizations", token=token_a2)
    check("List organizations", code == 200 and len(orgs) >= 2, f"{len(orgs)} companies")

    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
