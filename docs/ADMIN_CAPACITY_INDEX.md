# admin_capacity_index (0-1): definition and data limits

Status: documented, NOT yet computable at Beqaa / Baalbek-Hermel municipality or district level. Read "Coverage" first.

## Coverage (finest level the evidence supports)

Source: UN-Habitat Lebanon, Rapid Municipal Assessment 2026 (conflict), survey 16-29 April 2026, PDF in `data/raw/unhabitat_rma/rma_2026.pdf`. Extracted values: `transcribed/unhabitat_rma_2026.csv`.

- The report publishes only aggregate percentages for a national sample of 38 responding municipalities (59 targeted; 21 did not respond; sample is selected for IDP concentration, not random).
- It publishes no per-municipality, per-district or per-governorate indicator values. The only geographic detail is the Annex (p. 36), a list of the 38 responders.
- Responders in our area (10 of 38): Baalbek-Hermel: Deir El-Ahmar and Ras Baalbek (Baalbek district), Hermel (Hermel district). Bekaa: Ghazzeh (West Bekaa); Chtaura, Hazerta, Bar Elias, Majdel Anjar, Qab Elias-Ouadi El-Delm, Kfarzabad (Zahleh). No Rachaya or Baalbek city. No Union of Municipalities level data.
- Finest level with values: national sample. Finest level covered by list membership: municipality (10 in Bekaa/Baalbek-Hermel, value = "included in survey" only).
- Consequence: no district or governorate differences can be estimated from this source. Any district-level index would have to come from another source (e.g. UNDP/LADE/MoIM municipal data, registry rows SC08-SC10) or from a request to UN-Habitat for the municipal microdata.
- Data are perception-based self-reports (report p. 14), which adds bias.

## Components (only indicators actually found)

All oriented so higher = more administrative capacity, scaled 0-1. Values are the national-sample figures.

| id | component | formula from RMA indicator(s) | value | RMA page / figure |
|---|---|---|---|---|
| C1 | operational_functionality | 1 - (severe disruption + barely functioning)/100 = 1 - (34+18)/100 | 0.48 | p. 15, Figure 2 |
| C2 | external_support_received | 1 - share receiving no support = 1 - 0.79 | 0.21 | p. 27 text |
| C3 | technical_staff_profile | mean of shares of municipalities having engineers (0.34), IT officers (0.21), social workers (0.08), urban planners (0.03) | 0.165 | p. 19, Figure 5 |
| C4 | spending_headroom | 1 - share reporting increased spending = 1 - 0.79 | 0.21 | p. 27, Figure 15 |

Excluded on purpose:
- Asset damage (24% of municipalities; 1,407 buildings, ~1,100 in Tyre): an exposure measure, not capacity, and driven by one municipality. Available as a sensitivity add-on (C5 = 1 - 0.24 = 0.76).
- Revenue levels, budgets, staff counts per municipality: not published (only Beirut ~1,200, minimum 2, majority 5-50 staff, no distribution by area).
- Service functioning by service (water, waste, electricity): only reported as share of municipalities under pressure (Figures 9-10), not as functioning rates, so not entered.

## Formula

For municipality or district `g` with available components `k` in K_g and weights `w_k` (sum over available = 1 after renormalisation):

    admin_capacity_index_g = sum_k( w_k * C_k,g ) / sum_k( w_k )   over k in K_g

Default weights: equal, w_k = 1/4 for C1-C4.

Missing-data handling:
- If a component is missing for `g`, drop it and renormalise the remaining weights (above). Require at least 2 of 4 components, else index = NA.
- Never impute a municipality value from the national sample into a published municipal series. If a national-sample prior is needed as a fallback it must be flagged `source = national_prior`.
- Components are scaled by definition to 0-1, so no min-max rescaling across places is used (avoids spurious spread when few places are observed).

## Value computable now

With the only data available (national sample), equal weights:

    admin_capacity_index_national_sample = (0.48 + 0.21 + 0.165 + 0.21) / 4 = 0.266

This is one number for the whole sample (interpretation: low capacity under stress). It is NOT a Beqaa or Baalbek-Hermel estimate and must not be mapped as place-varying. Use it only as a flat prior or to anchor the scale.

## Weights to feed to the robustness module

Each set sums to 1. Order: C1, C2, C3, C4.

| scenario | C1 | C2 | C3 | C4 |
|---|---|---|---|---|
| equal (default) | 0.25 | 0.25 | 0.25 | 0.25 |
| drop C1 | 0 | 0.3333 | 0.3333 | 0.3333 |
| drop C2 | 0.3333 | 0 | 0.3333 | 0.3333 |
| drop C3 | 0.3333 | 0.3333 | 0 | 0.3333 |
| drop C4 | 0.3333 | 0.3333 | 0.3333 | 0 |
| capacity-heavy (staff and function) | 0.35 | 0.15 | 0.35 | 0.15 |
| finance-heavy | 0.15 | 0.35 | 0.15 | 0.35 |
| C1 only | 1 | 0 | 0 | 0 |
| add damage C5 (equal over 5; C5 weight 0.2) | 0.2 | 0.2 | 0.2 | 0.2 |

Because all four component values are national constants today, the robustness module can only vary the national-sample number (range across these weights 0.195 with C1 dropped to 0.48 with C1 only); place rankings will be unaffected until municipal or district data exist.

## To make this usable for Beqaa

1. Obtain municipal-level RMA microdata from UN-Habitat for the 10 Bekaa/Baalbek-Hermel responders (still only 10 places).
2. Or construct the index from a different source with district coverage and keep the RMA as a validation of the national level.
3. Record transcription provenance of any added indicators with `transcribed_by` and two-pass `checked` flags as in `transcribed/`.
