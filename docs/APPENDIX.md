# Appendix index (reproducibility)

One command rebuilds everything from `data/`: `make appendix` (= `make ingest`, `python -m beqaa.pipeline`, `scripts/make_figures.py`, `scripts/make_appendix_notebook.py`). `notebooks/appendix.ipynb` runs the same steps and shows the figures and tables.

| Item | Where | Notes |
|---|---|---|
| Figures 1-6 | `outputs/memo/` | real or sourced data only; fig 4 and 5 are scenario views (assumed inputs, labelled) |
| Break-evens | `data/processed/breakeven.csv` | `src/beqaa/breakeven.py`, tested |
| Rider costs | `data/processed/riders.csv` | `src/beqaa/riders.py`: sourced unit prices times assumed sample counts |
| Data status | `docs/DATA_STATUS.md`, `docs/MOCK_VS_REAL.md`, README | no dataset is entirely mock |
| Evidence (a/b/c) | `docs/EVIDENCE_TABLE.md` | no rung (c) for Beqaa |
| Assumptions to pilot | `docs/ASSUMPTIONS_PILOT.md` | break-evens quoted and tested against `breakeven.csv` |
| Headline audit | `docs/HEADLINE_AUDIT.md` | inputs and status of every dashboard output |
| Stakeholders, narrative, collateral damage | `docs/STAKEHOLDERS.md`, `docs/NARRATIVE.md` | options A/B/C |
| Rider shortlist and verification | `docs/RIDER_SHORTLIST.md`, `data/registry/projects_verification.csv` | most project pages could not be opened |
| Data requests (not sent) | `docs/DATA_REQUESTS.md` | analysis uses published proxies and scenario ranges until received |
| Tests | `tests/` (`make test`) | the notebook was generated, not executed here: run it with Jupyter |
