"use client";

import { useEffect, useRef, useState } from "react";
import { store, Product } from "@/lib/api";

type Msg = { role: "user" | "bot"; text: string; products?: any[] };
const BRAND = "#e31837";
const SUGGEST = ["A blazer under $150", "Running shoes", "A gift under $50", "Leather bag"];

export function ChatBot({ uid, onProduct }: { uid: string; onProduct: (p: Product) => void }) {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([
    { role: "bot", text: "Hi! I'm your VERVE shopping assistant 🛍️ Ask me for anything — like “a blazer under $150” or “running shoes”." },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, open, loading]);

  async function send(q?: string) {
    const text = (q ?? input).trim();
    if (!text || loading) return;
    setInput("");
    setMsgs((m) => [...m, { role: "user", text }]);
    setLoading(true);
    const r = await store.chat(uid, text);
    setMsgs((m) => [...m, { role: "bot", text: r.reply, products: r.products }]);
    setLoading(false);
  }

  return (
    <>
      <button onClick={() => setOpen((o) => !o)} aria-label="Shopping assistant"
        className="fixed bottom-5 right-5 z-40 w-14 h-14 rounded-full shadow-xl text-white text-2xl grid place-items-center hover:scale-105 transition"
        style={{ background: BRAND }}>
        {open ? "✕" : "💬"}
      </button>

      {open && (
        <div className="fixed bottom-24 right-5 z-40 w-[370px] max-w-[92vw] h-[540px] max-h-[76vh] bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden">
          <div className="px-4 py-3 text-white flex items-center gap-2" style={{ background: BRAND }}>
            <span className="text-xl">🛍️</span>
            <div>
              <div className="font-bold text-sm leading-none">VERVE Assistant</div>
              <div className="text-[10px] opacity-80 mt-0.5">Find anything in seconds</div>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-3 bg-slate-50">
            {msgs.map((m, i) => (
              <div key={i}>
                <div className={`text-sm rounded-2xl px-3 py-2 max-w-[88%] leading-relaxed ${m.role === "user" ? "ml-auto text-white" : "bg-white border border-slate-200 text-slate-700"}`}
                  style={m.role === "user" ? { background: BRAND } : {}}>
                  {m.text}
                </div>
                {m.products && m.products.length > 0 && (
                  <div className="mt-2 space-y-2">
                    {m.products.map((p) => (
                      <button key={p.id} onClick={() => { onProduct(p); setOpen(false); }}
                        className="w-full flex items-center gap-3 bg-white border border-slate-200 rounded-xl p-2 hover:border-rose-300 hover:shadow-md transition text-left">
                        <div className="w-12 h-12 rounded-lg grid place-items-center text-2xl bg-slate-100 shrink-0">{p.emoji}</div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-semibold text-slate-800 truncate">{p.name}</div>
                          <div className="text-[11px] text-slate-500 truncate">{p.cat}{p.rating ? ` · ★ ${p.rating}` : ""}</div>
                        </div>
                        <div className="font-bold text-slate-900 shrink-0">${p.price}</div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <div className="text-sm bg-white border border-slate-200 text-slate-400 rounded-2xl px-3 py-2 w-fit">typing…</div>
            )}
            <div ref={endRef} />
          </div>

          {msgs.length <= 1 && (
            <div className="px-3 pb-1 flex flex-wrap gap-1.5 bg-slate-50">
              {SUGGEST.map((s) => (
                <button key={s} onClick={() => send(s)}
                  className="text-[11px] text-slate-600 bg-white border border-slate-200 rounded-full px-2.5 py-1 hover:border-rose-300">{s}</button>
              ))}
            </div>
          )}

          <div className="p-2 border-t border-slate-200 flex gap-2 bg-white">
            <input value={input} onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
              placeholder="Ask for a product…"
              className="flex-1 bg-slate-100 rounded-full px-3 py-2 text-sm outline-none focus:bg-white focus:ring-1 focus:ring-rose-300" />
            <button onClick={() => send()} disabled={loading}
              className="text-white text-sm font-semibold px-4 rounded-full disabled:opacity-50" style={{ background: BRAND }}>Send</button>
          </div>
        </div>
      )}
    </>
  );
}
