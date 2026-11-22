# Evidence and price tables: Beqaa environmental-health policy

Compiled 2026-11-21. Every figure was read from the source named in the `url` column; nothing was estimated. Where the primary page was blocked (PMC/PubMed captcha, paywall), a mirror of the same text was used (eScholarship, scilit, the publisher's accepted-manuscript PDF, an abstract mirror) and named in `notes`.

## Files
- `evidence.csv`: 37 rows. Rungs: a = environmental finding, b = exposure pathway/vulnerability, c = health effect. Geography: Beqaa / other Lebanon / international.
- `prices.csv`: 20 rows of unit costs and cost-effectiveness benchmarks.

## Meaning of `verified`
- **yes**: the figure was read on the source page or PDF (or on a mirror of the same article).
- **secondary**: the figure was seen only in a search snippet or a compilation, or it is a figure the source quotes from someone else. Check it before citing.
- **Derived** values (simple arithmetic on catalogue figures) are labelled "Derived" in `notes`.

## Key caveats (read before citing)
1. **Salvatore 2015**: the "-51% DAP" result is **not statistically significant**. Adjusted -51.3%, 95% CI -81.3 to +26.8, p=0.14 (Table 4).
2. **Thompson 2008**: null result. p=0.21 for urinary metabolites, p=0.49 for dust. Metabolite levels rose in both arms.
3. **EELI cord blood (Whaibeh et al., Sci Rep 2026)**: n=74, recruited in **Beirut/Mount Lebanon, not the Beqaa**. Proximity to agricultural land was linked to antimony in the bivariate analysis (p=0.033) and to nickel in the multivariate model (beta=0.118, p=0.011). The printed CI for nickel is internally inconsistent. Exposure was self-reported. The abstract does not mention agriculture.
4. **The 2026 IJHEH "106 pollutants in cord blood" paper is from La Palma, Spain (n=471)**, not Lebanon.
5. **Assaf & Saadeh 2009**: no percentage of nitrate above 50 mg/L is available, because the abstract has none and the full text is paywalled. For a number, use Darwish 2011 (12 of 21 Bekaa wells >200 mg/L; 1 of 21 drinkable).
6. **CNRS-L Apr 2026**: the repo values (Chmestar Cr 110-230; Bouday Cr 140, Pb 230; Ksarnaba Cr 170; Rayak Cr 220, total P 1858) are **confirmed** against the local PDF (pp.18, 20). These are **total Cr**. The report has no Cr(VI) data. Values are listed by village, with no sample IDs or coordinates.
7. **Agrimovement 2025**: the 94/126 figure for women living in tents (executive summary) conflicts with 90/120 in Section 4. The sample covers Bekaa **and Koura**. The 22% legal-residency figure is quoted from VASyR 2019, which was not opened.
8. **EMHJ 2024**: one sampling round (June 2023) on 10 rivers. The nitrate count is internally inconsistent (3 rivers in the abstract vs "half" in the discussion).
9. **Prices**: UNICEF figures are indicative ex-works catalogue prices and exclude freight and distribution. It is unclear whether the UNICEF H2S test price is per test or per box. No programme price was found for the Aquagenx CBT. Both Cr(VI) lab prices are from the **USA**; no Lebanese lab price was found. The cost-effectiveness figures in Clasen 2007 are in 2002 USD and need inflating before use. The rows from the DCP3 compilation are marked secondary.

## Not found / unverifiable
- Number of farmworker-child pairs in Thompson 2008.
- Aquagenx CBT unit price, and any Lebanese price for PPE or water tests.
- A Lebanese lab price for Cr(VI) speciation.
