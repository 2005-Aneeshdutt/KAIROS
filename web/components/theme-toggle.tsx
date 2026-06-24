"use client";

import { useEffect, useState } from "react";

export function ThemeToggle({ className = "" }: { className?: string }) {
  const [light, setLight] = useState(false);

  useEffect(() => {
    const saved = typeof localStorage !== "undefined" && localStorage.getItem("kairos_theme") === "light";
    setLight(saved);
    document.documentElement.classList.toggle("light", saved);
  }, []);

  function toggle() {
    const next = !light;
    setLight(next);
    document.documentElement.classList.toggle("light", next);
    try { localStorage.setItem("kairos_theme", next ? "light" : "dark"); } catch { /* ignore */ }
  }

  return (
    <button onClick={toggle} title="Toggle dark / light"
      className={`text-xs px-2.5 py-1 rounded-md border transition ${light
        ? "border-slate-300 text-slate-600 hover:bg-slate-100"
        : "border-line text-slate-300 hover:bg-panel2"} ${className}`}>
      {light ? "🌙 Dark" : "☀️ Light"}
    </button>
  );
}
