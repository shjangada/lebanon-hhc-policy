# Methods decision log: how we chose the formulas, weights and thresholds

**Purpose.** The Barake et al. paper gives no formula, weights or thresholds for the Need Score. Everything below is our operationalisation, so each choice needs a defensible origin. This log records, for each decision: the options we considered, what comparable indices do, what we chose and why, how we test that the choice does not drive the result, and what is still unverified.

**Rule used throughout.**
1. Where a published standard exists for the exact quantity (e.g. the Lebanon Health Sector severity annex), use it and cite it.
2. Where comparable indices converge on a convention (e.g. equal weights absent evidence), adopt the convention.
3. Where neither exists, state the value as an **assumption**, set it by a stated *rule* (not a hand-picked number) where possible, and **test whether the ranking depends on it**. A choice that does not change the priority set needs little defence; a choice that does must be reported as a driver.
4. Never present a mock-data result as a finding. The sensitivity numbers quoted here come from mock data and show the method, not the Beqaa result. Re-run on real data (`data/processed/m2_method_sensitivity.csv`).

Sources are in `data/registry/sources.csv` (S36–S44, plus S25/S26/S35 for allocation evidence). Items marked **verify** were found by search summary only: read the primary document before the memo cites them.

---

## 1. What comparable indices do

| Index / method | Structure | Normalisation | Weights | Aggregation | Cut-offs / classes | Source |
|---|---|---|---|---|---|---|
| **INFORM Risk** (EC JRC) | 3 dimensions (hazard & exposure, vulnerability, lack of coping capacity), categories, indicators | min-max style rescaling with defined bounds (per-indicator; full rule to verify) | equal within dimension | **geometric mean** across dimensions (risk = 0 if any dimension is 0) | five risk classes | S38 |
| **INFORM Severity** (JRC/ACAPS) | impact × conditions of people + complexity | rescaled to 0–10 (Feb 2026 revision) | by formula (most sensitive to conditions of affected people) | mix of min, max, geometric and arithmetic means by level | five severity levels (boundaries to verify) | S39 |
| **JIAF 2.0** (IASC) | sector severity on a five-phase scale; people in need = phases 3–5 | absolute severity scales (same scale across space and time) | none across sectors | overall PiN taken from the **highest sectoral PiN** ("mosaic") | phase 1–5 (thresholds to verify in the Technical Manual) | S43 |
| **Lebanon Health Sector PiN/severity** (2024 annex) | health resources, health status, contextual factors | indicator thresholds mapped to severity bands | not retrieved | not retrieved | PHC per 50,000: bands from >3 (lowest severity) to 0.5 (highest); 20% threshold for people reporting two or more barriers | S37 (verify the band mapping) |
| **CDC Social Vulnerability Index** | 16 variables in 4 themes | **percentile rank** within the reference set (0–1) | **all variables and all themes weighted equally** (users may reweight) | sum of percentile ranks, re-ranked | none fixed (users choose, e.g. top quartile) | S42 |
| **HRSA Index of Medical Underservice** | 4 variables (providers per population, infant mortality, poverty, share aged 65+) | each converted to points by fixed tables | fixed point scales (exact points to verify) | **sum** of the four values (0 = worst, 100 = best) | **62.0 or below qualifies** for designation | S41 |
| **HDI (UNDP)** | 3 dimensions | min-max with fixed goalposts | equal | arithmetic until 2010, then **geometric** to reduce compensability | none | S44 |
| **OECD/JRC composite-indicator handbook** | 10-step method | min-max common; method should fit framework | equal weights, factor analysis, derived weights, DEA | arithmetic, geometric, Borda, Copeland | n/a | S40 |
| **E2SFCA** | spatial access | n/a | n/a | n/a | Luo & Qi used three travel-time zones with fixed weights; continuous (e.g. Gaussian) decay is a later refinement | S36 |

**What the precedents tell us.** (a) Equal weights are the standard default when there is no evidence for unequal ones (SVI, INFORM within dimensions, HDI). (b) Aggregation is the genuinely contested choice: sums (SVI, HRSA) treat deficits as substitutable, geometric means (INFORM Risk, HDI) reduce substitutability, and JIAF takes the worst sector. (c) Fixed absolute anchors (JIAF, HDI, Health Sector thresholds) keep scores comparable over time, percentile ranks (SVI) do not. (d) The JRC handbook's core advice is to test alternatives and report which assumptions move the result, which is what `method_sensitivity()` does.

---

## 2. Decisions

### D1. Framework: four domains
**Chosen:** clinical demand, capacity strain, vulnerability, environment.
**Options:** INFORM's hazard/vulnerability/coping structure; the Health Sector's resources/status/context; SVI's themes.
**Why:** it maps onto the Health Sector's logic (resources ≈ capacity strain, status ≈ clinical demand, context ≈ vulnerability) and adds the environment domain the challenge requires, kept separate so that **environmental findings are never merged into confirmed health outcomes** (evidence rungs a/b/c, principle 3).
**Test:** drop-one-domain variants (D10). **Status:** structure is a judgement; the sensitivity table shows how much each domain matters.

