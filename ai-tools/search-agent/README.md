# search-agent: AI-assisted study selection for the systematic mapping

An agent and a skill that automate **study selection** in updates of the systematic literature mapping "Accountability Through Digital Object Tracing in Information Security". The agent receives `DEF_TA.xlsx` (the current state of the mapping) and a `.bib` file with the results of a new search, scores each study 0, 1 or 2, and records the iteration in a new `DEF_TA` workbook.

## Contents

```
search-agent/
├── README.md                          this file
├── instructions.md                    agent instructions (about 6,500 characters; Copilot Studio limit is 8,000)
├── dist/slm-study-selection.zip       the skill packaged for upload
└── slm-study-selection/               the skill
    ├── SKILL.md                       workflow and judgement rules
    ├── references/criteria.md         RQs, search string, IC/EC, exclusion reasons, examples
    └── scripts/slm_screening.py       deterministic tool (Python 3 + openpyxl)
```

## How it works

Selection is split between what must be **reproducible** (done by the script) and what requires **judgement** (done by the AI):

| Step | Performed by | What happens |
|---|---|---|
| 1. `prepare` | Script | Reads the `.bib`, normalises DOI, Scopus EID and title. Removes duplicates within the `.bib` and records already screened (`Data Set` sheet). Excludes by rule: language, document type, thesis, technical report, arXiv |
| 2. `next` / `apply` | AI | Assesses title, abstract and keywords: 2 (included), 1 (requires review) or 0 (excluded, with a criterion and a reason from the closed set). The script validates every decision |
| 3. Resolving the 1s | AI with the full text, or the researcher | Every 1 becomes 0 or 2, recording the stage (FT) and who decided (AI or R1) |
| 4. `commit` | Script | Runs only when no 1 remains. Produces a new `DEF_TA` with the iteration sheet, the new records in `Data Set` and the included studies in `Data Extraction` |

### Criteria and exclusion reasons

The criteria come from the article (sections *Inclusion criteria* and *Exclusion criteria*). EC1 to EC5 are those of the article; EC6 (out of scope, failing IC5) and EC7 (language, document type or subject area) make failure to meet the inclusion criteria explicit, so that every exclusion has a code. Each exclusion receives a **reason code** from a closed set of 21 codes (e.g. `EC3-SLR-RELATED`, `EC4-AC-NO-TRACKING`, `EC6-VISUAL-TRACKING`), which allows exclusions to be counted and compared across iterations. Systematic reviews and mappings related to the topic receive `EC3-SLR-RELATED` and are listed in the report. The full table is in [`slm-study-selection/references/criteria.md`](slm-study-selection/references/criteria.md) and can be printed with `python scripts/slm_screening.py codes`.

### What changes in DEF_TA

The script writes the workbook directly at the XML level of the package, without openpyxl or pandas, so as to **preserve charts, tables, formulas and the data model (Power Pivot)**. The original file is never modified.

- **New sheet** (`Update.1`, `Update.2`, ... or a name of your choice) with the 13 `Data Set` columns plus: Document Type, Abstract, Author Keywords, Index Keywords, Bib Key, Screening Decision, Decision Label, Exclusion Criterion, Exclusion Reason Code, Exclusion Reason, Justification, Confidence, Screening Stage, Decided By, Decision Date and Data Extraction ID.
- **Data Set** (`FullDataSet` table): receives every record screened in the iteration, with `DataBase ID` set to the sheet name. The next iteration deduplicates against it.
- **Data Extraction** (`Articles` table): receives the included studies with Article ID, the Rayyan ID and Dataset formulas, the next `Papper` code (P154, P155, ...), DOI, title and year. The remaining columns are left empty for data extraction by R1 and the AI agents.
- **Report** `report_<iteration>.md` with PRISMA-style counts, exclusions by reason, related reviews and included studies; and `dedup_report.csv` listing each duplicate and the record it matched.

The analysis sheets (Thematic Analysis, Domains, Purposes, etc.) are not modified. They are updated after data extraction.

### Record identification

The `Article ID` is the Scopus EID (`2-s2.0-...`), taken from the `url` field of the export, as in the first round. Records without an EID (for example, from another database) receive `<iteration>-NNNN`. Deduplication uses, in this order, DOI, EID and normalised title with year. A matching title with a different year is not removed automatically; it becomes a hint for the AI to assess as a possible other version (`EC2-SAME-STUDY`).

## Use with Claude

With the `slm-study-selection` skill saved to your Claude account, send `DEF_TA.xlsx` and the `.bib` file in a conversation and ask, for example: "Run study selection on this new search". Claude follows `SKILL.md` and runs the script.

Local use, without an agent:

