import os
import re
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

SYSTEM = (
    "You are Kairos's marketing strategist agent. Kairos is a CAUSAL uplift decisioning system: "
    "it spends only where marketing actually changes the outcome. Every customer falls into one of "
    "four buckets — Persuadable (buys ONLY if contacted -> SPEND), Sure Thing (buys anyway -> HOLD), "
    "Sleeping Dog (contact makes them LESS likely to buy -> SUPPRESS), Lost Cause (won't buy either "
    "way -> SKIP). Budget is WASTED ('bled') on Sure Things (discounting people who buy anyway) and "
    "Sleeping Dogs (contacting them backfires) — never on Persuadables, where every dollar is well "
    "spent; when asked what wastes or 'bleeds' budget, name Sure Things and Sleeping Dogs. "
    "Answer the user's goal by calling the tools to pull the system's REAL numbers — never invent "
    "figures. Tools: get_segments (per-bucket counts, average uplift and incremental revenue), "
    "solve_allocation(budget) (optimizer output for a given $ budget), run_benchmark (Kairos vs a "
    "traditional batch-and-blast campaign), get_strategy (live storefront funnel + recommendations). "
    "Always call get_segments first to ground yourself. solve_allocation ranks ALL customers by "
    "incremental ROI and also returns the marginal-ROI 'knee' (knee.budget / knee.customers / "
    "knee.revenue) — the optimal place to STOP, because every dollar past the knee earns less. If the "
    "requested budget is past the knee (past_knee=true), do NOT recommend spending it all: advise "
    "stopping at the knee and quote the knee's customers and revenue as the recommended target. "
    "Be concise and concrete, cite the figures you pulled, emphasise incrementality and restraint, "
    "and finish with a short, prioritised action plan (SPEND / HOLD / SUPPRESS / SKIP)."
)

TOOLS = [
    {"name": "get_segments",
     "description": "Counts, average uplift, base rate and incremental revenue per bucket.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "solve_allocation",
     "description": "Given a budget in dollars, return incremental revenue, customers reached, and the marginal-ROI knee (the optimal point to stop spending).",
     "input_schema": {"type": "object",
                      "properties": {"budget": {"type": "number"}}, "required": ["budget"]}},
    {"name": "run_benchmark",
     "description": "Traditional vs Kairos over the base; returns net revenue, sends, deltas.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_strategy",
     "description": "Live funnel, segment counts and prioritised recommendations from the store.",
     "input_schema": {"type": "object", "properties": {}}},
]


def _openrouter_cfg():
    return (
        os.environ.get("OPENROUTER_API_KEY"),
        os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
    )


def _oai_tools():
    return [{"type": "function",
             "function": {"name": t["name"], "description": t["description"],
                          "parameters": t["input_schema"]}} for t in TOOLS]


def _exec(name, kw, executors, steps):
    impl = executors.get(name)
    steps.append({"tool": name, "input": kw})
    try:
        return impl(**(kw or {})) if impl else {"error": "unknown tool"}
    except Exception as e:
        return {"error": str(e)}


def run(goal: str, executors: dict, max_steps: int = 6) -> dict:
    """Tool-using agent. Routes to OpenRouter (OpenAI-compatible) if OPENROUTER_API_KEY is set,
    else Anthropic if ANTHROPIC_API_KEY is set, else a built-in deterministic planner that still
    selects + calls the system's tools and grounds its answer in the real numbers — no key needed."""
    okey, base, model = _openrouter_cfg()
    if okey:
        out = _openrouter(goal, executors, okey, base, model, max_steps)
        if out is not None:
            return out
    if os.environ.get("ANTHROPIC_API_KEY"):
        out = _anthropic(goal, executors, max_steps)
        if out is not None:
            return out
    return _local(goal, executors)


