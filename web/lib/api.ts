// Thin API client. All calls go through Next's /api proxy to FastAPI. If the
// backend is down, callers fall back to bundled snapshot data so the demo never
// shows a blank screen.

export type Segment = {
  bucket: string;
  count: number;
  pct: number;
  avg_uplift: number;
  avg_base_rate: number;
  inc_revenue: number;
  action: string;
  rationale: string;
};

export type Customer = {
  customer_id: string;
  bucket: string;
  base_rate: number;
  uplift: number;
  inc_revenue: number;
  channel: string;
  recency: number;
  history_segment: string;
  action: string;
  rationale: string;
};

async function get<T>(path: string, fallback: T): Promise<T> {
  try {
    const r = await fetch(`/api${path}`, { cache: "no-store" });
    if (!r.ok) throw new Error(`${r.status}`);
    return (await r.json()) as T;
  } catch {
    return fallback;
  }
}

async function post<T>(path: string, body: unknown, fallback: T): Promise<T> {
  try {
    const r = await fetch(`/api${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    if (!r.ok) throw new Error(`${r.status}`);
    return (await r.json()) as T;
  } catch {
    return fallback;
  }
}

export const api = {
  segments: () =>
    get<{ total_customers: number; segments: Segment[] }>("/segments", {
      total_customers: 0,
      segments: [],
    }),
  customers: (bucket?: string, limit = 60) =>
    get<{ total: number; items: Customer[] }>(
      `/customers?limit=${limit}${bucket ? `&bucket=${encodeURIComponent(bucket)}` : ""}`,
      { total: 0, items: [] }
    ),
  qini: () => get<any>("/qini", { x: [], y: [], auuc: 0, method: "" }),
  allocation: () => get<any>("/allocation", { curve: [], knee: {}, restraint_metrics: {}, economics: {} }),
  allocate: (budget: number) =>
    post<{ budget: number; revenue: number; customers_targeted: number }>(
      "/allocate",
      { budget },
      { budget, revenue: 0, customers_targeted: 0 }
    ),
  bandit: () => get<any>("/bandit", { curve: [], channels: [], summary: {} }),
  explain: (customer_id: string) =>
    post<{ explanation: string }>("/explain", { customer_id }, { explanation: "" }),
};

export type Product = {
  id: string; name: string; price: number; cat: string; emoji: string;
  rating?: number; blurb?: string; badge?: string | null;
  reviews_count?: number; stock?: number;
  offer?: string; offer_kind?: string; discount_pct?: number;
  list_price?: number; sale_price?: number; img?: string;
};

export type Bundle = {
  id: string; name: string; emoji: string; pct: number; blurb: string;
  products: Product[]; total: number; price: number; saves: number;
};
export type Coupon = { id: string; amount: string; desc: string; tag: string; expires: string };
export type Redemption = { id: string; name: string; cost: number; icon: string; partner: string };
export type Promotions = { ticker: string[]; bundles: Bundle[]; coupons: Coupon[]; redemptions: Redemption[] };

export type Review = {
  author: string; rating: number; title: string; text: string;
  date: string; verified: boolean; helpful: number;
};

export type ProductDetail = Product & {
  description: string; reviews: Review[]; rating_breakdown: Record<string, number>;
};

export const store = {
  catalogue: () =>
    get<{ products: Product[]; categories: string[] }>("/store/catalogue", { products: [], categories: [] }),
  product: (pid: string) => get<ProductDetail | null>(`/store/product/${pid}`, null),
  promotions: () =>
    get<Promotions>("/store/promotions", { ticker: [], bundles: [], coupons: [], redemptions: [] }),
  track: (body: {
    uid: string; type: string; product_id?: string; device?: string; dwell_ms?: number;
  }) => post<any>("/track", body, null),
  suggestion: (uid: string, device: string) =>
    get<any>(`/visitor/${uid}/suggestion?device=${device}`, null),
  redeem: (uid: string, reward_id: string) => post<any>("/redeem", { uid, reward_id }, null),
  visitor: (uid: string) => get<any>(`/visitor/${uid}`, null),
  purchase: (uid: string, applied_points = 0) =>
    post<any>("/purchase", { uid, applied_points }, null),
  inbox: (uid: string, device = "desktop") =>
    get<any>(`/inbox/${uid}?device=${device}`, { inbox: [] }),
  sessionEnd: (uid: string, device = "desktop") =>
    post<any>("/session/end", { uid, device }, null),
  analytics: () => get<any>("/analytics/live", null),
  strategy: () => get<any>("/strategy", null),
  benchmark: (n = 5000, seed = 42) => get<any>(`/benchmark?n=${n}&seed=${seed}`, null),
};

export type Pattern = { code: string; label: string; detail: string; intent: "up" | "down"; icon: string };
export type Bundle2 = {
  name: string; segment: string; discount_pct: number; kind: string;
  products: { id: string; name: string; emoji: string; price: number }[];
  total: number; price: number; saves: number; rationale: string;
};
export type InboxMail = {
  channel: string; channel_icon: string; subject: string; preview: string; body: string;
  cta: string; link: string; product: Product | null; reward_type?: string;
  offer_pct?: number; reason?: string; from: string; ts: number; read: boolean;
};
export type Order = {
  order_id: string; units: number; sale_total: number; incentive: number;
  points_used: number; points_value: number; grand_total: number; points_earned: number;
  segment: string; items: { id: string; name: string; emoji: string; price: number }[];
};

export function getUid(): string {
  if (typeof window === "undefined") return "ssr";
  let id = localStorage.getItem("conductor_uid");
  if (!id) {
    id = "v" + Math.random().toString(36).slice(2, 10);
    localStorage.setItem("conductor_uid", id);
  }
  return id;
}

export const fmtUSD = (n: number) =>
  "$" + Math.round(n).toLocaleString("en-US");
export const fmtPct = (n: number) => (n * 100).toFixed(1) + "%";

export const BUCKET_COLOR: Record<string, string> = {
  Persuadable: "#3b82f6",
  "Sure Thing": "#22c55e",
  "Lost Cause": "#ef4444",
  "Sleeping Dog": "#eab308",
};
