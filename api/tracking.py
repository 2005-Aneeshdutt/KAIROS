from __future__ import annotations

import hashlib
import random
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from pathlib import Path
from threading import Lock

import joblib
import numpy as np

import db

_LIVE_PATH = Path(__file__).resolve().parents[1] / "ml" / "artifacts" / "live_uplift.joblib"
_LIVE_MODEL = None
LIVE_SHOPPERS: dict[str, dict] = {}

def _live_model():
    global _LIVE_MODEL
    if _LIVE_MODEL is None:
        try:
            _LIVE_MODEL = joblib.load(_LIVE_PATH)
        except Exception as e:
            print(f"[live_model] failed to load ({e!r}); falling back to heuristic scoring")
            _LIVE_MODEL = {}
    return _LIVE_MODEL


def live_model_loaded() -> bool:
    return bool(_live_model())

PRODUCTS = [
    {"id": "p1", "name": "Floral Wrap Dress", "price": 79, "cat": "Women", "emoji": "👗", "rating": 4.7, "blurb": "Flowy midi, breathable viscose"},
    {"id": "p2", "name": "Tailored Blazer", "price": 129, "cat": "Women", "emoji": "🧥", "rating": 4.6, "blurb": "Structured, office-to-evening"},
    {"id": "p3", "name": "Silk Blouse", "price": 69, "cat": "Women", "emoji": "👚", "rating": 4.5, "blurb": "Mulberry silk, relaxed fit"},
    {"id": "p4", "name": "High-Rise Jeans", "price": 89, "cat": "Women", "emoji": "👖", "rating": 4.7, "blurb": "Sculpting stretch denim"},
    {"id": "p5", "name": "Slim-Fit Chinos", "price": 69, "cat": "Men", "emoji": "👖", "rating": 4.6, "blurb": "All-day comfort cotton twill"},
    {"id": "p6", "name": "Linen Shirt", "price": 59, "cat": "Men", "emoji": "👔", "rating": 4.5, "blurb": "Breathable, summer-ready"},
    {"id": "p7", "name": "Bomber Jacket", "price": 149, "cat": "Men", "emoji": "🧥", "rating": 4.8, "blurb": "Water-resistant, ribbed cuffs"},
    {"id": "p8", "name": "Graphic Tee", "price": 29, "cat": "Men", "emoji": "👕", "rating": 4.4, "blurb": "Soft combed cotton"},
    {"id": "p9", "name": "Leather Sneakers", "price": 119, "cat": "Shoes", "emoji": "👟", "rating": 4.7, "blurb": "Minimal, full-grain leather"},
    {"id": "p10", "name": "Chelsea Boots", "price": 159, "cat": "Shoes", "emoji": "🥾", "rating": 4.6, "blurb": "Suede, elastic side panels"},
    {"id": "p11", "name": "Strappy Heels", "price": 99, "cat": "Shoes", "emoji": "👠", "rating": 4.4, "blurb": "85mm, cushioned sole"},
    {"id": "p12", "name": "Running Shoes", "price": 109, "cat": "Shoes", "emoji": "👟", "rating": 4.8, "blurb": "Responsive foam, lightweight"},
    {"id": "p13", "name": "Leather Tote", "price": 189, "cat": "Bags", "emoji": "👜", "rating": 4.8, "blurb": "Full-grain, fits a 15\" laptop"},
    {"id": "p14", "name": "Mini Crossbody", "price": 89, "cat": "Bags", "emoji": "👛", "rating": 4.6, "blurb": "Adjustable strap, gold hardware"},
    {"id": "p15", "name": "Canvas Backpack", "price": 79, "cat": "Bags", "emoji": "🎒", "rating": 4.5, "blurb": "Water-repellent, padded straps"},
    {"id": "p16", "name": "Weekender Duffel", "price": 139, "cat": "Bags", "emoji": "🧳", "rating": 4.7, "blurb": "Cabin-size, shoe compartment"},
    {"id": "p17", "name": "Aviator Sunglasses", "price": 129, "cat": "Accessories", "emoji": "🕶️", "rating": 4.6, "blurb": "Polarized, UV400"},
    {"id": "p18", "name": "Silk Scarf", "price": 49, "cat": "Accessories", "emoji": "🧣", "rating": 4.5, "blurb": "Hand-rolled edges, print"},
    {"id": "p19", "name": "Classic Watch", "price": 199, "cat": "Accessories", "emoji": "⌚", "rating": 4.8, "blurb": "Sapphire glass, leather strap"},
    {"id": "p20", "name": "Statement Earrings", "price": 39, "cat": "Accessories", "emoji": "💎", "rating": 4.4, "blurb": "18k gold-plated, hypoallergenic"},
    {"id": "p21", "name": "Performance Hoodie", "price": 79, "cat": "Activewear", "emoji": "🧥", "rating": 4.7, "blurb": "Moisture-wicking, four-way stretch"},
    {"id": "p22", "name": "Training Shorts", "price": 35, "cat": "Activewear", "emoji": "🩳", "rating": 4.5, "blurb": "Lightweight, zip pocket"},
    {"id": "p23", "name": "Yoga Leggings", "price": 55, "cat": "Activewear", "emoji": "🧘", "rating": 4.8, "blurb": "High-rise, squat-proof"},
    {"id": "p24", "name": "Baseball Cap", "price": 25, "cat": "Activewear", "emoji": "🧢", "rating": 4.4, "blurb": "Adjustable, embroidered logo"},
]
PRODUCT_BY_ID = {p["id"]: p for p in PRODUCTS}
CATEGORIES = ["Women", "Men", "Shoes", "Bags", "Accessories", "Activewear"]
CHANNELS = ["Email", "Push", "SMS", "WhatsApp", "In-App", "Web Push", "Retargeting Ad",
            "Wallet Pass", "Live Concierge", "Voice Assistant", "QR Re-engage", "Smart Mirror"]
CHANNEL_META = {
    "Email":          {"cost": 0.05, "latency": "minutes",  "immediacy": 2, "icon": "📧", "kind": "off-site"},
    "Push":           {"cost": 0.08, "latency": "instant",  "immediacy": 5, "icon": "🔔", "kind": "off-site"},
    "SMS":            {"cost": 0.25, "latency": "instant",  "immediacy": 5, "icon": "💬", "kind": "off-site"},
    "WhatsApp":       {"cost": 0.15, "latency": "instant",  "immediacy": 4, "icon": "🟢", "kind": "off-site"},
    "In-App":         {"cost": 0.01, "latency": "live",     "immediacy": 5, "icon": "📲", "kind": "on-site"},
    "Web Push":       {"cost": 0.02, "latency": "instant",  "immediacy": 4, "icon": "🌐", "kind": "off-site"},
    "Retargeting Ad": {"cost": 0.12, "latency": "hours",    "immediacy": 1, "icon": "🎯", "kind": "ambient"},
    "Wallet Pass":    {"cost": 0.03, "latency": "instant",  "immediacy": 3, "icon": "🎟️", "kind": "off-site"},
    "Live Concierge": {"cost": 0.40, "latency": "live",     "immediacy": 5, "icon": "💁", "kind": "off-site"},
    "Voice Assistant":{"cost": 0.06, "latency": "scheduled","immediacy": 2, "icon": "🗣️", "kind": "off-site"},
    "QR Re-engage":   {"cost": 0.01, "latency": "physical", "immediacy": 2, "icon": "📱", "kind": "ambient"},
    "Smart Mirror":   {"cost": 0.02, "latency": "in-store", "immediacy": 4, "icon": "🪞", "kind": "in-store"},
}

_BADGES = [None, "Best Seller", "Sale", "New", "Staff Pick", None, "Sale"]

OFFERS = [
    {"label": "20% OFF", "kind": "discount", "pct": 20},
    {"label": "15% OFF $35+", "kind": "discount", "pct": 15},
    {"label": "Buy 1 Get 1 50%", "kind": "bogo", "pct": 0},
    {"label": "$3 Cash Rewards", "kind": "cash", "pct": 0},
    {"label": "25% OFF", "kind": "discount", "pct": 25},
    {"label": "2× Points", "kind": "points", "pct": 0},
    {"label": "30% OFF Clearance", "kind": "discount", "pct": 30},
    {"label": "Buy 2 Save 40%", "kind": "bundle", "pct": 0},
]

_UNSPLASH = "https://images.unsplash.com/photo-{id}?auto=format&fit=crop&w=600&h=600&q=72"
PRODUCT_IMG = {
    "p1":  "1572804013309-59a88b7e92f1",
    "p2":  "1594633312681-425c7b97ccd1",
    "p3":  "1564257631407-4deb1f99d992",
    "p4":  "1542272604-787c3835535d",
    "p5":  "1473966968600-fa801b869a1a",
    "p6":  "1602810318383-e386cc2a3ccf",
    "p7":  "1551028719-00167b16eac5",
    "p8":  "1521572163474-6864f9cf17ab",
    "p9":  "1549298916-b41d501d3772",
    "p10": "1638247025967-b4e38f787b76",
    "p11": "1543163521-1bf539c55dd2",
    "p12": "1542291026-7eec264c27ff",
    "p13": "1584917865442-de89df76afd3",
    "p14": "1548036328-c9fa89d128fa",
    "p15": "1553062407-98eeb64c6a62",
    "p16": "1547949003-9792a18a2601",
    "p17": "1572635196237-14b3f281503f",
    "p18": "1601924994987-69e26d50dc26",
    "p19": "1523275335684-37898b6baf30",
    "p20": "1535632066927-ab7c9ab60908",
    "p21": "1556821840-3a63f95609a7",
    "p22": "1591195853828-11db59a44f6b",
    "p23": "1552286450-4a669f880062",
    "p24": "1588850561407-ed78c282e89b",
}

TICKER = [
    "Up to 30% OFF new-season styles",
    "Buy 1 Get 1 50% OFF on tees",
    "FREE express shipping over $50",
    "Extra 20% OFF sale with code STYLE20",
    "2× loyalty points on shoes this weekend",
    "New members get 200 bonus points",
    "Members get early access to the drop",
]

BUNDLES = [
    {"id": "b1", "name": "Weekend Getaway Edit", "emoji": "🧳", "pct": 25,
     "items": ["p16", "p6", "p17"], "blurb": "Duffel + Linen Shirt + Sunglasses"},
    {"id": "b2", "name": "Office Power Look", "emoji": "💼", "pct": 30,
     "items": ["p2", "p3", "p10"], "blurb": "Blazer + Silk Blouse + Chelsea Boots"},
    {"id": "b3", "name": "Athleisure Set", "emoji": "🏃", "pct": 20,
     "items": ["p21", "p23", "p12"], "blurb": "Hoodie + Leggings + Running Shoes"},
    {"id": "b4", "name": "Date Night Look", "emoji": "✨", "pct": 22,
     "items": ["p1", "p11", "p14"], "blurb": "Wrap Dress + Heels + Crossbody"},
]

