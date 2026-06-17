"""Real-time behavioural tracking + identity resolution + next-best-action.

This powers the live, clickable demo:
  - The storefront posts every click to /track (product views, dwell, add-to-cart).
  - We accumulate a per-visitor behavioural profile and score *intent* live.
  - Identity resolution: the same identity key seen from a second device is linked,
    so the full cross-device journey is one profile (the Epsilon CORE-ID story).
  - When the visitor lands on a new device, we compute the next-best-action — the
    right message on the right channel — from everything we've observed.

State is in-memory (a dict). Fine for a demo; swap for Redis in production.
"""
from __future__ import annotations

import hashlib
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from threading import Lock

import joblib
import numpy as np

# Trained behavioral uplift model (ml/src/live_model.py) — the causal brain that
# scores live shoppers. Loaded lazily; falls back to heuristics if absent.
_LIVE_PATH = Path(__file__).resolve().parents[1] / "ml" / "artifacts" / "live_uplift.joblib"
_LIVE_MODEL = None
# Live shoppers currently being scored — surfaced to the marketer analytics so the
# storefront and the dashboard are visibly one connected product.
LIVE_SHOPPERS: dict[str, dict] = {}


def _live_model():
    global _LIVE_MODEL
    if _LIVE_MODEL is None:
        try:
            _LIVE_MODEL = joblib.load(_LIVE_PATH)
        except Exception:
            _LIVE_MODEL = {}
    return _LIVE_MODEL

