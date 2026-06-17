"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  store, getUid, Product, ProductDetail, Review, Bundle, Coupon, Redemption, Promotions,
} from "@/lib/api";

type Loyalty = {
  points: number; tier: string; next_tier: string; to_next: number;
  progress_pct: number; dollar_value: number;
};
type Profile = {
  segment: string; intent: string; intent_score: number; total_views: number;
  top_product: Product | null; top_views: number; cart: Product[]; wishlist: Product[];
  devices: string[]; events: number; dwell_s: number; loyalty: Loyalty;
};

const BRAND = "#e31837";
const CAT_THEME: Record<string, string> = {
  Women: "bg-gradient-to-br from-rose-200 to-pink-50",
  Men: "bg-gradient-to-br from-slate-200 to-slate-50",
  Shoes: "bg-gradient-to-br from-amber-200 to-orange-50",
  Bags: "bg-gradient-to-br from-yellow-200 to-amber-50",
  Accessories: "bg-gradient-to-br from-indigo-200 to-violet-50",
  Activewear: "bg-gradient-to-br from-teal-200 to-emerald-50",
};
const TIER_STYLE: Record<string, string> = {
  Bronze: "from-amber-700 to-amber-500", Silver: "from-slate-400 to-slate-300",
  Gold: "from-yellow-500 to-amber-400", Platinum: "from-cyan-300 to-indigo-300",
};
const OFFER_STYLE: Record<string, string> = {
  discount: "bg-rose-600", bogo: "bg-violet-600", cash: "bg-emerald-600",
  points: "bg-amber-500", bundle: "bg-sky-600",
};

