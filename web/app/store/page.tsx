"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  store, getUid, getSession, logout, setConsent, loginUser, popMerge, getGuestUid, MergeInfo,
  Session, Product, ProductDetail, Review, Bundle,
  Coupon, Redemption, Promotions, Bundle2, InboxMail, Order,
} from "@/lib/api";
import { ChatBot } from "@/components/chatbot";

type Loyalty = {
  points: number; tier: string; next_tier: string; to_next: number;
  progress_pct: number; dollar_value: number;
};
type Profile = {
  segment: string; intent: string; intent_score: number; total_views: number;
  top_product: Product | null; top_views: number; cart: Product[]; wishlist: Product[];
  devices: string[]; events: number; dwell_s: number; loyalty: Loyalty; consent?: boolean;
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
  const [bundle, setBundle] = useState<Bundle2 | null>(null);
  const [inbox, setInbox] = useState<InboxMail[]>([]);
  const [inboxOpen, setInboxOpen] = useState(false);
  const [seenInbox, setSeenInbox] = useState(0);
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [order, setOrder] = useState<Order | null>(null);
  const [activeDevice, setActiveDevice] = useState<"desktop" | "mobile">("desktop");
  const [ended, setEnded] = useState(false);
  const [me, setMe] = useState<Session | null>(null);
  const [mergeInfo, setMergeInfo] = useState<MergeInfo | null>(null);
  const [signInOpen, setSignInOpen] = useState(false);
  const lastView = useRef<Record<string, number>>({});
  const router = useRouter();

  useEffect(() => {
    // Anonymous browsing is allowed — identity resolves on sign-in (CORE ID stitch).
    setMe(getSession());
    setUid(getUid());
    const mg = popMerge();           // a merge that happened on the login page
    if (mg) setMergeInfo(mg);
    store.catalogue().then((d) => { setProducts(d.products); setCats(d.categories); });
    store.promotions().then(setPromos);
  }, []);

  async function signIn(email: string, name: string) {
    const s = await loginUser(email.trim(), name.trim(), getGuestUid());
    const mg = popMerge();
    setMe(s);
    setUid(s.core_id);               // future activity is keyed to the CORE ID
    setSignInOpen(false);
    if (mg?.merged) setMergeInfo(mg);
    else setToast({ id: Date.now(), msg: `Welcome, ${s.name} ✓` });
  }

  useEffect(() => {
    if (!uid || !products.length) return;
    const pid = new URLSearchParams(window.location.search).get("p");
    if (pid) {
      const p = products.find((x) => x.id === pid);
      if (p) openDetail(p);
      window.history.replaceState({}, "", "/store");
    }

  }, [uid, products]);

  // Live inbox: signed-in shoppers see marketer-sent messages arrive without a refresh.
  useEffect(() => {
    if (!uid || !me) return;
    const poll = () => store.inbox(uid).then((r) => r?.inbox && setInbox(r.inbox));
    const t = setInterval(poll, 4000);
    return () => clearInterval(t);
  }, [uid, me]);

  function absorb(res: any) {
    if (!res) return;
    if (res.profile) setProfile(res.profile);
    if ("bundle" in res) setBundle(res.bundle);
    if (res.inbox) setInbox(res.inbox);
    if (res.stored_event?.points_earned > 0)
      setToast({ id: Date.now(), msg: `+${res.stored_event.points_earned} loyalty points ✨` });
  }

  async function send(type: string, product?: Product, dwell_ms = 0, device: "desktop" | "mobile" = activeDevice) {
    if (!uid) return;
    if (ended) setEnded(false);
    absorb(await store.track({ uid, type, product_id: product?.id, device, dwell_ms }));
  }

  async function openDetail(p: Product, device: "desktop" | "mobile" = "desktop") {
    setActiveDevice(device);
    const now = Date.now();
    const dwell = lastView.current[p.id] ? now - lastView.current[p.id] : 3500;
    lastView.current[p.id] = now;
    send("view_product", p, Math.min(dwell, 12000), device);
    setDetail(await store.product(p.id));
  }

  async function endSession() {
    const res = await store.sessionEnd(uid, activeDevice);
    setEnded(true);
    if (res?.inbox) setInbox(res.inbox);
    if (res?.delivered) {
      setToast({ id: Date.now(), msg: "📧 You left — Kairos sent 1 targeted message" });
    } else {
      setToast({ id: Date.now(), msg: "👋 Session ended — Kairos stayed silent (no spend warranted)" });
    }
  }

  function openCheckout() {
    send("checkout_start");
    setCheckoutOpen(true);
  }

  async function placeOrder(applyPoints: boolean) {
    const pts = applyPoints ? (profile?.loyalty?.points ?? 0) : 0;
    const res = await store.purchase(uid, pts);
    if (res?.ok) {
      setOrder(res.order);
      setCheckoutOpen(false);
      const v = await store.visitor(uid);
      absorb(v);
      setToast({ id: Date.now(), msg: `Order placed · +${res.order.points_earned} pts 🎉` });
    } else {
      setToast({ id: Date.now(), msg: res?.error ?? "Checkout failed" });
    }
  }

  async function addBundleToCart() {
    if (!bundle) return;
    for (const bp of bundle.products) {
      const p = products.find((x) => x.id === bp.id);
      if (p && !(profile?.cart ?? []).some((c) => c.id === p.id)) await send("add_to_cart", p);
    }
    setToast({ id: Date.now(), msg: `Bundle added · saved $${bundle.saves} 🎁` });
  }

  async function openInbox() {
    const r = await store.inbox(uid);
    if (r?.inbox) setInbox(r.inbox);
    setInboxOpen(true);
    setSeenInbox(r?.inbox?.length ?? inbox.length);
  }

  function openFromMail(m: InboxMail) {
    setInboxOpen(false);
    const p = m.product && products.find((x) => x.id === m.product!.id);
    if (p) openDetail(p);
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

      <div className="bg-slate-900 text-white text-xs overflow-hidden whitespace-nowrap">
        <div className="inline-flex animate-marquee py-1.5">
          {[...promos.ticker, ...promos.ticker].map((t, i) => (
            <span key={i} className="mx-8 inline-flex items-center gap-2"><span style={{ color: "#ff8da1" }}>✦</span>{t}</span>
          ))}
        </div>
      </div>

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
            <button title="inbox" onClick={openInbox} className="relative hover:scale-110 transition">📧{inbox.length - seenInbox > 0 ? <Badge n={inbox.length - seenInbox} /> : null}</button>
            <span title="wishlist" className="relative">♡{profile?.wishlist?.length ? <Badge n={profile.wishlist.length} /> : null}</span>
            <button title="cart" onClick={() => profile?.cart?.length && openCheckout()} className="relative hover:scale-110 transition">🛒{profile?.cart?.length ? <Badge n={profile.cart.length} /> : null}</button>
            {me && (
              <div className="flex items-center gap-2 pl-1">
                <div className="text-right leading-tight hidden sm:block">
                  <div className="text-xs font-semibold text-slate-700">{me.name}</div>
                  <div className="text-[9px] text-slate-400 font-mono">{me.core_id}</div>
                </div>
                <button
                  onClick={async () => {
                    const nv = !(profile?.consent ?? true);
                    await setConsent(uid, nv);
                    const v = await store.visitor(uid);
                    if (v?.profile) setProfile(v.profile);
                  }}
                  title="Personalisation consent (privacy-safe CORE ID)"
                  className={`text-[10px] px-2 py-1 rounded-md border ${(profile?.consent ?? true) ? "border-emerald-300 text-emerald-600" : "border-amber-400 text-amber-600"}`}>
                  {(profile?.consent ?? true) ? "Personalisation: On" : "Personalisation: Off"}
                </button>
                <Link href="/console" target="_blank" className="text-xs text-white px-2.5 py-1 rounded-md hover:opacity-90" style={{ background: "#0d1320" }}>● Console</Link>
                <button onClick={() => { logout(); router.replace("/"); }}
                  className="text-xs text-slate-500 border border-slate-200 rounded-md px-2 py-1 hover:bg-slate-100">Sign out</button>
              </div>
            )}
            {!me && (
              <div className="flex items-center gap-2 pl-1">
                <span className="text-[11px] text-slate-400 hidden sm:inline">👤 Guest</span>
                <button onClick={() => setSignInOpen(true)}
                  className="text-xs text-white px-3 py-1.5 rounded-md hover:opacity-90" style={{ background: BRAND }}>Sign in</button>
              </div>
            )}
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

      {!me && (
        <div className="bg-amber-50 border-b border-amber-200 text-amber-900 text-xs">
          <div className="max-w-[1500px] mx-auto px-5 py-2 flex items-center justify-between gap-3">
            <span>👤 You&apos;re browsing as a guest — we&apos;re tracking this session anonymously. <b>Sign in</b> and we&apos;ll unify it with your CORE&nbsp;ID across every device.</span>
            <button onClick={() => setSignInOpen(true)} className="text-white px-3 py-1 rounded-md shrink-0" style={{ background: BRAND }}>Sign in to unify →</button>
          </div>
        </div>
      )}

      <div className="max-w-[1500px] mx-auto px-5 py-5">

        <div className="rounded-2xl p-6 mb-5 text-white flex items-center justify-between" style={{ background: `linear-gradient(110deg, ${BRAND}, #ff6b81)` }}>
          <div>
            <div className="text-xs uppercase tracking-widest opacity-90">New season</div>
            <div className="text-3xl font-extrabold leading-tight">Up to 30% off the summer edit</div>
            <div className="text-sm opacity-90 mt-1">Free express shipping over $50 · Every click personalizes your experience</div>
          </div>
          <div className="text-7xl hidden sm:block">👗</div>
        </div>

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

        {bundle && (
          <div className="mb-5 rounded-2xl p-4 border-2 border-dashed" style={{ borderColor: BRAND + "66", background: "linear-gradient(110deg,#fff,#fff5f6)" }}>
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div>
                <div className="text-sm font-bold flex items-center gap-2">
                  🎁 Kairos assembled a bundle for you
                  <span className="text-[10px] font-semibold text-white px-2 py-0.5 rounded-full" style={{ background: BRAND }}>{bundle.discount_pct}% OFF</span>
                </div>
                <div className="flex items-center gap-2 mt-2">
                  {bundle.products.map((p) => (
                    <div key={p.id} className="w-11 h-11 rounded-lg bg-white border border-slate-200 flex items-center justify-center text-xl">{p.emoji}</div>
                  ))}
                  <div className="ml-2 text-sm">
                    <span className="font-extrabold" style={{ color: BRAND }}>${bundle.price}</span>{" "}
                    <span className="text-xs text-slate-400 line-through">${bundle.total}</span>{" "}
                    <span className="text-xs font-bold text-emerald-600">save ${bundle.saves}</span>
                  </div>
                </div>
                <div className="text-[11px] text-slate-500 mt-1.5 max-w-xl">🧠 {bundle.rationale}</div>
              </div>
              <button onClick={addBundleToCart} className="text-sm font-semibold text-white px-4 py-2.5 rounded-lg shadow-sm hover:opacity-90" style={{ background: BRAND }}>Add bundle to cart →</button>
            </div>
          </div>
        )}

        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-lg font-bold">{activeCat === "All" ? "Trending now" : activeCat}</h2>
            <p className="text-xs text-slate-500">{shown.length} items · click to view details & reviews</p>
          </div>
          <div className="flex gap-2">
            <button onClick={continueOnPhone} className="text-sm font-semibold text-white px-3.5 py-2 rounded-lg shadow-sm hover:opacity-90" style={{ background: BRAND }}>Continue on phone 📱</button>
            <button onClick={endSession} title="Leave the site — marketing only makes sense once you've left"
              className="text-sm font-semibold px-3.5 py-2 rounded-lg border border-slate-300 hover:bg-slate-50">Leave site 🚪</button>
          </div>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {shown.map((p) => (
            <ProductCard key={p.id} p={p} wished={wishIds.has(p.id)} onOpen={() => openDetail(p)} onWish={() => toggleWish(p)} onAdd={() => send("add_to_cart", p)} />
          ))}
        </div>

        {profile?.cart?.length ? (
          <div className="mt-4 flex items-center justify-between bg-white border border-slate-200 rounded-xl px-4 py-2.5">
            <span className="text-sm text-slate-600">Cart: {profile.cart.map((c) => c.emoji).join(" ")}</span>
            <button onClick={openCheckout} className="text-sm font-semibold text-white px-3 py-1.5 rounded-lg" style={{ background: "#16a34a" }}>
              Checkout ${profile.cart.reduce((s, c) => s + (c.sale_price ?? c.price), 0).toFixed(2)}
            </button>
          </div>
        ) : null}
      </div>

      {detail && <ProductModal d={detail} wished={wishIds.has(detail.id)} onClose={() => setDetail(null)} onAdd={() => send("add_to_cart", detail)} onWish={() => toggleWish(detail)} onReadReviews={() => send("view_reviews", detail)} onViewAllReviews={() => send("view_all_reviews", detail)} onSizeGuide={() => send("view_size_guide", detail)} />}
      {rewardsOpen && profile?.loyalty && <RewardsModal l={profile.loyalty} redemptions={promos.redemptions} onClose={() => setRewardsOpen(false)} onRedeem={redeem} />}
      {checkoutOpen && profile && <CheckoutModal cart={profile.cart} loyalty={profile.loyalty} onClose={() => setCheckoutOpen(false)} onRemove={(p) => send("remove_from_cart", p)} onPlace={placeOrder} />}
      {order && <OrderConfirmation order={order} onClose={() => setOrder(null)} />}
      {inboxOpen && <InboxModal mails={inbox} onClose={() => setInboxOpen(false)} onOpenProduct={openFromMail} />}
      {phoneOn && <PhoneStore onClose={() => setPhoneOn(false)} resolving={resolving} sug={phoneSug}
        products={products} cats={cats} profile={profile} wishIds={wishIds}
        phoneSend={(type: string, p?: Product) => send(type, p, 0, "mobile")}
        onCheckout={() => { setActiveDevice("mobile"); openCheckout(); }}
        onEndSession={() => { setActiveDevice("mobile"); endSession(); }} />}
      {toast && <Toast key={toast.id} msg={toast.msg} onDone={() => setToast(null)} />}
      {signInOpen && <SignInModal onClose={() => setSignInOpen(false)} onSignIn={signIn} />}
      {mergeInfo && <MergeModal m={mergeInfo} name={me?.name} coreId={me?.core_id} onClose={() => setMergeInfo(null)} />}
      {uid && <ChatBot uid={uid} onProduct={(p) => openDetail(p)} />}
    </main>
  );
}

