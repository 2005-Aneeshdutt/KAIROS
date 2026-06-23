"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { loginUser, getSession } from "@/lib/api";

export default function LandingLogin() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (getSession()) router.replace("/store");
  }, [router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      await loginUser(email.trim(), name.trim());
      router.replace("/store");
    } catch (e: any) {
      setErr(e?.message || "Something went wrong");
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen grid lg:grid-cols-2">
      <div className="relative hidden lg:flex flex-col justify-between p-12 overflow-hidden"
        style={{ background: "radial-gradient(1200px 600px at 0% 0%, rgba(230,0,90,0.18), transparent), #0a0e17" }}>
        <div className="flex items-center gap-2 text-2xl font-black tracking-tight">
          <span className="text-epsilon">●</span> VERVE
          <span className="text-xs font-normal text-slate-500 ml-2">The Style Edit</span>
        </div>
        <div className="max-w-md">
          <h1 className="text-4xl font-black leading-tight">Shopping that knows<br />when <span className="text-epsilon">not</span> to bother you.</h1>
          <p className="text-slate-400 mt-4 leading-relaxed">
            Sign in and every visit is unified under your <b className="text-slate-200">CORE&nbsp;ID</b> — one
            person-level identity across devices. We only reach out when it genuinely helps you.
          </p>
          <div className="flex gap-2 mt-6 flex-wrap">
            {["Personalised picks", "AI shopping assistant", "No spam, ever"].map((t) => (
              <span key={t} className="text-xs text-slate-300 bg-white/5 border border-white/10 rounded-full px-3 py-1">{t}</span>
            ))}
          </div>
        </div>
        <div className="text-xs text-slate-600">Powered by Kairos · causal decisioning</div>
      </div>

      <div className="flex items-center justify-center p-6 bg-ink">
        <form onSubmit={submit} className="w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-2 text-2xl font-black mb-8">
            <span className="text-epsilon">●</span> VERVE
          </div>
          <h2 className="text-2xl font-bold">Welcome</h2>
          <p className="text-slate-400 text-sm mt-1 mb-6">Enter your email to sign in or create your account.</p>

          <label className="block text-xs uppercase tracking-wider text-slate-500 mb-1">Email</label>
          <input
            type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full bg-panel2 border border-line rounded-xl px-4 py-3 text-sm outline-none focus:border-epsilon/60 mb-4"
          />
          <label className="block text-xs uppercase tracking-wider text-slate-500 mb-1">Name <span className="text-slate-600 normal-case">(optional)</span></label>
          <input
            value={name} onChange={(e) => setName(e.target.value)}
            placeholder="Your name"
            className="w-full bg-panel2 border border-line rounded-xl px-4 py-3 text-sm outline-none focus:border-epsilon/60 mb-4"
          />

          {err && <div className="text-xs text-rose-400 bg-rose-500/10 border border-rose-500/30 rounded-lg px-3 py-2 mb-4">{err}</div>}

          <button type="submit" disabled={loading}
            className="w-full bg-epsilon text-white font-semibold rounded-xl px-4 py-3 hover:opacity-90 disabled:opacity-50 transition">
            {loading ? "Signing in…" : "Continue →"}
          </button>

          <p className="text-[11px] text-slate-500 mt-4 leading-relaxed">
            No password needed — your email becomes a privacy-safe CORE&nbsp;ID. By continuing you agree your
            on-site activity is used to personalise your experience.
          </p>
          <div className="mt-6 text-center flex flex-col gap-1.5">
            <Link href="/store" className="text-xs text-slate-400 hover:text-slate-200">Browse as a guest → <span className="text-slate-600">(we&apos;ll unify it when you sign in)</span></Link>
            <Link href="/dashboard" className="text-xs text-slate-500 hover:text-slate-300">View the company dashboard →</Link>
          </div>
        </form>
      </div>
    </main>
  );
}
