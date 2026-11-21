# research-artifact.github.io

The GitHub Pages site of the study: a static, browser-only dashboard for the article *Accountability Through Digital Object Tracing in Information Security: A Systematic Literature Mapping*.

All figures are computed in the browser from the DEF/TA spreadsheet each time the page loads, so updating the spreadsheet updates the page. There is no build step.

## Tabs

| Tab | What it shows |
|---|---|
| Overview | Title, abstract, keywords, headline figures and the distribution of studies by year. Any category of any dimension can be added to the chart, drawn as bars or as a line. Clicking a bar or point lists the studies behind it. |
| Study selection | The selection flow of the article (search, screening, snowballing, full-text reading), with the number of records and studies at each stage. Clicking a stage lists its records: included studies with their citation number, the others as plain citations. |
| Data extraction | The data extraction form (sheet *Data Extraction*) as recorded by Researcher 1. Clicking a cell shows the same field side by side with the output of the two AI agents of the article: AI Agent 1 (GPT-5.2) and AI Agent 2 (Claude Opus 4.6). |
| Thematic analysis | The coding of Researcher 1 at each stage (data extraction, initial codes, theme, final theme, high-level theme) for each dimension, followed by the final results. Clicking a cell compares it with the coding of the AI agents: labels that Researcher 1 shares with an AI agent are marked in green, and the study's agreement among the three raters is shown with the Fleiss' κ of that dimension and stage. |
| Fleiss' kappa | Inter-rater reliability for every dimension and coding stage, recomputed in the browser with the article's method and checked against the *Kappa_Fleiss* sheet; the mean by stage; an explanation of the calculation; a worked example for any study; and the *Equivalences* sheet, with filters. |
| RQ1–RQ5 | One table per research question with each category, its percentage and its number of studies. Clicking a number lists the studies, cited in the article's numeric style. RQ5 also shows the rules that assign the approach groups, recomputes the assignment from the DEF fields and checks it against *RQ5 Classification*, and lists the combinations of groups and the conditions met by each study. |
| TRL | The Technology Readiness Level assigned to each proposed solution: the rubric, the steps of the assessment, the distribution of levels, and the levels by technology, approach group and period, checked against the *TRL* sheets. |
| Data Protection Requirements | The fourteen technical requirements (TR) of the article (sheet *Data Protection Requirements*), with their source studies, the GDPR provisions on which each is grounded and the corresponding LGPD provisions. Selecting a provision opens its text, with a link to the official text in EUR-Lex (GDPR) or Planalto (LGPD). A bar chart, as in the article, shows the closest counterparts of each requirement among the categories of the corpus; clicking a bar lists its studies. The coverage table that the article keeps as supplementary material follows the chart, with the same counts. |
| Heatmaps | Any two dimensions of the thematic analysis crossed. Rows and columns are ordered so that the highest count is in the top-right cell and the lowest counts gather in the bottom-left corner. Clicking a cell lists the studies. |
| AI Tools | The AI agents used in the study (search-agent, extract-agent, review-agent and any tool added later), one card each. Opening a tool shows its README, and the tree on the right opens any of its files (instructions, skills, reference material, scripts, packages) in the central panel. The content comes from the snapshot in `ai-tools/`, which the tools repository updates automatically. |

## Files

| Path | Role |
|---|---|
| `index.html`, `assets/` | The page, its styles and scripts. `assets/data.js` reads the workbook; `assets/kappa.js` computes Fleiss' kappa; `assets/analyses.js` recomputes the RQ5 groups and the TRL summaries; `assets/legal.js` parses the legal provisions cited in the requirements table; `assets/ai-tools.js` draws the AI Tools section; `assets/app.js` draws the other views. |
| `data/DEF_TA.xlsx` | The DEF/TA spreadsheet the page reads. |
| `data/article.js` | Title, abstract, keywords and research questions, taken from the manuscript, and the record counts of the study selection (`selection`). |
| `data/legislation.js` | Text of the GDPR and LGPD provisions cited in the requirements table, taken from the official texts. |
| `data/references.js` | Citation number and formatted reference of every work cited in the article, in the order of the article's reference list (elsarticle-num). |
| `tools/add_analysis_sheets.py`, `tools/analysis_definitions.json` | Add the *RQ5* and *TRL* analysis sheets to the workbook. The JSON file holds the group rules, the term patterns, the TRL rubric and the periods. |
| `tools/build_legislation.py` | Regenerates `data/legislation.js` from the official GDPR (EUR-Lex) and LGPD (Planalto) pages saved from a browser, keeping only the articles the requirements table cites. |
| `tools/build_references.py` | Regenerates `data/references.js` from the manuscript's `.tex` and `.bib` files. |
| `tools/anonymise_workbook.py` | Removes the details that identify the authors from a workbook (file properties, the saved path and the Windows user name recorded by the data model) before it is published. |
| `ai-tools/` | Snapshot of the AI tools: `manifest.json` and a copy of the files of each tool. Written by the workflow of the tools repository; do not edit it by hand. |
| `assets/vendor/` | SheetJS 0.18.5 (Apache 2.0), Chart.js 4.4.1 (MIT) and marked 12.0.2 (MIT, Markdown of the AI Tools section), kept locally so the page works without external services. |