function SignInModal({ onClose, onSignIn }: { onClose: () => void; onSignIn: (email: string, name: string) => Promise<void> }) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setErr(""); setLoading(true);
    try { await onSignIn(email, name); }
    catch (x: any) { setErr(x?.message || "Sign in failed"); setLoading(false); }
  }
  return (
    <div className="fixed inset-0 z-[70] bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <form onClick={(e) => e.stopPropagation()} onSubmit={submit} className="bg-white rounded-2xl w-[min(420px,95vw)] shadow-2xl p-6">
        <div className="flex items-center justify-between">
          <div className="font-extrabold text-xl" style={{ color: BRAND }}>VERVE</div>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-700">✕</button>
        </div>
        <h2 className="text-lg font-bold mt-3">Sign in to unify your CORE&nbsp;ID</h2>
        <p className="text-xs text-slate-500 mt-1">We&apos;ll recognise you and merge this guest session with your activity across every device.</p>
        <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com"
          className="w-full bg-slate-100 border border-slate-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-slate-400 mt-4" />
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name (optional)"
          className="w-full bg-slate-100 border border-slate-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-slate-400 mt-3" />
        {err && <div className="text-xs text-rose-600 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2 mt-3">{err}</div>}
        <button type="submit" disabled={loading} className="w-full text-white font-semibold rounded-xl py-2.5 mt-4 hover:opacity-90 disabled:opacity-50" style={{ background: BRAND }}>
          {loading ? "Resolving identity…" : "Continue →"}
        </button>
        <p className="text-[10px] text-slate-400 mt-3 text-center">No password — your email becomes a privacy-safe CORE&nbsp;ID.</p>
      </form>
    </div>
  );
}

