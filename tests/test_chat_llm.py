from types import SimpleNamespace as NS

from beqaa import chat_llm, registry_tools as rt


def test_tools_return_cited_rows():
    rows = rt.search_funding("maternal health")
    assert rows and all(r["url"] is not None or r["fund_id"] for r in rows) and all("verified_on" in r for r in rows)
    assert rt.get_entry("F008")["fund_id"] == "F008" and rt.get_entry("F999") is None
    assert rt.search_funding("cryptocurrency mining") == []


def test_invalid_ids_detected():
    assert rt.invalid_citations("See [F004] and [F777] and [O001] [O999]") == ["F777", "O999"]


class FakeClient:
    """Scripted: turn 1 calls search_funding, turn 2 answers (optionally citing an invented id)."""
    def __init__(self, final_text):
        self.calls, self.final = 0, final_text
        self.beta = NS(messages=NS(create=self.create))

    def create(self, **kw):
        self.calls += 1
        if self.calls == 1:
            return NS(stop_reason="tool_use", content=[NS(type="tool_use", id="t1", name="search_funding", input={"query": "maternal"})])
        assert kw["messages"][-1]["content"][0]["type"] == "tool_result"
        return NS(stop_reason="end_turn", content=[NS(type="text", text=self.final)])


def test_loop_runs_tools_and_returns_answer():
    r = chat_llm.ask("maternal funding?", client=FakeClient("Try [F007] https://example verified_on 2026-11-21"))
    assert r["trace"][0]["tool"] == "search_funding" and r["citations"] == ["F007"] and not r["invalid_ids"]


def test_invented_citation_is_flagged():
    r = chat_llm.ask("x", client=FakeClient("Apply to [F777]"))
    assert r["invalid_ids"] == ["F777"] and "not in the registry" in r["answer"]


def test_falls_back_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(chat_llm, "_load_env", lambda: None)
    r = chat_llm.ask("cryptocurrency mining")
    assert r["mode"].startswith("retrieval-only") and r["answer"] == "No verified entry; add one to the registry."