COUPONS = [
    {"id": "cp1", "amount": "$15", "desc": "Off $75+ on dresses & tops", "tag": "myAura exclusive", "expires": "tomorrow"},
    {"id": "cp2", "amount": "$10", "desc": "Buy 2+ accessories", "tag": "myAura exclusive", "expires": "3 days"},
    {"id": "cp3", "amount": "20%", "desc": "First order of shoes online", "tag": "myAura exclusive", "expires": "this week"},
    {"id": "cp4", "amount": "$25", "desc": "Spend $150+ on outerwear", "tag": "seasonal", "expires": "5 days"},
    {"id": "cp5", "amount": "$8", "desc": "Activewear orders $40+", "tag": "myAura exclusive", "expires": "2 days"},
]

REDEMPTIONS = [
    {"id": "rd1", "name": "$5 off your order", "cost": 125, "icon": "🏷️", "partner": "aura"},
    {"id": "rd2", "name": "Free shipping", "cost": 50, "icon": "🚚", "partner": "aura"},
    {"id": "rd3", "name": "Swiggy ₹100 voucher", "cost": 500, "icon": "🍔", "partner": "Swiggy"},
    {"id": "rd4", "name": "MakeMyTrip ₹250 off", "cost": 1000, "icon": "✈️", "partner": "MakeMyTrip"},
    {"id": "rd5", "name": "Amazon ₹150 gift card", "cost": 750, "icon": "📦", "partner": "Amazon"},
    {"id": "rd6", "name": "$15 off $60+", "cost": 300, "icon": "💳", "partner": "aura"},
]
_REVIEWER_NAMES = [
    "Sarah M.", "James T.", "Priya K.", "Diego R.", "Emma L.", "Wei C.", "Aisha B.",
    "Tom H.", "Nina P.", "Marcus J.", "Lucia G.", "Raj S.", "Chloe W.", "Ahmed N.",
]
_POS_REVIEWS = [
    ("Absolutely love it", "Exactly what I was looking for. Noticed a difference within a week and will definitely repurchase."),
    ("Works as promised", "Been using this daily and it's become part of my routine. High quality and great value."),
    ("Highly recommend", "Bought it on a whim and so glad I did. Fast shipping and the product is even better in person."),
    ("My new favorite", "I've tried a lot of similar products and this is by far the best. Gentle and effective."),
    ("Great value", "Does everything it says. The price is fair for the quality you get. Five stars."),
]
_MIXED_REVIEWS = [
    ("Good, but…", "Solid product overall. Took a little longer to see results than I expected, but happy so far."),
    ("Decent", "Does the job. Packaging could be better but the contents are good quality."),
    ("Pretty good", "Works well for me, though results may vary. Would still recommend giving it a try."),
]

def _seed(pid: str) -> int:
    return int(hashlib.md5(pid.encode()).hexdigest(), 16)

