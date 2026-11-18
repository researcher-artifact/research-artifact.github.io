---
name: slm-research-type
description: Classify the research type (Research Method column, Wieringa/Petersen) and the empirical evaluation method (Evaluation Type column, Petersen/Easterbrook/Wohlin) of each full-text study of the systematic mapping, with the C1-C6 criteria, and record them in DEF_TA.xlsx under the rater role chosen by the user.
---

# Research type and evaluation method of the mapped studies (DEF_TA)

This skill fills, for each study read in full, the research-type criteria `C1` to `C6`, the `Research Method` column and the `Evaluation Type` column of the `Data Extraction` sheet of DEF_TA, for the mapping "Accountability Through Digital Object Tracing in Information Security". The values support the technology readiness assessment of the article (section *Technology readiness assessment*), which uses the fields on research method, evaluation type and research-type criteria as evidence.

Read `references/classification.md` before classifying any study. It defines the six criteria, the decision table, the ten evaluation methods and gives calibration examples.

## Principle

You make the judgement from the full text; the script `scripts/slm_extract.py` checks it and writes it. The script rejects any answer that contradicts the decision table of Petersen et al. (2015, Table 7) or pairs a research type with an evaluation method of the other kind. Never write DEF_TA with openpyxl or pandas: doing so deletes charts, tables and the data model.

## Role

DEF_TA holds one column per rater for each field, for example `Research Method (Researcher 1)` and `Research Method (AI Tool - OpenAI GPT)`. Before any classification, run

```bash
python scripts/slm_extract.py roles --def DEF_TA.xlsx
```

show the AI Tool roles found (for example AI Tool - OpenAI GPT, AI Tool - Anthropic Claude, or a new role such as AI Tool 3; do not offer Researcher 1 as an option) and **ask the user which role you are playing**. Write only in the columns of that role.

Some fields of the first round were analysed only by Researcher 1 and have no column for every AI tool: `C1`...`C6`, `Research Method`, `Evaluation Type` and `Notes` (for example, `AI Tool - Anthropic Claude` has none). When the AI Tool role you play lacks a column for a field you fill, add it with `write --add-columns` and tell the user which columns were added; a new AI Tool role (for example `AI Tool 3`) gets all its columns this way.

 Do not read the other raters' values for the same study before you finish your own classification: the raters must be independent for the agreement analysis.

## Workflow

`S=scripts/slm_extract.py`. One study at a time.

1. Match the PDF to its row and create the template:
   ```bash
   python $S match --def DEF_TA.xlsx paper.pdf
   python $S template --def DEF_TA.xlsx --role "<role>" --skill research-type --ids <Article ID> --out rt.json
   python $S pdftext paper.pdf --out paper.txt
   ```
2. Read the full text, giving most attention to the sections on implementation, evaluation, experiments, results, case study and limitations. Locate where (and whether) the solution is deployed and where the evaluation was carried out.
3. Decide C1 to C6 in this order, each with a justification that cites the section or page:
   - C3 first: is there an empirical evaluation (section 3 of the guide)? A worked example is not one.
   - C1 and C4: is the solution used in a real-world organisation, and is the evaluation carried out there? A testnet, a local network or a cloud instance set up by the authors is a laboratory.
   - C2: is the solution new?
   - C5: is the main contribution a conceptual framework or taxonomy?
   - C6: is the paper an opinion or an experience report? If True, start the justification with `Opinion:` or `Experience:`.
4. Apply the decision table (section 4 of the guide) to obtain the research type.
5. If the research type is Evaluation research or Validation research, choose the principal evaluation method from section 5 of the guide; otherwise use `-`. Name secondary methods in the C3 justification.
6. Fill `rt.json`:
   ```json
   "research_type": {
     "C1": {"value": false, "justification": "The scheme runs on a private Ethereum network set up by the authors (Section 6.1); no deployment in an organisation is reported."},
     "C2": {"value": true, "justification": "..."},
     "C3": {"value": true, "justification": "Section 6 measures ... (laboratory experiment); Section 5 also gives a security proof."},
     "C4": {"value": false, "justification": "..."},
     "C5": {"value": false, "justification": "..."},
     "C6": {"value": false, "justification": "..."},
     "research_method": "Validation research",
     "evaluation_type": "Laboratory experiment (machine or human)"
   }
   ```
7. Validate and correct until there are no errors:
   ```bash
   python $S validate --def DEF_TA.xlsx --input rt.json --skill research-type
   ```
   An error means that the criteria, the research type and the method do not agree. Re-read the study and correct the criterion that is wrong; do not change the research type merely to silence the error.
8. Write (usually together with the other skills, see the agent instructions):
   ```bash
   python $S write --def DEF_TA.xlsx --input rt.json --skill research-type --out DEF_TA_YYYY-MM-DD.xlsx
   ```
   Add `--add-columns` when the role has no columns for these fields. Cells already filled are kept unless the user asks for `--overwrite`.

The script stores each criterion in the format of the role's columns: one cell `True. Justification: ...` (as for Researcher 1), or two cells `C1 - Value` and `C1 - Justification` (as for AI Tool - OpenAI GPT).

## Rules

- Classify from the full text, not from the abstract. Authors' labels ("case study", "experiment", "real-world") do not decide the class; what was actually done does.
- Implemented is not used in practice. Laboratory, testnet, simulator, synthetic or public benchmark data: C1 and C4 False.
- Controlled experiment with practitioners requires human practitioners as subjects. Machine benchmarks are laboratory experiments.
- When the evidence is ambiguous between two adjacent classes, choose the one that claims less (Validation rather than Evaluation; Solution proposal rather than Validation) and state the doubt in the justification.
- Do not invent evaluation details. If the study does not report something, say so in the justification.
- Write in formal British English.

## Reply

For each study, report the research type, the evaluation method and one sentence on the decisive evidence. If you are playing an AI Tool role and Researcher 1 has already classified the study, say whether you agree only after writing your own classification.