export default function StorePage() {
  const [uid, setUid] = useState("");
  const [products, setProducts] = useState<Product[]>([]);
  const [cats, setCats] = useState<string[]>([]);
  const [promos, setPromos] = useState<Promotions>({ ticker: [], bundles: [], coupons: [], redemptions: [] });
  const [activeCat, setActiveCat] = useState("All");
  const [query, setQuery] = useState("");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [detail, setDetail] = useState<ProductDetail | null>(null);
  const [clipped, setClipped] = useState<Set<string>>(new Set());
  const [rewardsOpen, setRewardsOpen] = useState(false);
  const [phoneOn, setPhoneOn] = useState(false);
  const [phoneSug, setPhoneSug] = useState<any>(null);
  const [resolving, setResolving] = useState(false);
  const [toast, setToast] = useState<{ id: number; msg: string } | null>(null);
  const lastView = useRef<Record<string, number>>({});

  useEffect(() => {
    setUid(getUid());
    store.catalogue().then((d) => { setProducts(d.products); setCats(d.categories); });
    store.promotions().then(setPromos);
  }, []);

  async function send(type: string, product?: Product, dwell_ms = 0) {
    if (!uid) return;
    const res = await store.track({ uid, type, product_id: product?.id, device: "desktop", dwell_ms });
    if (res?.profile) {
      setProfile(res.profile);
      if (res.stored_event?.points_earned > 0) setToast({ id: Date.now(), msg: `+${res.stored_event.points_earned} loyalty points ✨` });
    }
  }

  async function openDetail(p: Product) {
    const now = Date.now();
    const dwell = lastView.current[p.id] ? now - lastView.current[p.id] : 3500;
    lastView.current[p.id] = now;
    send("view_product", p, Math.min(dwell, 12000));
    setDetail(await store.product(p.id));
  }

  const wishIds = new Set((profile?.wishlist ?? []).map((w) => w.id));
  const toggleWish = (p: Product) => send(wishIds.has(p.id) ? "remove_from_wishlist" : "add_to_wishlist", p);

  async function continueOnPhone() {
    setPhoneOn(true); setResolving(true); setPhoneSug(null);
    await new Promise((r) => setTimeout(r, 1000));
    const s = await store.suggestion(uid, "mobile");
    setPhoneSug(s); setResolving(false);
    if (s?.profile) setProfile(s.profile);
  }

  async function redeem(r: Redemption) {
    const res = await store.redeem(uid, r.id);
    if (res?.ok) { setToast({ id: Date.now(), msg: `Redeemed ${r.name} 🎉` }); const v = await store.visitor(uid); if (v?.profile) setProfile(v.profile); }
    else setToast({ id: Date.now(), msg: res?.need ? `Need ${res.need} more points` : "Couldn't redeem" });
  }

  const shown = products.filter((p) =>
    (activeCat === "All" || p.cat === activeCat) &&
    (!query || p.name.toLowerCase().includes(query.toLowerCase())));
  const topCat = profile?.top_product?.cat;
  const recs = topCat ? products.filter((p) => p.cat === topCat && p.id !== profile?.top_product?.id).slice(0, 6) : [];

  return (
    <main className="min-h-screen bg-[#f3f4f6] text-slate-900">
      {/* moving ticker */}
      <div className="bg-slate-900 text-white text-xs overflow-hidden whitespace-nowrap">
        <div className="inline-flex animate-marquee py-1.5">
          {[...promos.ticker, ...promos.ticker].map((t, i) => (
            <span key={i} className="mx-8 inline-flex items-center gap-2"><span style={{ color: "#ff8da1" }}>✦</span>{t}</span>
          ))}
        </div>
      </div>

      {/* header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-[1500px] mx-auto px-5 h-14 flex items-center gap-4">
          <div className="flex items-center gap-2 font-extrabold text-xl tracking-tight" style={{ color: BRAND }}>
            VERVE<span className="text-slate-400 font-normal text-xs ml-1">the style edit</span>
          </div>
          <div className="flex-1 max-w-xl">
            <input value={query} onChange={(e) => setQuery(e.target.value)}
              placeholder="Search dresses, sneakers, bags…"
              className="w-full bg-slate-100 border border-slate-200 rounded-full px-4 py-1.5 text-sm outline-none focus:border-slate-400" />
          </div>
          <div className="flex items-center gap-4 text-sm">
            {profile?.loyalty && <button onClick={() => setRewardsOpen(true)}><RewardsWidget l={profile.loyalty} /></button>}
            <span title="wishlist" className="relative">♡{profile?.wishlist?.length ? <Badge n={profile.wishlist.length} /> : null}</span>
            <span title="cart" className="relative">🛒{profile?.cart?.length ? <Badge n={profile.cart.length} /> : null}</span>
            <Link href="/console" target="_blank" className="text-white text-xs px-2.5 py-1 rounded-md" style={{ background: "#0d1320" }}>● Conductor console</Link>
          </div>
        </div>
        <div className="max-w-[1500px] mx-auto px-5 flex gap-1 overflow-x-auto pb-2">
          {["All", ...cats].map((c) => (
            <button key={c} onClick={() => setActiveCat(c)}
              className={`text-xs whitespace-nowrap px-3 py-1 rounded-full border transition ${activeCat === c ? "text-white border-transparent" : "bg-white text-slate-600 border-slate-200 hover:border-slate-400"}`}
              style={activeCat === c ? { background: BRAND } : {}}>{c}</button>
          ))}
        </div>
      </header>

      <div className="max-w-[1500px] mx-auto px-5 py-5">
        {/* hero */}
        <div className="rounded-2xl p-6 mb-5 text-white flex items-center justify-between" style={{ background: `linear-gradient(110deg, ${BRAND}, #ff6b81)` }}>
          <div>
            <div className="text-xs uppercase tracking-widest opacity-90">New season</div>
            <div className="text-3xl font-extrabold leading-tight">Up to 30% off the summer edit</div>
            <div className="text-sm opacity-90 mt-1">Free express shipping over $50 · Every click personalizes your experience</div>
          </div>
          <div className="text-7xl hidden sm:block">👗</div>
        </div>

        {/* clip coupons */}
        {promos.coupons.length > 0 && (
          <div className="mb-5">
            <div className="text-sm font-bold mb-2">🎟️ Offers just for you <span className="text-xs font-normal text-slate-400">· clip & save at checkout</span></div>
            <div className="flex gap-3 overflow-x-auto pb-1">
              {promos.coupons.map((c) => (
                <div key={c.id} className="min-w-[210px] bg-white border border-dashed border-slate-300 rounded-xl p-3 flex flex-col">
                  <div className="text-2xl font-extrabold" style={{ color: BRAND }}>{c.amount} <span className="text-xs font-semibold text-slate-500">off</span></div>
                  <div className="text-xs text-slate-700 mt-0.5 flex-1">{c.desc}</div>
                  <div className="text-[10px] text-slate-400 mt-1">{c.tag} · expires {c.expires}</div>
                  <button onClick={() => setClipped((s) => new Set(s).add(c.id))}
                    className={`mt-2 text-xs font-semibold rounded-full py-1.5 border transition ${clipped.has(c.id) ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "border-slate-300 hover:border-slate-500"}`}>
                    {clipped.has(c.id) ? "✓ Clipped" : "+ Clip"}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* bundles */}
        {promos.bundles.length > 0 && (
          <div className="mb-5">
            <div className="text-sm font-bold mb-2">🎁 Shop the look — bundle & save</div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {promos.bundles.map((b) => (
                <div key={b.id} className="bg-white border border-slate-200 rounded-xl p-3">
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">{b.emoji}</span>
                    <div className="text-sm font-bold leading-tight">{b.name}</div>
                  </div>
                  <div className="flex gap-1 my-2">
                    {b.products.map((p) => <div key={p.id} className={`w-9 h-9 rounded-md flex items-center justify-center text-lg ${CAT_THEME[p.cat] ?? "bg-slate-100"}`}>{p.emoji}</div>)}
                  </div>
                  <div className="text-[11px] text-slate-500">{b.blurb}</div>
                  <div className="flex items-center justify-between mt-2">
                    <div><span className="font-bold" style={{ color: BRAND }}>${b.price}</span> <span className="text-xs text-slate-400 line-through">${b.total}</span></div>
                    <span className="text-[10px] font-bold text-white px-1.5 py-0.5 rounded bg-emerald-600">SAVE ${b.saves}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* recommendations */}
        {recs.length > 0 && (
          <div className="mb-5 bg-white border border-slate-200 rounded-xl p-3">
            <div className="text-sm font-bold mb-2">✨ Recommended for you <span className="text-xs font-normal text-slate-400">· because you viewed {profile?.top_product?.name}</span></div>
            <div className="flex gap-3 overflow-x-auto pb-1">
              {recs.map((p) => (
                <div key={p.id} onClick={() => openDetail(p)} className="min-w-[120px] cursor-pointer">
                  <div className="w-[120px]"><ProductImage p={p} /></div>
                  <div className="text-xs font-semibold mt-1 line-clamp-1">{p.name}</div>
                  <div className="text-xs font-bold" style={{ color: BRAND }}>${p.sale_price ?? p.price}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* product grid */}
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-lg font-bold">{activeCat === "All" ? "Trending now" : activeCat}</h2>
            <p className="text-xs text-slate-500">{shown.length} items · click to view details & reviews</p>
          </div>
          <button onClick={continueOnPhone} className="text-sm font-semibold text-white px-3.5 py-2 rounded-lg shadow-sm hover:opacity-90" style={{ background: BRAND }}>Continue on phone 📱</button>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {shown.map((p) => (
            <ProductCard key={p.id} p={p} wished={wishIds.has(p.id)} onOpen={() => openDetail(p)} onWish={() => toggleWish(p)} onAdd={() => send("add_to_cart", p)} />
          ))}
        </div>

        {profile?.cart?.length ? (
          <div className="mt-4 flex items-center justify-between bg-white border border-slate-200 rounded-xl px-4 py-2.5">
            <span className="text-sm text-slate-600">Cart: {profile.cart.map((c) => c.emoji).join(" ")}</span>
            <button onClick={() => send("checkout")} className="text-sm font-semibold text-white px-3 py-1.5 rounded-lg" style={{ background: "#16a34a" }}>
              Checkout ${profile.cart.reduce((s, c) => s + (c.sale_price ?? c.price), 0).toFixed(2)}
            </button>
          </div>
        ) : null}
      </div>

      {detail && <ProductModal d={detail} wished={wishIds.has(detail.id)} onClose={() => setDetail(null)} onAdd={() => send("add_to_cart", detail)} onWish={() => toggleWish(detail)} onReadReviews={() => send("view_reviews", detail)} />}
      {rewardsOpen && profile?.loyalty && <RewardsModal l={profile.loyalty} redemptions={promos.redemptions} onClose={() => setRewardsOpen(false)} onRedeem={redeem} />}
      {phoneOn && <PhoneOverlay onClose={() => setPhoneOn(false)} resolving={resolving} sug={phoneSug} />}
      {toast && <Toast key={toast.id} msg={toast.msg} onDone={() => setToast(null)} />}
    </main>
  );
}

/* ---------- image with graceful fallback ---------- */
function ProductImage({ p, big }: { p: Product; big?: boolean }) {
  const [failed, setFailed] = useState(false);
  return (
    <div className={`relative ${CAT_THEME[p.cat] ?? "bg-slate-100"} rounded-xl overflow-hidden ${big ? "w-full aspect-square" : "aspect-square"}`}>
      {p.img && !failed ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={p.img} alt={p.name} onError={() => setFailed(true)} loading="lazy"
          className="absolute inset-0 w-full h-full object-cover" />
      ) : (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="absolute inset-0 opacity-40" style={{ background: "radial-gradient(120px 80px at 30% 25%, #fff, transparent)" }} />
          <span className={big ? "text-[120px]" : "text-5xl"} style={{ filter: "drop-shadow(0 6px 10px rgba(0,0,0,.15))" }}>{p.emoji}</span>
        </div>
      )}
    </div>
  );
}

function Badge({ n }: { n: number }) {
  return <span className="absolute -top-2 -right-2 text-[10px] text-white rounded-full w-4 h-4 flex items-center justify-center" style={{ background: BRAND }}>{n}</span>;
}

const BADGE_STYLE: Record<string, string> = {
  "Best Seller": "bg-amber-100 text-amber-700", Sale: "bg-rose-100 text-rose-700",
  New: "bg-sky-100 text-sky-700", "Staff Pick": "bg-violet-100 text-violet-700",
};

function ProductCard({ p, wished, onOpen, onWish, onAdd }: { p: Product; wished: boolean; onOpen: () => void; onWish: () => void; onAdd: () => void; }) {
  const onSale = p.discount_pct && p.discount_pct > 0;
  return (
    <div onClick={onOpen} className="group relative bg-white border border-slate-200 rounded-xl p-3 cursor-pointer hover:shadow-lg hover:border-slate-300 transition">
      <span className={`absolute top-2 left-2 z-10 text-[10px] font-bold text-white px-1.5 py-0.5 rounded ${OFFER_STYLE[p.offer_kind ?? "discount"]}`}>{p.offer}</span>
      <button onClick={(e) => { e.stopPropagation(); onWish(); }} className="absolute top-2 right-2 z-10 text-lg leading-none transition" style={{ color: wished ? BRAND : "#94a3b8" }}>{wished ? "♥" : "♡"}</button>
      <div className="group-hover:scale-[1.03] transition"><ProductImage p={p} /></div>
      <div className="text-sm font-semibold text-slate-800 mt-2 leading-tight line-clamp-1">{p.name}</div>
      <div className="text-[11px] text-amber-500">{stars(p.rating ?? 4.5)} <span className="text-slate-400">({p.reviews_count})</span></div>
      <div className="flex items-center justify-between mt-1.5">
        <div className="flex items-baseline gap-1.5">
          <span className="font-bold text-slate-900">${onSale ? p.sale_price : p.price}</span>
          {onSale && <span className="text-[11px] text-slate-400 line-through">${p.list_price}</span>}
        </div>
        <button onClick={(e) => { e.stopPropagation(); onAdd(); }} className="text-[11px] font-semibold text-white px-2.5 py-1 rounded-md hover:opacity-90" style={{ background: BRAND }}>Add</button>
      </div>
    </div>
  );
}

function ProductModal({ d, wished, onClose, onAdd, onWish, onReadReviews }: { d: ProductDetail; wished: boolean; onClose: () => void; onAdd: () => void; onWish: () => void; onReadReviews: () => void; }) {
  const [added, setAdded] = useState(false);
  const reviewsRef = useRef<HTMLDivElement>(null);
  const total = Object.values(d.rating_breakdown).reduce((a, b) => a + b, 0) || 1;
  const onSale = d.discount_pct && d.discount_pct > 0;
  return (
    <div className="fixed inset-0 z-40 bg-black/50 flex items-start justify-center overflow-auto py-8" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="bg-white rounded-2xl w-[min(880px,94vw)] shadow-2xl overflow-hidden">
        <div className="grid md:grid-cols-2">
          <div className="p-6 flex flex-col items-center justify-center">
            <div className="w-full max-w-[300px]"><ProductImage p={d} big /></div>
          </div>
          <div className="p-6">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400">{d.cat}</span>
              <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-lg">✕</button>
            </div>
            <span className={`inline-block mt-1 text-[10px] font-bold text-white px-1.5 py-0.5 rounded ${OFFER_STYLE[d.offer_kind ?? "discount"]}`}>{d.offer}</span>
            <h2 className="text-xl font-bold text-slate-900 mt-1">{d.name}</h2>
            <button onClick={() => { onReadReviews(); reviewsRef.current?.scrollIntoView({ behavior: "smooth" }); }} className="text-sm text-amber-500 mt-1 hover:underline">{stars(d.rating ?? 4.5)} <span className="text-slate-500">{d.rating} · {d.reviews_count} reviews</span></button>
            <div className="flex items-baseline gap-2 mt-3">
              <span className="text-2xl font-extrabold" style={{ color: BRAND }}>${onSale ? d.sale_price : d.price}</span>
              {onSale && <><span className="text-slate-400 line-through">${d.list_price}</span><span className="text-xs font-semibold text-rose-600">{d.discount_pct}% off</span></>}
            </div>
            {typeof d.stock === "number" && d.stock < 20 && <div className="text-xs text-rose-600 mt-1">Only {d.stock} left — order soon</div>}
            <p className="text-sm text-slate-600 mt-3 leading-relaxed">{d.description}</p>
            <div className="flex gap-2 mt-5">
              <button onClick={() => { onAdd(); setAdded(true); setTimeout(() => setAdded(false), 1200); }} className="flex-1 text-white font-semibold rounded-lg py-2.5 hover:opacity-90" style={{ background: BRAND }}>{added ? "Added ✓" : "Add to cart"}</button>
              <button onClick={onWish} className="px-4 rounded-lg border border-slate-300 hover:bg-slate-50" style={{ color: wished ? BRAND : "#475569" }}>{wished ? "♥" : "♡"}</button>
            </div>
            <div className="text-[11px] text-slate-400 mt-3 flex gap-4"><span>🚚 Free shipping over $50</span><span>↩ 30-day returns</span><span>🔒 Secure checkout</span></div>
          </div>
        </div>
        <div ref={reviewsRef} className="border-t border-slate-200 p-6">
          <h3 className="font-bold text-slate-900 mb-3">Customer reviews</h3>
          <div className="grid md:grid-cols-[200px_1fr] gap-6">
            <div>
              <div className="text-4xl font-extrabold">{d.rating}</div>
              <div className="text-amber-500">{stars(d.rating ?? 4.5)}</div>
              <div className="text-xs text-slate-500 mb-3">{d.reviews_count} global ratings</div>
              {["5", "4", "3", "2", "1"].map((s) => (
                <div key={s} className="flex items-center gap-2 text-[11px] text-slate-500">
                  <span className="w-6">{s}★</span>
                  <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden"><div className="h-full bg-amber-400" style={{ width: `${(d.rating_breakdown[s] / total) * 100}%` }} /></div>
                </div>
              ))}
            </div>
            <div className="space-y-4">{d.reviews.map((r, i) => <ReviewItem key={i} r={r} />)}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ReviewItem({ r }: { r: Review }) {
  return (
    <div className="border-b border-slate-100 pb-3">
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-full bg-slate-200 flex items-center justify-center text-xs font-bold text-slate-600">{r.author[0]}</div>
        <span className="text-sm font-semibold text-slate-800">{r.author}</span>
        {r.verified && <span className="text-[10px] text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">✓ Verified</span>}
      </div>
      <div className="text-amber-500 text-xs mt-1">{stars(r.rating)} <span className="text-slate-800 font-semibold ml-1">{r.title}</span></div>
      <p className="text-sm text-slate-600 mt-1">{r.text}</p>
      <div className="text-[11px] text-slate-400 mt-1">{r.date} · {r.helpful} found this helpful</div>
    </div>
  );
}

function RewardsWidget({ l }: { l: Loyalty }) {
  return (
    <div className="hidden sm:flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-full pl-1 pr-3 py-1 hover:border-slate-400 transition">
      <span className={`text-[10px] font-bold text-white px-2 py-0.5 rounded-full bg-gradient-to-r ${TIER_STYLE[l.tier] ?? "from-slate-400 to-slate-300"}`}>{l.tier}</span>
      <div className="leading-tight text-left">
        <div className="text-xs font-bold tabular-nums">{l.points} pts <span className="text-slate-400 font-normal">· ${l.dollar_value}</span></div>
        <div className="w-24 h-1 bg-slate-200 rounded-full overflow-hidden mt-0.5"><div className="h-full" style={{ width: `${l.progress_pct}%`, background: BRAND }} /></div>
      </div>
    </div>
  );
}

function RewardsModal({ l, redemptions, onClose, onRedeem }: { l: Loyalty; redemptions: Redemption[]; onClose: () => void; onRedeem: (r: Redemption) => void; }) {
  return (
    <div className="fixed inset-0 z-40 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="bg-white rounded-2xl w-[min(560px,95vw)] shadow-2xl overflow-hidden">
        <div className="p-5 text-white" style={{ background: `linear-gradient(110deg, ${BRAND}, #ff6b81)` }}>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs uppercase tracking-widest opacity-90">myVERVE Rewards</div>
              <div className="text-3xl font-extrabold">{l.points} <span className="text-base font-semibold opacity-90">points</span></div>
              <div className="text-sm opacity-90">{l.tier} member · ${l.dollar_value} value · {l.to_next} pts to {l.next_tier}</div>
            </div>
            <button onClick={onClose} className="text-white/80 hover:text-white text-lg">✕</button>
          </div>
        </div>
        <div className="p-5 max-h-[60vh] overflow-auto">
          <div className="text-sm font-bold mb-2">Redeem your points</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {redemptions.map((r) => {
              const ok = l.points >= r.cost;
              return (
                <div key={r.id} className="flex items-center gap-3 border border-slate-200 rounded-xl p-3">
                  <div className="text-2xl">{r.icon}</div>
                  <div className="flex-1">
                    <div className="text-sm font-semibold leading-tight">{r.name}</div>
                    <div className="text-[11px] text-slate-400">{r.partner !== "aura" ? `${r.partner} · ` : ""}{r.cost} pts</div>
                  </div>
                  <button onClick={() => ok && onRedeem(r)} disabled={!ok}
                    className={`text-xs font-semibold px-3 py-1.5 rounded-lg ${ok ? "text-white" : "bg-slate-100 text-slate-400"}`} style={ok ? { background: BRAND } : {}}>
                    {ok ? "Redeem" : "Locked"}
                  </button>
                </div>
              );
            })}
          </div>
          <div className="text-[11px] text-slate-400 mt-3">Earn points on every browse, wishlist & purchase. Use them here or at checkout.</div>
        </div>
      </div>
    </div>
  );
}

function PhoneOverlay({ onClose, resolving, sug }: { onClose: () => void; resolving: boolean; sug: any }) {
  const nba = sug?.next_best_action;
  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="w-[320px] h-[640px] rounded-[2.6rem] border-[11px] border-[#0d1320] bg-[#0d1320] shadow-2xl overflow-hidden relative">
        <div className="h-7 bg-[#0d1320] flex items-center justify-center"><div className="w-24 h-4 bg-black rounded-full" /></div>
        {resolving ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-300"><div className="animate-pulse text-lg">🔗 Resolving identity…</div><div className="text-xs text-slate-500 mt-2">matching this device to a known shopper</div></div>
        ) : (
          <div className="p-4 space-y-3 bg-[#f3f4f6] h-full text-slate-900">
            {sug?.identity_resolved && <div className="text-[11px] text-emerald-700 bg-emerald-100 border border-emerald-200 rounded-lg px-2 py-1">✓ Same shopper recognized · {sug.devices?.join(" → ")}</div>}
            <div className="text-sm font-extrabold" style={{ color: BRAND }}>VERVE</div>
            {nba?.recommend ? (
              <div className="bg-white border rounded-2xl p-4 shadow-sm" style={{ borderColor: BRAND + "55" }}>
                {nba.product && <div className="text-5xl mb-2">{nba.product.emoji}</div>}
                <div className="text-base font-bold leading-snug">{nba.headline}</div>
                <div className="text-sm text-slate-600 mt-1.5">{nba.message}</div>
                {nba.offer_pct && <button className="mt-3 w-full text-white font-semibold rounded-xl py-2 text-sm" style={{ background: BRAND }}>Claim {nba.offer_pct}% off →</button>}
                <div className="text-[10px] text-slate-400 mt-2">delivered via {nba.channel} · the right moment</div>
              </div>
            ) : (
              <div className="bg-white border border-slate-200 rounded-2xl p-4"><div className="text-base font-bold">{nba?.headline}</div><div className="text-sm text-slate-600 mt-1.5">{nba?.message}</div><div className="text-[10px] text-slate-400 mt-2">Conductor chose restraint — no spend here.</div></div>
            )}
            <button onClick={onClose} className="text-xs text-slate-400 w-full mt-2">close</button>
          </div>
        )}
      </div>
    </div>
  );
}

function Toast({ msg, onDone }: { msg: string; onDone: () => void }) {
  useEffect(() => { const t = setTimeout(onDone, 1700); return () => clearTimeout(t); }, [onDone]);
  return <div className="fixed bottom-6 right-6 z-[60] animate-bounce"><div className="text-white font-bold px-4 py-2 rounded-full shadow-lg" style={{ background: BRAND }}>{msg}</div></div>;
}

function stars(r: number) {
  const full = Math.round(r);
  return "★★★★★".slice(0, full) + "☆☆☆☆☆".slice(0, 5 - full);
}
