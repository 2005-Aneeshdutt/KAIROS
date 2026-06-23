"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// Framed as Epsilon PeopleCloud: Audiences → Activation → Measurement.
const NAV = [
  { href: "/people", label: "Audiences", icon: "👥", stage: "Identity & segments" },
  { href: "/strategy", label: "Activation", icon: "📣", stage: "Channels & offers" },
  { href: "/dashboard", label: "Measurement", icon: "📊", stage: "Incrementality in $" },
  { href: "/console", label: "Live Console", icon: "🖥️", stage: "Real-time shopper" },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname() || "";
  return (
    <div className="flex min-h-screen">
      <aside className="w-56 shrink-0 border-r border-line bg-ink/70 flex flex-col sticky top-0 h-screen">
        <div className="px-5 h-16 flex items-center gap-2 border-b border-line">
          <div className="w-2.5 h-7 bg-epsilon rounded-sm" />
          <div className="leading-tight">
            <div className="font-black text-lg tracking-tight">Kairos</div>
            <div className="text-[9px] text-slate-500 -mt-0.5">PeopleCloud</div>
          </div>
        </div>
        <div className="px-4 pt-3 text-[9px] uppercase tracking-widest text-slate-600">Audiences → Activation → Measurement</div>
        <nav className="flex-1 p-3 space-y-1">
          {NAV.map((n) => {
            const active = path === n.href || (n.href !== "/dashboard" && path.startsWith(n.href));
            return (
              <Link key={n.href} href={n.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition ${active
                  ? "bg-epsilon/15 text-epsilon font-semibold"
                  : "text-slate-400 hover:text-slate-100 hover:bg-panel2"}`}>
                <span className="w-5 text-center">{n.icon}</span>
                <span className="flex-1">{n.label}<span className="block text-[9px] font-normal text-slate-600">{n.stage}</span></span>
              </Link>
            );
          })}
        </nav>
        <div className="p-3 border-t border-line space-y-1">
          <Link href="/store" className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-400 hover:text-white hover:bg-panel2">
            <span className="w-5 text-center">▶</span> Storefront
          </Link>
          <div className="text-[10px] text-slate-600 px-3 pt-1">Causal decisioning</div>
        </div>
      </aside>
      <div className="flex-1 min-w-0">{children}</div>
    </div>
  );
}
