# extract-agent: AI-assisted data extraction and thematic analysis for the systematic mapping

An agent and three skills that automate the steps that follow study selection in the systematic literature mapping "Accountability Through Digital Object Tracing in Information Security": reading each included study in full, filling the Data Extraction Form (DEF), carrying out the thematic analysis and classifying the research type and evaluation method. The agent receives `DEF_TA.xlsx` and the full-text PDFs, **asks the user which AI rater role it is playing** (AI Tool - OpenAI GPT, AI Tool - Anthropic Claude, or a new one) and writes only in the columns of that role, in a new `DEF_TA` workbook.

It is the companion of [`search-agent`](../search-agent/README.md): the search agent adds the included studies to the `Data Extraction` sheet, and this agent fills them in.

## Contents

```
extract-agent/
├── README.md                          this file
├── instructions.md                    agent instructions (7,152 characters; Copilot Studio limit is 8,000)
├── dist/                              the three skills packaged for upload
│   ├── slm-data-extraction.zip
│   ├── slm-thematic-analysis.zip
│   └── slm-research-type.zip
├── slm-data-extraction/               skill 1: DEF fields
│   ├── SKILL.md
│   ├── references/def-fields.md       field definitions, architecture labels, guardrails
│   └── scripts/slm_extract.py
├── slm-thematic-analysis/             skill 2: thematic analysis
│   ├── SKILL.md
│   ├── references/codebook.md         dimensions, stages, high-level and final themes, normalisation
│   └── scripts/slm_extract.py
├── slm-research-type/                 skill 3: research type and evaluation method
│   ├── SKILL.md
│   ├── references/classification.md   C1-C6, decision table, evaluation methods, calibration
│   └── scripts/slm_extract.py
├── examples/answers_P110_P120_P146.json   a filled answers file for three real studies
├── tools/
│   ├── slm_extract.py                 source of the script (copied into each skill)
│   └── build.sh                       copies the script and rebuilds dist/
└── tests/test_slm_extract.py          automated tests on a synthetic workbook
```

## How it works

As in the search agent, the work is split between what must be **reproducible** (the script) and what requires **judgement** (the AI):

| Step | Performed by | What happens |
|---|---|---|
| 1. `roles` | Script, then the user | Lists the rater roles found in the column headers (`... (Researcher 1)`, `... (AI Tool - OpenAI GPT)`, ...). The agent offers the AI Tool roles (not Researcher 1, although it is not forbidden) and asks the user which one to play; the answer decides the columns written |
| 2. `match`, `status` | Script | Matches each PDF to its row (Article ID, Rayyan ID, Papper code or DOI) and shows which fields of the role are still empty |
| 3. `template`, `pdftext` | Script | Writes a JSON template for the study and extracts the PDF text with page markers |
| 4. Reading and judgement | AI | Reads the whole article and fills the template: DEF fields (skill 1), thematic analysis per dimension (skill 2), C1-C6, research type and evaluation method (skill 3) |
| 5. `validate --pdf` | Script | Checks that every verbatim excerpt occurs in the PDF, that themes and final themes come from the codebook and are supported by codes and excerpts, that the decision rules are cited where required, that the architecture follows from the decision questions, and that C1-C6, research type and evaluation method agree with the decision table |
| 6. `write --pdf` | Script | Repeats every check, derives the high-level themes from the final themes, and only then writes the role's cells in a new `DEF_TA_<date>.xlsx` and a report that records the model, the tool version and the rules version |
| 7. `kappa` | Script | Fleiss' kappa among the raters per dimension and coding stage, with the article's normalisation and the `Equivalences` sheet |

### Methodological basis

| Skill | Basis | How it is applied |
|---|---|---|
| Data extraction | Kitchenham and Charters (2007); Petersen et al. (2015); the DEF of the article | One field per DEF column, with the guardrails of the first-round extraction prompt; Architecture Type limited to the three labels reported in the article (Server-centered, User-centered, Hybrid), read from the data subject's point of view |
| Thematic analysis | Cruzes and Dybå (2011), with the coding methods of Saldaña (2021) | Per study and dimension: verbatim extraction, descriptive coding (first cycle), themes and final themes (second cycle), high-level themes (closed set of the article), self-verification; integrated approach with the 153-study codebook as start list and `[NEW]` themes for R1 to adjudicate; Fleiss' kappa for reliability |
| Research type (`Research Method` column) | Wieringa et al. (2006); Petersen et al. (2015, Table 7) | Six criteria C1-C6 and the decision table, applied strictly: evaluation research only when the solution is used and evaluated in a real-world setting; laboratory, testnet and simulation studies are validation research |
| Evaluation method (`Evaluation Type` column) | Petersen et al. (2015, Fig. 19); Easterbrook et al. (2008); Wohlin et al. (2012) | Ten methods (five of evaluation research, five of validation research) with definitions taken from Easterbrook and Wohlin; the method must agree with the research type |