# ---- The catalogue the storefront renders (a health & beauty retailer, the kind
# of brand that actually runs on Epsilon). Each item carries price/rating/blurb so
# the store looks real and the scorer knows value. ----
PRODUCTS = [
    # Women
    {"id": "p1", "name": "Floral Wrap Dress", "price": 79, "cat": "Women", "emoji": "👗", "rating": 4.7, "blurb": "Flowy midi, breathable viscose"},
    {"id": "p2", "name": "Tailored Blazer", "price": 129, "cat": "Women", "emoji": "🧥", "rating": 4.6, "blurb": "Structured, office-to-evening"},
    {"id": "p3", "name": "Silk Blouse", "price": 69, "cat": "Women", "emoji": "👚", "rating": 4.5, "blurb": "Mulberry silk, relaxed fit"},
    {"id": "p4", "name": "High-Rise Jeans", "price": 89, "cat": "Women", "emoji": "👖", "rating": 4.7, "blurb": "Sculpting stretch denim"},
    # Men
    {"id": "p5", "name": "Slim-Fit Chinos", "price": 69, "cat": "Men", "emoji": "👖", "rating": 4.6, "blurb": "All-day comfort cotton twill"},
    {"id": "p6", "name": "Linen Shirt", "price": 59, "cat": "Men", "emoji": "👔", "rating": 4.5, "blurb": "Breathable, summer-ready"},
    {"id": "p7", "name": "Bomber Jacket", "price": 149, "cat": "Men", "emoji": "🧥", "rating": 4.8, "blurb": "Water-resistant, ribbed cuffs"},
    {"id": "p8", "name": "Graphic Tee", "price": 29, "cat": "Men", "emoji": "👕", "rating": 4.4, "blurb": "Soft combed cotton"},
    # Shoes
    {"id": "p9", "name": "Leather Sneakers", "price": 119, "cat": "Shoes", "emoji": "👟", "rating": 4.7, "blurb": "Minimal, full-grain leather"},
    {"id": "p10", "name": "Chelsea Boots", "price": 159, "cat": "Shoes", "emoji": "🥾", "rating": 4.6, "blurb": "Suede, elastic side panels"},
    {"id": "p11", "name": "Strappy Heels", "price": 99, "cat": "Shoes", "emoji": "👠", "rating": 4.4, "blurb": "85mm, cushioned sole"},
    {"id": "p12", "name": "Running Shoes", "price": 109, "cat": "Shoes", "emoji": "👟", "rating": 4.8, "blurb": "Responsive foam, lightweight"},
    # Bags
    {"id": "p13", "name": "Leather Tote", "price": 189, "cat": "Bags", "emoji": "👜", "rating": 4.8, "blurb": "Full-grain, fits a 15\" laptop"},
    {"id": "p14", "name": "Mini Crossbody", "price": 89, "cat": "Bags", "emoji": "👛", "rating": 4.6, "blurb": "Adjustable strap, gold hardware"},
    {"id": "p15", "name": "Canvas Backpack", "price": 79, "cat": "Bags", "emoji": "🎒", "rating": 4.5, "blurb": "Water-repellent, padded straps"},
    {"id": "p16", "name": "Weekender Duffel", "price": 139, "cat": "Bags", "emoji": "🧳", "rating": 4.7, "blurb": "Cabin-size, shoe compartment"},
    # Accessories
    {"id": "p17", "name": "Aviator Sunglasses", "price": 129, "cat": "Accessories", "emoji": "🕶️", "rating": 4.6, "blurb": "Polarized, UV400"},
    {"id": "p18", "name": "Silk Scarf", "price": 49, "cat": "Accessories", "emoji": "🧣", "rating": 4.5, "blurb": "Hand-rolled edges, print"},
    {"id": "p19", "name": "Classic Watch", "price": 199, "cat": "Accessories", "emoji": "⌚", "rating": 4.8, "blurb": "Sapphire glass, leather strap"},
    {"id": "p20", "name": "Statement Earrings", "price": 39, "cat": "Accessories", "emoji": "💎", "rating": 4.4, "blurb": "18k gold-plated, hypoallergenic"},
    # Activewear
    {"id": "p21", "name": "Performance Hoodie", "price": 79, "cat": "Activewear", "emoji": "🧥", "rating": 4.7, "blurb": "Moisture-wicking, four-way stretch"},
    {"id": "p22", "name": "Training Shorts", "price": 35, "cat": "Activewear", "emoji": "🩳", "rating": 4.5, "blurb": "Lightweight, zip pocket"},
    {"id": "p23", "name": "Yoga Leggings", "price": 55, "cat": "Activewear", "emoji": "🧘", "rating": 4.8, "blurb": "High-rise, squat-proof"},
    {"id": "p24", "name": "Baseball Cap", "price": 25, "cat": "Activewear", "emoji": "🧢", "rating": 4.4, "blurb": "Adjustable, embroidered logo"},
]
PRODUCT_BY_ID = {p["id"]: p for p in PRODUCTS}
CATEGORIES = ["Women", "Men", "Shoes", "Bags", "Accessories", "Activewear"]
CHANNELS = ["Email", "Push", "SMS", "WhatsApp"]


# ---------------------------------------------------------------------------
# Product enrichment: badges, sale prices, descriptions, and customer reviews.
# Everything is generated deterministically from the product id so the catalogue
# is stable across reloads without us hand-writing 24 detail pages.
# ---------------------------------------------------------------------------
_BADGES = [None, "Best Seller", "Sale", "New", "Staff Pick", None, "Sale"]

# Every product carries one of these offers (the brief: highlight offers everywhere).
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

# Real product photos, keyword-matched per category (graceful fallback in the UI).
IMG_KW = {
    "Women": "dress,fashion,womenswear", "Men": "menswear,shirt,fashion",
    "Shoes": "shoes,sneakers,footwear", "Bags": "handbag,bag,fashion",
    "Accessories": "sunglasses,watch,accessories", "Activewear": "activewear,sportswear,fitness",
}

# Scrolling top-strip promos.
TICKER = [
    "Up to 30% OFF new-season styles",
    "Buy 1 Get 1 50% OFF on tees",
    "FREE express shipping over $50",
    "Extra 20% OFF sale with code STYLE20",
    "2× loyalty points on shoes this weekend",
    "New members get 200 bonus points",
    "Members get early access to the drop",
]

# Combo bundles — buy together, save more.
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