```bash
pip install openpyxl
S=slm-study-selection/scripts/slm_screening.py
python $S prepare --bib new.bib --def DEF_TA.xlsx --workdir work
python $S next --workdir work --size 20          # batch to assess
python $S apply --workdir work --decisions batch01.csv
python $S export --workdir work --only 1 --out to_review.csv
python $S status --workdir work
python $S commit --workdir work --def DEF_TA.xlsx --out DEF_TA_2026-11-01.xlsx
```

## Building the agent in Microsoft Copilot Studio

The menu names below follow the Copilot Studio interface in 2026 and may change. The skills and code interpreter features depend on what your tenant administrator has enabled.

### 1. Create the agent

1. Go to [copilotstudio.microsoft.com](https://copilotstudio.microsoft.com) and select the environment you will work in.
2. Click **Create** > **New agent** and go straight to the **Configure** tab (without using the conversational assistant).
3. **Name**: `Search Agent - SLM Study Selection`. **Description**: "Selects studies for a new iteration of the systematic mapping from DEF_TA.xlsx and a .bib file".
4. **Instructions**: paste the content of [`instructions.md`](instructions.md). It has about 6,500 characters, within the 8,000-character limit.
5. Under **Model**, choose the most capable model available in your tenant (screening depends on careful reading of abstracts).

### 2. Enable code execution and file uploads

The agent must run Python and receive files:

1. Under **Settings** > **Generative AI**, turn on **Code interpreter** (sometimes listed under **Capabilities** on the **Overview** tab).
2. Turn on user file uploads (**File uploads** / *Allow users to upload files*) so that the researcher can attach the `.xlsx`, the `.bib` and the PDFs.
3. Save.

### 3. Add the skill

1. On the **Build** tab, open **Skills** and click **Add skill** > **Upload a skill**.
2. Upload [`dist/slm-study-selection.zip`](dist/slm-study-selection.zip). The package has `SKILL.md` at its root, plus `references/` and `scripts/`, which is the layout Copilot Studio accepts.
3. Check that the skill appears with the name `slm-study-selection`.

To rebuild the zip after changing the skill:

```bash
cd search-agent/slm-study-selection && zip -r ../dist/slm-study-selection.zip SKILL.md references scripts
```

**If your tenant does not have the Skills feature:** add `SKILL.md` and `references/criteria.md` as knowledge (step 4) and, in each conversation, also attach `slm_screening.py` together with the `.xlsx` and the `.bib`, so that the code interpreter can run it.

### 4. Knowledge base

Under **Knowledge** > **Add knowledge** > **Files**, upload:

| File | Why |
|---|---|
| `slm-study-selection/references/criteria.md` | Criteria, exclusion reasons and calibration examples. The main reference for judgement |
| PDF of the mapping article (latest version) | Full context: research questions, protocol, taxonomies of objects, technologies, purposes and domains |
| Optional: list of the 153 included studies (`python scripts/slm_screening.py included --def DEF_TA.xlsx > included.txt`) | Examples of studies already accepted, useful for calibrating borderline cases |

Do **not** put `DEF_TA.xlsx` in the knowledge base: it changes with every iteration and must be sent in the conversation, always in its latest version. Under **Knowledge**, turn off general web knowledge (*Use general knowledge* / *Web search*), so that the agent judges only by the protocol and the records.

### 5. Test and publish

1. In the **Test** pane, attach a `DEF_TA.xlsx` and a small `.bib` (5 to 10 records, including one already screened and one duplicate) and ask: "Run study selection on this new search".
2. Check that the agent runs `prepare`, reports the counts, assesses in batches, asks for help with the 1s and produces the file only after they are resolved.
3. Open the resulting `DEF_TA` in Excel and check the new sheet, the end of the `Data Set` and `Data Extraction` sheets, and that the charts are still present.
4. If the code interpreter lacks `openpyxl`, `prepare` reports it. In that case, ask the agent to install it (`pip install openpyxl`) or contact your administrator.
5. Click **Publish** and choose the channel (Teams, Microsoft 365 Copilot or a website).

## Good practice for updating the mapping

- Run the same search string (table *Filters and search string applied in Scopus* in the article) and export to BibTeX with **all fields**, including abstract, keywords, language and document type. Without an abstract, a record tends to be scored 1.
- Always use the latest `DEF_TA` as input. It is what prevents records already seen from being screened again.
- Review decisions with `low` and `medium` confidence and a sample of the others. To report agreement between the AI and the researcher, record your own decisions in a copy of the CSV and compare them.
- If the researcher changes a decision, apply it with `--decided-by R1`; the history is kept in `state.json`.
- Keep the reason codes stable. If a new reason is genuinely needed, add it to `REASONS` in the script and to `criteria.md`, in both copies of the skill.