## Updating the data

- **Spreadsheet:** remove the authors' details from the new version and write it over `data/DEF_TA.xlsx`, then commit it:

  ```sh
  python3 tools/anonymise_workbook.py --in DEF_TA_new.xlsx --out data/DEF_TA.xlsx
  ```

  Use `--check` to list what would be removed without writing, and `--term` to report other terms (names, e-mail addresses, institutions). Sheet and column names must stay as they are; category names are read from the RQ summary sheets, and the study assignments from *Thematic Analysis* and *RQ5 Classification* (or *ApproachesAnalyses* when that sheet is absent). The TRL views read *TRA Solutions* and *TRL Rubric*. Coding stages are read from headers of the form `<Stage> (<Rater>)` in the dimension sheets, and the kappa analysis uses the rules of *Equivalences* (and its "Apply equivalences in Kappa?" switch). If a recomputed κ differs from *Kappa_Fleiss*, the row is marked on the page and a warning is written to the browser console.
- **Analysis sheets:** to rebuild the *RQ5* and *TRL* sheets, start from a workbook without them and run

  ```sh
  python3 tools/add_analysis_sheets.py --workbook DEF_TA_without_analyses.xlsx \
      --tra TRA_solutions.xlsx --previous RQ5_approach_groups.xlsx --out data/DEF_TA.xlsx
  ```

  The sheets are added inside the xlsx package, so charts, tables and the data model of the workbook are kept.
- **Legal texts:** after the requirements table changes, or to update the wording of the laws, save the two official pages and run

  ```sh
  python3 tools/build_legislation.py --workbook data/DEF_TA.xlsx --gdpr gdpr.html --lgpd lgpd.html \
      --retrieved "25 October 2026" --out data/legislation.js
  ```

  Superseded wording (struck through in the consolidated LGPD) and the notes on amendments are left out.
- **Article text and selection counts:** edit `data/article.js`. While the article is under double-anonymised review, keep `authors` empty and `anonymised` set to `true`; the overview then states that author details are withheld. The screening-stage counts are not in the spreadsheet, so they are kept in its `selection` block.
- **AI tools:** nothing to do here. Each push to the tools repository runs its workflow, which rewrites `ai-tools/` in this repository; a new tool folder with a README appears as a new card.
- **Citation numbers:** after the article's citations change, run

  ```sh
  python3 tools/build_references.py --tex "path/to/Tracking and Accountability for Digital Objects.tex" \
      --bib path/to/cas-refs.bib --out data/references.js
  ```

  A study that is not cited in the article is listed with its title and year and the mark `[?]`.

The footer has a file picker for previewing another version of the spreadsheet locally, without committing it.

## Viewing

The site is published by GitHub Pages from the `main` branch (root folder) at <https://researcher-artifact.github.io/research-artifact.github.io/>. The `.nojekyll` file tells Pages to serve the files as they are, without running Jekyll. Every link in the page is relative, so it works under that sub-path.

Opened directly from disk (double-clicking `index.html`), the page still shows the article, tabs and citation numbers, but the browser does not let it read `data/DEF_TA.xlsx` by itself, so choose that file with the picker at the bottom of the page. To preview locally with the spreadsheet loaded automatically:

```sh
python3 -m http.server 8000
# then open http://localhost:8000
```

All the data of the study are in this site: the spreadsheet `data/DEF_TA.xlsx`, which holds the records retrieved in each search (sheets *Data Set*, *Seed 0*, *Backward.1* and *Forward.1*), the data extraction form, the thematic analysis and the analysis sheets; and the codebook of the thematic analysis, in the AI Tools section (`ai-tools/extract-agent/slm-thematic-analysis/references/codebook.md`).

## Anonymity

The article is under double-anonymised review, so the page carries no author names, affiliations, ORCID identifiers, e-mail addresses or acknowledgements, and the published spreadsheet has no author in its file properties. Before publishing a new file, check it with `tools/anonymise_workbook.py --check`.