# Clip-style coupons (myAura exclusives).
COUPONS = [
    {"id": "cp1", "amount": "$15", "desc": "Off $75+ on dresses & tops", "tag": "myAura exclusive", "expires": "tomorrow"},
    {"id": "cp2", "amount": "$10", "desc": "Buy 2+ accessories", "tag": "myAura exclusive", "expires": "3 days"},
    {"id": "cp3", "amount": "20%", "desc": "First order of shoes online", "tag": "myAura exclusive", "expires": "this week"},
    {"id": "cp4", "amount": "$25", "desc": "Spend $150+ on outerwear", "tag": "seasonal", "expires": "5 days"},
    {"id": "cp5", "amount": "$8", "desc": "Activewear orders $40+", "tag": "myAura exclusive", "expires": "2 days"},
]

# Points redemption catalogue — use points later, incl. partner rewards.
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
    """Add an offer, sale price, image, badge and social-proof to a catalogue card.
    Every product gets an offer (per the brief)."""
    s = _seed(p["id"])
    offer = OFFERS[s % len(OFFERS)]
    pct = offer["pct"]
    sale = round(p["price"] * (1 - pct / 100), 2) if pct else p["price"]
    badge = _BADGES[(s // 7) % len(_BADGES)]
    kw = IMG_KW.get(p["cat"], "product")
    return {**p, "offer": offer["label"], "offer_kind": offer["kind"],
            "discount_pct": pct, "list_price": p["price"], "sale_price": sale,
            "img": f"https://loremflickr.com/400/400/{kw}?lock={s % 250}",
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


# Loyalty: points earned per interaction, and the tier ladder.
POINTS_PER = {"view_product": 2, "view_detail": 3, "view_reviews": 3,
              "add_to_wishlist": 5, "add_to_cart": 10, "checkout": 50}
TIERS = [("Bronze", 0), ("Silver", 80), ("Gold", 200), ("Platinum", 400)]


@dataclass
class Visitor:
    uid: str
    events: list = field(default_factory=list)
    devices: list = field(default_factory=list)        # ordered, unique
    cart: list = field(default_factory=list)
    wishlist: list = field(default_factory=list)
    points: int = 0
    created: float = field(default_factory=time.time)

    def add_device(self, device: str):
        if device and device not in self.devices:
            self.devices.append(device)


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
            "dollar_value": round(points * 0.04, 2)}   # 100 pts ≈ $4


class Store:
    def __init__(self):
        self._v: dict[str, Visitor] = {}
        self._lock = Lock()

    def visitor(self, uid: str) -> Visitor:
        with self._lock:
            if uid not in self._v:
                self._v[uid] = Visitor(uid=uid)
            return self._v[uid]

    def track(self, uid: str, event: dict) -> Visitor:
        v = self.visitor(uid)
        with self._lock:
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
        return v

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
        return {"ok": True, "reward": reward, "loyalty": loyalty(v.points)}


STORE = Store()


# ----------------------------------------------------------------------------
# Live intent scoring + next-best-action
# ----------------------------------------------------------------------------
def _product_view_counts(v: Visitor) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for e in v.events:
        if e.get("type") == "view_product" and e.get("product_id"):
            counts[e["product_id"]] += 1
    return counts


def visitor_features(v: Visitor) -> np.ndarray:
    """Build the behavioral feature vector the uplift model expects."""
    views = _product_view_counts(v)
    total = sum(views.values())
    distinct = len(views)
    top = max(views.values()) if views else 0
    dwell_min = sum(e.get("dwell_ms", 0) for e in v.events) / 60000.0
    reviews = sum(1 for e in v.events if e.get("type") == "view_reviews")
    prior = sum(1 for e in v.events if e.get("type") == "checkout")
    recency = 0.5                       # active session = very recent
    return np.array([[total, distinct, top, dwell_min, len(v.wishlist),
                      len(v.cart), reviews, prior, recency]], dtype=float)


def score_visitor(v: Visitor) -> dict | None:
    """Run the trained uplift model on the live shopper → real CATE + bucket.
    Returns None if the model isn't available (then callers use heuristics)."""
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


def profile(v: Visitor) -> dict:
    """Turn raw behaviour into a live intent profile + segment.

    Heuristics that mirror the causal buckets:
      - Repeated views of one item + no purchase  → hesitating  → Persuadable
      - Added to cart but didn't checkout         → high intent → Persuadable (hot)
      - Lots of browsing, many items, no focus     → exploring   → Lost/early
      - Bounced quickly                            → low intent
    """
    views = _product_view_counts(v)
    total_views = sum(views.values())
    top_pid = max(views, key=views.get) if views else None
    top_views = views.get(top_pid, 0) if top_pid else 0
    has_cart = bool(v.cart)
    has_wish = bool(v.wishlist)
    read_reviews = sum(1 for e in v.events if e.get("type") == "view_reviews")
    opened_detail = sum(1 for e in v.events if e.get("type") == "view_detail")
    checked_out = any(e.get("type") == "checkout" for e in v.events)
    dwell = sum(e.get("dwell_ms", 0) for e in v.events) / 1000.0

    # Intent score 0..100 — richer engagement = stronger signal (UX meter only).
    score = min(100, total_views * 5 + top_views * 9 + opened_detail * 6
                + read_reviews * 8 + (30 if has_cart else 0) + (22 if has_wish else 0)
                + min(dwell, 25))

    # The SEGMENT is decided by the trained causal uplift model (not heuristics).
    model = score_visitor(v)
    INTENT_TEXT = {
        "Persuadable": "Engaged, not yet bought — a nudge changes the outcome",
        "Sure Thing": "Decisive — likely to buy anyway",
        "Sleeping Dog": "Over-browsing — contact would backfire",
        "Lost Cause": "Low purchase intent",
    }
    if v.events == [] or not v.events:
        segment, intent = "Unknown", "No signal yet"
    elif checked_out:
        segment, intent = "Converted", "Purchased"
    elif model:
        segment, intent = model["bucket"], INTENT_TEXT[model["bucket"]]
    else:                                   # heuristic fallback if model missing
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
        "top_product": PRODUCT_BY_ID.get(top_pid) if top_pid else None,
        "top_views": top_views,
        "cart": [PRODUCT_BY_ID[c] for c in v.cart if c in PRODUCT_BY_ID],
        "wishlist": [PRODUCT_BY_ID[c] for c in v.wishlist if c in PRODUCT_BY_ID],
        "devices": v.devices,
        "events": len(v.events),
        "dwell_s": round(dwell, 1),
        "loyalty": loyalty(v.points),
        # Real causal numbers from the uplift model (None until there's signal).
        "uplift": model["uplift"] if model else None,
        "base_rate": model["base_rate"] if model else None,
        "inc_value": model["inc_value"] if model else None,
        "scored_by": model["scored_by"] if model else "heuristic",
    }
    # Surface this live shopper to the marketer analytics (one connected product).
    if v.events and model:
        LIVE_SHOPPERS[v.uid] = {
            "uid": v.uid, "bucket": segment, "base_rate": model["base_rate"],
            "uplift": model["uplift"], "inc_value": model["inc_value"],
            "intent_score": int(score), "events": len(v.events),
            "top_product": (PRODUCT_BY_ID.get(top_pid) or {}).get("name"),
            "devices": list(v.devices), "ts": time.time(),
        }
    return out


def best_channel_for_device(device: str) -> str:
    return {"mobile": "Push", "tablet": "WhatsApp"}.get(device, "Email")


def next_best_action(v: Visitor, device: str) -> dict:
    """The recommendation surfaced to the visitor on a (new) device."""
    p = profile(v)
    seg = p["segment"]
    channel = best_channel_for_device(device)
    top = p["top_product"]
    lty = p["loyalty"]
    member = lty["points"] >= 80                       # Silver+ = engaged member

    if seg == "Converted":
        return {"recommend": False, "segment": seg, "channel": channel,
                "headline": "Order on its way 🎉",
                "message": "Thanks for your purchase — no need to spend a rupee here.",
                "rationale": "Already converted — marketing would be wasted."}

    if seg in ("Persuadable",):
        item = top["name"] if top else "the items you viewed"
        disc = 15
        # Loyalty members get a points reward layered on — feels premium, and
        # redeemed points cost less margin than a blanket discount.
        if member:
            reward = (f"Use your {lty['points']} pts (${lty['dollar_value']}) plus "
                      f"{disc}% off {item}")
            reward_type = "points + discount"
        else:
            reward = f"Here's {disc}% off {item} — and you'll earn 2× points today"
            reward_type = "discount + 2× points"
        return {
            "recommend": True, "segment": seg, "channel": channel,
            "headline": f"Still thinking about the {top['emoji'] + ' ' + top['name'] if top else 'your pick'}?",
            "message": f"{reward} — pick up where you left off on your other device.",
            "offer_pct": disc, "reward_type": reward_type, "loyalty": lty,
            "product": top, "expected_lift": "high",
            "rationale": (f"Repeated interest, no purchase = marketing changes the outcome. "
                          f"Best channel on {device}: {channel}. {lty['tier']} member."),
        }

    if seg == "Sure Thing":
        # The clever move: reward loyalty instead of discounting. Margin protected,
        # customer still delighted.
        return {"recommend": True, "segment": seg, "channel": channel,
                "headline": "A thank-you, not a discount 🎁",
                "message": f"Earn 2× loyalty points on today's order — you're {lty['to_next']} pts "
                           f"from {lty['next_tier']}. No discount needed.",
                "reward_type": "2× points (no discount)", "loyalty": lty,
                "product": top,
                "rationale": "Would buy anyway — a points reward keeps margin while "
                             "deepening loyalty. This is restraint with upside."}

    if seg == "Lost Cause":
        return {"recommend": False, "segment": seg, "channel": channel,
                "headline": "Just browsing 👀",
                "message": "Low purchase intent — not worth spending budget yet.",
                "rationale": "No focused intent — spend would not change the outcome."}

    return {"recommend": False, "segment": seg, "channel": channel,
            "headline": "Getting to know you…",
            "message": "Not enough signal yet — keep browsing.",
            "rationale": "Need more behaviour before acting."}


# Generic blasts the OLD way (no targeting) fires at everyone, all the time.
TRADITIONAL_BLASTS = [
    {"channel": "Email", "subject": "🔥 50% OFF EVERYTHING — TODAY ONLY!", "preview": "Shop the mega sale before it's gone. Hurry!", "tag": "batch · all 2.4M users"},
    {"channel": "SMS", "subject": "FLASH SALE ends at MIDNIGHT ⏰", "preview": "Reply STOP to opt out", "tag": "batch · all 2.4M users"},
    {"channel": "Email", "subject": "Don't miss out!! Last chance 😱", "preview": "Everything must go — extra 10% at checkout", "tag": "batch · all 2.4M users"},
    {"channel": "Push", "subject": "We miss you 😢 come back!", "preview": "Here's a coupon, just for you (and everyone)", "tag": "batch · all 2.4M users"},
]


def mail_simulation(v: Visitor, device: str) -> dict:
    """Contrast the two worlds for the demo:
      conductor  — at most ONE message, chosen by causal intent, perfectly timed
                   (or deliberate silence when contact wouldn't change the outcome).
      traditional — the same generic promo blasts everyone gets regardless of behaviour.
    """
    p = profile(v)
    nba = next_best_action(v, device)
    top = p["top_product"]

    if nba["recommend"]:
        emoji = top["emoji"] if top else "🛍️"
        conductor = {
            "send": True,
            "channel": nba["channel"],
            "subject": f"{emoji} {nba['headline']}",
            "preview": nba["message"],
            "body": nba["message"] + " Your cart and points follow you on every device.",
            "reward_type": nba.get("reward_type", "personalized offer"),
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