In DEF_TA, the `Research Method` column holds the research type and the `Evaluation Type` column holds the empirical method, as in the 153 studies already coded and in the article's description of the DEF. The skills keep these meanings so that the new values stay comparable with the existing ones.

**Note on the existing codings.** In the 153 studies coded before this agent, C1 ("used in practice") was often read as "implemented", and 89 studies implemented and tested in a laboratory or testnet were classified as Evaluation research. The researcher chose (29 October 2026) to apply Petersen's decision table strictly, so the agent classifies such studies as Validation research. Disagreements with the earlier R1 values on this point are expected and are a reason to review those codings, not to imitate them. See section 7 of [`classification.md`](slm-research-type/references/classification.md).

### What changes in DEF_TA

The script writes the workbook directly at the XML level of the package, without openpyxl or pandas, so as to **preserve charts, tables, formulas and the data model (Power Pivot)**. The original file is never modified.

- **Data Extraction** (`Articles` table): the role's DEF columns, `C1`...`C6` (one cell `True. Justification: ...`, or two cells `Cn - Value` and `Cn - Justification`, following the role's existing layout), `Research Method` and `Evaluation Type`.
- **Digital Objects, Technologies, Purposes, Domains, Sub-Domains**: the role's `Data extraction`, `Codes`, `Theme`, `Final Theme` and `High-level Theme`. **Architecture**: the role's `Codes` (its Theme columns are formulas over `Architecture Type`).
- **Never written**: other raters' columns, `Theme (Final decision)`, `High-level theme`, formula cells, metadata (Article ID, Rayyan ID, DOI, title, year), and cells already filled (unless `--overwrite`).
- **New studies** (added by a new iteration of study selection): when a study is not yet in a dimension sheet or in `Thematic Analysis`, the script appends a row with the Article ID and the formulas of the previous row, and extends the table.
- **Missing columns**: the role `AI Tool - Anthropic Claude` has no `Notes`, `C1`...`C6`, `Research Method` or `Evaluation Type` columns in the current workbook, and a new role has none. These fields were analysed only by Researcher 1 in the first round. When an AI Tool role fills them, the agent runs `write` with `--add-columns`, which appends the missing columns at the right edge of the tables, and reports which columns were added. Without the flag, those answers are skipped and listed in the report. The tables are part of the data model, so Excel may ask to refresh it after columns are added.
- **Report** `DEF_TA_<date>_report.md`: cells written per sheet, rows and columns added, cells kept, answers not written, warnings for R1 (for example new final themes) and the self-verification notes of the thematic analysis.

Formula-driven sheets (Thematic Analysis, RQ summaries, heatmaps, RQ5, TRL) recalculate when the workbook is opened in Excel. The `Kappa_Fleiss` sheet keeps its ranges (rows 2 to 154); use the `kappa` command after adding studies, or extend the ranges in Excel.

## Harness for uniform coding across models (version 1.1.0)

The comparison of the GPT and Claude codings of the 153 studies (16 November 2026) showed that the two models did not apply the same method: one used free-text themes in the Theme stage (272 to 543 distinct labels per dimension, against 21 to 39 for the other and 13 to 25 for Researcher 1), wrote high-level labels in the Final Theme column, used labels outside the closed sets and labelled 106 architectures as Hybrid (the other, 26). Synonyms explained little of the difference. Version 1.1.0 therefore moves every decision that is not judgement into the script, so that any model, on any platform, produces answers in the same space:

| Mechanism | What it does |
|---|---|
| Mandatory gate | `write` runs the validation and the verbatim check itself and writes nothing while there is an error; the report records the model (`"model"` in the answers file), the tool version, the rules version and a digest of the script and references |
| Closed vocabulary in every stage after the codes | `theme` and `final_theme` accept only codebook final themes (sub-domain: the closed list), plus at most one `[NEW]`; a high-level label in the final column is rejected with the final themes to use instead |
| Derived high-level themes | The final theme → high-level theme table of the codebook is in the script (`FINAL_THEMES`); the rater chooses only where a final theme has several options |
| Evidence links | `support` gives, for each final theme, the codes and excerpt numbers behind it; themes without evidence are rejected |
| Decision rules | Codebook section 6 (G, DO, TEC, PUR, DOM, SUB) defines the labels with overlapping or residual meanings; the labels marked † must cite their rule. Rule DO-1 (Researcher 1, 16 November 2026): the hashes and logs that the solution writes are not tracked objects |
| Architecture decision questions | The architecture is seen from the data subject, not from the technical construction: the subject's actions over the object (active or passive) and whether the controller decides determine the label (ARC-1 to ARC-3 in `def-fields.md`) |
| Limits | At most 4/5/5/2/2 high-level themes for object, technology, purpose, domain and sub-domain; codes of at most eight words; at most ten excerpts per dimension |
| Agreement diagnostics | `kappa` also prints Krippendorff's alpha with the MASI distance and, with `--per-label`, the kappa of every theme |

