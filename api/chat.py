import re

import agent

CATS = ["Women", "Men", "Shoes", "Bags", "Accessories"]
STOP = {"the", "and", "for", "you", "have", "any", "can", "show", "want", "need",
        "looking", "some", "with", "that", "this", "what", "are", "got", "under",
        "below", "less", "than", "around", "about", "good", "nice", "give", "find",
        "would", "like", "please", "buy", "shop", "something", "anything", "me"}


def _parse(message: str):
    m = message.lower()
    price_cap = None
    pm = re.search(r"(?:under|below|less than|upto|up to|max|<)\s*\$?\s*(\d+)", m)
    if pm:
        price_cap = float(pm.group(1))
    elif re.search(r"\$\s*\d+", m) and any(w in m for w in ["under", "below", "cheap", "budget", "max"]):
        price_cap = float(re.search(r"\$\s*(\d+)", m).group(1))

    cat = None
    for c in CATS:
        if c.lower() in m:
            cat = c
    if re.search(r"\bwomen|\bwomens|\bladies|\bdress|\bblouse|\bskirt", m):
        cat = "Women"
    elif re.search(r"\bmen\b|\bmens\b|\bmenswear", m):
        cat = "Men"
    if any(w in m for w in ["shoe", "sneaker", "boot", "heel", "trainer"]):
        cat = "Shoes"
    if any(w in m for w in ["bag", "tote", "backpack", "duffel", "crossbody", "purse"]):
        cat = "Bags"
    if any(w in m for w in ["watch", "sunglass", "scarf", "earring", "accessor", "jewel"]):
        cat = "Accessories"
    return price_cap, cat


def search(message: str, products: list, top: int = 4):
    price_cap, cat = _parse(message)
    words = [w for w in re.findall(r"[a-z]{3,}", message.lower()) if w not in STOP]
    scored = []
    for p in products:
        s = 0
        name = p["name"].lower()
        blurb = (p.get("blurb", "") + " " + p["cat"]).lower()
        for w in words:
            if w in name:
                s += 5            # a name hit is the strongest signal
            elif w in blurb:
                s += 2
        if cat and p["cat"] == cat:
            s += 3
        if price_cap is not None and p["price"] > price_cap:
            s = -100             # over budget -> hard exclude
        scored.append((s, p))
    scored.sort(key=lambda x: (-x[0], x[1]["price"]))
    matches = [p for s, p in scored if s > 0][:top]
    if not matches and (cat or price_cap is not None):   # category/price-only fallback
        pool = products
        if cat:
            pool = [p for p in pool if p["cat"] == cat]
        if price_cap is not None:
            pool = [p for p in pool if p["price"] <= price_cap]
        matches = sorted(pool, key=lambda p: p["price"])[:top]
    return matches, price_cap, cat


def answer(message: str, products: list) -> dict:
    matches, price_cap, cat = search(message, products)
    if not matches:
        return {"reply": "I couldn't find a match for that. Try a category (dresses, sneakers, "
                         "bags, watches) or a budget like “under $100”.",
                "products": [], "source": "rules"}

    bits = []
    if cat:
        bits.append(cat.lower())
    if price_cap is not None:
        bits.append(f"under ${price_cap:.0f}")
    desc = " ".join(bits) or "great"
    reply = (f"Here's a {desc} pick I think you'll like:" if len(matches) == 1
             else f"Here are {len(matches)} {desc} picks you might like:")
    source = "rules"

    try:
        names = ", ".join(f"{p['name']} (${p['price']})" for p in matches)
        sys = ("You are VERVE's friendly shopping assistant. In ONE warm, short sentence, "
               "recommend these products to the shopper. Never invent products or prices.")
        txt, src = agent.llm_complete(sys, f"Shopper asked: {message}\nProducts: {names}", 80)
        if txt and txt.strip():
            reply = txt.strip()
            source = src or "rules"
    except Exception:
        pass

    cards = [{"id": p["id"], "name": p["name"], "price": p["price"], "emoji": p["emoji"],
              "cat": p["cat"], "blurb": p.get("blurb", ""), "rating": p.get("rating")}
             for p in matches]
    return {"reply": reply, "products": cards, "source": source}
