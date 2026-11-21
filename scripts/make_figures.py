"""Memo figures from REAL / sourced data only -> outputs/memo/*.png (refuses to run if any dataset is entirely mock).

    python scripts/make_figures.py        (also: make appendix)

Six figures: 1 Why Beqaa; 2 funding to Lebanese actors (national + Beqaa proxy); 3 priority map with the evidence-gap layer; 4 escrow handover (design, scenario); 5 options with ranges and
break-evens (scenario); 6 robustness. Figures that depend on assumed inputs say so in the title. Every figure is regenerated from `make ingest && python -m beqaa.pipeline`."""
from __future__ import annotations

import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from beqaa import breakeven, escrow, io, m2_need_score as m2, robustness as rb, theme_kpi  # noqa: E402

OUT = ROOT / "outputs" / "memo"
PROC = io.PROCESSED
BLUE, RED, GREY, ORANGE = "#2874a6", "#c0392b", "#9aa5b1", "#e59866"


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print("wrote", OUT / name)


def fig1_why_beqaa():
    cad = io.load_dataset("cadasters").df
    pop = io.load_dataset("population").df.merge(cad[["cadaster_id", "district"]], on="cadaster_id")
    conf = io.load_dataset("conflict_exposure").df.merge(cad[["cadaster_id", "district"]], on="cadaster_id")
    a = pd.read_csv(PROC / "agesex_by_district.csv").groupby(["sex", "age_band"]).population.sum().unstack(0)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.6))
    y = np.arange(len(a))
    ax[0].barh(y, -a["male"], color=BLUE, label="men")
    ax[0].barh(y, a["female"], color="#b03a6e", label="women")
    ax[0].set_yticks(y[::2], [("90+" if b == 90 else str(b)) for b in a.index[::2]])
    ax[0].set_xlabel("people (modelled, WorldPop 2025)")
    ax[0].set_title("Who lives in the five districts")
    ax[0].legend(frameon=False)
    ax[0].xaxis.set_major_formatter(lambda v, _: f"{abs(v) / 1000:.0f}k")
    byd = pop.groupby("district").population_total.sum()
    inc = conf.groupby("district").conflict_incidents.sum() / byd * 1000
    inc = inc.sort_values()
    ax[1].barh(inc.index, inc.values, color=RED)
    ax[1].set_xlabel("conflict incidents per 1,000 people, Oct 2023 to Jul 2025 (LRP)")
    ax[1].set_title("Military action (stops before the 2026 war)")
    fig.suptitle("Why Beqaa: Beqaa Valley = Zahle, West Bekaa, Rachaya, Baalbek, Hermel", y=1.02)
    save(fig, "fig1_why_beqaa.png")


def fig2_funding():
    nat = pd.read_csv(PROC / "lhf_national_ngo_share_by_year.csv")
    bq = theme_kpi.beqaa_proxy_series()
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(nat.year, nat.national_ngo_share * 100, marker="o", color=BLUE, label="LHF, all projects (real)")
    ax.scatter(bq.year, bq.national_ngo_share * 100, color=RED, zorder=3, s=60, label="proxy: health projects whose title names Beqaa")
    ax.axhline(25, color=GREY, ls="--", lw=1)
    ax.text(nat.year.min(), 26, "25% Grand Bargain pledge (direct to local actors; 4.3% delivered in 2025, ALNAP)", fontsize=8, color="#555")
    ax.set_ylabel("% of project budgets to national NGOs")
    ax.set_ylim(0, 60)
    ax.set_title("Funding to Lebanese actors: national and Beqaa proxy (2026 partial year; proxy misses projects not naming Beqaa)")
    ax.legend(frameon=False, loc="upper left", fontsize=8)
    save(fig, "fig2_funding_lebanese_actors.png")


def fig3_priority_map():
    sc = m2.compute(m2.raw_indicators(), spec=m2.apply_quantile_anchors(m2.load_spec(), m2.raw_indicators()))
    fac = io.load_dataset("facilities").df
    soil = pd.read_csv(PROC / "soil_sites.csv").drop_duplicates("site_name")
    fig, ax = plt.subplots(figsize=(7.5, 8))
    gap = sc.env_evidence_gap
    ax.scatter(sc.lon[gap], sc.lat[gap], c=sc.need_score[gap], cmap="YlOrRd", s=34, vmin=0, vmax=sc.need_score.max(), edgecolor="#777", linewidth=0.6, label="environment evidence gap")
    h = ax.scatter(sc.lon[~gap], sc.lat[~gap], c=sc.need_score[~gap], cmap="YlOrRd", s=34, vmin=0, vmax=sc.need_score.max(), edgecolor="none", label="soil result within 15 km")
    ax.scatter(fac[fac.type == "PHC"].lon, fac[fac.type == "PHC"].lat, marker="+", c="#1a5276", s=26, label="MoPH-list centre (village position)")
    ax.scatter(fac[fac.type == "hospital_hub"].lon, fac[fac.type == "hospital_hub"].lat, marker="s", facecolor="none", edgecolor="#1a5276", s=40, label="hospital")
    ax.scatter(soil.lon, soil.lat, marker="*", c="black", s=150, label="soil sampled (rung a)")
    top = sc.nsmallest(10, "rank")
    ax.scatter(top.lon, top.lat, facecolor="none", edgecolor="#154360", s=130, linewidth=1.6, label="top 10 (district-reliable, cadaster = screening)")
    ax.set_title("Priority areas: need score and the evidence-gap layer\n(grey outline = no environmental evidence for that cadaster)", fontsize=10)
    ax.set_xlabel("longitude")
    ax.set_ylabel("latitude")
    ax.legend(frameon=False, fontsize=7, loc="upper left", bbox_to_anchor=(1.18, 1.0))
    plt.colorbar(h, ax=ax, shrink=0.6, label="need score (0-1)")
    save(fig, "fig3_priority_map.png")