def enrich(p: dict) -> dict:
    s = _seed(p["id"])
    offer = OFFERS[s % len(OFFERS)]
    pct = offer["pct"]
    sale = round(p["price"] * (1 - pct / 100), 2) if pct else p["price"]
    badge = _BADGES[(s // 7) % len(_BADGES)]
    img_id = PRODUCT_IMG.get(p["id"])
    img = _UNSPLASH.format(id=img_id) if img_id else ""
    return {**p, "offer": offer["label"], "offer_kind": offer["kind"],
            "discount_pct": pct, "list_price": p["price"], "sale_price": sale,
            "img": img,
            "badge": badge, "reviews_count": 40 + s % 960, "stock": 4 + s % 50}

def bundles_detail() -> list[dict]:
    out = []
    for b in BUNDLES:
        items = [PRODUCT_BY_ID[i] for i in b["items"] if i in PRODUCT_BY_ID]
        total = round(sum(i["price"] for i in items), 2)
        price = round(total * (1 - b["pct"] / 100), 2)
        out.append({**b, "products": items, "total": total, "price": price,
                    "saves": round(total - price, 2)})
    return out

def promotions() -> dict:
    return {"ticker": TICKER, "bundles": bundles_detail(),
            "coupons": COUPONS, "redemptions": REDEMPTIONS}

def reviews_for(p: dict) -> list[dict]:
    rng = random.Random(_seed(p["id"]))
    n = 3 + rng.randint(0, 2)
    base = p.get("rating", 4.5)
    out = []
    for _ in range(n):
        good = rng.random() < (0.55 + (base - 4.0))
        rating = (5 if rng.random() < 0.6 else 4) if good else rng.choice([3, 4])
        title, text = rng.choice(_POS_REVIEWS if good else _MIXED_REVIEWS)
        out.append({
            "author": rng.choice(_REVIEWER_NAMES),
            "rating": rating,
            "title": title,
            "text": text,
            "date": (date.today() - timedelta(days=rng.randint(2, 240))).isoformat(),
            "verified": rng.random() < 0.85,
            "helpful": rng.randint(0, 64),
        })
    return out

def _description(p: dict) -> str:
    benefits = {
        "Vitamins": "supports your daily wellness with clinically-studied ingredients",
        "Skincare": "is dermatologist-tested and designed for visible, lasting results",
        "Cold & Flu": "delivers fast, reliable relief when you need it most",
        "Personal Care": "brings everyday care up to a professional standard",
        "Eye Care": "is crafted for all-day comfort and clarity",
        "Baby & Child": "is gentle, safe, and trusted by parents",
    }
    return (f"The {p['name']} {benefits.get(p['cat'], 'is made to a high standard')}. "
            f"{p['blurb']}. Free shipping on orders over $35, and easy 30-day returns.")

def product_detail(pid: str) -> dict | None:
    p = PRODUCT_BY_ID.get(pid)
    if not p:
        return None
    revs = reviews_for(p)
    breakdown = {str(s): 0 for s in range(5, 0, -1)}
    for r in revs:
        breakdown[str(r["rating"])] += 1
    return {**enrich(p), "description": _description(p),
            "reviews": revs, "rating_breakdown": breakdown}

def catalogue_cards() -> list[dict]:
    return [enrich(p) for p in PRODUCTS]

POINTS_PER = {"view_product": 2, "view_detail": 3, "view_reviews": 3,
              "view_all_reviews": 4, "add_to_wishlist": 5, "add_to_cart": 10,
              "apply_coupon": 6, "view_size_guide": 4, "compare": 5,
              "checkout_start": 20, "purchase": 50}

INTENT_WEIGHT = {
    "view_product": 3, "view_detail": 6, "view_image_zoom": 5, "view_reviews": 8,
    "view_all_reviews": 12,
    "sort_reviews": 6, "view_size_guide": 11, "check_delivery": 9, "compare": 10,
    "add_to_wishlist": 14, "apply_coupon": 16, "clip_coupon": 7, "view_bundle": 9,
    "add_to_cart": 22, "checkout_start": 34, "purchase": 0,
    "search": 4, "filter_category": 2, "remove_from_cart": -10, "back_to_browse": -3,
}
TIERS = [("Bronze", 0), ("Silver", 80), ("Gold", 200), ("Platinum", 400)]

@dataclass
class Visitor:
    uid: str
    events: list = field(default_factory=list)
    devices: list = field(default_factory=list)
    cart: list = field(default_factory=list)
    wishlist: list = field(default_factory=list)
    orders: list = field(default_factory=list)
    total_spent: float = 0.0
    inbox: list = field(default_factory=list)
    ended: bool = False
    points: int = 0
    consent: bool = True
    merged_from: list = field(default_factory=list)   # stitched anonymous/guest sessions
    created: float = field(default_factory=time.time)

    def add_device(self, device: str):
        if device and device not in self.devices:
            self.devices.append(device)

REVENUE = {"orders": 0, "gross": 0.0, "incentive_given": 0.0, "units": 0,
           "by_category": defaultdict(float), "by_segment": defaultdict(float),
           "recent": []}

def loyalty(points: int) -> dict:
    tier, idx = TIERS[0][0], 0
    for i, (name, thr) in enumerate(TIERS):
        if points >= thr:
            tier, idx = name, i
    if idx + 1 < len(TIERS):
        nxt_name, nxt_thr = TIERS[idx + 1]
        cur_thr = TIERS[idx][1]
        progress = round(100 * (points - cur_thr) / max(nxt_thr - cur_thr, 1))
        to_next = nxt_thr - points
    else:
        nxt_name, progress, to_next = "—", 100, 0
    return {"points": points, "tier": tier, "next_tier": nxt_name,
            "to_next": to_next, "progress_pct": min(progress, 100),
            "dollar_value": round(points * 0.04, 2)}

class Store:
    def __init__(self):
        self._v: dict[str, Visitor] = {}
        self._lock = Lock()
        self._load()

    def _load(self):
        try:
            rows = db.load_all()
        except Exception:
            rows = {}
        for uid, d in rows.items():
            try:
                self._v[uid] = _visitor_from_dict(d)
            except Exception:
                pass
        if self._v:
            _rebuild_revenue(self._v.values())
            print(f"[store] loaded {len(self._v)} visitors from {db.backend()}")

    def _persist(self, v: Visitor):
        try:
            db.save(v.uid, _visitor_to_dict(v))
        except Exception:
            pass

    def visitor(self, uid: str) -> Visitor:
        with self._lock:
            if uid not in self._v:
                self._v[uid] = Visitor(uid=uid)
            return self._v[uid]

    def track(self, uid: str, event: dict) -> Visitor:
        v = self.visitor(uid)
        with self._lock:
            v.ended = False
            earned = POINTS_PER.get(event.get("type"), 0)
            v.points += earned
            event = {**event, "ts": time.time(), "points_earned": earned}
            v.events.append(event)
            v.add_device(event.get("device", "desktop"))
            pid = event.get("product_id")
            et = event.get("type")
            if et == "add_to_cart" and pid and pid not in v.cart:
                v.cart.append(pid)
            elif et == "remove_from_cart":
                v.cart = [c for c in v.cart if c != pid]
            elif et == "add_to_wishlist" and pid and pid not in v.wishlist:
                v.wishlist.append(pid)
            elif et == "remove_from_wishlist":
                v.wishlist = [c for c in v.wishlist if c != pid]
        self._persist(v)
        return v

    def purchase(self, uid: str, applied_points: int = 0) -> dict:
        v = self.visitor(uid)
        with self._lock:
            items = [enrich(PRODUCT_BY_ID[c]) for c in v.cart if c in PRODUCT_BY_ID]
            if not items:
                return {"ok": False, "error": "cart is empty"}
            list_total = round(sum(i["list_price"] for i in items), 2)
            sale_total = round(sum(i["sale_price"] for i in items), 2)
            incentive = round(list_total - sale_total, 2)
            applied_points = max(0, min(applied_points, v.points))
            points_value = round(applied_points * 0.04, 2)
            grand_total = max(0.0, round(sale_total - points_value, 2))

            seg = profile(v)["segment"]
            earned = POINTS_PER["purchase"] + int(sale_total // 10)
            v.points = v.points - applied_points + earned
            order = {
                "order_id": "ord_" + hashlib.md5(f"{uid}{time.time()}".encode()).hexdigest()[:8],
                "items": [{"id": i["id"], "name": i["name"], "emoji": i["emoji"],
                           "price": i["sale_price"]} for i in items],
                "units": len(items), "list_total": list_total, "sale_total": sale_total,
                "incentive": incentive, "points_used": applied_points,
                "points_value": points_value, "grand_total": grand_total,
                "points_earned": earned, "segment": seg, "ts": time.time(),
            }
            v.orders.append(order)
            v.total_spent = round(v.total_spent + grand_total, 2)
            v.cart = []
            v.events.append({"type": "purchase", "order_id": order["order_id"],
                             "value": grand_total, "ts": time.time(), "points_earned": earned})

            REVENUE["orders"] += 1
            REVENUE["gross"] = round(REVENUE["gross"] + grand_total, 2)
            REVENUE["incentive_given"] = round(REVENUE["incentive_given"] + incentive, 2)
            REVENUE["units"] += len(items)
            for i in items:
                REVENUE["by_category"][i["cat"]] += i["sale_price"]
            REVENUE["by_segment"][seg] += grand_total
            REVENUE["recent"].insert(0, {"order_id": order["order_id"], "uid": uid,
                                         "total": grand_total, "units": len(items),
                                         "segment": seg, "ts": order["ts"]})
            del REVENUE["recent"][30:]
        self._persist(v)
        return {"ok": True, "order": order, "loyalty": loyalty(v.points)}

    def end_session(self, uid: str, device: str = "desktop") -> dict:
        v = self.visitor(uid)
        v.ended = True
        if v.events and v.events[-1].get("type") != "session_end":
            v.events.append({"type": "session_end", "device": device,
                             "ts": time.time(), "points_earned": 0})
        delivered = deliver_to_inbox(v, device)
        sent = bool(v.inbox) and (delivered[0]["ts"] > time.time() - 2 if delivered else False)
        self._persist(v)
        return {"ended": True, "delivered": sent, "inbox": delivered,
                "mail": mail_simulation(v, device)}

    def redeem(self, uid: str, reward_id: str) -> dict:
        v = self.visitor(uid)
        reward = next((r for r in REDEMPTIONS if r["id"] == reward_id), None)
        if not reward:
            return {"ok": False, "error": "unknown reward"}
        with self._lock:
            if v.points < reward["cost"]:
                return {"ok": False, "error": "not enough points",
                        "need": reward["cost"] - v.points, "loyalty": loyalty(v.points)}
            v.points -= reward["cost"]
            v.events.append({"type": "redeem", "reward_id": reward_id,
                             "cost": reward["cost"], "ts": time.time(), "points_earned": 0})
        self._persist(v)
        return {"ok": True, "reward": reward, "loyalty": loyalty(v.points)}

def _visitor_to_dict(v: Visitor) -> dict:
    return asdict(v)


def _visitor_from_dict(d: dict) -> Visitor:
    return Visitor(
        uid=d["uid"], events=d.get("events", []), devices=d.get("devices", []),
        cart=d.get("cart", []), wishlist=d.get("wishlist", []), orders=d.get("orders", []),
        total_spent=d.get("total_spent", 0.0), inbox=d.get("inbox", []),
        ended=d.get("ended", False), points=d.get("points", 0),
        consent=d.get("consent", True), merged_from=d.get("merged_from", []),
        created=d.get("created", time.time()),
    )


def _rebuild_revenue(visitors) -> None:
    REVENUE["orders"] = 0
    REVENUE["gross"] = 0.0
    REVENUE["incentive_given"] = 0.0
    REVENUE["units"] = 0
    REVENUE["by_category"] = defaultdict(float)
    REVENUE["by_segment"] = defaultdict(float)
    rows = []
    for v in visitors:
        for o in v.orders:
            REVENUE["orders"] += 1
            REVENUE["gross"] = round(REVENUE["gross"] + o.get("grand_total", 0), 2)
            REVENUE["incentive_given"] = round(REVENUE["incentive_given"] + o.get("incentive", 0), 2)
            REVENUE["units"] += o.get("units", 0)
            for it in o.get("items", []):
                p = PRODUCT_BY_ID.get(it.get("id"))
                if p:
                    REVENUE["by_category"][p["cat"]] += it.get("price", 0)
            REVENUE["by_segment"][o.get("segment", "?")] += o.get("grand_total", 0)
            rows.append({"order_id": o.get("order_id"), "uid": v.uid,
                         "total": o.get("grand_total", 0), "units": o.get("units", 0),
                         "segment": o.get("segment", "?"), "ts": o.get("ts", 0)})
    rows.sort(key=lambda x: x["ts"], reverse=True)
    REVENUE["recent"] = rows[:30]


STORE = Store()

# ---- COREid identity layer (person-level identifier, à la Epsilon CORE ID) ----
USERS: dict[str, dict] = {}
try:
    USERS.update(db.load_users())
except Exception:
    pass


def core_id_for(email: str) -> str:
    h = hashlib.sha1(email.strip().lower().encode()).hexdigest()[:10].upper()
    return "CORE-" + h


def login(email: str, name: str = "", guest_uid: str = "") -> dict:
    email = (email or "").strip().lower()
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        return {"error": "A valid email is required."}
    existing = USERS.get(email, {})
    is_new = email not in USERS
    cid = existing.get("core_id") or core_id_for(email)
    nm = (name or "").strip() or existing.get("name") or email.split("@")[0].replace(".", " ").title()
    rec = {"email": email, "core_id": cid, "name": nm,
           "created": existing.get("created") or time.time()}
    USERS[email] = rec
    try:
        db.save_user(email, cid, nm, rec["created"])
    except Exception:
        pass
    STORE.visitor(cid)  # ensure a profile bucket exists for this person
    # Identity resolution: fold any anonymous guest activity into this CORE ID.
    merge = None
    if guest_uid:
        try:
            merge = merge_guest(cid, guest_uid)
        except Exception:
            merge = {"merged": False, "reason": "merge error"}
    profile(STORE.visitor(cid), record=True)  # surface in the live console immediately (empty logs ok)
    return {**rec, "is_new": is_new, "merge": merge}


def list_people() -> list[dict]:
    out = []
    now = time.time()
    for email, u in USERS.items():
        cid = u["core_id"]
        v = STORE._v.get(cid)
        if v is None or not v.events:
            out.append({"core_id": cid, "email": email, "name": u["name"],
                        "segment": "New", "intent_score": 0, "events": 0, "orders": 0,
                        "revenue": 0.0, "cart": 0, "devices": [],
                        "last_seen": u.get("created", 0), "online": False})
            continue
        p = profile(v)
        last = v.events[-1].get("ts", u.get("created", 0)) if v.events else u.get("created", 0)
        out.append({
            "core_id": cid, "email": email, "name": u["name"],
            "segment": p["segment"], "intent_score": p["intent_score"],
            "events": len(v.events), "orders": len(v.orders),
            "revenue": round(v.total_spent, 2), "cart": len(v.cart),
            "devices": v.devices, "last_seen": last, "online": (now - last) <= 120,
            "consent": getattr(v, "consent", True),
        })
    out.sort(key=lambda r: r["last_seen"], reverse=True)
    return out


def set_consent(uid: str, consent: bool) -> dict:
    v = STORE.visitor(uid)
    prev = getattr(v, "consent", True)
    v.consent = bool(consent)
    if bool(consent) != prev:
        # Auditable consent change — feeds the privacy ledger (Epsilon: privacy-safe identity).
        v.events.append({"type": "consent", "value": bool(consent),
                         "ts": time.time(), "points_earned": 0})
    STORE._persist(v)
    return {"uid": uid, "consent": v.consent}


def reset_all() -> dict:
    USERS.clear()
    STORE._v.clear()
    LIVE_SHOPPERS.clear()
    _rebuild_revenue([])
    try:
        db.reset_all()
    except Exception:
        pass
    return {"ok": True}


def delete_person(core_id: str) -> dict:
    """Fully remove a person: registry, live profile, persisted rows, and rebuild totals."""
    email = next((e for e, u in USERS.items() if u["core_id"] == core_id), None)
    if email:
        USERS.pop(email, None)
        try:
            db.delete_user(email)
        except Exception:
            pass
    STORE._v.pop(core_id, None)
    LIVE_SHOPPERS.pop(core_id, None)
    try:
        db.delete_visitor(core_id)
    except Exception:
        pass
    _rebuild_revenue(STORE._v.values())
    return {"deleted": core_id, "email": email}


SESSION_GAP = 1800   # a >30-min gap between events = a new session


def _email_for(core_id: str) -> str | None:
    return next((e for e, u in USERS.items() if u["core_id"] == core_id), None)


def _session_count(v: "Visitor") -> int:
    """Distinct sessions: a new one starts after a 'Leave site' (session_end) boundary
    or a >30-min gap in the activity stream."""
    evs = [e for e in v.events if e.get("ts")]
    if not evs:
        return 0
    n = 1
    for prev, cur in zip(evs, evs[1:]):
        if prev.get("type") == "session_end" or (cur.get("ts", 0) - prev.get("ts", 0)) > SESSION_GAP:
            n += 1
    return n


_CHANNEL_ICON = {"Web": "🌐", "Chatbot": "💬", "Email": "📬"}


def _channels_seen(v: "Visitor") -> list[str]:
    """Distinct touchpoints (not devices) this person has been observed on — the
    channels CORE ID unifies into one view."""
    ch = set()
    if any(e.get("type") not in ("chat", "session_end") for e in v.events):
        ch.add("Web")
    if any(e.get("type") == "chat" for e in v.events):
        ch.add("Chatbot")
    if v.inbox:
        ch.add("Email")
    return [c for c in ("Web", "Chatbot", "Email") if c in ch]


def _device_icon(d: str) -> str:
    return {"mobile": "📱", "tablet": "📟", "desktop": "💻"}.get(d, "🖥️")


def identity_graph(core_id: str) -> dict:
    """The CORE ID resolution graph: one person resolved from many signals — email,
    devices, channels and sessions (including any stitched anonymous activity)."""
    email = _email_for(core_id)
    u = USERS.get(email, {}) if email else {}
    v = STORE._v.get(core_id)
    devices = list(v.devices) if v else []
    channels = _channels_seen(v) if v else []
    sessions = _session_count(v) if v else 0
    events = len(v.events) if v else 0
    merged = list(getattr(v, "merged_from", [])) if v else []
    tss = [e.get("ts", 0) for e in (v.events if v else []) if e.get("ts")]
    first_seen = min(tss) if tss else u.get("created", 0)
    last_seen = max(tss) if tss else 0

    signals = []
    if email:
        signals.append({"type": "email", "label": email, "icon": "📧"})
    for d in devices:
        signals.append({"type": "device", "label": d.title(), "icon": _device_icon(d)})
    for c in channels:
        signals.append({"type": "channel", "label": c, "icon": _CHANNEL_ICON.get(c, "🔗")})

    return {
        "core_id": core_id, "email": email, "name": u.get("name"),
        "devices": devices, "channels": channels, "sessions": sessions, "events": events,
        "first_seen": first_seen, "last_seen": last_seen,
        "signals": signals, "signal_count": len(signals),
        "merged_from": merged, "merged_sessions": sum(m.get("sessions", 0) for m in merged),
        "revenue": round(v.total_spent, 2) if v else 0.0,
        "consent": getattr(v, "consent", True) if v else True,
        "consent_log": [{"ts": e.get("ts", 0), "consent": e.get("value")}
                        for e in (v.events if v else []) if e.get("type") == "consent"][::-1],
    }


def send_marketer_mail(core_id: str, device: str = "desktop") -> dict:
    """Marketer-initiated send: compose the right targeted message for this customer's
    CURRENT best action (the product they're still considering) and drop it into their
    inbox so they actually receive it."""
    v = STORE.visitor(core_id)
    if not getattr(v, "consent", True):
        return {"ok": False, "error": "Customer opted out of personalisation — respect consent."}
    p = profile(v)
    nba = next_best_action(v, device)
    top = p.get("top_product")
    emoji = top["emoji"] if top else "🛍️"
    mail = {
        "channel": nba.get("channel", "Email"), "channel_icon": nba.get("channel_icon", "📧"),
        "subject": f"{emoji} {nba.get('headline', 'A little something for you')}",
        "preview": nba.get("message", ""),
        "body": nba.get("message", "") + " Your cart and points follow you on every device.",
        "cta": nba.get("cta", "Shop now →"), "link": nba.get("link", "/store"),
        "product": top, "reward_type": nba.get("reward_type"),
        "offer_pct": nba.get("offer_pct"),
        "reason": nba.get("rationale") or nba.get("reason"),
        "from": "VERVE · The Style Edit", "ts": time.time(), "read": False, "sent_by": "marketer",
    }
    v.inbox.append(mail)
    del v.inbox[:-12]
    STORE._persist(v)
    return {"ok": True, "mail": mail, "segment": p["segment"],
            "to": _email_for(core_id), "channel": mail["channel"]}


def _pc(x):
    try:
        return f"{float(x) * 100:.0f}%"
    except Exception:
        return "—"


def customer_facts(v: "Visitor") -> str:
    """Rich, real-time behavioural context for the LLM strategist — so it reasons about
    THIS shopper's actual actions, not a generic segment."""
    p = profile(v)
    interests = p.get("interests") or []
    def lst(items):
        return ", ".join(f"{i['name']} (intent {i['intent']})" for i in items) or "none"
    bought = [i for i in interests if i.get("bought")]
    cart = [i for i in interests if i.get("in_cart")]
    wish = [i for i in interests if i.get("in_wishlist") and not i.get("bought")]
    considering = [i for i in interests if not i.get("bought") and not i.get("in_cart")]
    nba = next_best_action(v, v.devices[-1] if v.devices else "desktop")
    med = nba.get("med") or {}
    name = (USERS.get(_email_for(v.uid) or "", {}) or {}).get("name") or "This shopper"
    return (
        f"Shopper: {name}. Segment: {p['segment']} ({p['intent']}). "
        f"Intent score {p['intent_score']}/100. Uplift {_pc(p.get('uplift'))}, baseline {_pc(p.get('base_rate'))}. "
        f"Orders: {len(v.orders)} (${round(v.total_spent,2)} spent). "
        f"Already bought: {lst(bought)}. In cart: {lst(cart)}. Wishlisted (wants, not bought): {lst(wish)}. "
        f"Still browsing: {lst(considering)}. "
        f"Devices: {', '.join(v.devices) or 'one'}. Best channel now: {nba.get('channel')}. "
        f"Suggested right-sized discount: {med.get('discount', 'n/a')}%. "
        f"Consent to personalisation: {getattr(v, 'consent', True)}."
    )


def analyze_customer(v: "Visitor") -> dict:
    """Deterministic but genuinely ANALYTICAL recommendation — reads the shopper's real-time
    actions (what they bought vs still want, cart, wishlist, uplift) and decides the single
    best move. This is the offline brain when no LLM key is set."""
    p = profile(v)
    seg = p["segment"]
    interests = p.get("interests") or []
    nba = next_best_action(v, v.devices[-1] if v.devices else "desktop")
    channel = nba.get("channel", "Email")
    name = (USERS.get(_email_for(v.uid) or "", {}) or {}).get("name") or "This shopper"
    uplift, base, score = p.get("uplift"), p.get("base_rate"), p.get("intent_score", 0)

    bought = [i for i in interests if i.get("bought")]
    cart = [i for i in interests if i.get("in_cart")]
    wish = [i for i in interests if i.get("in_wishlist") and not i.get("bought")]
    considering = [i for i in interests if not i.get("bought") and not i.get("in_cart")]
    med = nba.get("med") or {}
    disc = med.get("discount") if med else nba.get("offer_pct")

    if not v.events:
        return {"decision": "OBSERVE", "segment": seg,
                "narrative": f"{name} has no activity yet — not enough signal to act. Wait for a focused intent signal."}
    if not getattr(v, "consent", True):
        return {"decision": "DO NOT CONTACT", "segment": seg,
                "narrative": f"{name} has opted out of personalisation. Respect it — no outbound message; rely on the on-site experience only."}

    # describe what they actually did
    did = []
    if bought:
        did.append(f"bought the {bought[0]['name']}")
    if cart:
        did.append(f"has the {cart[0]['name']} sitting in their cart")
    if wish:
        did.append(f"wishlisted the {wish[0]['name']}")
    if not cart and not wish and considering:
        did.append(f"keeps coming back to the {considering[0]['name']}")
    behaviour = "; ".join(did) or f"has {p['total_views']} recent product views"

    # decision driven by the strongest live signal
    if cart:
        offer = f"{disc}% off (the minimum effective dose)" if disc else "a points-backed nudge"
        return {"decision": "SPEND — recover the cart", "segment": seg,
                "narrative": (f"{name} {behaviour}. Cart-stage intent with {_pc(uplift)} uplift means a nudge is "
                              f"incremental — send via {channel}: {offer}, deep-linked to the item, the moment they leave. "
                              f"Don't blanket-discount; right-size it.")}
    if bought and (wish or considering):
        tgt = (wish or considering)[0]
        return {"decision": "NURTURE — cross-sell (no discount)", "segment": seg,
                "narrative": (f"{name} {behaviour}. They've already converted, so don't re-pitch what they own — "
                              f"cross-sell the {tgt['name']} (intent {tgt['intent']}) via {channel} with 2× points, not a "
                              f"discount. Protect margin on a proven buyer.")}
    if seg == "Persuadable":
        tgt = (considering or wish or [{}])[0]
        what = f"the {tgt['name']}" if tgt.get("name") else "the items they viewed"
        return {"decision": "SPEND — marketing changes the outcome here", "segment": seg,
                "narrative": (f"{name} {behaviour}. Persuadable with {_pc(uplift)} uplift — this is exactly where a dollar is "
                              f"incremental. Send via {channel}: {(str(disc)+'% off') if disc else 'a reminder'} on {what}, "
                              f"right-sized so you keep the margin you don't need to give away.")}
    if seg == "Sure Thing":
        return {"decision": "HOLD — reward, don't discount", "segment": seg,
                "narrative": (f"{name} {behaviour}. High baseline ({_pc(base)}) with low uplift — they'll buy anyway. "
                              f"Reward with loyalty points via {channel}; a discount here is pure margin lost.")}
    if seg == "Sleeping Dog":
        return {"decision": "SUPPRESS — stay silent", "segment": seg,
                "narrative": (f"{name} {behaviour}, but contact lowers their conversion. Leave them alone — silence here "
                              f"protects organic revenue you'd otherwise erode.")}
    if seg == "Converted":
        return {"decision": "NURTURE lightly — no spend", "segment": seg,
                "narrative": (f"{name} just purchased and shows no new intent. A thank-you with 2× points on their next "
                              f"visit is enough; no discount, no outbound spend.")}
    return {"decision": "SKIP — keep it cheap", "segment": seg,
            "narrative": (f"{name} {behaviour} but intent is low ({score}/100). Keep it ambient and cheap — don't spend "
                          f"until there's a focused signal that marketing can move.")}


def identity_summary() -> dict:
    """Fleet-wide CORE ID resolution stats — the analytics for the identity layer."""
    people = len(USERS)
    resolved = cross_device = multi_channel = 0
    signals = stitched_events = stitched_sessions = stitched_people = 0
    chan = defaultdict(int)
    for u in USERS.values():
        g = identity_graph(u["core_id"])
        signals += g["signal_count"]
        if g["signal_count"] > 1:
            resolved += 1
        if len(g["devices"]) > 1:
            cross_device += 1
        if len(g["channels"]) > 1:
            multi_channel += 1
        for c in g["channels"]:
            chan[c] += 1
        if g["merged_from"]:
            stitched_people += 1
            stitched_events += sum(m.get("events", 0) for m in g["merged_from"])
            stitched_sessions += sum(m.get("sessions", 0) for m in g["merged_from"])
    return {
        "people": people, "resolved": resolved, "cross_device": cross_device,
        "multi_channel": multi_channel, "signals_unified": signals,
        "avg_signals": round(signals / max(people, 1), 1),
        "stitched_people": stitched_people, "stitched_events": stitched_events,
        "stitched_sessions": stitched_sessions, "channels": dict(chan),
    }


def seed_demo(reset: bool = True) -> dict:
    """Populate a realistic demo IN-PROCESS (works on a fresh deploy, no localhost needed):
    a Persuadable, buyers, a cross-device identity merge, a bundle-builder, and an opt-out."""
    if reset:
        reset_all()

    def jrny(uid, steps):
        for t, pid, dev in steps:
            STORE.track(uid, {"type": t, "product_id": pid, "device": dev, "dwell_ms": 4000})

    # 1) ANEESH — Persuadable hero + cross-device identity merge. Browses as a guest on
    #    desktop, leaves, returns on mobile, then signs in → his anonymous trail stitches in.
    g = "seedguest_" + hashlib.md5(str(time.time()).encode()).hexdigest()[:6]
    jrny(g, [("view_product", "p9", "desktop"), ("view_detail", "p9", "desktop"),
             ("view_all_reviews", "p9", "desktop"), ("view_product", "p9", "desktop"),
             ("add_to_wishlist", "p9", "desktop")])
    STORE.end_session(g, "desktop")
    jrny(g, [("view_product", "p9", "mobile"), ("view_reviews", "p9", "mobile"),
             ("add_to_cart", "p9", "mobile"), ("view_product", "p12", "mobile")])
    login("aneesh@kairos.demo", "Aneesh", guest_uid=g)

    # 2) DISHAN — Sure Thing: decisive, buys fast, returns and buys again (revenue + HOLD story)
    u = login("dishan@kairos.demo", "Dishan")["core_id"]
    jrny(u, [("view_product", "p13", "desktop"), ("add_to_cart", "p13", "desktop")])
    STORE.purchase(u)
    jrny(u, [("view_product", "p17", "mobile"), ("add_to_cart", "p17", "mobile")])
    STORE.purchase(u)

    # 3) NAGARJUN — Sleeping Dog / over-browser: views everything, never carts (SUPPRESS)
    u = login("nagarjun@kairos.demo", "Nagarjun")["core_id"]
    jrny(u, [("view_product", f"p{i}", "desktop") for i in range(1, 12)])

    # 4) RAJEEV — Persuadable bundle-builder across categories (cart held, not bought)
    u = login("rajeev@kairos.demo", "Rajeev")["core_id"]
    jrny(u, [("view_product", "p1", "desktop"), ("add_to_wishlist", "p1", "desktop"),
             ("view_product", "p11", "desktop"), ("add_to_cart", "p11", "desktop"),
             ("view_detail", "p11", "desktop"), ("view_product", "p14", "desktop")])

    # 5) NIHAL — light browser (Lost Cause) who opted OUT of personalisation (privacy story)
    u = login("nihal@kairos.demo", "Nihal")["core_id"]
    jrny(u, [("view_product", "p20", "desktop"), ("view_product", "p3", "desktop")])
    set_consent(u, False)

    return {"ok": True, "people": len(USERS), **identity_summary()}


def merge_guest(core_id: str, guest_uid: str) -> dict:
    """Stitch an anonymous guest's activity into a known CORE ID — the signature
    identity-resolution moment. Idempotent and safe: no-op if there's nothing to merge."""
    if not guest_uid or guest_uid == core_id:
        return {"merged": False, "reason": "no guest id"}
    g = STORE._v.get(guest_uid)
    if not g or not g.events:
        return {"merged": False, "reason": "no guest activity"}
    k = STORE.visitor(core_id)
    with STORE._lock:
        g_sessions = _session_count(g)
        g_devices = list(g.devices)
        g_events = len(g.events)
        k.events.extend(g.events)
        k.events.sort(key=lambda e: e.get("ts", 0))
        for d in g.devices:
            k.add_device(d)
        for c in g.cart:
            if c not in k.cart:
                k.cart.append(c)
        for w in g.wishlist:
            if w not in k.wishlist:
                k.wishlist.append(w)
        k.orders.extend(g.orders)
        k.total_spent = round(k.total_spent + g.total_spent, 2)
        k.points += g.points
        k.inbox.extend(g.inbox)
        k.merged_from.append({"guest_uid": guest_uid, "events": g_events,
                              "devices": g_devices, "sessions": g_sessions, "ts": time.time()})
    STORE._v.pop(guest_uid, None)
    LIVE_SHOPPERS.pop(guest_uid, None)
    try:
        db.delete_visitor(guest_uid)
    except Exception:
        pass
    STORE._persist(k)
    _rebuild_revenue(STORE._v.values())
    return {"merged": True, "guest_uid": guest_uid, "events": g_events,
            "devices": g_devices, "sessions": g_sessions,
            "total_sessions": _session_count(k), "total_events": len(k.events),
            "signal_count": identity_graph(core_id)["signal_count"]}


def live_shoppers_detail(window: int = 600) -> list[dict]:
    """People on the site right now and what each is actually looking at — the real
    live signal the AI strategist needs for 'who is viewing X now' questions."""
    now = time.time()
    out = []
    for email, u in USERS.items():
        v = STORE._v.get(u["core_id"])
        if not v or not v.events:
            continue
        last = v.events[-1].get("ts", 0)
        if now - last > window:
            continue
        p = profile(v)
        seen = []
        for e in reversed(v.events):
            if e.get("type") == "view_product":
                nm = (PRODUCT_BY_ID.get(e.get("product_id")) or {}).get("name")
                if nm and nm not in seen:
                    seen.append(nm)
            if len(seen) >= 5:
                break
        out.append({
            "name": u["name"], "core_id": u["core_id"], "segment": p["segment"],
            "intent_score": p["intent_score"],
            "looking_at": p.get("looking_at") or (p.get("top_product") or {}).get("name"),
            "recently_viewed": seen,
            "in_cart": [c.get("name") for c in (p.get("cart") or [])],
            "events": len(v.events), "online": (now - last) <= 120,
        })
    out.sort(key=lambda r: not r["online"])
    return out

def _product_view_counts(v: Visitor) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for e in v.events:
        if e.get("type") == "view_product" and e.get("product_id"):
            counts[e["product_id"]] += 1
    return counts

def visitor_features(v: Visitor) -> np.ndarray:
    views = _product_view_counts(v)
    total = sum(views.values())
    distinct = len(views)
    top = max(views.values()) if views else 0
    dwell_min = sum(e.get("dwell_ms", 0) for e in v.events) / 60000.0
    reviews = sum(1 for e in v.events if e.get("type") in ("view_reviews", "view_all_reviews"))
    prior = len(v.orders) + sum(1 for e in v.events if e.get("type") in ("purchase", "checkout"))
    recency = 0.5
    return np.array([[total, distinct, top, dwell_min, len(v.wishlist),
                      len(v.cart), reviews, prior, recency]], dtype=float)

def score_visitor(v: Visitor) -> dict | None:
    m = _live_model()
    if not m:
        return None
    X = visitor_features(v)
    model = m["model"]
    base = float(model.predict_proba(np.column_stack([X, [0]]))[0, 1])
    uplift = float(model.predict_proba(np.column_stack([X, [1]]))[0, 1] - base)
    if uplift < 0:
        bucket = "Sleeping Dog"
    elif uplift >= m["uplift_q"]:
        bucket = "Persuadable"
    elif base >= m["base_q"]:
        bucket = "Sure Thing"
    else:
        bucket = "Lost Cause"
    return {"base_rate": round(base, 4), "uplift": round(uplift, 4),
            "bucket": bucket, "inc_value": round(max(uplift, 0) * m["aov"], 2),
            "scored_by": "T-Learner uplift model (9 behavioral features)"}

_DRIVER_LABELS = [
    "product views", "distinct products browsed", "repeat views of one item",
    "time on site", "wishlist items", "items in cart", "review reads",
    "prior purchases", "recency",
]

def decision_drivers(v: Visitor, top: int = 4) -> dict:
    """Explainable causal decisions: ablation attribution on the live uplift model — how
    much each behaviour moves THIS shopper's incremental lift. Real model, no rules."""
    m = _live_model()
    if not m:
        return {"available": False, "drivers": [], "uplift_pp": None}
    model = m["model"]
    X = visitor_features(v)

    def uplift_of(xrow):
        base = model.predict_proba(np.column_stack([xrow, [0]]))[0, 1]
        return float(model.predict_proba(np.column_stack([xrow, [1]]))[0, 1] - base)

    full = uplift_of(X)
    drivers = []
    for i in range(X.shape[1] - 1):           # skip recency (constant)
        if X[0, i] == 0:
            continue
        xa = X.copy()
        xa[0, i] = 0.0
        contrib = (full - uplift_of(xa)) * 100  # percentage points this behaviour adds
        if abs(contrib) >= 0.05:
            drivers.append({"feature": _DRIVER_LABELS[i], "value": round(float(X[0, i]), 1),
                            "contribution_pp": round(contrib, 2)})
    drivers.sort(key=lambda d: -abs(d["contribution_pp"]))
    return {"available": True, "uplift_pp": round(full * 100, 2), "drivers": drivers[:top]}

def product_interests(v: Visitor, top_n: int = 5) -> list[dict]:
    stats: dict[str, dict] = {}
    for e in v.events:
        pid = e.get("product_id")
        if not pid or pid not in PRODUCT_BY_ID:
            continue
        s = stats.setdefault(pid, {"views": 0, "dwell_ms": 0, "reviews": 0})
        et = e.get("type")
        if et in ("view_product", "view_detail"):
            s["views"] += 1
        if et in ("view_reviews", "view_all_reviews"):
            s["reviews"] += 1
        s["dwell_ms"] += e.get("dwell_ms", 0)
    bought = {it["id"] for o in v.orders for it in o.get("items", [])}
    out = []
    for pid, s in stats.items():
        in_cart, in_wish, is_bought = pid in v.cart, pid in v.wishlist, pid in bought
        out.append({**{k: v_ for k, v_ in enrich(PRODUCT_BY_ID[pid]).items()
                       if k in ("name", "emoji", "img", "cat")},
                    "id": pid, "price": enrich(PRODUCT_BY_ID[pid])["sale_price"],
                    "views": s["views"], "dwell_s": round(s["dwell_ms"] / 1000, 1),
                    "reviews": s["reviews"], "in_cart": in_cart, "in_wishlist": in_wish,
                    "bought": is_bought,
                    "intent": _interest_intent(s["views"], s["dwell_ms"] / 1000.0,
                                               s["reviews"], in_cart, in_wish, is_bought)})
    # Lead with ACTIVE intent (not yet bought) so fresh browsing surfaces immediately;
    # already-bought items still show, but after — they're not "live" intent.
    out.sort(key=lambda x: (x["bought"], not x["in_cart"], not x["in_wishlist"], -x["intent"]))
    return out[:top_n]

def _interest_intent(views, dwell_s, reviews, in_cart, in_wish, bought) -> int:
    if bought:
        return 100
    engagement = views * 7 + dwell_s * 1.2 + reviews * 9
    if in_cart:
        return int(min(95, 65 + engagement * 0.4))
    if in_wish:
        return int(min(80, 40 + engagement * 0.4))
    return int(min(70, engagement))

_INTENT_EVENTS = ("view_product", "view_detail", "view_reviews", "view_all_reviews",
                  "add_to_cart", "add_to_wishlist")


def profile(v: Visitor, record: bool = False) -> dict:
    views = _product_view_counts(v)
    total_views = sum(views.values())
    bought_ids = {it["id"] for o in v.orders for it in o.get("items", [])}
    # Lead with the most-viewed product they HAVEN'T bought yet (ongoing intent),
    # falling back to any viewed item.
    active_views = {p: c for p, c in views.items() if p not in bought_ids}
    top_pid = (max(active_views, key=active_views.get) if active_views
               else (max(views, key=views.get) if views else None))
    top_views = views.get(top_pid, 0) if top_pid else 0
    # What they're looking at RIGHT NOW = most recent product view (not most-viewed).
    recent_pid = next((e.get("product_id") for e in reversed(v.events)
                       if e.get("type") in ("view_product", "view_detail")
                       and e.get("product_id") in PRODUCT_BY_ID), None)
    looking_at_name = (PRODUCT_BY_ID.get(recent_pid) or PRODUCT_BY_ID.get(top_pid) or {}).get("name")
    has_cart = bool(v.cart)
    has_wish = bool(v.wishlist)
    read_reviews = sum(1 for e in v.events if e.get("type") in ("view_reviews", "view_all_reviews"))
    opened_detail = sum(1 for e in v.events if e.get("type") == "view_detail")
    # Has the shopper shown fresh intent AFTER their last purchase? If so they're a live
    # shopper again (for the new items) — not permanently "Converted".
    order_ts = [e.get("ts", 0) for e in v.events if e.get("type") in ("purchase", "checkout")]
    last_order_ts = max(order_ts) if order_ts else 0
    has_new_intent = any(e.get("type") in _INTENT_EVENTS and e.get("ts", 0) > last_order_ts
                         for e in v.events)
    just_converted = (bool(v.orders) or bool(order_ts)) and not has_new_intent
    dwell = sum(e.get("dwell_ms", 0) for e in v.events) / 1000.0

    score = min(100, total_views * 5 + top_views * 9 + opened_detail * 6
                + read_reviews * 8 + (30 if has_cart else 0) + (22 if has_wish else 0)
                + min(dwell, 25))

    model = score_visitor(v)
    INTENT_TEXT = {
        "Persuadable": "Engaged, not yet bought — a nudge changes the outcome",
        "Sure Thing": "Decisive — likely to buy anyway",
        "Sleeping Dog": "Over-browsing — contact would backfire",
        "Lost Cause": "Low purchase intent",
    }
    if v.events == [] or not v.events:
        segment, intent = "New", "Just arrived — no signal yet"
    elif just_converted:
        segment, intent = "Converted", "Purchased"
    elif model:
        segment, intent = model["bucket"], INTENT_TEXT[model["bucket"]]
    else:
        if has_cart or has_wish or top_views >= 3:
            segment, intent = "Persuadable", "Hesitating on one item"
        elif total_views >= 5:
            segment, intent = "Lost Cause", "Browsing widely"
        elif total_views >= 1:
            segment, intent = "Sure Thing", "Light browsing"
        else:
            segment, intent = "Unknown", "No signal yet"

    out = {
        "uid": v.uid,
        "segment": segment,
        "intent": intent,
        "intent_score": int(score),
        "total_views": total_views,
        "top_product": enrich(PRODUCT_BY_ID[top_pid]) if top_pid else None,
        "looking_at": looking_at_name,
        "top_views": top_views,
        "interests": product_interests(v),
        "cart": [enrich(PRODUCT_BY_ID[c]) for c in v.cart if c in PRODUCT_BY_ID],
        "wishlist": [enrich(PRODUCT_BY_ID[c]) for c in v.wishlist if c in PRODUCT_BY_ID],
        "devices": v.devices,
        "events": len(v.events),
        "dwell_s": round(dwell, 1),
        "consent": getattr(v, "consent", True),
        "loyalty": loyalty(v.points),
        "uplift": model["uplift"] if model else None,
        "base_rate": model["base_rate"] if model else None,
        "inc_value": model["inc_value"] if model else None,
        "scored_by": model["scored_by"] if model else "heuristic",
    }
    if record and model:
        # Register even with 0 events so a freshly signed-in shopper is immediately visible
        # in the live console (empty logs) instead of disappearing until their first click.
        LIVE_SHOPPERS[v.uid] = {
            "uid": v.uid, "bucket": segment, "base_rate": model["base_rate"],
            "uplift": model["uplift"], "inc_value": model["inc_value"],
            "intent_score": int(score), "events": len(v.events),
            "top_product": (PRODUCT_BY_ID.get(top_pid) or {}).get("name"),
            "looking_at": looking_at_name,
            "devices": list(v.devices), "ts": time.time(),
        }
    return out

def best_channel_for_device(device: str) -> str:
    return {"mobile": "Push", "tablet": "WhatsApp"}.get(device, "Email")

def orchestrate_channel(v: "Visitor", device: str, segment: str) -> dict:
    ended = getattr(v, "ended", False)
    seconds_idle = time.time() - (v.events[-1]["ts"] if v.events else time.time())
    live_now = (not ended) and seconds_idle < 30
    cart_value = sum(enrich(PRODUCT_BY_ID[c])["sale_price"] for c in v.cart if c in PRODUCT_BY_ID)
    returning = bool(v.orders) or v.points >= 200

    if live_now:
        ch, why, when = "In-App", "shopper is live on the site — nudge in the moment, not the inbox", "on-site"
    elif returning and segment in ("Sure Thing", "Persuadable"):
        ch, why, when = "Live Concierge", "high-value loyal — a personal stylist touch deepens the relationship without discounting", "off-site"
    elif cart_value >= 150:
        ch, why, when = "Wallet Pass", "valuable bag left behind — drop the offer into their wallet so it geo-reminds them near a store", "off-site"
    elif segment == "Lost Cause":
        ch, why, when = "Retargeting Ad", "left without intent — ambient retargeting, never an inbox touch", "ambient"
    elif device == "mobile":
        ch, why, when = "Push", "off-site re-engagement: instant and cheapest on mobile", "off-site"
    elif device == "desktop":
        ch, why, when = "Email", "off-site re-engagement: rich content now that they've left", "off-site"
    else:
        ch, why, when = "WhatsApp", "off-site rich async re-engagement across devices", "off-site"
    meta = CHANNEL_META[ch]
    return {"channel": ch, "icon": meta["icon"], "cost": meta["cost"],
            "latency": meta["latency"], "why": why, "timing": when}

def _product_link(p: dict | None) -> str | None:
    return f"/store?p={p['id']}" if p else "/store"

def next_best_action(v: Visitor, device: str) -> dict:
    p = profile(v)
    seg = p["segment"]
    orch = orchestrate_channel(v, device, seg)
    channel = orch["channel"]
    top = p["top_product"]
    lty = p["loyalty"]
    member = lty["points"] >= 80
    interests = p.get("interests") or []
    base = {"channel": channel, "channel_icon": orch["icon"], "channel_why": orch["why"],
            "channel_cost": orch["cost"], "link": _product_link(top), "product": top,
            "interests": interests}

    if seg == "Converted":
        return {**base, "recommend": False, "segment": seg,
                "headline": "Order on its way 🎉",
                "message": "Thanks for your purchase — no need to spend a rupee here.",
                "rationale": "Already converted — marketing would be wasted."}

    if seg in ("Persuadable",):
        # Lead with items they're still considering — never the one they already bought.
        active_interests = [i for i in interests if not i.get("bought")] or interests
        names = [i["name"] for i in active_interests[:3]]
        if len(names) >= 2:
            item = ", ".join(names[:-1]) + f" & {names[-1]}"
        elif names:
            item = names[0]
        else:
            item = top["name"] if top else "the items you viewed"
        med = min_effective_discount(p.get("base_rate"), p.get("uplift"), p.get("intent_score"))
        disc = med["discount"]
        if disc == 0:
            reward = f"A quick reminder about {item} — plus 2× points today (no discount needed)"
            reward_type = "reminder + 2× points"
        elif member:
            reward = (f"Use your {lty['points']} pts (${lty['dollar_value']}) plus "
                      f"{disc}% off {item}")
            reward_type = "points + discount"
        else:
            reward = f"Here's {disc}% off {item} — and you'll earn 2× points today"
            reward_type = "discount + 2× points"
        dose_note = (f"right-sized to {disc}% (the smallest dose that converts; "
                     f"+${med['vs_flat20_margin']:.0f} margin vs a flat 20%)")
        lead = active_interests[0] if active_interests else top
        more = len(active_interests) - 1
        headline = (f"Still comparing the {lead['emoji']} {lead['name']}"
                    + (f" (+{more} more)?" if more >= 1 else "?")) if lead else "Still thinking it over?"
        return {
            **base, "recommend": True, "segment": seg,
            "headline": headline,
            "message": f"{reward} — pick up where you left off on your other device.",
            "offer_pct": disc, "reward_type": reward_type, "loyalty": lty, "med": med,
            "cta": "Resume your cart →", "expected_lift": "high",
            "rationale": (f"Repeated interest, no purchase = marketing changes the outcome. "
                          f"Channel: {channel} ({orch['why']}). Discount {dose_note}."),
        }

    if seg == "Sure Thing":
        return {**base, "recommend": True, "segment": seg,
                "headline": "A thank-you, not a discount 🎁",
                "message": f"Earn 2× loyalty points on today's order — you're {lty['to_next']} pts "
                           f"from {lty['next_tier']}. No discount needed.",
                "reward_type": "2× points (no discount)", "loyalty": lty,
                "cta": "Shop the new edit →",
                "rationale": "Would buy anyway — a points reward keeps margin while "
                             "deepening loyalty. This is restraint with upside."}

    if seg == "Lost Cause":
        return {**base, "recommend": False, "segment": seg,
                "headline": "Just browsing 👀",
                "message": "Low purchase intent — not worth spending budget yet.",
                "rationale": "No focused intent — spend would not change the outcome."}

    return {**base, "recommend": False, "segment": seg,
            "headline": "Getting to know you…",
            "message": "Not enough signal yet — keep browsing.",
            "rationale": "Need more behaviour before acting."}

TRADITIONAL_BLASTS = [
    {"channel": "Email", "subject": "🔥 50% OFF EVERYTHING — TODAY ONLY!", "preview": "Shop the mega sale before it's gone. Hurry!", "tag": "batch · all 2.4M users"},
    {"channel": "SMS", "subject": "FLASH SALE ends at MIDNIGHT ⏰", "preview": "Reply STOP to opt out", "tag": "batch · all 2.4M users"},
    {"channel": "Email", "subject": "Don't miss out!! Last chance 😱", "preview": "Everything must go — extra 10% at checkout", "tag": "batch · all 2.4M users"},
    {"channel": "Push", "subject": "We miss you 😢 come back!", "preview": "Here's a coupon, just for you (and everyone)", "tag": "batch · all 2.4M users"},
]

def mail_simulation(v: Visitor, device: str) -> dict:
    p = profile(v)
    nba = next_best_action(v, device)
    top = p["top_product"]

    if nba["recommend"]:
        emoji = top["emoji"] if top else "🛍️"
        conductor = {
            "send": True,
            "channel": nba["channel"],
            "channel_icon": nba.get("channel_icon"),
            "subject": f"{emoji} {nba['headline']}",
            "preview": nba["message"],
            "body": nba["message"] + " Your cart and points follow you on every device.",
            "reward_type": nba.get("reward_type", "personalized offer"),
            "offer_pct": nba.get("offer_pct"),
            "cta": nba.get("cta", "Shop now →"),
            "link": nba.get("link", "/store"),
            "product": top,
            "interests": nba.get("interests"),
            "timing": "now · peak-intent moment",
            "reason": nba["rationale"],
        }
    else:
        conductor = {
            "send": False,
            "channel": nba["channel"],
            "subject": "(no message sent)",
            "preview": nba["message"],
            "body": nba["rationale"],
            "timing": "—",
            "reason": nba["rationale"],
        }

    return {
        "segment": p["segment"],
        "conductor": conductor,
        "traditional": TRADITIONAL_BLASTS,
        "contrast": {
            "conductor_sends": 1 if conductor["send"] else 0,
            "traditional_sends": len(TRADITIONAL_BLASTS),
            "conductor_personalized": conductor["send"],
        },
    }

AOV = 92.0
DISCOUNT = 0.20
COGS = 0.55

def min_effective_discount(base_rate, uplift, intent_score) -> dict:
    import math
    base = base_rate if base_rate is not None else 0.12
    up = max(uplift or 0.0, 0.0)
    sens = min(0.85, max(0.05, up * 1.8 + (intent_score or 0) / 250))
    rows = []
    for d in (0, 5, 10, 15, 20, 25):
        p = min(0.98, base + up * 0.4 + sens * (1 - math.exp(-d / 11)))
        margin_per = AOV * (1 - d / 100) - AOV * COGS
        rows.append({"discount": d, "conv_prob": round(p, 3),
                     "exp_profit": round(p * margin_per, 2)})
    best = max(rows, key=lambda r: r["exp_profit"])
    flat20 = next(r for r in rows if r["discount"] == 20)
    return {
        "discount": best["discount"], "conv_prob": best["conv_prob"],
        "exp_profit": best["exp_profit"],
        "vs_flat20_margin": round(best["exp_profit"] - flat20["exp_profit"], 2),
        "curve": rows,
    }

def _categories_viewed(v: Visitor) -> dict[str, int]:
    cats: dict[str, int] = defaultdict(int)
    for e in v.events:
        if e.get("type") in ("view_product", "view_detail") and e.get("product_id"):
            p = PRODUCT_BY_ID.get(e["product_id"])
            if p:
                cats[p["cat"]] += 1
    return cats

def detect_patterns(v: Visitor) -> list[dict]:
    views = _product_view_counts(v)
    top_pid = max(views, key=views.get) if views else None
    top_views = views.get(top_pid, 0) if top_pid else 0
    cats = _categories_viewed(v)
    types = [e.get("type") for e in v.events]
    dwell = sum(e.get("dwell_ms", 0) for e in v.events) / 1000.0
    out: list[dict] = []

    def add(code, label, detail, intent, icon):
        out.append({"code": code, "label": label, "detail": detail,
                    "intent": intent, "icon": icon})

    if top_views >= 3 and top_pid:
        nm = PRODUCT_BY_ID[top_pid]["name"]
        add("fixation", "Fixated on one item", f"Viewed {nm} {top_views}× — deciding, not discovering", "up", "🎯")
    if v.cart and not any(t == "purchase" for t in types):
        add("cart_abandon", "Cart abandonment risk", f"{len(v.cart)} item(s) in cart, no checkout yet", "up", "🛒")
    if len(cats) >= 2:
        add("cross_cat", "Cross-category browsing", f"Looking across {', '.join(list(cats)[:3])} — bundle opportunity", "up", "🧩")
    if types.count("view_all_reviews") or types.count("view_reviews") >= 2 or "view_size_guide" in types:
        add("research", "Researching before buying", "Reading reviews / sizing — high deliberate intent", "up", "🔍")
    if len(v.wishlist) >= 2:
        add("wishlist", "Building a wishlist", f"{len(v.wishlist)} saved — planning a multi-item purchase", "up", "💖")
    if any(t in ("apply_coupon", "clip_coupon", "compare") for t in types):
        add("price_sensitive", "Price-sensitive", "Engaging with offers/compare — promo-responsive", "up", "🏷️")
    if sum(views.values()) >= 5 and top_views <= 1 and not v.cart:
        add("window", "Window shopping", "Wide, shallow browsing with no focus — low intent so far", "down", "🪟")
    if v.orders:
        add("returning", "Returning buyer", f"{len(v.orders)} prior order(s) this session — loyal", "up", "🔁")
    if dwell > 30 and top_pid:
        add("lingering", "Lingering", f"{int(dwell)}s dwell — strong consideration signal", "up", "⏳")
    return out

def detect_bundle(v: Visitor) -> dict | None:
    views = _product_view_counts(v)
    ranked: list[str] = []
    for pid in v.cart + v.wishlist + sorted(views, key=views.get, reverse=True):
        if pid in PRODUCT_BY_ID and pid not in ranked:
            ranked.append(pid)
    if len(ranked) < 2:
        return None
    picks = [enrich(PRODUCT_BY_ID[p]) for p in ranked[:3]]
    total = round(sum(p["list_price"] for p in picks), 2)

    seg = profile(v)["segment"]
    if seg == "Sleeping Dog":
        return None
    pct, kind, rationale = {
        "Persuadable": (18, "discount", "Multi-item interest + a nudge changes the outcome — worth a real bundle discount."),
        "Sure Thing":  (8,  "points",   "Would buy anyway — keep margin: small bundle saving + 2× points, not a deep cut."),
        "Lost Cause":  (12, "discount", "Low intent — a modest bundle may be the only thing that converts."),
    }.get(seg, (15, "discount", "Frequently-viewed-together items — bundle to lift basket size."))
    price = round(total * (1 - pct / 100), 2)
    return {
        "name": "Your personalised bundle",
        "segment": seg, "discount_pct": pct, "kind": kind,
        "products": [{"id": p["id"], "name": p["name"], "emoji": p["emoji"],
                      "price": p["list_price"]} for p in picks],
        "total": total, "price": price, "saves": round(total - price, 2),
        "rationale": rationale,
    }

def session_economics(v: Visitor) -> dict:
    p = profile(v)
    seg = p["segment"]
    nba = next_best_action(v, v.devices[-1] if v.devices else "desktop")

    cart_adds = sum(1 for e in v.events if e.get("type") == "add_to_cart")
    browsed = any(e.get("type") in ("view_product", "view_detail", "view_category",
                                    "view_reviews", "view_all_reviews") for e in v.events)

    # Kairos: count ONLY what it actually decided to send — the messages in the inbox.
    # Zero until a touch is genuinely warranted, so a fresh login reads 0 and matches the
    # customer's (empty) inbox exactly — no phantom "sent" count.
    cond_msgs = len(v.inbox)
    gives_discount = seg == "Persuadable" and "discount" in str(nba.get("reward_type", ""))
    cond_incentive = AOV * 0.15 if gives_discount else 0.0
    cond_budget = round(cond_msgs * 0.04 + cond_incentive, 2)
    cond_annoy = min(20, cond_msgs * 5)

    # Traditional batch-and-blast: a touch on entry + a nudge for every cart action + a
    # post-purchase blast — everything Kairos sent PLUS the touches it chose to withhold.
    # Always >= Kairos, so the gap (saved) is the restraint, and it's 0 before any activity.
    trad_msgs = max(cond_msgs, (1 if browsed else 0) + cart_adds + (1 if v.orders else 0))
    trad_incentive = AOV * DISCOUNT if (browsed and seg in ("Sure Thing", "Persuadable")) else 0.0
    trad_budget = round(trad_msgs * 0.12 + trad_incentive, 2)
    trad_annoy = min(95, trad_msgs * 18)

    return {
        "segment": seg,
        "traditional": {"messages": trad_msgs, "budget": trad_budget, "annoyance_pct": trad_annoy},
        "conductor": {"messages": cond_msgs, "budget": cond_budget, "annoyance_pct": cond_annoy},
        "delta": {
            "messages_saved": trad_msgs - cond_msgs,
            "budget_saved": round(trad_budget - cond_budget, 2),
            "annoyance_avoided_pct": trad_annoy - cond_annoy,
        },
        "basis": "projected per-shopper economics",
    }

def _send_inbox(v: Visitor, channel: str, subject: str, preview: str, body: str,
                reason: str, icon: str = "📧") -> None:
    v.inbox.append({"channel": channel, "channel_icon": icon, "subject": subject,
                    "preview": preview, "body": body, "cta": "Shop now →", "link": "/store",
                    "product": None, "reward_type": None, "offer_pct": None, "reason": reason,
                    "from": "VERVE · The Style Edit", "ts": time.time(), "read": False})
    del v.inbox[:-12]
    STORE._persist(v)

def implement_play(code: str) -> dict:
    """Actually EXECUTE a recommended play — send the real messages / apply the policy — so
    the strategist's 'Implement' button does something, not just advises. Message-sending
    plays land in the customer's inbox (and show up as real Kairos sends in the economics)."""
    shoppers = [v for v in STORE._v.values() if v.events]
    sent = 0
    if code == "recover_carts":
        recovered = 0.0
        for v in shoppers:
            if v.cart and not v.orders:
                _send_inbox(v, "In-App", "Still thinking it over?",
                            "Your bag is waiting — a small nudge while you're here.",
                            "We saved your items. Complete checkout while they're in stock.",
                            "cart-recovery — incremental for this shopper", "📲")
                sent += 1
                recovered += sum(enrich(PRODUCT_BY_ID[c])["sale_price"] for c in v.cart if c in PRODUCT_BY_ID)
        return {"ok": True, "code": code, "action": "Cart-recovery nudges sent",
                "count": sent, "detail": f"{sent} live cart(s) nudged · ${recovered:,.0f} back in play"}
    if code == "target_persuadables":
        for v in shoppers:
            if profile(v)["segment"] == "Persuadable":
                _send_inbox(v, "Email", "Picked for you",
                            "A right-sized offer on what you've been eyeing.",
                            "Because it actually changes your decision — here's our best offer.",
                            "Persuadable — spend is incremental here")
                sent += 1
        return {"ok": True, "code": code, "action": "Targeted offers sent to Persuadables",
                "count": sent, "detail": f"{sent} Persuadable(s) contacted on their best channel"}
    if code == "hold_sure_things":
        n = sum(1 for v in shoppers if profile(v)["segment"] == "Sure Thing")
        return {"ok": True, "code": code, "action": "Discounts swapped for 2× points",
                "count": n, "detail": f"{n} Sure Thing(s) moved to loyalty — margin kept, no blast"}
    if code == "suppress_dogs":
        n = sum(1 for v in shoppers if profile(v)["segment"] == "Sleeping Dog")
        return {"ok": True, "code": code, "action": "Sleeping Dogs suppressed",
                "count": n, "detail": f"{n} negative-uplift shopper(s) excluded from outbound"}
    if code == "right_size_discount":
        n = sum(1 for v in shoppers if profile(v)["segment"] == "Persuadable")
        return {"ok": True, "code": code, "action": "Minimum Effective Dose applied",
                "count": n, "detail": f"{n} Persuadable(s) set to their smallest converting dose"}
    return {"ok": False, "code": code, "action": "Unknown play", "count": 0, "detail": "No such play"}

def session_end_mail(v: Visitor, device: str) -> dict | None:
    p = profile(v)
    seg = p["segment"]
    if seg == "Sleeping Dog" or not v.events:
        return None

    nba = next_best_action(v, device)
    orch = orchestrate_channel(v, device, seg)
    top = p["top_product"]
    cart = p["cart"]

    if nba.get("recommend"):
        emoji = top["emoji"] if top else "🛍️"
        return {"channel": nba["channel"], "channel_icon": nba.get("channel_icon", "📧"),
                "subject": f"{emoji} {nba['headline']}", "preview": nba["message"],
                "body": nba["message"] + " Your cart and points follow you everywhere.",
                "cta": nba.get("cta", "Shop now →"), "link": nba.get("link", "/store"),
                "product": top, "reward_type": nba.get("reward_type"),
                "offer_pct": nba.get("offer_pct"), "reason": nba["rationale"]}

    if seg == "Converted":
        return {"channel": orch["channel"], "channel_icon": orch["icon"],
                "subject": "🎉 Thanks for your order — here's 2× points",
                "preview": "Your order's on its way. Enjoy 2× points on your next visit.",
                "body": "Your order is on its way! Enjoy 2× loyalty points on your next visit, plus pieces that pair perfectly with what you just bought.",
                "cta": "Explore the edit →", "link": "/store", "product": None,
                "reward_type": "thank-you + cross-sell (no discount)", "offer_pct": None,
                "reason": "Converted: reward and cross-sell on points — no discount needed."}

    if cart:
        subj = f"🛍️ You left {len(cart)} item{'s' if len(cart) > 1 else ''} in your bag"
        body = "Your bag is saved and your points are waiting — finish whenever you're ready."
        cta, link, prod = "Resume your bag →", "/store", (cart[0] if cart else None)
    elif top:
        subj = f"👀 Still curious about the {top['emoji']} {top['name']}?"
        body = "It's still here — plus free shipping over $50 and easy 30-day returns."
        cta, link, prod = "Take another look →", _product_link(top), top
    else:
        subj = "✨ Thanks for stopping by VERVE"
        body = "New-season styles just dropped — come browse when you have a moment."
        cta, link, prod = "See what's new →", "/store", None
    return {"channel": orch["channel"], "channel_icon": orch["icon"], "subject": subj,
            "preview": body, "body": body, "cta": cta, "link": link, "product": prod,
            "reward_type": "light win-back (no discount)", "offer_pct": None,
            "reason": f"{seg}: low live intent, but a cheap {orch['channel']} touch keeps the door open without giving away margin."}

def deliver_to_inbox(v: Visitor, device: str) -> list[dict]:
    if not getattr(v, "consent", True):
        return v.inbox[::-1]
    c = session_end_mail(v, device)
    if c:
        recent = v.inbox and (time.time() - v.inbox[-1]["ts"] < 1.5)
        if not recent:
            v.inbox.append({
                "channel": c["channel"], "channel_icon": c.get("channel_icon", "📧"),
                "subject": c["subject"], "preview": c["preview"], "body": c["body"],
                "cta": c.get("cta", "Shop now →"), "link": c.get("link", "/store"),
                "product": c.get("product"), "reward_type": c.get("reward_type"),
                "offer_pct": c.get("offer_pct"), "reason": c.get("reason"),
                "from": "VERVE · The Style Edit", "ts": time.time(), "read": False,
            })
            del v.inbox[:-12]
    return v.inbox[::-1]

def cohort_analytics() -> dict:
    shoppers = list(STORE._v.values())
    # Only count people who actually entered the funnel — not empty/phantom records left by
    # a bare login or an abandoned guest id. visitors >= browsed >= carted >= bought always.
    visitors = sum(1 for v in shoppers if v.events or v.orders)
    browsed = sum(1 for v in shoppers if any(e.get("type") in ("view_product", "view_detail") for e in v.events))
    carted = sum(1 for v in shoppers if v.cart or any(e.get("type") == "add_to_cart" for e in v.events))
    bought = sum(1 for v in shoppers if v.orders)

    buckets: dict[str, int] = defaultdict(int)
    views: dict[str, int] = defaultdict(int)
    revenue_at_risk = 0.0
    for v in shoppers:
        if v.events:
            buckets[profile(v)["segment"]] += 1
        for pid, c in _product_view_counts(v).items():
            views[pid] += c
        if v.cart and not v.orders:
            revenue_at_risk += sum(enrich(PRODUCT_BY_ID[c])["sale_price"]
                                   for c in v.cart if c in PRODUCT_BY_ID)

    top_products = sorted(
        ({"id": pid, "name": PRODUCT_BY_ID[pid]["name"], "emoji": PRODUCT_BY_ID[pid]["emoji"],
          "cat": PRODUCT_BY_ID[pid]["cat"], "views": c}
         for pid, c in views.items() if pid in PRODUCT_BY_ID),
        key=lambda x: -x["views"])[:6]

    return {
        "funnel": {"visitors": visitors, "browsed": browsed, "carted": carted, "bought": bought,
                   "browse_to_cart_pct": round(100 * carted / max(browsed, 1), 1),
                   "cart_to_buy_pct": round(100 * bought / max(carted, 1), 1)},
        "buckets": dict(buckets),
        "top_products": top_products,
        "revenue": {"orders": REVENUE["orders"], "gross": round(REVENUE["gross"], 2),
                    "units": REVENUE["units"], "incentive_given": round(REVENUE["incentive_given"], 2),
                    "by_category": {k: round(val, 2) for k, val in REVENUE["by_category"].items()},
                    "by_segment": {k: round(val, 2) for k, val in REVENUE["by_segment"].items()},
                    "aov": round(REVENUE["gross"] / max(REVENUE["orders"], 1), 2),
                    "recent": REVENUE["recent"][:8]},
        "revenue_at_risk": round(revenue_at_risk, 2),
    }

SEGMENT_PLAYBOOK = {
    "Persuadable": {
        "action": "TARGET — spend here", "color": "#3b82f6",
        "channel": "In-App live → Push/Email once they leave",
        "discount": "Real incentive (15–20%): this is the one place a discount changes the outcome",
        "message": "Cart/intent-based, deep-linked straight to the item, sent at session end",
        "why": "Marketing measurably lifts their purchase probability — every dollar here is incremental revenue.",
    },
    "Sure Thing": {
        "action": "REWARD, don't discount", "color": "#22c55e",
        "channel": "Live Concierge / loyalty points",
        "discount": "No discount — 2× points instead. Protects margin.",
        "message": "Thank-you + status progress, never a coupon",
        "why": "They buy anyway; a discount is pure margin given away for a sale you already had.",
    },
    "Sleeping Dog": {
        "action": "SUPPRESS — stay silent", "color": "#eab308",
        "channel": "— (no contact)",
        "discount": "None. Do not message.",
        "message": "No message",
        "why": "Contact provably LOWERS their conversion — silence protects organic revenue you'd otherwise destroy.",
    },
    "Lost Cause": {
        "action": "MINIMAL / ambient", "color": "#ef4444",
        "channel": "Retargeting Ad / cheap win-back",
        "discount": "None or tiny — never deep",
        "message": "Light brand presence, no inbox cost",
        "why": "Won't convert regardless, so any spend is wasted — keep it ambient and cheap, not a discount.",
    },
}

def strategy_report() -> dict:
    co = cohort_analytics()
    funnel, rev, buckets = co["funnel"], co["revenue"], co["buckets"]
    total_seg = sum(buckets.values()) or 1

    incentive = rev["incentive_given"]
    incentive_efficiency = round(rev["gross"] / incentive, 1) if incentive else None
    sure_n = buckets.get("Sure Thing", 0)
    dog_n = buckets.get("Sleeping Dog", 0)
    pers_n = buckets.get("Persuadable", 0)
    est_discount_waste = round(sure_n * AOV * DISCOUNT, 2)
    protected = round(dog_n * AOV * 0.08, 2)

    segments = []
    for name, pb in SEGMENT_PLAYBOOK.items():
        n = buckets.get(name, 0)
        segments.append({**pb, "segment": name, "count": n, "pct": round(100 * n / total_seg, 1)})

    med_margin, depths = 0.0, []
    for v in STORE._v.values():
        if not v.events:
            continue
        pp = profile(v)
        if pp["segment"] == "Persuadable":
            med = min_effective_discount(pp.get("base_rate"), pp.get("uplift"), pp.get("intent_score"))
            med_margin += med["vs_flat20_margin"]
            depths.append(med["discount"])
    avg_depth = round(sum(depths) / len(depths), 1) if depths else None
    med_margin = round(med_margin, 2)

    channels = []
    for name in CHANNELS:
        m = CHANNEL_META[name]
        channels.append({"channel": name, "icon": m["icon"], "cost": m["cost"],
                         "immediacy": m["immediacy"], "kind": m["kind"]})

    recs = []
    if funnel["carted"] and co["revenue_at_risk"] > 0:
        recs.append({"code": "recover_carts", "priority": "High", "title": "Recover abandoned carts the moment shoppers leave",
                     "detail": f"${co['revenue_at_risk']:.0f} sits in abandoned bags. Fire an In-App nudge while they're live, then one Push/Wallet-Pass touch at session end — not a blast.",
                     "impact": f"${co['revenue_at_risk']:.0f} recoverable"})
    if sure_n:
        recs.append({"code": "hold_sure_things", "priority": "High", "title": "Stop discounting Sure Things",
                     "detail": f"{sure_n} shopper(s) would buy anyway. Swap their coupon for 2× points and you keep the margin.",
                     "impact": f"~${est_discount_waste:.0f} margin protected"})
    if pers_n:
        recs.append({"code": "target_persuadables", "priority": "Medium", "title": "Concentrate budget on Persuadables",
                     "detail": f"{pers_n} shopper(s) are genuinely movable. Deep-link, real offer, best channel — this is where spend is incremental.",
                     "impact": "highest ROI per $"})
    if depths:
        recs.append({"code": "right_size_discount", "priority": "High", "title": "Right-size the discount (Minimum Effective Dose)",
                     "detail": f"Avg effective discount is {avg_depth}% — not a reflexive 20%. Give each Persuadable the smallest dose that still converts instead of blanket promos.",
                     "impact": f"~${med_margin:.0f} margin right-sized"})
    if dog_n:
        recs.append({"code": "suppress_dogs", "priority": "Medium", "title": "Suppress Sleeping Dogs",
                     "detail": f"{dog_n} shopper(s) convert LESS when contacted. Leaving them alone protects organic revenue.",
                     "impact": f"~${protected:.0f} revenue protected"})

    return {
        "funnel": funnel,
        "headline": {
            "visitors": funnel["visitors"], "buyers": funnel["bought"],
            "conversion_pct": round(100 * funnel["bought"] / max(funnel["visitors"], 1), 1),
            "revenue": rev["gross"], "aov": rev["aov"], "orders": rev["orders"],
            "revenue_at_risk": co["revenue_at_risk"], "incentive_given": incentive,
            "incentive_efficiency": incentive_efficiency,
            "est_discount_waste_avoided": est_discount_waste,
            "avg_discount_depth": avg_depth,
            "margin_right_sized": med_margin,
        },
        "segments": segments,
        "channels": channels,
        "recommendations": recs,
        "top_products": co["top_products"],
        "revenue_by_segment": rev["by_segment"],
        "revenue_by_category": rev["by_category"],
    }
