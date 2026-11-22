# Appendix index (reproducibility)

One command rebuilds everything from `data/`: `make appendix` (= `make ingest`, `python -m beqaa.pipeline`, `scripts/make_figures.py`, `scripts/make_implementation.py`, `scripts/make_sources_list.py`, `scripts/make_appendix_notebook.py`). `notebooks/appendix.ipynb` runs the same steps and shows the figures and tables. Repo: github.com/shjangada/lebanon-hhc-policy. Tests: `make test` (the notebook was generated, not executed here: run it with Jupyter).

| Item | Where | Notes |
|---|---|---|
| 13 figures at 2x scale with source lines | `figures/` (mirrored in `outputs/memo/`) | real or sourced data only; figures 4, 5, 9-12 rest on assumptions and say so |
| Evidence table (rung a / b / c, geography, verification) | `docs/EVIDENCE_TABLE.md` | no rung (c) for Beqaa; research-pass figures checked against the abstracts, with caveats |
| Assumptions and what the pilot measures | `docs/ASSUMPTIONS_PILOT.md` | 22 rows; break-evens quoted and tested against `breakeven.csv` |
| Headline audit | `docs/HEADLINE_AUDIT.md` | every memo number traced to a file and a source, with status |
| Trigger table (Q2), options, route, implementation and budget | `docs/TRIGGERS.md`, `OPTIONS.md`, `DECISION_ROUTE.md`, `IMPLEMENTATION.md` | the budget is generated from the model and tested |
| Stakeholders, narrative (with the grapevine framing), objections | `docs/STAKEHOLDERS.md`, `NARRATIVE.md`, `OBJECTIONS.md` | |
| Methods | `docs/METHODS_DECISIONS.md`, `FEASIBILITY.md`, `MODEL_LINKAGE.md`, `COSTS.md`, `FACILITIES_MOPH.md` | |
| Data sources with access dates; data status; proxies and data requests | `docs/DATA_SOURCES.md`, `DATA_STATUS.md`, `DATA_REQUESTS.md`, `MANUAL_STEPS.md` | no dataset is entirely mock; nothing was sent |
| Break-evens, rank stability, sensitivity | `data/processed/breakeven.csv`, `src/beqaa/breakeven.py`, `start_site.rank_stability`, `sensitivity.py` | scenario parameters have no published value |
| Rider shortlist and verification | `docs/RIDER_SHORTLIST.md`, `data/registry/projects_verification.csv` | most project pages could not be opened |