### D2. Normalisation: fixed "safe/crisis" goalposts
**Chosen:** `s = clip((x − safe)/(crisis − safe), 0, 1)` per indicator, with anchors in `need_score_indicators.yaml`.
**Options:** percentile rank (SVI); z-scores; min-max over the sample.
**Why:** absolute anchors match JIAF and the Health Sector annex (a score means the same thing next quarter and in another district) and let us report *how far from crisis* an area is. Percentile ranks make every score relative to the cadasters included, so adding or removing areas moves everyone.
**Test:** percentile variant in `method_sensitivity()`. **Status:** done; see D6 for how anchors are set.

### D3. Aggregation: weighted arithmetic mean (default), geometric and "worst domain" as tests
**Chosen:** mean of indicators within a domain; weighted arithmetic mean across domains.
**Options:** geometric mean (INFORM Risk, HDI); maximum / worst domain (JIAF's mosaic logic); sum of ranks (SVI, HRSA).
**Why:** INFORM Risk uses a geometric mean because risk needs hazard *and* vulnerability *and* lack of coping capacity: if one is absent, risk is absent. Need is different: a town with a severe access gap is in need even if its vulnerability score is modest. That argues against a conjunctive rule. The arithmetic mean is the transparent, communicable default (the handbook stresses communicability); but arithmetic lets a high score in one domain be offset by a low one, so we report the geometric and worst-domain versions.
**Test:** `aggregation: geometric` and `aggregation: max` variants. On mock data these change the top-8 membership more than any weight change (Spearman ≈ 0.7 and 0.6, 5 of 8 retained). **This is the choice most likely to matter and must be re-tested on real data; if it moves the priority set, report the set that survives all three and treat the rest as contested.**
**Status:** default chosen; sensitivity is the defence.

### D4. Weights: equal across domains
**Chosen:** 0.25 each (changed from an earlier unjustified 0.25/0.30/0.30/0.15).
**Options:** expert weights; PCA/factor weights; "benefit of the doubt" (DEA); equal.
**Why:** equal weights are the convention when there is no evidence for unequal ones (SVI; handbook lists them as the common choice). Our earlier unequal weights had no source and we could not defend them. Expert or participatory weights are better in principle: the pilot's community panels could supply them (open question for the team); until then equal weights plus uncertainty analysis.
**Test:** three "heavy" variants (0.4 on one domain) and 5,000 Dirichlet draws over domain weights (`robustness()` → `p_top_tier`, rank intervals). **Status:** equal weights adopted; stable priority cadasters are those with high `p_top_tier` under all draws.
**Note:** the team brief mentions a Health Sector annex weighting of 30% resources / 70% services. We could not retrieve that weighting from the annex search (S37): verify before citing.

### D5. Tiers: absolute bands for the response package, relative top-k for "where first"
**Chosen:** High ≥ 0.66, Moderate 0.33–0.66, Low < 0.33 (assumption, exposed as sliders); allocation uses the top-k cadasters (default k = 8) by score.
**Options:** five phases like JIAF/INFORM; quantile tiers; a single cut-off like HRSA's 62.0.
**Why:** the response package (what to do) needs an absolute meaning; the budget decision (where first) is inherently relative because funds are finite, as with HRSA's ranking of designated areas by score. Equal-interval bands are the simplest rule that does not pretend to precision. With the equal-weight mean of many indicators, scores compress toward the middle, so on mock data nearly every cadaster is "Moderate": that is a reason the app colours by continuous score and uses top-k, not a reason to move the thresholds to produce spread.
**Test:** `p_top_tier` (rank stability) does not depend on the tier thresholds. **Status:** thresholds are assumptions; revisit when real scores exist (consider JIAF-style five phases).

### D6. Indicator anchors: published where possible, otherwise a data rule, otherwise tested assumption
Every indicator in `need_score_indicators.yaml` carries `anchor:`.
- **published:** `phc_per_50k` uses the Health Sector annex bands (>3 lowest severity to 0.5 highest → safe 3, crisis 0.5; earlier we had 2→0 labelled "verified", which was wrong); `nitrate_mg_l` crisis anchor is the WHO guideline value of 50 mg/L. **Verify** the band-to-severity mapping against the annex.
- **quantile:** `pregnant_per_1000`, `women_share`, `unregistered_workers_share`, `conflict_incidents`: no published threshold exists. Rule: once real data are loaded, set safe/crisis to the **10th/90th percentile** of the real cadaster distribution (`apply_quantile_anchors`), the way goalposts are taken from the observed range in the HDI. Until then the hand-set placeholders are flagged as assumptions.
- **assumption:** the rest (district-level IPC, insurance, female-headed households, access deficit): hand-set, flagged; tested by the drop-indicator and weight variants.
**Why not just pick numbers:** a percentile rule can be re-run and explained in one sentence; a hand-picked number cannot be defended.
**Status:** rule implemented and tested; to be applied when real data are the default.

### D7. Capacity strain uses our own access measure, anchored to the pre-2026 median
**Chosen:** `access_deficit = 1 − (current access / pre-2026 median access)`, clipped to [0, 1].
**Why:** it expresses lost capacity relative to the system's own baseline, avoiding an arbitrary absolute capacity target. **Limitation:** facilities come from OSM and cover only ~15% of MoPH-network PHCs (`facilities_coverage.csv`), so on real data this indicator is understated until the MoPH locator is added.

### D8. Missing data
Nitrate: cadasters without a well take the district median (flagged `nitrate_imputed`); then the global median. Imputation affects only the environment domain and is tested by `drop domain: environment`. JRC: report the imputation method (done here); full multiple imputation is not warranted at this data quality.

### D9. Access model (E2SFCA)
**Chosen:** Gaussian continuous distance decay within a catchment d0 (default 30 minutes; 15 and 60 as sensitivity); stepped zones available.
**Correction made:** we had attributed the Gaussian form to Luo & Qi (2009). They used stepped travel-time zones; continuous decay (e.g. Gaussian) came in later work (to cite properly: verify). The stepped weights in the code (1, 0.68, 0.22) are from memory: verify against S36.
**Why Gaussian:** avoids arbitrary zone edges. **Test:** d0 sensitivity and the stepped variant.

### D10. Robustness protocol (what we report)
1. Rank stability under 5,000 random domain-weight draws (`p_top_tier`, rank 5th–95th percentile).
2. Method sensitivity (`method_sensitivity()`): geometric and max aggregation, percentile normalisation, three heavy-weight variants, drop-one-domain, drop unregistered workers. Reported as Spearman correlation, top-k overlap and maximum rank shift against the reference.
3. Comparison with official district severity (JIAF/FSA), including cadasters the district map hides.
4. **Claim rule:** a cadaster is called a priority only if it stays in the top-k across the variants that matter (aggregation, weights); otherwise it is "sensitive to method" and the memo says so.

### D11. Exposure screen (M4)
Hazard quotient threshold HQ = 1 (US EPA convention); child soil ingestion 200 mg/day and body weight 15 kg, adult 100 mg/day and 70 kg (EPA defaults); reference doses Cr(III) 1.5 and Cr(VI) 0.003 mg/kg-day and the lead soil screening level of 200 mg/kg (EPA 2024) are all marked `verify` in `exposure_params.yaml`. The chromium(VI) fraction is the unknown that drives the result (HQ ≈ 0.002 to 0.98 for Chemstar soil-only), so we report the range, never a point value. Tier 2 means a **plausible exposure pathway (rung b)**; rung c (demonstrated health effect) is never assigned without health data. The food-pathway transfer factors are mock until Abi Saab et al. (2022) are transcribed.

### D12. Allocation and escrow parameters
Community-decided allocation, local-fit multiplier (1.0–1.3), capture rate (0.1–0.4), escrow thresholds and administrator bands are **assumptions with no empirical estimate for Lebanon**. Evidence on community-driven development is mixed (3ie WP30; Mansuri & Rao 2013): improves facilities, not governance or cohesion. They are framed as pilot test arms and shown with a sensitivity grid (see `docs/FEASIBILITY.md`).

---

## 3. What is not defensible yet (open items)

| Item | Why open | What closes it |
|---|---|---|
| Health Sector annex bands and weights | only a search summary was read | read the annex (S37): confirm PHC per 50,000 band mapping, the 20% barrier threshold and any 30/70 weighting |
| JIAF and INFORM class boundaries | thresholds not retrieved | read S43 and S39 and decide whether to adopt five phases for D5 |
| Quantile anchors | need real indicator distributions | apply `apply_quantile_anchors` after the cadaster-level converters are the default |
| Stepped weights 1 / 0.68 / 0.22 and the later-work citation for Gaussian decay | from memory | read S36 and find the citation |
| Equal weights vs participatory weights | no community input yet | pilot panel exercise (team decision) |
| Aggregation sensitivity on real data | mock result only | re-run `m2_method_sensitivity.csv` on real data and apply the claim rule (D10) |

## 4. How to keep this current
`python -m beqaa.pipeline` writes `data/processed/m2_method_sensitivity.csv` and `assumptions.csv` every run; the dashboard shows both. When a decision changes, edit the yaml (not the code), re-run, and update the relevant D-entry and the status table above.
