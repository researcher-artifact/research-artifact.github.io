---
name: slm-data-extraction
description: Extract the Data Extraction Form (DEF) fields of each full-text study of the systematic mapping on digital object tracing and accountability (objective, proposed solution and tracking, what is tracked, architecture, technology stack, purpose, responsibility attribution, findings, limitations, notes) and record them in DEF_TA.xlsx under the rater role chosen by the user.
---

# Data extraction from the full texts (DEF_TA)

This skill performs the **data extraction** step of the mapping "Accountability Through Digital Object Tracing in Information Security" for studies already included by study selection. Inputs:

1. the full-text **PDF** of each study;
2. the latest **DEF_TA.xlsx**, whose `Data Extraction` sheet already has one row per included study (Article ID, Rayyan ID, Papper, DOI, title, year).

Output: a new **DEF_TA_<date>.xlsx** with the DEF fields of the chosen role filled in, plus a write report.

Read `references/def-fields.md` before extracting. It defines each field, the closed set of architecture labels, the missing-data tokens and the guardrails.

## Principle

You read the article and write the content; the script `scripts/slm_extract.py` matches the PDF to its row, gives you a template, checks quotes and formats, and writes the cells at XML level. Never write DEF_TA with openpyxl or pandas: doing so deletes charts, tables and the data model (Power Pivot). Never modify the original file.

## Role

DEF_TA keeps one column per rater: `Researcher 1`, `AI Tool - OpenAI GPT`, `AI Tool - Anthropic Claude`, and any other role the user creates. Always start with

```bash
python scripts/slm_extract.py roles --def DEF_TA.xlsx
```

then show the AI Tool roles found (do not offer `Researcher 1` as an option), plus the option of a new AI Tool role, and **ask the user which role you are playing**. Use that role, exactly as listed, in every command.

Some fields of the first round were analysed only by Researcher 1 and have no column for every AI tool: `C1`...`C6`, `Research Method`, `Evaluation Type` and `Notes` (for example, `AI Tool - Anthropic Claude` has none). When the AI Tool role you play lacks a column for a field you fill, add it with `write --add-columns` and tell the user which columns were added; a new AI Tool role (for example `AI Tool 3`) gets all its columns this way.

 Do not look at another rater's values for the same study before your extraction is finished.

## Workflow

`S=scripts/slm_extract.py`. Process one study at a time; batches of up to five studies per answers file are fine.

1. **Match** each PDF to its row (file name = Article ID, Rayyan ID, Papper code or DOI with `/` replaced by `_`):
   ```bash
   python $S match --def DEF_TA.xlsx *.pdf
   ```
   If a PDF is `NOT FOUND`, ask the user which study it is; if the study is not in `Data Extraction`, it must first go through study selection.
2. **Check what is pending** for the role:
   ```bash
   python $S status --def DEF_TA.xlsx --role "<role>" --skill extraction --only-pending
   ```
3. **Template and text**:
   ```bash
   python $S template --def DEF_TA.xlsx --role "<role>" --skill extraction --ids <id1>,<id2> --out de.json
   python $S pdftext paper.pdf --out paper.txt
   ```
   If `pdftext` warns that there is very little text, the PDF is probably scanned: follow the UNREADABLE rule.
4. **Read the whole article** (title, abstract, introduction, method or design, implementation, evaluation, discussion, conclusion). Fill `data_extraction` in `de.json` following `references/def-fields.md`, and set `source_pdf` to the file name.
5. **Check** quotes and formats, and correct until there are no errors:
   ```bash
   python $S validate --def DEF_TA.xlsx --input de.json --skill extraction --pdf paper.pdf
   ```
6. **Write** a new workbook (or pass the answers of all three skills at once, see the agent instructions). `write` repeats the validation and the quote check and writes nothing while there is an error; set `"model"` in the answers file to the AI model you are:
   ```bash
   python $S write --def DEF_TA.xlsx --input de.json --skill extraction --pdf paper.pdf --out DEF_TA_YYYY-MM-DD.xlsx
   ```
   The script writes only the columns of the role, never formula cells, and keeps cells that are already filled unless the user asks for `--overwrite`. It reports any answer it could not write (for example, a field for which the role has no column).

## Self-check before validating

- Every field of the role has content or `NOT REPORTED` / `NOT APPLICABLE`.
- `objective` begins with an infinitive; `responsibility` begins with `Yes.`, `Partially.` or `Not explicitly addressed.`.
- `architecture` is `Server-centered`, `User-centered` or `Hybrid (user-centered and server-centered)`, and follows from `architecture_decision` (rules ARC-1 to ARC-3 of `references/def-fields.md`): the architecture is seen from the data subject (active control or passive follow-up), not from the technical construction.
- `technology_stack` lists only technologies named in the article.
- Every number in `findings` appears in the article.
- Inferences are marked; there is no editorial voice; the text is in formal British English.

## Reply to the researcher

Report, for each study, the Papper code, the architecture label, and anything Researcher 1 should check (unreadable pages, title mismatch, inferred architecture). Deliver the new workbook and its report. The final decision on every field rests with Researcher 1.
