"""LLM funding assistant: Claude loops over the registries via tools (registry_tools) and answers only from what the tools return.

Guardrails (CLAUDE.md section 9): every claim cites a registry id + URL + verified_on; unsupported questions get
'No verified entry; add one to the registry.'; any cited id that is not in the registries is flagged as a hard failure.
Falls back to retrieval-only chat.answer() when no credentials are available. API key comes from the environment / .env (never committed).
"""
from __future__ import annotations

import json
import os

from . import chat, registry_tools as rt
from .io import ROOT

MODEL = "claude-opus-5-5"
MAX_TURNS = 8

SYSTEM = """You are the funding and partner assistant for a team designing primary-care funding in Lebanon's Beqaa Valley.
The team's priority: money should reach and be controlled by local communities and Lebanese entities (local NGOs, municipalities, women's organisations, cooperatives), \
with communities deciding how funds are used, including displaced Syrians and unregistered workers who are often missed. Use land- and community-based wording and "displaced Syrians".

Rules:
- Answer ONLY from tool results. Loop through the registries with the tools (several searches, different keywords and filters) before answering. Never use memory for grants, amounts, deadlines or organisations.
- Cite every funding or organisation claim with its id in square brackets, e.g. [F004], plus its URL and verified_on date. Never write an id a tool did not return.
- If nothing matches, say exactly: "No verified entry; add one to the registry." Do not guess or suggest unlisted grants.
- Flag rows that are expired, older than 6 months, or unverified (status to_verify) and say what the team should check.
- `community_decision_fit` is `to_verify` unless a row says otherwise: say it is unconfirmed rather than assuming a funder supports local decision-making.
- Note collateral risks when relevant (excludes unregistered workers, capture, dependency on foreign intermediaries). Be concise: a short ranked list, then one line on what to verify next."""


def _load_env():
    f = ROOT / ".env"
    if f.exists() and not os.environ.get("ANTHROPIC_API_KEY"):
        for line in f.read_text().splitlines():
            if line.strip().startswith("ANTHROPIC_API_KEY="):
                os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1].strip().strip('"')


def get_client():
    """Anthropic client from env / .env, or None if no credentials."""
    _load_env()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    import anthropic
    return anthropic.Anthropic()


def ask(question: str, history: list[dict] | None = None, client=None, context: str = "", use_llm: bool = True) -> dict:
    """Returns {answer, citations, trace, invalid_ids, mode}. `history` = prior plain-text turns [{role, content}]."""
    client = (client or get_client()) if use_llm else None      # use_llm=False: never call the API, even when a key exists
    if client is None:
        r = chat.answer(question)
        return {"answer": r["answer"], "citations": r["citations"], "trace": [], "invalid_ids": [], "mode": "retrieval-only (no API key or LLM off)"}
    messages = list(history or []) + [{"role": "user", "content": (f"[Current project context: {context}]\n\n" if context else "") + question}]
    trace = []
    for _ in range(MAX_TURNS):
        resp = client.beta.messages.create(
            model=MODEL, max_tokens=16000, system=SYSTEM, tools=rt.TOOL_SPECS, messages=messages,
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"], fallbacks="default")
        if resp.stop_reason == "refusal":
            return {"answer": "The model declined this request.", "citations": [], "trace": trace, "invalid_ids": [], "mode": MODEL}
        messages.append({"role": "assistant", "content": resp.content})     # keep thinking blocks unchanged
        if resp.stop_reason != "tool_use":
            text = "".join(b.text for b in resp.content if b.type == "text")
            bad = rt.invalid_citations(text)
            if bad:
                text += f"\n\n⚠ **Unverified ids removed from consideration: {', '.join(bad)} are not in the registry. Do not use them.**"
            import re
            return {"answer": text, "citations": sorted(set(re.findall(r"\b[FOS]\d{2,3}\b", text)) - set(bad)), "trace": trace, "invalid_ids": bad, "mode": MODEL}
        results = []
        for b in resp.content:
            if b.type != "tool_use":
                continue
            fn = rt.TOOLS.get(b.name)
            try:
                out = fn(**(b.input or {})) if fn else {"error": f"unknown tool {b.name}"}
                err = False
            except Exception as e:                                         # return the error to the model, don't crash the loop
                out, err = {"error": str(e)}, True
            trace.append({"tool": b.name, "input": b.input, "n_results": len(out) if isinstance(out, list) else int(out is not None)})
            results.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(out, default=str), **({"is_error": True} if err else {})})
        messages.append({"role": "user", "content": results})               # all results in ONE user message
    return {"answer": "Stopped after too many search steps; try a narrower question.", "citations": [], "trace": trace, "invalid_ids": [], "mode": MODEL}
