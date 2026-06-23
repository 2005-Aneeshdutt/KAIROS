#!/usr/bin/env python3
"""Seed the Kairos demo with realistic people, a cross-device identity merge, and
revenue — so the dashboards, /people and identity analytics look alive on stage.

Usage:  python seed_demo.py            # add demo data
        python seed_demo.py --reset    # wipe first, then seed
"""
import json, sys, time, urllib.request, urllib.error

BASE = "http://localhost:8000"


def _req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode()[:120]}
    except Exception as e:
        return {"error": str(e)}


def track(uid, t, pid=None, device="desktop", dwell=0):
    _req("POST", "/track", {"uid": uid, "type": t, "product_id": pid, "device": device, "dwell_ms": dwell})


def login(email, name, guest=None):
    return _req("POST", "/auth/login", {"email": email, "name": name, "guest_uid": guest or ""})


def journey(uid, steps):
    for (t, pid, dev, dw) in steps:
        track(uid, t, pid, dev, dw)


def main():
    if "--reset" in sys.argv:
        print("reset:", _req("POST", "/admin/reset"))

    if _req("GET", "/health").get("status") != "ok":
        print("✗ API not reachable at", BASE, "— start it first."); return

    # 1) Persuadable — fixates on one item, researches, carts, doesn't buy (the TARGET demo)
    p = login("aarav@demo.com", "Aarav Shah")
    u = p["core_id"]
    journey(u, [("view_product", "p9", "desktop", 6000), ("view_detail", "p9", "desktop", 8000),
                ("view_all_reviews", "p9", "desktop", 5000), ("view_product", "p9", "desktop", 4000),
                ("add_to_wishlist", "p9", "desktop", 0), ("add_to_cart", "p9", "desktop", 0),
                ("view_product", "p12", "desktop", 3000)])

    # 2) Sure Thing — decisive, buys fast (HOLD / don't discount)
    p = login("diya@demo.com", "Diya Menon"); u = p["core_id"]
    journey(u, [("view_product", "p13", "desktop", 2000), ("add_to_cart", "p13", "desktop", 0)])
    _req("POST", "/purchase", {"uid": u})

    # 3) Over-browser, never carts (skews toward Sleeping Dog / Lost Cause — SUPPRESS/SKIP)
    p = login("kabir@demo.com", "Kabir Rao"); u = p["core_id"]
    journey(u, [("view_product", f"p{i}", "desktop", 1200) for i in range(1, 12)])

    # 4) Light browser — low intent (Lost Cause)
    p = login("isha@demo.com", "Isha Nair"); u = p["core_id"]
    journey(u, [("view_product", "p20", "desktop", 1500)])

    # 5) CROSS-DEVICE IDENTITY MERGE — guest on desktop, leaves, mobile, then signs in
    g = "seedguest_" + str(int(time.time()))
    journey(g, [("view_product", "p7", "desktop", 5000), ("view_detail", "p7", "desktop", 6000),
                ("add_to_cart", "p7", "desktop", 0)])
    _req("POST", "/session/end", {"uid": g, "device": "desktop"})
    journey(g, [("view_product", "p10", "mobile", 4000), ("view_reviews", "p10", "mobile", 3000)])
    _req("POST", "/chat", {"uid": g, "message": "chelsea boots in my size?"})
    m = login("rohan@demo.com", "Rohan Gupta", guest=g)
    mg = m.get("merge") or {}
    print(f"   merged Rohan: {mg.get('events')} events, {mg.get('sessions')} sessions, {mg.get('signal_count')} signals")

    # 6) A loyal returning buyer with two orders (revenue + Sure Thing reward story)
    p = login("ananya@demo.com", "Ananya Iyer"); u = p["core_id"]
    journey(u, [("view_product", "p19", "desktop", 3000), ("add_to_cart", "p19", "desktop", 0)])
    _req("POST", "/purchase", {"uid": u})
    journey(u, [("view_product", "p17", "mobile", 2500), ("add_to_cart", "p17", "mobile", 0)])
    _req("POST", "/purchase", {"uid": u})

    # 7) Bundle-builder across categories (cross-category, bundle opportunity)
    p = login("vihaan@demo.com", "Vihaan Reddy"); u = p["core_id"]
    journey(u, [("view_product", "p1", "desktop", 3000), ("add_to_wishlist", "p1", "desktop", 0),
                ("view_product", "p11", "desktop", 2500), ("add_to_cart", "p11", "desktop", 0),
                ("view_product", "p14", "desktop", 2200)])

    # 8) One person who opted OUT of personalisation (privacy/consent story)
    p = login("sara@demo.com", "Sara Khan"); u = p["core_id"]
    journey(u, [("view_product", "p3", "desktop", 2000)])
    _req("POST", "/consent", {"uid": u, "consent": False})

    # summary
    ppl = _req("GET", "/people").get("people", [])
    rev = _req("GET", "/analytics/live").get("revenue", {})
    ids = _req("GET", "/analytics/identity")
    print(f"\n✅ Seeded {len(ppl)} people")
    print(f"   revenue: ${rev.get('gross', 0):,.0f} across {rev.get('orders', 0)} orders")
    print(f"   identity: {ids.get('resolved')}/{ids.get('people')} resolved · "
          f"{ids.get('cross_device')} cross-device · {ids.get('signals_unified')} signals · "
          f"{ids.get('stitched_sessions')} stitched sessions")
    print("   segments:", {p['name'].split()[0]: p['segment'] for p in ppl})


if __name__ == "__main__":
    main()