def _openrouter(goal, executors, key, base, model, max_steps):
    try:
        from openai import OpenAI
        client = OpenAI(base_url=base, api_key=key,
                        default_headers={"HTTP-Referer": "https://kairos.app", "X-Title": "Kairos"})
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": goal}]
        tools = _oai_tools()
        steps = []
        for _ in range(max_steps):
            resp = client.chat.completions.create(
                model=model, messages=messages, tools=tools, tool_choice="auto", max_tokens=1024)
            msg = resp.choices[0].message
            calls = msg.tool_calls or []
            if not calls:
                return {"answer": msg.content or "", "steps": steps,
                        "source": "openrouter", "model": model}
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [{"id": c.id, "type": "function",
                                "function": {"name": c.function.name,
                                             "arguments": c.function.arguments}} for c in calls],
            })
            for c in calls:
                try:
                    args = json.loads(c.function.arguments or "{}")
                except Exception:
                    args = {}
                out = _exec(c.function.name, args, executors, steps)
                messages.append({"role": "tool", "tool_call_id": c.id,
                                 "content": json.dumps(out, default=str)[:4000]})
        return {"answer": "(stopped after the step limit)", "steps": steps,
                "source": "openrouter", "model": model}
    except Exception:
        return None


def _anthropic(goal, executors, max_steps):
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        messages = [{"role": "user", "content": goal}]
        steps = []
        for _ in range(max_steps):
            resp = client.messages.create(model="claude-sonnet-4-6", max_tokens=1024,
                                          system=SYSTEM, tools=TOOLS, messages=messages)
            if resp.stop_reason != "tool_use":
                text = "".join(b.text for b in resp.content if b.type == "text")
                return {"answer": text, "steps": steps, "source": "claude",
                        "model": "claude-sonnet-4-6"}
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for block in resp.content:
                if block.type != "tool_use":
                    continue
                out = _exec(block.name, block.input, executors, steps)
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": json.dumps(out, default=str)[:4000]})
            messages.append({"role": "user", "content": results})
        return {"answer": "(stopped after the step limit)", "steps": steps,
                "source": "claude", "model": "claude-sonnet-4-6"}
    except Exception:
        return None


def llm_complete(system: str, user: str, max_tokens: int = 400):
    """Single-shot completion via OpenRouter, else Anthropic, else (None, None).
    Used by lightweight features (e.g. per-decision explanations) so one key powers the app."""
    okey, base, model = _openrouter_cfg()
    if okey:
        try:
            from openai import OpenAI
            client = OpenAI(base_url=base, api_key=okey,
                            default_headers={"HTTP-Referer": "https://kairos.app", "X-Title": "Kairos"})
            r = client.chat.completions.create(
                model=model, max_tokens=max_tokens,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
            return r.choices[0].message.content, "openrouter"
        except Exception:
            pass
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
            m = client.messages.create(model="claude-sonnet-4-6", max_tokens=max_tokens,
                                       system=system, messages=[{"role": "user", "content": user}])
            return m.content[0].text, "claude"
        except Exception:
            pass
    return None, None


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
        knee = a.get("knee") or {}
        if a.get("past_knee") and knee.get("budget"):
            parts.append(
                f"At ${budget:,.0f} you could reach {a.get('customers_targeted',0):,} customers — but "
                f"that's past the marginal-ROI knee. The optimal stop is ${knee['budget']:,.0f}, funding "
                f"{knee.get('customers',0):,} of the highest-uplift customers for "
                f"${knee.get('revenue',0):,.0f} in incremental revenue. Spend to the knee, not beyond — "
                f"every dollar after it earns less."
            )
        else:
            parts.append(
                f"At a ${budget:,.0f} budget, Kairos reaches {a.get('customers_targeted',0):,} of the "
                f"highest-ROI customers for ${a.get('revenue',0):,.0f} in incremental revenue. The "
                f"marginal-ROI knee sits at ${knee.get('budget',0):,.0f} — the point where each extra "
                f"dollar starts earning less."
            )

    if wants_bench:
        b = call("run_benchmark")
        T, C, d = b.get("traditional", {}), b.get("conductor", {}), b.get("deltas", {})
        parts.append(
            f"Head-to-head on the same customers: Kairos nets ${C.get('net',0):,.0f} vs "
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
