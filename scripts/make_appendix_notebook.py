"""Writes notebooks/appendix.ipynb (plain JSON, no nbformat needed). The notebook rebuilds every memo figure and table from `make ingest` and `python -m beqaa.pipeline`.
Regenerate the notebook with this script; run it with Jupyter (`jupyter nbconvert --to html --execute notebooks/appendix.ipynb`) if installed."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def md(t):
    return {"cell_type": "markdown", "metadata": {}, "source": t.strip("\n").splitlines(True)}


def code(t):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": t.strip("\n").splitlines(True)}


cells = [
    md("""# Appendix: reproducing the analysis
Beqaa health prioritisation and funding handover (2026 MIT Policy Hackathon). **Beqaa Valley = Zahle, West Bekaa, Rachaya, Baalbek, Hermel.** Every number traces to `data/registry/sources.csv` or carries an assumption label.
Run order: `make ingest` (raw files to `data/processed`), `python -m beqaa.pipeline` (models), `python scripts/make_figures.py` (figures in `outputs/memo`). ACLED is not used; the HDX ACLED district-month file and the pack's damage figures are context only."""),
    code("""import subprocess, sys, pathlib
ROOT = pathlib.Path.cwd().parent if pathlib.Path.cwd().name == 'notebooks' else pathlib.Path.cwd()
def run(*args):
    r = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)
    print(r.stdout[-1500:] or r.stderr[-1500:])
run('-m', 'beqaa.ingest', 'all')          # step 1: raw -> processed (real, schema-compatible, provenance columns)"""),
    code("""run('-m', 'beqaa.pipeline')                # step 2: M1 access, M2 need score, M4 exposure, M5 options, robustness, break-evens, riders"""),
    code("""run('scripts/make_figures.py')             # step 3: memo figures (refuses to run if a dataset is entirely mock)"""),
    md("## Data status (what is real, what is a proxy, what was removed)"),
    code("""import sys; sys.path.insert(0, str(ROOT / 'src'))
import pandas as pd
from beqaa import io
io.data_status()"""),
    md("## Figures\n1 Why Beqaa; 2 funding to Lebanese actors (national and Beqaa proxy); 3 priority map with the evidence-gap layer; 4 escrow handover (design, scenario); 5 options with break-evens (assumed inputs); 6 robustness."),
    code("""from IPython.display import Image, display
for f in sorted((ROOT / 'outputs' / 'memo').glob('fig*.png')):
    print(f.name); display(Image(filename=str(f)))"""),
    md("## Break-evens and escrow thresholds (`breakeven.csv`)"),
    code("""be = pd.read_csv(ROOT / 'data/processed/breakeven.csv')
be[be.kind == 'allocation'][['comparison', 'parameter', 'priorities', 'flips_at', 'central_value', 'ratio_at_centre', 'reading']]"""),
    code("""be[be.kind == 'escrow release'][['threshold', 'release_needs', 'current_assumed', 'reading']]"""),
    md("## Robust core set, regret and rank intervals"),
    code("""print((ROOT / 'data/processed/robust_core_set.txt').read_text())
pd.read_csv(ROOT / 'data/processed/robust_regret_summary.csv').round(1)"""),
    md("## Rider costs from sourced unit prices (`riders.csv`)"),
    code("""r = pd.read_csv(ROOT / 'data/processed/riders.csv')
r[['project_id', 'hook_type', 'districts', 'nearest_phc', 'phc_minutes', 'rider_cost_low_usd', 'rider_cost_central_usd', 'rider_cost_high_usd', 'rider_pct_of_budget_central', 'verified']]"""),
    md("""## Documents behind the numbers
`docs/EVIDENCE_TABLE.md` (rung a/b/c per claim, verification status) · `docs/ASSUMPTIONS_PILOT.md` (what we assume, what the pilot measures) · `docs/HEADLINE_AUDIT.md` (inputs behind every output) ·
`docs/STAKEHOLDERS.md` · `docs/NARRATIVE.md` (options A/B/C, collateral-damage check) · `docs/RIDER_SHORTLIST.md` (verification of the shortlisted projects) · `docs/DATA_REQUESTS.md` (data requested; the analysis uses published proxies and scenario ranges until received)."""),
    code("""run('-m', 'pytest', '-q')                  # tests"""),
]
nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
out = ROOT / "notebooks" / "appendix.ipynb"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(nb, indent=1))
print("wrote", out)