**Calibration before a full run.** Run both AI roles on the same ten studies, compute `kappa --ids <ten ids> --per-label --raters "AI Tool - OpenAI GPT,AI Tool - Anthropic Claude"`, and look at the themes with kappa below 0.6. If a disagreement comes from an unclear rule, refine the rule in codebook section 6 (and `GUARDED`, `FINAL_THEMES` or `MAX_LABELS` in the script), rebuild with `tools/build.sh`, and repeat on ten other studies. Freeze the rules (the `RULES_VERSION` in the report) before the full run, and use the same version for both models.

**Same conditions for both models.** Give both models the same `pdftext` output, the same template and the same packaged skills; one study per answers file is preferable; use the lowest temperature the platform allows.

## Use with Claude

With the three skills saved to your Claude account, send `DEF_TA.xlsx` and the PDFs in a conversation and ask, for example: "Extract the data of these studies". Claude follows `instructions.md` and the skills, asks which role to play, and runs the script.

Local use, without an agent (Python 3, `pip install openpyxl pypdf`):

```bash
S=tools/slm_extract.py
python $S roles --def DEF_TA.xlsx
python $S match --def DEF_TA.xlsx pdfs/*.pdf
python $S status --def DEF_TA.xlsx --role "AI Tool - OpenAI GPT" --only-pending
python $S template --def DEF_TA.xlsx --role "AI Tool - OpenAI GPT" --ids rayyan-172027982.pdf --out s01.json
python $S pdftext pdfs/rayyan-172027982.pdf --out s01.txt
#   ... fill s01.json, including "model" ...
python $S validate --def DEF_TA.xlsx --input s01.json --pdf pdfs/rayyan-172027982.pdf
python $S write --def DEF_TA.xlsx --input s01.json --pdf pdfs/rayyan-172027982.pdf --out DEF_TA_2026-11-01.xlsx
python $S kappa --def DEF_TA_2026-11-01.xlsx --per-label
python $S vocab --def DEF_TA.xlsx            # closed sets and final themes in use
```

The answers file has one entry per study with up to three sections, `data_extraction`, `research_type` and `thematic`; [`examples/answers_P110_P120_P146.json`](examples/answers_P110_P120_P146.json) shows a complete one in the format of version 1.0 (it lacks `support`, `architecture_decision` and `model`, and uses free-text sub-domain themes, so the 1.1.0 validator rejects it); the codebook (section 7) and `def-fields.md` show the 1.1.0 additions. Each skill may write its own file; `write` merges several files.

## Building the agent in Microsoft Copilot Studio

The menu names below follow the Copilot Studio interface in 2026 and may change. The skills and code interpreter features depend on what your tenant administrator has enabled.

### 1. Create the agent

