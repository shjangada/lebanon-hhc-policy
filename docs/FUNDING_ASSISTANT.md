# Funding and eligibility assistant (section 5, Funding sources)

**What it is.** A funding navigator for Lebanese local actors, not a general "ask anything about Lebanon health" bot. It lowers the cost of *direct access*: small organisations and municipalities rarely know which funds they qualify for or what they would need to move up the escrow ladder, and international NGOs have grant teams for exactly this. It supports the theme (money and decisions in Lebanese hands) and the Grand Bargain's local-funding goal.

**Built on structured filters; chat is an optional layer.** If time runs short, drop the chat and keep the checker: almost nothing is lost.

| Query | Where | How |
|---|---|---|
| "We are a women-led group in Baalbek. Which funds can we apply to now?" | Eligibility checker | `eligibility.eligible_funds`: registry rows filtered by `local_org_eligible`, `status`, `channel`, women-only funds (keyword), with the reason for each row. Closed annual calls show as "expected next round". `to_verify` rows are "check eligibility", never "yes" |
| "What do we need to move up a rung?" | Rung-gap check | `eligibility.threshold_gaps`: compares self-reported capacity, transparent reporting, referral completion and posts filled with the escrow thresholds (`data/params/escrow_params.yaml`) and lists the gaps to the next rung |
| "Which high-need cadasters still have no funded partner?" | Donor view | `eligibility.uncovered_priority_cadasters`: high-need cadasters from the need score. **Partner presence is "unknown"**: FTS and the Lebanon Humanitarian Fund report funding for Lebanon as a whole (no district or cadaster); the Health Sector 4W/5W is not public (`docs/MANUAL_STEPS.md`) |

**Rules.**
- Never invents a grant: every row is a registry row with its source URL and `verified_on`. The page states "registry last verified on [date]" and how many rows are `to_verify` or older than six months.
- Retrieval-only by default. The optional Claude layer only phrases what the tools return, cites registry ids, and flags invented ids (`chat_llm.py`; CLAUDE.md section 9).
- Eligibility is the registry's, read mechanically. Women-only funds are detected by keyword (women, feminist, girls, gender in the name or sectors).

**Feasibility by 2030: someone must own the registry.** Proposed owner: the Lebanon Humanitarian Fund's localisation staff, a Lebanese NGO network or the municipal union. Routine: every row older than six months is re-checked against its source URL and re-dated; new calls are added with a source. Without an owner the tool fails the feasibility filter (F5, F8).

**Language.** Real users need Arabic. The prototype is English-only; say so in the pitch.

**Pitch time.** About 20 seconds of a five-minute pitch: "and here is how a local group acts on this". It is not a headline feature.

**Not done.** Fiscal-host schemes for unregistered groups (the registry does not list any), partner locations (no public 4W), Arabic.
