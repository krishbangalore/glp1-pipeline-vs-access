# GLP-1 Peptide Drug Pipeline vs. Accessibility

**A SQL/Python analysis of how the FDA shortage listing, not only commercial growth, shaped the GLP-1 market, and what that precedent suggests about how Eli Lilly may commercialize retatrutide.**

---

## The Question

GLP-1 receptor agonist drugs (semaglutide, tirzepatide and related drugs) became household names between 2022 and 2026, driven by demand that outpaced supply. That shortage had a specific legal consequence: while a drug is on FDA's shortage list, compounding pharmacies may legally make copies of it, which created a parallel low-cost market. This project asks whether that accessibility window, and not just organic R&D growth, changed the competitive and regulatory dynamics of the GLP-1 space. It then uses that pattern to assess how Lilly might commercialize retatrutide differently.

**Primary question:** How has the GLP-1 clinical trial pipeline grown by phase and sponsor? How does that growth line up with the FDA shortage window? What does that history suggest about how Lilly will price and launch retatrutide?

---

## What's Real, What's Hand-Entered, What's Inference

This project mixes three kinds of data. They are not equally strong, so each one is labelled.

| Data | Kind | Where it lives | How firm |
|---|---|---|---|
| Clinical trials | **Pulled from API**: ClinicalTrials.gov v2, real NCT IDs | `data/raw/*.csv` via `data_pull.py` | Real registry records, as of the pull date |
| FDA shortage windows (2 drugs) | **Hand-entered, cited**: dates typed in from FDA declaratory orders | `shortage_status` table in `build_db.py` | Primary source (FDA orders) |
| FDA warning-letter batches (3 events) | **Hand-entered, cited**: one row per documented batch, with source and how firm the count is | `enforcement_events` table in `build_db.py` | Mixed: one FDA press release, one SEC filing + FDA letter, one secondary source |
| Lilly pricing/access + FDA policy (8 events) | **Hand-entered, cited** | `policy_events` table in `build_db.py` | Company press releases / FDA press release / trade press |
| Retatrutide commercial outlook | **Author's inference**, not data | Case study below | Forward-looking opinion |

### Correction notice

An earlier version of this project had a 91-row `warning_letters` table that this README described as "hand-compiled from FDA's Warning Letters database," with dates that "reflect FDA's published enforcement calendar." **That was not true.** The rows were constructed: batch totals were spread across invented per-letter dates, recipient types and violation categories, and the cited "Sept 8 2025" FDA press release does not exist. The table has been removed and replaced with `enforcement_events`, which holds only batches that can be tied to a source (listed below). Liraglutide and dulaglutide shortage rows were also removed: their dates had no source and contradicted FDA's own December 2024 status, which still listed both drugs as in shortage.

---

## Data Sources

**Trial data:** downloaded from the ClinicalTrials.gov v2 public API (`clinicaltrials.gov/api/v2/studies`) using `data_pull.py`. The current `data/raw/` files were pulled on **2026-10-14**. The raw pull holds 3,328 studies. The analysis scope (the `studies_in_scope` view in `build_db.py`) keeps **2,865**:

- **Interventional studies only.** This drops 434 observational studies and 4 expanded-access records. Observational studies aren't part of a drug-development pipeline.
- **Start dates through 2026.** This drops trials with planned start dates in 2027–28: 22 in the raw pull, of which 18 are interventional (the other 4 were already dropped as observational).
- It also drops 7 interventional studies with no start date.
- **2026 is a partial year.** It covers trials registered up to the pull date, including 25 whose planned start falls between the pull date and the end of 2026. It is hatched in the figures and flagged `partial` in `q6_combined_timeline.csv`. Don't compare 2026 directly with full years.

**FDA shortage windows** (`shortage_status`):

