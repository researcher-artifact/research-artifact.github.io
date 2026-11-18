---
name: "british-scientific-latex-review"
description: "Invoke to revise scientific-article passages in their original language, applying British English when appropriate while preserving meaning, citations, LaTeX structure, and alignment with supplied references in applied computing and justice."
---

## Purpose
Revise passages from scientific articles for clarity, cohesion, concision, and formal academic style while preserving the original meaning, citation relationships, and LaTeX syntax. Apply British English conventions when the source passage is in English. Use this skill especially for manuscripts on applied computing, law, and justice, including submissions to journals such as *Computer Law & Security Review*.

## Uses
- Agent knowledge sources: reference articles supplied by the user with their BibTeX keys.

## Instructions
1. Confirm that the source language, article section, LaTeX passage, and any references needed for citation checking are available. If an essential input is missing, request only that input.
2. Examine the passage's central idea, logical progression, repetition, terminology, citation placement, and LaTeX constructs in light of the stated article section.
3. Revise in the original language. For English passages, apply formal British English spelling, grammar, punctuation, and academic usage consistently. Never translate the passage.
4. Improve clarity, cohesion, and concision by reorganising sentences or paragraphs, removing repetition without losing content, merging or splitting sentences, and refining transitions. Where the original content permits, order the reasoning as context, problem or gap, contribution or argument, then supporting evidence.
5. Preserve the exact semantic force of every statement, including certainty, scope, causality, qualification, and strength of conclusions. Add no claim, datum, example, interpretation, or citation absent from the source.
6. Preserve every citation command and key, including `\cite{}`, `\citep{}`, `\citet{}`, `\parencite{}`, and `\textcite{}`. Keep each citation attached to the statement it supports. When merging repeated sentences, retain the union of all cited keys without renaming, removing, exchanging, or regrouping them.
7. Preserve all LaTeX structure and syntax, including `\label{}`, `\ref{}`, `\eqref{}`, `\autoref{}`, `\footnote{}`, `\url{}`, `\href{}`, section hierarchy, environments, mathematical notation, formatting commands, custom macros, and comments. Do not convert the passage to another format or escape characters unnecessarily.
8. Preserve all numerical values, units, defined abbreviations, proper names, and mathematical symbols exactly. Do not use em dashes in revised prose; use commas, semicolons, parentheses, or full stops as appropriate.
9. Use supplied references only to verify terminology, whether cited sources support attributed statements, and conceptual alignment with the literature. Do not import new content from them. If a statement may diverge from a cited source, preserve the statement and flag the possible divergence separately.
10. Before responding, verify that every original citation key remains and no new key was introduced; every label, reference, environment, macro, comment, number, unit, abbreviation, name, and symbol is preserved; the LaTeX is syntactically valid; no meaning changed; no information was added; and repetition was removed without content loss.
11. Return exactly two parts. First, provide the complete revised passage in one fenced `latex` code block, ready to replace the original. Second, provide a short list of the main restructurings, removed repetitions, sentence merges, and possible divergences between the passage and cited references. Flag divergences without correcting them. Add no greeting, introduction, processing note, recommendation, or closing offer.

## Parameters
- `source_language`: Portuguese or English.
- `article_section`: Introduction, Literature Review, Methodology, Results, Discussion, Conclusion, or another named section.
- `reference_articles`: Attached or pasted articles, each associated with its BibTeX key; optional when citation verification is not requested.
- `latex_passage`: Complete LaTeX passage to revise.

## Output
- One fenced `latex` code block containing the complete revised passage.
- A short list of major restructurings, removed repetitions, sentence merges, and possible citation-to-source divergences.