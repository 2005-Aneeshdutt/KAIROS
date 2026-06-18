import os
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
    {
        "name": "get_segments",
        "description": "Counts, average uplift, base rate and incremental revenue for each of the four buckets (Persuadable, Sure Thing, Sleeping Dog, Lost Cause).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "solve_allocation",
        "description": "Given a marketing budget in dollars, return the incremental revenue captured and how many customers get targeted at that spend.",
        "input_schema": {
            "type": "object",
            "properties": {"budget": {"type": "number", "description": "budget in USD"}},
            "required": ["budget"],
        },
    },
    {
        "name": "run_benchmark",
        "description": "Head-to-head Traditional vs Conductor over the customer base; returns net revenue, conversion, sends, discount and the deltas.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_strategy",
        "description": "Live marketing strategy from the connected storefront: funnel, segment counts, and prioritised recommendations.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def run(goal: str, executors: dict, max_steps: int = 5) -> dict:
    """A real tool-using agent loop: Claude plans, calls our tools, reads the results,
    and iterates until it has a grounded answer. Returns the answer plus the tool trace."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return {"answer": "Set ANTHROPIC_API_KEY on the API service to enable the agent.",
                "steps": [], "source": "disabled"}
    try:
        import anthropic
    except Exception as e:
        return {"answer": f"anthropic SDK unavailable ({e})", "steps": [], "source": "error"}

    client = anthropic.Anthropic(api_key=key)
    messages = [{"role": "user", "content": goal}]
    steps = []

    for _ in range(max_steps):
        resp = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=1024,
            system=SYSTEM, tools=TOOLS, messages=messages,
        )
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