def fig4_escrow():
    sc = m2.compute(m2.raw_indicators(), spec=m2.apply_quantile_anchors(m2.load_spec(), m2.raw_indicators()))
    path, _ = theme_kpi._escrow_path("baseline", sc)
    cols = {"usd_INGO": GREY, "usd_National NGO": "#7fb3d5", "usd_Union of Municipalities": BLUE, "usd_MoPH": "#0b3d63", "held_usd": ORANGE}
    share = path.set_index("year")[list(cols)]
    share = share.div(share.sum(axis=1), axis=0)
    fig, ax = plt.subplots(figsize=(8, 3.8))
    left = np.zeros(len(share))
    for c, col in cols.items():
        ax.barh(share.index.astype(str), share[c], left=left, color=col, label=c.replace("usd_", "").replace("held_usd", "held in escrow"))
        left += share[c].values
    ax.set_xlabel("share of released money by holder")
    ax.set_title("Escrow handover (DESIGN, scenario): capacity starts at the national anchor 0.299, +0.03/yr; thresholds pre-agreed")
    ax.legend(frameon=False, ncol=3, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    ax.invert_yaxis()
    save(fig, "fig4_escrow_handover.png")


def fig5_options():
    be = breakeven.allocation_breakevens(m2.compute(rb.scenario_raw(None, 30, 0.1, rb.load_uncertainty()), spec=m2.load_spec()))
    iv = pd.read_csv(PROC / "interventions.csv")
    iv = iv[~iv.is_mock.astype(bool)]
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.4), gridspec_kw={"wspace": 0.55})
    labels = [{"chw_women_orgs": "CHWs via women's orgs\n(per 10 CHW-years)", "soil_water_screening": "Soil + water screening\n(per catchment)", "mobile_maternal_unit": "Mobile maternal unit\n(per unit-year, proxy)"}.get(i, i) for i in iv.intervention_id]
    ax[0].hlines(labels, iv.cost_low_usd, iv.cost_high_usd, color=BLUE, lw=8)
    ax[0].set_xscale("log")
    ax[0].set_xlabel("cost per unit (USD, log scale; derived from sourced unit prices)")
    ax[0].set_title("Option costs: 5 further options have no published unit cost", fontsize=10)
    q = be[(be.comparison == "community vs status quo") & be.priorities.str.startswith("community picks") & be.parameter.isin(["capture", "local_fit"])].set_index("parameter")
    ax[1].barh(["capture rate\n(wins only below)", "local-fit multiplier\n(wins only above)"], [q.loc["capture", "flips_at"], q.loc["local_fit", "flips_at"]], color=[ORANGE, ORANGE])
    ax[1].scatter([0.10, 0.40, 1.0, 1.3], [0, 0, 1, 1], color="black", zorder=3, marker="|", s=300)
    ax[1].set_title("Break-even: 'community beats status quo' (best case)\nblack ticks = tested range (capture 0.10-0.40; local fit 1.00-1.30)", fontsize=10)
    ax[1].set_xlabel("break-even value (ASSUMED INPUTS: no Lebanon value is published)")
    save(fig, "fig5_options_breakeven.png")


def fig6_robustness():
    p = pd.read_csv(PROC / "robust_rank_per_cadaster.csv").head(12)
    cols = [c for c in p.columns if c.startswith("p_top_") and c != "p_top_overall"]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    im = ax.imshow(p[cols].values, cmap="Blues", vmin=0, vmax=1, aspect="auto")
    ax.set_yticks(range(len(p)), p.cadaster_name)
    ax.set_xticks(range(len(cols)), [c.replace("p_top_", "").replace("_", " ") for c in cols], rotation=30, ha="right", fontsize=7)
    for i in range(len(p)):
        for j in range(len(cols)):
            ax.text(j, i, f"{p[cols].values[i, j]:.1f}", ha="center", va="center", fontsize=7)
    ax.set_title("Robustness: share of draws in the top 8, by scenario (core set = every cell >= 0.8; only one cadaster qualifies)")
    plt.colorbar(im, ax=ax, shrink=0.7)
    save(fig, "fig6_robustness.png")


def main():
    if io.any_mock():
        sys.exit("refusing to write memo figures: a dataset is entirely mock")
    for f in (fig1_why_beqaa, fig2_funding, fig3_priority_map, fig4_escrow, fig5_options, fig6_robustness):
        f()


if __name__ == "__main__":
    main()
