import os
import re
import json

SYSTEM = (
    "You are Kairos's marketing strategist agent. Answer the user's goal by calling the "
    "tools to pull the system's REAL numbers, then decide where to spend, where to hold, "
    "and where to stay silent. Ground every claim in tool results. Emphasise incrementality "
    "(spend only where marketing changes the outcome) and restraint (Sleeping Dogs hurt when "
    "contacted). Be concise and concrete; cite the figures you pulled. End with a short, "
    "prioritised action plan."
)

TOOLS = [
    {"name": "get_segments",
     "description": "Counts, average uplift, base rate and incremental revenue per bucket.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "solve_allocation",
     "description": "Given a budget in dollars, return incremental revenue and customers targeted.",
     "input_schema": {"type": "object",
                      "properties": {"budget": {"type": "number"}}, "required": ["budget"]}},
    {"name": "run_benchmark",
     "description": "Traditional vs Conductor over the base; returns net revenue, sends, deltas.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_strategy",
     "description": "Live funnel, segment counts and prioritised recommendations from the store.",
     "input_schema": {"type": "object", "properties": {}}},
]


def run(goal: str, executors: dict, max_steps: int = 5) -> dict:
    """Tool-using agent. Uses Claude if ANTHROPIC_API_KEY is set; otherwise falls back to a
    built-in planning agent that still selects + calls the system's tools and grounds its
    answer in the real numbers — no API key required."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return _local(goal, executors)
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        messages = [{"role": "user", "content": goal}]
        steps = []
        for _ in range(max_steps):
            resp = client.messages.create(model="claude-sonnet-4-6", max_tokens=1024,
                                          system=SYSTEM, tools=TOOLS, messages=messages)
            if resp.stop_reason != "tool_use":
                text = "".join(b.text for b in resp.content if b.type == "text")
                return {"answer": text, "steps": steps, "source": "claude"}
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for block in resp.content:
                if block.type != "tool_use":
                    continue
                impl = executors.get(block.name)
                try:
                    out = impl(**(block.input or {})) if impl else {"error": "unknown tool"}
                except Exception as e:
                    out = {"error": str(e)}
                steps.append({"tool": block.name, "input": block.input})
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": json.dumps(out, default=str)[:4000]})
            messages.append({"role": "user", "content": results})
        return {"answer": "(stopped after the step limit)", "steps": steps, "source": "claude"}
    except Exception:
        return _local(goal, executors)


def _pct(x):
    try:
        return f"{float(x) * 100:.1f}%"
    except Exception:
        return "n/a"


def _budget(goal: str):
    m = re.search(r"\$?\s*(\d+(?:\.\d+)?)\s*([kK])?", goal.replace(",", ""))
    if not m:
        return None
    val = float(m.group(1))
    return val * 1000 if m.group(2) else val


def _local(goal: str, executors: dict) -> dict:
    """A deterministic planning agent: picks tools by the goal, calls them, reads the
    results, and writes a grounded plan. Genuinely agentic (perceive -> act -> observe ->
    plan) without any LLM or API key."""
    g = goal.lower()
    steps = []

    def call(name, **kw):
        steps.append({"tool": name, "input": kw})
        try:
            return executors[name](**kw)
        except Exception as e:
            return {"error": str(e)}

    seg = call("get_segments")
    by = {s.get("bucket"): s for s in (seg.get("segments") or [])}
    pers, sure = by.get("Persuadable", {}), by.get("Sure Thing", {})
    dog, lost = by.get("Sleeping Dog", {}), by.get("Lost Cause", {})
    total = seg.get("total_customers", 0)

    parts = [
        f"Customer base: {total:,} customers — {pers.get('pct',0)}% Persuadable, "
        f"{sure.get('pct',0)}% Sure Thing, {dog.get('pct',0)}% Sleeping Dog, "
        f"{lost.get('pct',0)}% Lost Cause. Only the Persuadables are worth spending on."
    ]

    wants_budget = any(k in g for k in ["budget", "spend", "allocate", "$"])
    budget = _budget(goal) if wants_budget else None
    wants_bench = any(k in g for k in ["benchmark", "traditional", "compare", " vs", "case for",
                                       "better", "roi", "beat"])
    wants_live = any(k in g for k in ["live", "now", "store", "shopper", "funnel", "abandon",
                                      "bleed", "waste", "wasting", "losing"])

    if budget:
        a = call("solve_allocation", budget=budget)
        parts.append(
            f"At a ${budget:,.0f} budget, Kairos targets {a.get('customers_targeted',0):,} "
            f"customers (highest incremental ROI first) for ${a.get('revenue',0):,.0f} in "
            f"incremental revenue — and stops there: past the marginal-ROI knee each extra "
            f"dollar earns less."
        )

    if wants_bench:
        b = call("run_benchmark")
        T, C, d = b.get("traditional", {}), b.get("conductor", {}), b.get("deltas", {})
        parts.append(
            f"Head-to-head on the same customers: Conductor nets ${C.get('net',0):,.0f} vs "
            f"Traditional ${T.get('net',0):,.0f} (+{d.get('net_revenue_pct',0)}%), with "
            f"{abs(d.get('messages_saved',0)):,} fewer messages and ${d.get('discount_saved',0):,.0f} "
            f"less discount given away."
        )

    if wants_live:
        st = call("get_strategy")
        recs = (st or {}).get("recommendations") or []
        if recs:
            parts.append("Live store says: " + "; ".join(
                f"{r.get('title')} ({r.get('impact')})" for r in recs[:3]) + ".")

    plan = [
        f"SPEND on Persuadables — {pers.get('count',0):,} customers, avg uplift "
        f"{_pct(pers.get('avg_uplift'))}, ~${pers.get('inc_revenue',0):,.0f} incremental revenue.",
        f"HOLD Sure Things — {sure.get('count',0):,} buy anyway; swap discounts for loyalty to keep margin.",
        f"SUPPRESS Sleeping Dogs — {dog.get('count',0):,} convert LESS when contacted; silence protects organic revenue.",
        f"SKIP Lost Causes — {lost.get('count',0):,} won't act either way.",
    ]
    answer = " ".join(parts) + "\n\nAction plan:\n" + "\n".join(
        f"{i+1}. {p}" for i, p in enumerate(plan))
    return {"answer": answer, "steps": steps, "source": "planner"}