function MergeModal({ m, name, coreId, onClose }: { m: MergeInfo; name?: string; coreId?: string; onClose: () => void }) {
  const devs = (m.devices ?? []).join(" + ") || "this device";
  return (
    <div className="fixed inset-0 z-[80] bg-black/60 flex items-center justify-center p-4" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="bg-white rounded-2xl w-[min(460px,95vw)] shadow-2xl overflow-hidden">
        <div className="p-6 text-white text-center" style={{ background: "linear-gradient(120deg,#0d1320,#3b1d2a)" }}>
          <div className="text-5xl mb-1">🔗</div>
          <div className="text-xl font-extrabold">Welcome back{name ? `, ${name}` : ""}</div>
          <div className="text-sm opacity-90 mt-1">Identity resolved — one person, unified.</div>
        </div>
        <div className="p-5">
          <p className="text-sm text-slate-700 leading-relaxed">
            We recognised you and unified <b>{m.events ?? 0} guest events</b> across <b>{devs}</b>
            {m.sessions ? <> and <b>{m.sessions} session{m.sessions === 1 ? "" : "s"}</b></> : null} into your CORE&nbsp;ID.
          </p>
          <div className="grid grid-cols-3 gap-2 mt-4 text-center">
            <Stat2 k="Sessions" v={`${m.total_sessions ?? m.sessions ?? 1}`} />
            <Stat2 k="Events" v={`${m.total_events ?? m.events ?? 0}`} />
            <Stat2 k="Signals" v={`${m.signal_count ?? 0}`} />
          </div>
          {coreId && <div className="text-center text-[11px] text-slate-400 font-mono mt-3">{coreId}</div>}
          <button onClick={onClose} className="w-full text-white font-semibold rounded-xl py-2.5 mt-4 hover:opacity-90" style={{ background: BRAND }}>Continue shopping</button>
          <div className="text-[10px] text-slate-400 text-center mt-2">This is CORE ID identity resolution — your full journey, stitched into one profile.</div>
        </div>
      </div>
    </div>
  );
}