| Drug | On shortage list | Resolved | 503A wind-down ended | 503B wind-down ended | Source |
|---|---|---|---|---|---|
| Semaglutide | Mar 2022 (Wegovy; Ozempic Aug 2022) | Feb 21, 2025 | Apr 22, 2025 | May 22, 2025 | [FDA order](https://www.fda.gov/media/185526/download) |
| Tirzepatide | Dec 15, 2022 | Dec 19, 2024* | Feb 18, 2025 | Mar 19, 2025 | [FDA order](https://www.fda.gov/media/184606/download) |

\*FDA first removed tirzepatide on Oct 2, 2024. After a lawsuit from the Outsourcing Facilities Association, FDA re-evaluated, and its Dec 19, 2024 order revoked and replaced the October decision. Dec 19 is the operative date.

**FDA warning-letter batches** (`enforcement_events`). These are letters about compounded GLP-1 products, almost all aimed at telehealth marketing claims ("same active ingredient as Ozempic"):

| Letters dated | Announced | Count | How firm the count is | Source |
|---|---|---|---|---|
| Sep 9, 2025 | Sep 9, 2025 (posted ~Sep 16) | ~50 | Approximate. Hims & Hers' FY2025 10-K says "approximately 50 companies"; trade press reports 40 to 55+ | [FDA letter to Hims & Hers](https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/warning-letters/hims-hers-health-inc-dba-hims-716567-09092025), [TechTarget](https://www.techtarget.com/pharmalifesciences/news/366631512/FDA-cracks-down-on-online-advertising-of-compounded-GLP-1-drugs) |
| Feb 20, 2026 | Mar 3, 2026 | 30 | FDA press release | [FDA](https://www.fda.gov/news-events/press-announcements/fda-warns-30-telehealth-companies-against-illegal-marketing-compounded-glp-1s) |
| Jun 8, 2026 | Jun 16, 2026 (as reported) | 25 | Secondary source only; no FDA press release found | [Mondaq](https://www.mondaq.com/unitedstates/healthcare/1814666/fda-takes-aim-at-misleading-online-claims-for-compounded-glp-1-drugs) |

This is **not** a complete census of FDA's GLP-1 warning letters. Individual letters outside these batches (for example, 2024 sterility and cGMP letters to outsourcing facilities) are not included. A full count would mean exporting FDA's Warning Letters database and filtering by product.

**Lilly and FDA policy events** (`policy_events`): LillyDirect launch (Jan 4, 2024); Zepbound vials at $399/$549 (Aug 27, 2024); added vial doses and price changes (Feb 25, 2025); vial price cut to $299–$449 (Dec 1, 2025); FDA proposal to exclude semaglutide, tirzepatide and liraglutide from the 503B bulks list (Apr 30, 2026). Each row carries its source URL in the table.

---

## Methods

1. **Data acquisition:** `data_pull.py` queries the ClinicalTrials.gov v2 API for 10 GLP-1 drugs, their brand names, and "TRIUMPH". Output: 4 CSVs in `data/raw/`.
2. **Database:** SQLite (`glp1_analysis.db`), built by `build_db.py`. Trial queries run against the `studies_in_scope` and `trials_clean` views described above.
3. **Hand-entered tables:** `shortage_status`, `policy_events` and `enforcement_events` are typed in from the cited sources. Every row has a `source_url`. No rows are generated or interpolated.
4. **Analysis:** `analysis.py` runs 6 queries (saved to `sql/`) and writes results to `data/processed/`.
5. **Visualizations:** matplotlib, 3 figures.

---

## Key Findings

### 1. The pipeline has grown steadily, and Phase 3 picked up after Wegovy's approval

Interventional GLP-1 drug-trial starts averaged ~78/year in 2010–2015 and ~138/year in 2020–2025, about 1.8x. 2025 alone (187) is 3.6x 2010 (52). Phase 3 starts held around 12–31/year through 2020. They then rose to 36–40/year in 2023–2025, after FDA approved Wegovy (semaglutide) for chronic weight management on **June 4, 2021**. The 2026 count (232 so far, 44 Phase 3) is partial.

**Figure 1: Interventional trial starts by phase (2005–2026; 2026 partial):**
![Pipeline Growth](figures/fig1_pipeline_growth.png)

### 2. Two companies dominate industry Phase 3

Novo Nordisk (322 trials, 143 Phase 3) and Eli Lilly (173 trials, 71 Phase 3) are the largest sponsors. Together they lead 37% of all 582 Phase 3 trials in scope. Non-industry sponsors (universities and hospitals) lead the majority of trials overall (~65%). Those trials are mostly Phase 4, Phase 2 and "N/A" studies, while industry leads 68% of Phase 3.

**Implication for retatrutide:** Lilly has the infrastructure to run large multinational programs. The pull contains 14 Phase 3 retatrutide trials, started 2023–2026.

**Figure 2: Sponsor landscape:**
![Sponsor Landscape](figures/fig2_sponsor_landscape.png)

### 3. The compounding window was a legal mechanism with hard dates

Cheap compounded GLP-1s were *legally enabled by the FDA shortage listing*. That window had hard start and end dates:

- **Semaglutide:** 35.7 months on the shortage list (Mar 2022 – Feb 21, 2025), plus a wind-down to May 22, 2025 for 503B facilities
- **Tirzepatide:** 24.1 months (Dec 15, 2022 – Dec 19, 2024), plus a wind-down to Mar 19, 2025

After the wind-downs ended, FDA's documented GLP-1 enforcement came in batches aimed mainly at telehealth marketing. There were ~50 letters on Sep 9, 2025, 30 announced Mar 3, 2026, and a reported 25 in June 2026. That's roughly 105 letters across three batches, with the caveats on firmness in the table above.

### 4. Lilly cut self-pay prices while tirzepatide was still in shortage

Lilly launched LillyDirect in **January 2024**. It began selling Zepbound single-dose vials there at **$399 (2.5 mg) and $549 (5 mg) on Aug 27, 2024**, about half the pen list price. That was while tirzepatide was still on the shortage list and compounded copies were legal. Lilly added higher-dose vials at $499 in **February 2025** and cut vial prices to **$299–$449 on Dec 1, 2025**.

The sequence: shortage listing → legal compounding market → Lilly self-pay vial pricing (Aug 2024) → shortage resolved (Dec 2024 / Feb 2025) → wind-downs end (Mar / May 2025) → FDA warning-letter batches on compounded-GLP-1 marketing (Sep 2025 onward) → proposed 503B bulks exclusion (Apr 2026). The ordering is documented. The causal links between steps are the author's interpretation (see Limitations).

**Figure 3: Shortage windows, enforcement batches and Lilly pricing (cited events only):**
![Access Timeline](figures/fig3_access_timeline.png)

---

## Case Study: What This Means for Retatrutide

> **This section is the author's inference.** The trial facts and Lilly announcements are sourced. The forecasts about pricing and launch strategy are opinion, not data.

Retatrutide (LY3437943) is Lilly's triple agonist (GLP-1/GIP/glucagon). Sourced facts:
- 14 Phase 3 trials in this ClinicalTrials.gov pull, started 2023–2026
- TRIUMPH-1 topline results announced **May 21, 2026**; TRIUMPH-2 and TRIUMPH-3 announced **July 23, 2026**
- Lilly says it plans to submit a Biologics License Application to FDA in **Q1 2027**

**The key question:** having been through the tirzepatide compounding episode, will Lilly price and launch retatrutide differently?

**Author's view: likely yes, in three ways:**

**1. Direct-to-patient access from day one.** Lilly built LillyDirect and the self-pay vial program while tirzepatide compounding was legal. It has the infrastructure and the incentive to offer self-pay access at launch, which would shrink the price gap that made compounding attractive.

**2. Supply preparation.** Compounding copies is only legal while the drug is on the shortage list. Tirzepatide's listing was driven by manufacturing capacity. If Lilly avoids a shortage listing at launch, the mechanism never activates. FDA's April 2026 proposal to exclude GLP-1s from the 503B bulks list would, if finalized, further narrow that pathway for outsourcing facilities.

**3. Transparent cash pricing.** A high list price with opaque PBM rebates creates a visible arbitrage opportunity. A LillyDirect-style transparent cash price is the counter. *Lilly has not announced a retatrutide price or launch plan; this is an extrapolation from the tirzepatide precedent.*

---

## Limitations

- Trial counts reflect what was registered at pull time (2026-10-14). Some trials may be missed if the drug-name search didn't match them. `trials_clean` counts only trials with at least one "Drug" intervention. 2026 is a partial year.
- The warning-letter table holds three documented batches, not every GLP-1 warning letter. One count is approximate and one comes from a secondary source.
- Shortage start dates are month-precision for semaglutide (FDA's order gives only "March 2022").
- None of this establishes causation. The timing of shortage resolution, enforcement and price cuts is consistent with the story above. But there are confounders: PBM negotiations, the November 2025 federal pricing agreements, and manufacturing expansion.
- The retatrutide case study is forward-looking opinion.

---

## Resume Bullet

> *"Built a SQL/Python pipeline over 2,865 interventional GLP-1 trials (ClinicalTrials.gov API) joined with hand-entered, source-cited FDA shortage, enforcement and pricing events, showing how a regulatory mechanism (the shortage listing) enabled the compounded-drug market; used that precedent for a clearly labelled forward assessment of Eli Lilly's retatrutide commercialization."*

---

## Repo Structure

```
glp1-pipeline-vs-access/
├── data_pull.py            # Downloads trial data from ClinicalTrials.gov API → data/raw/
├── build_db.py             # Loads trials into SQLite; hand-entered cited tables; scope views
├── analysis.py             # Runs SQL queries; saves results to data/processed/
├── visualize.py            # Creates 3 figures
├── glp1_analysis.db        # Built database
├── data/
│   ├── raw/                # studies.csv, sponsors.csv, conditions.csv, interventions.csv
│   └── processed/          # q1–q6 result CSVs (q5 = q5_enforcement_events.csv)
├── sql/                    # Saved SQL query files (q1–q6)
├── figures/                # fig1_pipeline_growth.png, fig2_sponsor_landscape.png,
│                           # fig3_access_timeline.png
└── README.md
```

---

## Running This Project

```bash
pip install matplotlib
python data_pull.py    # downloads trial data from ClinicalTrials.gov (~2-4 min)
python build_db.py     # builds glp1_analysis.db (update PULL_DATE if you re-pull)
python analysis.py     # runs SQL queries, saves data/processed/
python visualize.py    # creates figures/
```

---

## Sources

- FDA, semaglutide shortage resolution order (Feb 21, 2025): https://www.fda.gov/media/185526/download
- FDA, tirzepatide shortage resolution order (Dec 19, 2024): https://www.fda.gov/media/184606/download
- FDA, warning letter to Hims & Hers Health (Sep 9, 2025): https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/warning-letters/hims-hers-health-inc-dba-hims-716567-09092025
- FDA press release, "FDA Warns 30 Telehealth Companies Against Illegal Marketing of Compounded GLP-1s" (Mar 3, 2026): https://www.fda.gov/news-events/press-announcements/fda-warns-30-telehealth-companies-against-illegal-marketing-compounded-glp-1s
- FDA press release, "FDA Proposes to Exclude Semaglutide, Tirzepatide, and Liraglutide on 503B Bulks List" (Apr 30, 2026): https://www.fda.gov/news-events/press-announcements/fda-proposes-exclude-semaglutide-tirzepatide-and-liraglutide-503b-bulks-list
- TechTarget, FDA crackdown on online advertising of compounded GLP-1s (Sep 18, 2025): https://www.techtarget.com/pharmalifesciences/news/366631512/FDA-cracks-down-on-online-advertising-of-compounded-GLP-1-drugs
- Mondaq, June 2026 telehealth GLP-1 warning letters (Jul 9, 2026): https://www.mondaq.com/unitedstates/healthcare/1814666/fda-takes-aim-at-misleading-online-claims-for-compounded-glp-1-drugs
- Foley & Lardner, FDA removes tirzepatide from shortage list (Oct 2024): https://www.foley.com/insights/publications/2024/10/fda-removes-lillys-zepbound-mounjaro-tirzepatide-injection-drug-shortage-list/
- Lilly, LillyDirect launch (Jan 4, 2024): https://investor.lilly.com/node/50106
- Healthcare Brew, Zepbound vial launch (Aug 30, 2024): https://www.healthcare-brew.com/stories/2024/08/30/eli-lilly-selling-discounted-single-dose-vials-glp1-drug-zepbound
- Lilly, additional Zepbound vial doses (Feb 25, 2025): https://investor.lilly.com/node/52091
- Fierce Pharma, Lilly cuts Zepbound vial prices (Dec 2025): https://www.fiercepharma.com/marketing/lilly-joins-novo-glp-1-self-pay-price-cuts-lowering-costs-single-dose-zepbound-vials
- Lilly, TRIUMPH-1 topline (May 21, 2026) and TRIUMPH-2/3 topline (Jul 23, 2026): investor.lilly.com
- Jastreboff et al. (2023), NEJM: retatrutide Phase 2 results
