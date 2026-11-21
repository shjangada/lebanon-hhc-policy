# Beqaa Health Prioritization Framework & Dashboard

2026 MIT Policy Hackathon (Born Global Foundation / Impossible Lebanon). Full brief: `CLAUDE.md`.

**Theme:** an adaptive funding switch for Beqaa primary care. Money follows measured need, and administrative control shifts from foreign NGOs to Lebanese entities (national NGOs, Unions of Municipalities, with MoPH co-governing) as measured capacity improves. Horizon 2030.

> **Everything currently runs on MOCK data** (synthetic cadasters, placeholder costs). The dashboard shows a red MOCK banner and watermarks every chart. Mock figures are never written to `outputs/memo/`. Real files in `data/raw/` override mock files of the same name automatically.

## Run
```
python3 -m venv .venv && source .venv/bin/activate && pip install -e . pytest
make mock     # generate MOCK data in data/mock/
make all      # mock + full pipeline -> data/processed/ and outputs/figures/
make test     # mock + pytest (30 tests)
make app      # Streamlit dashboard at http://localhost:8501
```
The Makefile uses `.venv/bin/python` (override with `make PY=python3 ...`).

## What the project does today (analyses and the data they use)

| Analysis (module) | What it answers | Data it uses | Status |
|---|---|---|---|
| **M1 Access** (`m1_access.py`): E2SFCA, pre-2026 vs 2026 closures, d0 sensitivity, mobile-unit siting (MCLP) | Q1: whose access is most constrained? | population, facilities, travel_time, cadasters | Runs on mock |
| **Group access** (`equity.py` + M1): access by host / displaced Lebanese / registered displaced Syrians / unregistered workers (est.) / women 15–49, gap vs host; optional demand weighting by group (WorldPop age/sex share × displacement counts × multiplier) | Q1, Q5: equity gaps | population (+ displacement columns) | Runs on mock; mock groups are near-uniform, so gaps are small until real data |
| **M2 Need Score** (`m2_need_score.py`): 4 domains, 5,000 Dirichlet weight draws → `p_top_tier` and rank intervals; comparison with JIAF/FSA district severity; map layers (need, environment) | Q1, Q5: where to prioritise | M1 output, M4 tiers, vulnerability, water_quality, official_severity | Runs on mock; weights, thresholds and safe/crisis values are **assumptions** |
| **M4 Exposure screen** (`m4_exposure.py`): HQ ranges (Cr speciation unknown), Pb vs EPA screening level, Monte Carlo, tornado (what evidence would change the response), tiers 0–3 with a/b/c evidence rungs | Q2, Q4 | soil_sites, crop_transfer, exposure_params.yaml | Soil **values are real** (CNRS-L/MoE 2026), **locations mock**; reference doses need confirming in EPA IRIS |
| **M5 Options & budget** (`m5_options.py`): $1k / $100k / $1M tiers, fundable-or-not, Monte Carlo extra completed pathways, cost per pathway, equity-gap change, collateral-damage checklist | Q3 | interventions, cascade_baseline | Runs on mock; costs and lifts are **mock** |
| **Community allocation** (`allocation.py`): top-down vs per-capita vs community-decided with capture safeguards | Q3 (team theme) | M2 scores, M5 effects, mock community priorities | Effect of local choice is an **assumption** (range 1.0–1.3), not an estimate |
| **Escrow & funding switch** (`escrow.py`): need floor + capacity tranche, editable thresholds, administrator ladder INGO → national NGO → Union of Municipalities (MoPH co-governs, not assumed to administer by 2030; renewed-escalation scenario), lock-out and gaming warnings, restricted vs unrestricted | Q3, Q5 | M2 scores, governance_capacity and staffing_referrals (mock **scenario inputs**: no public source, the pilot would measure them) | Runs on mock; thresholds are assumptions |
| **Funding finder + registry chat** (`funding_finder.py`, `chat.py`): rank registry rows, recency and "fits escrow?" flags; grounded retrieval that refuses when nothing matches | Q3 | `data/registry/*.csv` (8 funding rows, 7 org rows to verify) | Registry rows from team research 2026-11-21; re-check before use |

Dashboard: one page with five sections (Priority & access · Options & budget · Allocation & escrow · Soil & water triggers · Funding sources) plus evidence, assumptions and data in expanders. Interventions carry a feasibility filter (F1–F8) from `docs/FEASIBILITY.md`. Every mock file is listed in `data/registry/mock_provenance.csv` with the real source it stands in for and how obtainable it is (a test enforces this).

Not built yet: M3 network simulation, Workforce & network page, Pilot design page (stepped-wedge, PDIA log), case-study cards, notebook appendix, LLM layer for the registry chat.

## Data status
`data/raw/` holds real files; anything missing falls back to `data/mock/`.

| Dataset | Raw file | Status |
|---|---|---|
| cadasters | `data/raw/cadasters.csv` | 🔴 mock |
| population | `data/raw/population.csv` | 🔴 mock |
| facilities | `data/raw/facilities.csv` | 🔴 mock |
| travel_time | `data/raw/travel_time.csv` | 🔴 mock |
| vulnerability | `data/raw/vulnerability.csv` | 🔴 mock |
| official_severity | `data/raw/official_severity.csv` | 🔴 mock |
| soil_sites | `data/raw/soil_sites.csv` | 🔴 mock |
| water_quality | `data/raw/water_quality.csv` | 🔴 mock |
| crop_transfer | `data/raw/crop_transfer.csv` | 🔴 mock |
| interventions | `data/raw/interventions.csv` | 🔴 mock |
| cascade_baseline | `data/raw/cascade_baseline.csv` | 🔴 mock |
| staffing_referrals | `data/raw/staffing_referrals.csv` | 🔴 mock |
| governance_capacity | `data/raw/governance_capacity.csv` | 🔴 mock |

Reference series (do not affect the REAL/MOCK mode): wdi_population (Lebanon national series) in `data/raw/worldbank_population/` is ✅ real. It is national total population 1960–2025 for all countries (World Bank WDI), used for the Lebanon time series and as a national sanity check for cadaster populations. It is **not** cadaster-level, so it cannot replace `population.csv`.

Download checklist for the remaining real files: `scripts/fetch_real_data.md`.

## Principles (short)
Every number has a source and a status (`verified` / `assumption` / `mock`). Equity by group is reported in every model. Ranges and rank stability, not single numbers. Environmental claims carry rung a/b/c and nothing is ever tagged c without health data. One command rebuilds everything, with fixed seeds.
