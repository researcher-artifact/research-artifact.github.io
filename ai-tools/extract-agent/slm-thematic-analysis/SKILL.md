---
name: slm-thematic-analysis
description: Perform the thematic analysis (Cruzes and Dybå's thematic synthesis with Saldaña's coding methods) of each full-text study of the systematic mapping on digital object tracing and accountability, for the tracked object, technology, purpose, domain, sub-domain and architecture dimensions, and record extraction, codes, themes, final themes and high-level themes in DEF_TA.xlsx under the rater role chosen by the user.
---

# Thematic analysis of the mapped studies (DEF_TA)

This skill carries out, for each study read in full, the steps of the thematic analysis of the mapping "Accountability Through Digital Object Tracing in Information Security" (article, section *Steps of thematic analysis*). It follows the thematic synthesis of Cruzes and Dybå (2011) and the coding methods of Saldaña (2021), as the article does, and records the result in the dimension sheets of DEF_TA (`Digital Objects`, `Technologies`, `Purposes`, `Domains`, `Sub-Domains`, `Architecture`).

Read `references/codebook.md` before coding. It lists the dimensions, the format of each stage, the closed set of high-level themes with their definitions, the closed set of final themes, the **decision rules** (section 6) and the normalisation rules.

## Harness: what the script enforces

Two different models code the same studies, so everything that is not judgement is fixed by the script (version 1.1.0, rules of 16 November 2026). `validate` and `write` reject the answers when:

- `theme` or `final_theme` has a label outside the codebook (section 3; sub-domain: the closed list) or more than one `[NEW]` label, or a high-level label used as a final theme;
- a final theme is not also in `theme`, or has no `support` entry pointing to its codes and excerpts, or (labels marked † in the codebook) does not cite its decision rule;
- `high_level_theme` has a label that the final themes do not license: the script **derives** the high-level themes from the final themes and writes those;
- a dimension has more labels than the limit of rule G-2, a code is longer than eight words, or a sub-domain is a domain label or `0`;
- an excerpt is not found verbatim in the PDF (`write` checks them; pass `--pdf`), or the answers file does not say which `model` produced it.

Do not try to get round an error by changing a label without re-reading the article: an error means that the coding does not follow the codebook.

## Method

Cruzes and Dybå (2011, Table 2) describe five steps: extract data, code data, translate codes into themes, create a model of higher-order themes, and assess the trustworthiness of the synthesis. The article implements them in four steps per rater. For each study and each dimension:

| Step | Cruzes and Dybå (2011) | What you do | Stage (JSON key) |
|---|---|---|---|
| 1. Familiarisation | Extract data | Read the whole article and copy the **verbatim** text segments that answer the question of the dimension. Ignore related work that the authors do not adopt. | `extraction` |
| 2. Initial coding | Code data | **Descriptive coding** (Saldaña, 2021, ch. 3): label each segment with a short noun or noun phrase that summarises its topic ("EHR stored on IPFS", "watermark identifying the recipient"). In Vivo codes (the authors' own words) are acceptable. Code each dimension separately. | `codes` |
| 3. Theme development | Translate codes into themes | **Second-cycle coding** (Saldaña, 2021, ch. 5; pattern and focused coding) against the codebook start list: in `theme`, list every codebook final theme that the codes suggest; in `final_theme`, keep those that the decision rules (codebook section 6) confirm. Record in `support` the codes and excerpts behind each final theme. | `theme`, `final_theme`, `support` |
| 4. Higher-order themes | Create a model of higher-order themes | The script maps each final theme to its **high-level theme** (codebook section 3). Choose only where a final theme has several options (containers of rule DO-4, Infosec, Conceptual Model Only) or for a `[NEW]` final theme. | `high_level_theme` |
| 5. Trustworthiness | Assess the trustworthiness of the synthesis | Self-verification of the study (below), verbatim check by the script, and Fleiss' kappa among the raters once the corpus is coded. | `self_verification` and `kappa` |

This is the **integrated approach** of Cruzes and Dybå (2011): the codebook of the 153 studies is the deductive starting list (start list, Saldaña); codes are inductive, themes come from the codebook, and a new theme is developed only when the evidence requires it. A new final theme is written with the prefix `[NEW]` (at most one per dimension) so that Researcher 1 can adjudicate it; new high-level themes are decided by Researcher 1, never by a rater.

## Role

The dimension sheets keep one column per rater for each stage. Always start with

```bash
python scripts/slm_extract.py roles --def DEF_TA.xlsx
```

then show the AI Tool roles found (do not offer `Researcher 1` as an option), plus the option of a new AI Tool role, and **ask the user which role you are playing**. For a new AI Tool role, write with `--add-columns` and tell the user which columns were added. Write only in that role's columns. Never write `Theme (Final decision)` or `High-level theme` (the reconciliation by Researcher 1). Code independently: do not read the other raters' codes or themes for the same study before your own coding is complete, because the agreement analysis assumes independent raters.

## Workflow

`S=scripts/slm_extract.py`. One study at a time.

1. Match and template:
   ```bash
   python $S match --def DEF_TA.xlsx paper.pdf
   python $S template --def DEF_TA.xlsx --role "<role>" --skill thematic --ids <Article ID> --out ta.json
   python $S pdftext paper.pdf --out paper.txt
   ```
2. For each dimension, fill the stages in order (`architecture` takes only `codes`). Use lists in the JSON:
   ```json
   "digital_object": {
     "extraction": ["electronic health records are encrypted and stored on IPFS", "the hash of each record is written to the ledger"],
     "codes": ["encrypted EHR", "IPFS storage", "record hashes on ledger"],
     "theme": ["Health Data"],
     "final_theme": ["Health Data"],
     "high_level_theme": [],
     "support": {"Health Data": {"codes": ["encrypted EHR"], "excerpts": [1]}}
   }
   ```
   The record hashes are coded but not themed as Metadata: they are the trace written by the solution, not the tracked object (rule DO-1). `high_level_theme` stays empty because Health Data has a single high-level theme (Structured Records), which the script fills in. Set `"model"` at the top of the file to the AI model you are (for example `"GPT-5.2"` or `"Claude Opus 4.6"`).
   Copy the extraction **exactly** as printed in the article (one segment per list item, without quotation marks). If the article gives no evidence for a dimension, write `["Not addressed in the article."]` in `extraction` and choose the codes and themes only if the rest of the text supports them.
3. Fill `self_verification` with one or two sentences: the pages or sections of the excerpts, whether every code comes from an excerpt, whether every theme is licensed by the codes, any `[NEW]` theme and any residual doubt.
4. Check that every excerpt occurs in the PDF and that the themes are valid:
   ```bash
   python $S validate --def DEF_TA.xlsx --input ta.json --skill thematic --pdf paper.pdf
   ```
   Excerpts reported as not found must be copied again from `paper.txt`, not paraphrased. Repeat until `Valid.`.
5. Write (the same checks run again; nothing is written while there is an error):
   ```bash
   python $S write --def DEF_TA.xlsx --input ta.json --skill thematic --pdf paper.pdf --out DEF_TA_YYYY-MM-DD.xlsx
   ```
   If the study is not yet in a dimension sheet (a study added by a new iteration), the script appends a row with the Article ID and copies the formulas of the previous row, in each dimension sheet and in `Thematic Analysis`.

## Reliability (step 4 of the article)

When the user asks for it, or after a batch has been coded by all the raters, compute Fleiss' kappa with the normalisation and equivalences of the article:

```bash
python $S kappa --def DEF_TA_YYYY-MM-DD.xlsx                       # all studies, all roles
python $S kappa --def DEF_TA_YYYY-MM-DD.xlsx --ids <id1>,<id2>     # only the new studies
python $S kappa --def DEF_TA_YYYY-MM-DD.xlsx --per-label           # also the kappa of each theme
```

Report the coefficients with the Landis and Koch interpretation. Besides Fleiss' kappa on the complete combination (the article's measure), the command prints Krippendorff's alpha with the MASI distance, which gives partial credit to overlapping sets of labels, and `--per-label` gives the kappa of each final and high-level theme, which shows which decision rules need calibration. The `Kappa_Fleiss` sheet keeps its original ranges (rows 2 to 154) until Researcher 1 extends them in Excel.

## Rules

- Excerpts are verbatim; codes summarise excerpts; themes are licensed by codes. Never derive a theme from the title alone or from knowledge outside the article.
- A study may have several labels per stage; list each once.
- Use codebook labels exactly as written, so that agreement is not lost to spelling; never write a free-text theme.
- Apply the decision rules of codebook section 6 before keeping a final theme, and cite the rule in `support` for the labels marked †.
- If the article is a secondary study or a framework, code its own contribution, not the studies it cites.
- If your confidence in a theme is low, keep the best candidate and explain the doubt in `self_verification`.
- Write codes and themes in British English, except the workbook's labels, which are kept as they are.

## Reply

For each study, report the high-level themes per dimension, any `[NEW]` theme proposed and any doubt recorded in the self-verification. Remind the user that Researcher 1 reconciles the raters and records the final decision.
