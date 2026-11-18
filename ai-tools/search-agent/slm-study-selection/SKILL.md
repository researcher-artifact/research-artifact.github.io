---
name: slm-study-selection
description: Study selection (0/1/2 screening) for the systematic mapping on digital object tracing and accountability in information security, from a .bib file and DEF_TA.xlsx, with deterministic deduplication, standardised exclusion reasons and recording of the iteration in DEF_TA.
---

# Study selection for the systematic mapping (DEF_TA)

This skill performs the **study selection** step of a new iteration (update) of the mapping "Accountability Through Digital Object Tracing in Information Security". Inputs:

1. a **.bib** file with the search results (a Scopus export or a snowballing export);
2. the latest **DEF_TA.xlsx**, which records everything already screened (`Data Set` sheet) and the included studies (`Data Extraction` sheet).

Output: a new **DEF_TA_<date>.xlsx** with an iteration sheet, the new records in `Data Set` and the references of the included studies in `Data Extraction`, plus a `.md` report with the counts.

Read `references/criteria.md` before assessing any study. It contains the research questions, the search string, the IC/EC criteria, the closed set of exclusion reasons and calibration examples.

## Principle

Everything that must be reproducible is done by the script `scripts/slm_screening.py` (Python 3, standard library only, plus `openpyxl` for reading). You, the agent, make **only the judgement** on title, abstract and keywords and hand the decisions back to the script, which validates them. Never edit `state.json` or the workbook by hand, and never write DEF_TA with openpyxl or pandas: doing so deletes charts, tables and the data model.

## Workflow

Use one working folder per iteration (e.g. `work/`). `S=scripts/slm_screening.py`.

### 1. Prepare (deterministic)

```bash
python $S prepare --bib new.bib --def DEF_TA.xlsx --workdir work [--iteration Update.1]
```

The script:
- reads the .bib and normalises DOI, Scopus EID (from the URL) and title;
- removes **duplicates within the .bib** (DOI, EID or title plus year) and **records already screened** in previous iterations (compared with the `Data Set` sheet), logging them all in `work/dedup_report.csv` (codes `EC2-DUP-BIB` and `EC2-PREVIOUS`);
- excludes by rule: language other than English (`EC7-LANGUAGE`), document type other than Article, Conference paper or Review (`EC7-DOCUMENT-TYPE`), thesis (`EC1-THESIS`), technical report (`EC1-TECH-REPORT`) and arXiv (`EC1-PREPRINT`);
- adds hints (`hints`): no abstract, Scopus document type Review, same title as a study already screened but a different year (possible other version).

The default sheet name is `Update.N` (following the pattern of `Forward.1` and `Backward.1`). Confirm the name with the researcher if they have a preference.

### 2. Screening by title, abstract and keywords (you)

```bash
python $S codes                      # valid criteria and reasons
python $S next --workdir work --size 20
```

For each record in the batch, follow the order EC7 > EC1 > EC2 > EC3 > EC4 > EC5 > EC6 and record the first criterion that applies. If none applies, ask: can you tell **what** is tracked, **how** and **why** (IC5)? If so, decision 2. If there is genuine doubt, decision 1.

Write a decisions file (CSV or JSON) with the columns:

| Column | Content |
|---|---|
| `record_id` | As given by `next` |
| `decision` | 0, 1 or 2 |
| `reason_code` | Mandatory if 0 (e.g. `EC6-VISUAL-TRACKING`); empty if 1 or 2 |
| `justification` | One or two sentences in English, citing what in the title or abstract led to the decision. For 2, state the object, approach and purpose |
| `confidence` | high, medium or low |

```bash
python $S apply --workdir work --decisions batch01.csv
```

If the script rejects any line, correct it and resubmit the batch. Repeat `next` and `apply` until `status` shows no records without a decision.

Judgement rules:
- Systematic review or mapping **related to this study** (tracing, provenance, auditing or accountability of digital objects): `EC3-SLR-RELATED`. Related non-systematic survey: `EC3-REVIEW-RELATED`. These appear in the report as related work.
- Access control **with** an audit trail, log or usage record is not EC4. It is EC4 only when there is no tracking at all.
- Watermarking or fingerprinting to identify who leaked or to trace distribution is an inclusion. It is EC5 only when the study deals solely with proof of authorship or robustness, without distribution.
- Cloud data integrity auditing, provenance and tamper-evident logs count as traceability.
- Do not exclude merely because the domain is unusual (healthcare, judiciary, digital supply chain, IoT): what matters is tracing digital objects for accountability.
- `EC6-OTHER` only when no other code fits, with a justification.
- Do not invent information that is not in the title, abstract or keywords.

### 3. Resolve the "1"s (full text or researcher)

```bash
python $S export --workdir work --only 1 --out to_review.csv
python $S next --workdir work --stage FT --size 10
```

If the researcher provides the PDFs, read the full text and reassess with `--stage FT`. If the researcher decides, apply with `--decided-by R1`. Every 1 must become 0 or 2:

```bash
python $S apply --workdir work --decisions review.csv --stage FT [--decided-by R1]
```

Rule-based exclusions may be changed only with `--override-rules`, and only with the researcher's authorisation.

### 4. Record in DEF_TA (deterministic)

```bash
python $S status --workdir work      # must show "Ready to commit: YES"
python $S commit --workdir work --def DEF_TA.xlsx --out DEF_TA_YYYY-MM-DD.xlsx
```

`commit` refuses to run while any 1 or undecided record remains. It:
- creates the iteration sheet with the metadata of every screened record and the columns `Screening Decision`, `Decision Label`, `Exclusion Criterion`, `Exclusion Reason Code`, `Exclusion Reason`, `Justification`, `Confidence`, `Screening Stage`, `Decided By`, `Decision Date` and `Data Extraction ID`;
- appends the new records to the `FullDataSet` table (`Data Set` sheet), with `DataBase ID` set to the iteration name, so that the next iteration deduplicates against them;
- appends the included studies (2) to the `Articles` table (`Data Extraction` sheet) with Article ID, the Rayyan ID and Dataset formulas, the next `Papper` code (P154, P155, ...), DOI, title and year. The remaining columns are left empty for data extraction;
- writes `work/report_<iteration>.md` with PRISMA-style counts, exclusions by reason and related secondary studies.

The original file is not modified. Deliver the new workbook, the report and `dedup_report.csv` to the researcher.

## Reply to the researcher

At the end, report: records in the .bib, records removed as duplicates (distinguishing those within the .bib from those in previous iterations), records excluded by rule, records you excluded by reason, included studies, how many 1s were resolved and by whom, and the related systematic reviews found. Remind the researcher that the final decision rests with them (R1), as in the article's protocol.
