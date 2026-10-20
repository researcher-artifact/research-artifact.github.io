# research-artifact.github.io

The GitHub Pages site of the study: a static, browser-only dashboard for the article *Accountability Through Digital Object Tracing in Information Security: A Systematic Literature Mapping*.

All figures are computed in the browser from the DEF/TA spreadsheet each time the page loads, so updating the spreadsheet updates the page. There is no build step.

## Tabs

| Tab | What it shows |
|---|---|
| Overview | Title, authors, abstract, headline figures and the distribution of studies by year. Any category of any dimension can be added to the chart, drawn as bars or as a line. Clicking a bar or point lists the studies behind it. |
| Data extraction | The data extraction form (sheet *Data Extraction*) as recorded by Researcher 1. Clicking a cell shows the same field side by side with the output of the AI tools (OpenAI GPT and Anthropic Claude). |
| Thematic analysis | The coding of Researcher 1 at each stage (data extraction, initial codes, theme, final theme, high-level theme) for each dimension, followed by the final results. Clicking a cell compares it with the coding of the AI tools: labels that Researcher 1 shares with an AI tool are marked in green, and the study's agreement among the three raters is shown with the Fleiss' κ of that dimension and stage. |
| Fleiss' kappa | Inter-rater reliability for every dimension and coding stage, recomputed in the browser with the article's method and checked against the *Kappa_Fleiss* sheet; the mean by stage; an explanation of the calculation; a worked example for any study; and the *Equivalences* sheet, with filters. |
| RQ1–RQ5 | One table per research question with each category, its percentage and its number of studies. Clicking a number lists the studies, cited in the article's numeric style. |
| Heatmaps | Any two dimensions of the thematic analysis crossed. Rows and columns are ordered so that the highest count is in the top-right cell and the lowest counts gather in the bottom-left corner. Clicking a cell lists the studies. |

## Files

| Path | Role |
|---|---|
| `index.html`, `assets/` | The page, its styles and scripts. `assets/data.js` reads the workbook; `assets/kappa.js` computes Fleiss' kappa; `assets/app.js` draws the views. |
| `data/DEF_TA.xlsx` | The DEF/TA spreadsheet the page reads. |
| `data/article.js` | Title, authors, abstract, keywords and research questions, taken from the manuscript. |
| `data/references.js` | Citation number and formatted reference of every work cited in the article, in the order of the article's reference list (elsarticle-num). |
| `tools/build_references.py` | Regenerates `data/references.js` from the manuscript's `.tex` and `.bib` files. |
| `assets/vendor/` | SheetJS 0.18.5 (Apache 2.0) and Chart.js 4.4.1 (MIT), kept locally so the page works without external services. |

## Updating the data

- **Spreadsheet:** replace `data/DEF_TA.xlsx` with the new version (same file name) and commit it. Sheet and column names must stay as they are; category names are read from the RQ summary sheets, and the study assignments from *Thematic Analysis* and *ApproachesAnalyses*. Coding stages are read from headers of the form `<Stage> (<Rater>)` in the dimension sheets, and the kappa analysis uses the rules of *Equivalences* (and its "Apply equivalences in Kappa?" switch). If a recomputed κ differs from *Kappa_Fleiss*, the row is marked on the page and a warning is written to the browser console.
- **Article text:** edit `data/article.js`.
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

The supplementary material (spreadsheet and AI tool prompts) is in <https://github.com/researcher-artifact/sok-tracking-and-accountability>.
