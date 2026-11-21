"""One-sentence page answers, built from current outputs with templates (no LLM). Every number in a sentence comes from a named fact with a source: the templates themselves
contain no digits (a test enforces it), so no figure can appear without a source."""
from __future__ import annotations

import re

from dataclasses import dataclass, field


@dataclass
class Sentence:
    template: str
    facts: dict = field(default_factory=dict)          # name -> (formatted value, source)

    @property
    def text(self) -> str:
        return self.template.format(**{k: v[0] for k, v in self.facts.items()})

    @property
    def sources(self) -> dict:
        return {k: v[1] for k, v in self.facts.items()}


def pct(x) -> str:
    return "n/a" if x is None else f"{x:.0%}"


def usd(x) -> str:
    return "n/a" if x is None else (f"${x / 1e6:,.1f}M" if abs(x) >= 1e6 else f"${x:,.0f}")


def page1(lhf_share, lhf_year, flash_pct, gov_share, global_direct) -> Sentence:
    return Sentence("Only {global_direct} of humanitarian money went directly to local actors globally, against a {pledge} pledge; in Lebanon's pooled fund national NGOs got {lhf} of {year} budgets, "
                    "the {fa_year} Flash Appeal is {flash} funded, and the state pays {gov} of health spending.",
                    {"global_direct": ("n/a" if global_direct is None else f"{global_direct:.1%}", "ALNAP SOHS 2026 ch.4"), "pledge": ("quarter-of-funding", "Grand Bargain 2016 (ALNAP SOHS 2026 ch.4)"),
                     "lhf": (pct(lhf_share), "CBPF project summary (LHF)"), "year": (str(lhf_year), "CBPF project summary (LHF)"), "fa_year": ("2026", "OCHA FTS"),
                     "flash": (pct(flash_pct), "OCHA FTS"), "gov": (pct(gov_share), "SC02 K2P/UNICEF memo")})


def page2(top_names: list[str], district: str, share_top_in_district: float, n_target: int) -> Sentence:
    return Sentence("The highest-priority cadasters are {names}, {share} of the top ten sit in {district}, and {n} cadasters combine high exposure with low access.",
                    {"names": (", ".join(top_names[:3]), "M2 Need Score"), "share": (pct(share_top_in_district), "M2 Need Score"), "district": (district, "M2 Need Score"),
                     "n": (str(n_target), "M2 x M4 target list")})


def page3(share_2026, share_2030, scenario_label: str, share_2030_stall) -> Sentence:
    return Sentence("Under the {scenario} path local control of the escrow window rises from {a} in {y0} to {b} in {y1}, and stays at {c} if capacity stalls; the district capacity inputs are mock.",
                    {"scenario": (scenario_label, "escrow model"), "a": (pct(share_2026), "escrow model"), "b": (pct(share_2030), "escrow model"), "c": (pct(share_2030_stall), "escrow model, S5"),
                     "y0": ("2026", "escrow model horizon"), "y1": ("2030", "escrow model horizon")})


def page4(n_core: int, k: int, thr: float, minimax: str) -> Sentence:
    return Sentence("{n} cadasters stay in the top {k} in at least {thr} of draws and in every scenario, and {policy} has the smallest worst-case regret.",
                    {"n": (str(n_core), "robustness module"), "k": (str(k), "robustness module"), "thr": (pct(thr), "data/params/uncertainty.yaml"), "policy": (minimax.replace("_", " "), "robustness module")})


def page5(n_pool: int, n_direct: int, n_women: int) -> Sentence:
    return Sentence("{pool} registry rows could be pooled into the escrow, {direct} go straight to local groups, and {women} are open to women-led organisations; all are rows of funding_registry.csv with a source.",
                    {"pool": (str(n_pool), "funding_registry.csv"), "direct": (str(n_direct), "funding_registry.csv"), "women": (str(n_women), "funding_registry.csv")})


def template_has_digits(template: str) -> bool:
    return bool(re.search(r"\d", template))