1. Go to [copilotstudio.microsoft.com](https://copilotstudio.microsoft.com) and select the environment you will work in.
2. Click **Create** > **New agent** and go straight to the **Configure** tab.
3. **Name**: `Extract Agent - SLM Data Extraction`. **Description**: "Extracts the DEF, performs the thematic analysis and classifies research type and evaluation method of full-text studies, recording them in DEF_TA.xlsx under a chosen rater role".
4. **Instructions**: paste the content of [`instructions.md`](instructions.md) (7,152 characters, within the 8,000-character limit).
5. Under **Model**, choose the most capable model available (the agent reads full papers). If you are creating a second AI rater, use a different model from the first one, as in the article (GPT-5.2 and Claude Opus 4.6), and give the agent a matching role name.

### 2. Enable code execution and file uploads

1. Under **Settings** > **Generative AI**, turn on **Code interpreter**.
2. Turn on user file uploads so that the researcher can attach the `.xlsx` and the PDFs.
3. Save.

### 3. Add the skills

1. On the **Build** tab, open **Skills** and click **Add skill** > **Upload a skill**.
2. Upload the three packages in [`dist/`](dist/): `slm-data-extraction.zip`, `slm-thematic-analysis.zip` and `slm-research-type.zip`. Each has `SKILL.md` at its root, plus `references/` and `scripts/`.
3. Check that the three skills appear with the names `slm-data-extraction`, `slm-thematic-analysis` and `slm-research-type`.

To rebuild the packages after changing a skill or the script:

```bash
extract-agent/tools/build.sh
```

**If your tenant does not have the Skills feature:** add the three `SKILL.md` files and the three `references/*.md` files as knowledge (step 4) and, in each conversation, attach `slm_extract.py` together with the `.xlsx` and the PDFs.

### 4. Knowledge base

Under **Knowledge** > **Add knowledge** > **Files**, upload:

| File | Why |
|---|---|
| `slm-data-extraction/references/def-fields.md` | DEF fields and guardrails |
| `slm-thematic-analysis/references/codebook.md` | Dimensions, themes and their definitions |
| `slm-research-type/references/classification.md` | Criteria, decision table and methods |
| PDF of the mapping article (latest version) | Research questions, protocol, definitions of the themes |
| Optional: Cruzes and Dybå (2011), Petersen et al. (2015), Wieringa et al. (2006), Easterbrook et al. (2008) | The methodological sources cited by the skills |

Do **not** put `DEF_TA.xlsx` in the knowledge base: it changes with every batch and must be sent in the conversation, always in its latest version. Turn off general web knowledge, so that the agent works only from the article and the protocol.

### 5. Test and publish

1. In the **Test** pane, attach `DEF_TA.xlsx` and one or two PDFs, and ask: "Extract the data of these studies".
2. Check that the agent first lists the roles and asks which one to play, then runs `match`, `template`, `pdftext`, `quotes`, `validate` and `write`, and delivers the new workbook and the report.
3. Open the new `DEF_TA` in Excel and check the role's columns in `Data Extraction` and in the dimension sheets, and that the charts and the data model are still present.
4. If the code interpreter lacks `openpyxl` or `pypdf`, the script reports it; ask the agent to install them or contact your administrator.
5. Click **Publish** and choose the channel.

## Tests

```bash
cd extract-agent
python -m unittest discover -s tests -v
```

The 37 tests build a small DEF_TA with tables and formulas and check role discovery, PDF matching, templates, every validation rule of the decision table, the closed sets of themes and architectures, the harness of version 1.1.0 (codebook-only themes, high-level themes derived and extra ones rejected, container choice, support and decision rules, sub-domain checks, tooling rejected as technology, label limits, architecture decision questions, mandatory PDF check and model in `write`), writing in both criterion layouts, preservation of formulas and of other raters' cells, `--overwrite`, rows appended for new studies, `--add-columns` for a new role, Fleiss' kappa against a value computed by hand, the verbatim-quote check, and that the packaged skills match the source.

The tool was also run on the real `DEF_TA_2026-10-24.xlsx` with three studies read in full (P110, P120 and P146, see `examples/`), as a new role with `--add-columns`: all 27 excerpts were found in the PDFs, the workbook kept its 26 tables, charts and data model, and LibreOffice opened the result. Against Researcher 1, the agent agreed on the architecture of the three studies and on most high-level themes, and classified the three as Validation research where R1 had Evaluation research, as expected from the strict reading of Petersen's table.

## Good practice

- Always use the latest `DEF_TA` as input, and the file written by the previous batch for the next one.
- Keep raters independent: an AI role must not read the R1 values of a study before coding it, and each AI role should run on a different model.
- Review warnings, `[NEW]` themes and inferred architectures before using the new workbook; the reconciliation and the final themes are decided by Researcher 1.
- Keep the closed sets stable. If a new high-level theme, architecture or evaluation method is genuinely needed, change `HIGH_LEVEL`, `ARCHITECTURES` or `EVALUATION_METHODS` in `tools/slm_extract.py` and the matching reference file, then run `tools/build.sh`.

## References

- Cruzes, D. S., Dybå, T. (2011). Recommended steps for thematic synthesis in software engineering. *ESEM 2011*, 275–284.
- Easterbrook, S., Singer, J., Storey, M.-A., Damian, D. (2008). Selecting empirical methods for software engineering research. In *Guide to Advanced Empirical Software Engineering*, Springer, 285–311.
- Kitchenham, B., Charters, S. (2007). *Guidelines for performing systematic literature reviews in software engineering*. EBSE Technical Report EBSE-2007-01.
- Petersen, K., Vakkalanka, S., Kuzniarz, L. (2015). Guidelines for conducting systematic mapping studies in software engineering: an update. *Information and Software Technology* 64, 1–18.
- Saldaña, J. (2021). *The Coding Manual for Qualitative Researchers*, 4th ed. SAGE.
- Wieringa, R., Maiden, N., Mead, N., Rolland, C. (2006). Requirements engineering paper classification and evaluation criteria: a proposal and a discussion. *Requirements Engineering* 11(1), 102–107.
- Wohlin, C., Runeson, P., Höst, M., Ohlsson, M. C., Regnell, B., Wesslén, A. (2012). *Experimentation in Software Engineering*. Springer.