function Stat2({ k, v }: { k: string; v: string }) {
  return (
    <div className="bg-slate-50 border border-slate-200 rounded-xl py-2">
      <div className="text-xl font-extrabold tabular-nums" style={{ color: BRAND }}>{v}</div>
      <div className="text-[9px] uppercase tracking-wider text-slate-400">{k}</div>
    </div>
  );
}

function ProductImage({ p, big }: { p: Product; big?: boolean }) {
  const [failed, setFailed] = useState(false);
  return (
    <div className={`relative ${CAT_THEME[p.cat] ?? "bg-slate-100"} rounded-xl overflow-hidden ${big ? "w-full aspect-square" : "aspect-square"}`}>
      {p.img && !failed ? (

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

function ProductModal({ d, wished, onClose, onAdd, onWish, onReadReviews, onViewAllReviews, onSizeGuide }: { d: ProductDetail; wished: boolean; onClose: () => void; onAdd: () => void; onWish: () => void; onReadReviews: () => void; onViewAllReviews: () => void; onSizeGuide: () => void; }) {
  const [added, setAdded] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const reviewsRef = useRef<HTMLDivElement>(null);
  const total = Object.values(d.rating_breakdown).reduce((a, b) => a + b, 0) || 1;
  const onSale = d.discount_pct && d.discount_pct > 0;

  const topReviews = d.reviews.slice(0, 2);
  const shownReviews = showAll ? d.reviews : topReviews;
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
            <div className="flex gap-3 mt-3 text-xs">
              <button onClick={onSizeGuide} className="text-slate-600 hover:text-slate-900 underline decoration-dotted">📏 Size guide</button>
              <button onClick={onReadReviews} className="text-slate-600 hover:text-slate-900 underline decoration-dotted">💬 What buyers say</button>
            </div>
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
            <div className="space-y-4">
              {shownReviews.map((r, i) => <ReviewItem key={i} r={r} />)}
              {!showAll && d.reviews.length > topReviews.length && (
                <button onClick={() => { setShowAll(true); onViewAllReviews(); }}
                  className="text-sm font-semibold w-full border border-slate-300 rounded-lg py-2 hover:bg-slate-50" style={{ color: BRAND }}>
                  View all {d.reviews_count ?? d.reviews.length} reviews ↓
                </button>
              )}
            </div>
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

function CheckoutModal({ cart, loyalty, onClose, onRemove, onPlace }: { cart: Product[]; loyalty: Loyalty; onClose: () => void; onRemove: (p: Product) => void; onPlace: (applyPoints: boolean) => void; }) {
  const [applyPoints, setApplyPoints] = useState(false);
  const [placing, setPlacing] = useState(false);
  const subtotal = cart.reduce((s, c) => s + (c.sale_price ?? c.price), 0);
  const listTotal = cart.reduce((s, c) => s + (c.list_price ?? c.price), 0);
  const saved = listTotal - subtotal;
  const ptsValue = applyPoints ? Math.min(loyalty.dollar_value, subtotal) : 0;
  const total = Math.max(0, subtotal - ptsValue);
  return (
    <div className="fixed inset-0 z-[60] bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="bg-white rounded-2xl w-[min(560px,95vw)] shadow-2xl overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
          <div className="font-bold text-lg">Your bag · {cart.length} item{cart.length === 1 ? "" : "s"}</div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-lg">✕</button>
        </div>
        <div className="p-5 max-h-[44vh] overflow-auto space-y-2">
          {cart.length === 0 ? <div className="text-sm text-slate-500 py-6 text-center">Your bag is empty.</div> :
            cart.map((c) => (
              <div key={c.id} className="flex items-center gap-3 border border-slate-100 rounded-xl p-2">
                <div className={`w-11 h-11 rounded-lg flex items-center justify-center text-xl ${CAT_THEME[c.cat] ?? "bg-slate-100"}`}>{c.emoji}</div>
                <div className="flex-1"><div className="text-sm font-semibold leading-tight">{c.name}</div><div className="text-xs text-slate-400">{c.cat}</div></div>
                <div className="text-sm font-bold">${(c.sale_price ?? c.price).toFixed(2)}</div>
                <button onClick={() => onRemove(c)} className="text-slate-300 hover:text-rose-500 text-sm">✕</button>
              </div>
            ))}
        </div>
        <div className="px-5 pb-5 space-y-1.5">
          <div className="flex justify-between text-sm text-slate-500"><span>Subtotal</span><span>${listTotal.toFixed(2)}</span></div>
          {saved > 0 && <div className="flex justify-between text-sm text-emerald-600"><span>Offers applied</span><span>−${saved.toFixed(2)}</span></div>}
          {loyalty.points >= 25 && (
            <label className="flex justify-between text-sm text-slate-700 cursor-pointer items-center">
              <span className="flex items-center gap-2"><input type="checkbox" checked={applyPoints} onChange={(e) => setApplyPoints(e.target.checked)} />Use {loyalty.points} points (${loyalty.dollar_value})</span>
              {ptsValue > 0 && <span className="text-emerald-600">−${ptsValue.toFixed(2)}</span>}
            </label>
          )}
          <div className="flex justify-between font-extrabold text-lg pt-1 border-t border-slate-200 mt-1"><span>Total</span><span style={{ color: BRAND }}>${total.toFixed(2)}</span></div>
          <button disabled={!cart.length || placing} onClick={() => { setPlacing(true); onPlace(applyPoints); }}
            className="w-full text-white font-semibold rounded-lg py-3 mt-2 hover:opacity-90 disabled:opacity-50" style={{ background: "#16a34a" }}>
            {placing ? "Processing payment…" : `Pay $${total.toFixed(2)} →`}
          </button>
          <div className="text-[11px] text-slate-400 text-center mt-1">🔒 Secure checkout · simulated payment for the demo</div>
        </div>
      </div>
    </div>
  );
}

function OrderConfirmation({ order, onClose }: { order: Order; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-[60] bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="bg-white rounded-2xl w-[min(520px,95vw)] shadow-2xl overflow-hidden">
        <div className="p-6 text-white text-center" style={{ background: `linear-gradient(110deg, #16a34a, #4ade80)` }}>
          <div className="text-5xl mb-1">🎉</div>
          <div className="text-2xl font-extrabold">Order confirmed</div>
          <div className="text-sm opacity-90">#{order.order_id} · {order.segment}</div>
        </div>
        <div className="p-5">
          <div className="space-y-2 mb-3">
            {order.items.map((i) => (
              <div key={i.id} className="flex items-center gap-3">
                <span className="text-xl">{i.emoji}</span>
                <span className="flex-1 text-sm font-semibold">{i.name}</span>
                <span className="text-sm">${i.price.toFixed(2)}</span>
              </div>
            ))}
          </div>
          <div className="border-t border-slate-200 pt-3 space-y-1 text-sm">
            <div className="flex justify-between text-slate-500"><span>Items ({order.units})</span><span>${order.sale_total.toFixed(2)}</span></div>
            {order.incentive > 0 && <div className="flex justify-between text-emerald-600"><span>You saved</span><span>−${order.incentive.toFixed(2)}</span></div>}
            {order.points_used > 0 && <div className="flex justify-between text-emerald-600"><span>Points redeemed</span><span>−${order.points_value.toFixed(2)}</span></div>}
            <div className="flex justify-between font-extrabold text-lg"><span>Paid</span><span style={{ color: BRAND }}>${order.grand_total.toFixed(2)}</span></div>
            <div className="text-xs text-amber-600 font-semibold pt-1">+{order.points_earned} loyalty points earned ✨</div>
          </div>
          <button onClick={onClose} className="w-full text-white font-semibold rounded-lg py-2.5 mt-4 hover:opacity-90" style={{ background: BRAND }}>Continue shopping</button>
          <div className="text-[11px] text-slate-400 text-center mt-2">This revenue is now live on the analytics dashboard.</div>
        </div>
      </div>
    </div>
  );
}

function InboxModal({ mails, onClose, onOpenProduct }: { mails: InboxMail[]; onClose: () => void; onOpenProduct: (m: InboxMail) => void; }) {
  const [sel, setSel] = useState(0);
  const m = mails[sel];
  return (
    <div className="fixed inset-0 z-[60] bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="bg-white rounded-2xl w-[min(820px,96vw)] h-[min(560px,90vh)] shadow-2xl overflow-hidden flex flex-col">
        <div className="px-5 py-3 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div className="font-bold flex items-center gap-2">📧 Inbox <span className="text-xs font-normal text-slate-400">— messages Kairos decided were worth sending</span></div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-lg">✕</button>
        </div>
        {mails.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-400 text-sm">
            <div className="text-4xl mb-2">📭</div>
            No targeted messages yet. Browse a few products — Kairos only emails when it changes the outcome.
          </div>
        ) : (
          <div className="flex-1 grid grid-rows-[auto_1fr] sm:grid-rows-1 sm:grid-cols-[240px_1fr] overflow-hidden">
            <div className="border-b sm:border-b-0 sm:border-r border-slate-200 overflow-auto max-h-[32vh] sm:max-h-none">
              {mails.map((mail, i) => (
                <button key={i} onClick={() => setSel(i)}
                  className={`w-full text-left px-3 py-2.5 border-b border-slate-100 ${i === sel ? "bg-rose-50" : "hover:bg-slate-50"}`}>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-700">{mail.channel_icon} {mail.from}</span>
                    <span className="text-[10px] text-slate-400">{timeAgo(mail.ts)}</span>
                  </div>
                  <div className="text-sm font-semibold truncate">{mail.subject}</div>
                  <div className="text-xs text-slate-400 truncate">{mail.preview}</div>
                </button>
              ))}
            </div>
            <div className="overflow-auto p-5">
              <div className="text-xs text-slate-400">{m.channel_icon} delivered via {m.channel} · {m.from}</div>
              <h2 className="text-lg font-bold mt-1">{m.subject}</h2>
              {m.product && (
                <div className="my-3 flex items-center gap-3 bg-slate-50 rounded-xl p-3">
                  <div className={`w-16 h-16 rounded-lg flex items-center justify-center text-3xl ${CAT_THEME[m.product.cat] ?? "bg-white"}`}>{m.product.emoji}</div>
                  <div><div className="text-sm font-semibold">{m.product.name}</div><div className="text-sm font-bold" style={{ color: BRAND }}>${m.product.sale_price ?? m.product.price}</div></div>
                </div>
              )}
              <p className="text-sm text-slate-700 leading-relaxed">{m.body}</p>
              {m.offer_pct ? <div className="mt-2 inline-block text-xs font-bold text-white px-2 py-1 rounded" style={{ background: BRAND }}>{m.offer_pct}% OFF inside</div> : null}
              <button onClick={() => onOpenProduct(m)} className="block w-full text-center text-white font-semibold rounded-lg py-2.5 mt-4 hover:opacity-90" style={{ background: BRAND }}>{m.cta}</button>
              <div className="text-[11px] text-slate-400 mt-2">🔗 Links straight to the product — no hunting, before the moment passes.</div>
              {m.reason && <div className="text-[11px] text-slate-400 mt-3 border-t border-slate-100 pt-2">🧠 Why you got this: {m.reason}</div>}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function timeAgo(ts: number) {
  const s = Math.max(1, Math.floor(Date.now() / 1000 - ts));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

function PhoneStore({ onClose, resolving, sug, products, cats, profile, wishIds, phoneSend, onCheckout, onEndSession }: {
  onClose: () => void; resolving: boolean; sug: any; products: Product[]; cats: string[];
  profile: Profile | null; wishIds: Set<string>;
  phoneSend: (type: string, p?: Product) => void; onCheckout: () => void; onEndSession: () => void;
}) {
  const [cat, setCat] = useState("All");
  const [sel, setSel] = useState<Product | null>(null);
  const [added, setAdded] = useState(false);
  const nba = sug?.next_best_action;
  const cartCount = profile?.cart?.length ?? 0;
  const shown = products.filter((p) => cat === "All" || p.cat === cat);

  function view(p: Product) { phoneSend("view_product", p); setSel(p); }
  function back() { phoneSend("back_to_browse"); setSel(null); }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="w-[348px] h-[700px] rounded-[2.6rem] border-[11px] border-[#0d1320] bg-[#0d1320] shadow-2xl overflow-hidden relative">
        <div className="h-7 bg-[#0d1320] flex items-center justify-center"><div className="w-24 h-4 bg-black rounded-full" /></div>
        {resolving ? (
          <div className="flex flex-col items-center justify-center h-[calc(100%-1.75rem)] text-slate-300">
            <div className="animate-pulse text-lg">🔗 Resolving identity…</div>
            <div className="text-xs text-slate-500 mt-2">matching this device to a known shopper</div>
          </div>
        ) : (
          <div className="bg-[#f3f4f6] h-[calc(100%-1.75rem)] overflow-auto text-slate-900 relative">

            <div className="sticky top-0 z-10 bg-white border-b border-slate-200 px-3 h-11 flex items-center justify-between">
              {sel ? <button onClick={back} className="text-sm text-slate-500">← Back</button>
                   : <div className="font-extrabold text-lg" style={{ color: BRAND }}>VERVE</div>}
              <button onClick={onCheckout} className="relative text-lg">🛒{cartCount ? <Badge n={cartCount} /> : null}</button>
            </div>

            {sug?.identity_resolved && (
              <div className="m-2 text-[11px] text-emerald-700 bg-emerald-100 border border-emerald-200 rounded-lg px-2 py-1">
                ✓ Same shopper recognized · {sug.devices?.join(" → ")} — cart & points followed you
              </div>
            )}

            {!sel && nba?.recommend && (
              <div className="m-2 bg-white border rounded-2xl p-3 shadow-sm" style={{ borderColor: BRAND + "55" }}>
                <div className="text-[10px] uppercase tracking-widest text-slate-400">{nba.channel_icon} In-app · {nba.channel}</div>
                <div className="text-sm font-bold leading-snug mt-0.5">{nba.headline}</div>
                <div className="text-xs text-slate-600 mt-1">{nba.message}</div>
                {nba.product && <button onClick={() => view(nba.product)} className="mt-2 w-full text-white font-semibold rounded-xl py-1.5 text-xs" style={{ background: BRAND }}>{nba.cta ?? "Shop now →"}</button>}
              </div>
            )}

            {sel ? (

              <div className="p-3">
                <div className="w-full max-w-[200px] mx-auto"><ProductImage p={sel} big /></div>
                <div className="text-[10px] text-slate-400 mt-2">{sel.cat}</div>
                <div className="text-base font-bold leading-tight">{sel.name}</div>
                <div className="text-amber-500 text-xs">{stars(sel.rating ?? 4.5)} <span className="text-slate-400">({sel.reviews_count})</span></div>
                <div className="flex items-baseline gap-2 mt-1">
                  <span className="text-xl font-extrabold" style={{ color: BRAND }}>${sel.sale_price ?? sel.price}</span>
                  {sel.discount_pct ? <span className="text-xs text-slate-400 line-through">${sel.list_price}</span> : null}
                </div>
                <p className="text-xs text-slate-600 mt-2">{sel.blurb}</p>
                <div className="flex gap-3 mt-2 text-[11px]">
                  <button onClick={() => phoneSend("view_size_guide", sel)} className="text-slate-600 underline decoration-dotted">📏 Size guide</button>
                  <button onClick={() => phoneSend("view_all_reviews", sel)} className="text-slate-600 underline decoration-dotted">💬 View all reviews</button>
                </div>
                <div className="flex gap-2 mt-3">
                  <button onClick={() => { phoneSend("add_to_cart", sel); setAdded(true); setTimeout(() => setAdded(false), 1000); }}
                    className="flex-1 text-white font-semibold rounded-lg py-2 text-sm" style={{ background: BRAND }}>{added ? "Added ✓" : "Add to cart"}</button>
                  <button onClick={() => phoneSend(wishIds.has(sel.id) ? "remove_from_wishlist" : "add_to_wishlist", sel)}
                    className="px-3 rounded-lg border border-slate-300" style={{ color: wishIds.has(sel.id) ? BRAND : "#475569" }}>{wishIds.has(sel.id) ? "♥" : "♡"}</button>
                </div>
              </div>
            ) : (
              <>

                <div className="flex gap-1 overflow-x-auto px-2 py-2">
                  {["All", ...cats].map((c) => (
                    <button key={c} onClick={() => setCat(c)}
                      className={`text-[11px] whitespace-nowrap px-2.5 py-1 rounded-full border ${cat === c ? "text-white border-transparent" : "bg-white text-slate-600 border-slate-200"}`}
                      style={cat === c ? { background: BRAND } : {}}>{c}</button>
                  ))}
                </div>

                <div className="grid grid-cols-2 gap-2 px-2 pb-24">
                  {shown.map((p) => (
                    <ProductCard key={p.id} p={p} wished={wishIds.has(p.id)}
                      onOpen={() => view(p)} onWish={() => phoneSend(wishIds.has(p.id) ? "remove_from_wishlist" : "add_to_wishlist", p)} onAdd={() => phoneSend("add_to_cart", p)} />
                  ))}
                </div>
              </>
            )}

            <div className="sticky bottom-0 bg-white border-t border-slate-200 px-3 py-2 flex gap-2">
              {cartCount > 0 && (
                <button onClick={onCheckout} className="flex-1 text-white font-semibold rounded-lg py-2 text-sm" style={{ background: "#16a34a" }}>
                  Checkout ({cartCount})
                </button>
              )}
              <button onClick={onEndSession} className="flex-1 font-semibold rounded-lg py-2 text-sm border border-slate-300">Leave site 🚪</button>
            </div>
          </div>
        )}
        <button onClick={onClose} className="absolute top-1 right-4 text-slate-500 text-xs z-20">✕</button>
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
