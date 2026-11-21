"""Plot helpers. Every figure built on mock data gets a red 'MOCK DATA' watermark (principle 2)."""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

WATERMARK = "MOCK DATA"


def watermark(ax_or_fig, is_mock: bool):
    if not is_mock:
        return None
    fig = ax_or_fig.figure if hasattr(ax_or_fig, "figure") else ax_or_fig
    return fig.text(0.5, 0.5, WATERMARK, color="red", alpha=0.25, fontsize=46, rotation=25, ha="center", va="center", weight="bold", zorder=100)


def priority_map(scored: pd.DataFrame, is_mock: bool, path, top_k: int = 8):
    fig, ax = plt.subplots(figsize=(7, 7))
    sc = ax.scatter(scored.lon, scored.lat, c=scored.need_score, s=scored.population_total / 100, cmap="YlOrRd", edgecolor="grey", alpha=0.85)
    top = scored.nsmallest(top_k, "rank")
    ax.scatter(top.lon, top.lat, s=top.population_total / 100 + 80, facecolors="none", edgecolors="black", linewidths=1.6, label=f"Top {top_k}")
    fig.colorbar(sc, label="Need Score (0–1)")
    ax.set_title("Beqaa Need Score by cadaster"); ax.set_xlabel("lon"); ax.set_ylabel("lat"); ax.legend(loc="lower right")
    watermark(fig, is_mock)
    fig.savefig(path, dpi=150, bbox_inches="tight"); plt.close(fig)


def access_lost(acc: pd.DataFrame, is_mock: bool, path):
    a = acc.sort_values("access_lost", ascending=False).head(15)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(a.cadaster_name, a.access_baseline * 1000, color="#bbb", label="Pre-2026 (all open)")
    ax.barh(a.cadaster_name, a.access_current * 1000, color="#c0392b", label="Current 2026")
    ax.invert_yaxis(); ax.set_xlabel("Weekly ANC-capable capacity per 1,000 women 15–49 (E2SFCA)")
    ax.set_title("Access lost to 2026 closures (15 most affected cadasters)"); ax.legend()
    watermark(fig, is_mock)
    fig.savefig(path, dpi=150, bbox_inches="tight"); plt.close(fig)
