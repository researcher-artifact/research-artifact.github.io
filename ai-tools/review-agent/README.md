# review-agent: AI-assisted text review of the article

An agent and a skill that revise passages of the article "Accountability Through Digital Object Tracing in Information Security: A Systematic Literature Mapping", written in LaTeX, for clarity, cohesion, concision and formal academic style. The agent revises each passage in its original language, applies British English when the passage is in English, and keeps the meaning, the citation keys and the LaTeX structure of the source unchanged. It returns the revised passage and a short list of what changed, so that the authors can accept or reject each revision.

It is the companion of [`search-agent`](../search-agent/README.md) and [`extract-agent`](../extract-agent/README.md): those agents support study selection and data extraction, and this one supports the writing of the manuscript.

## Contents

```
review-agent/
├── README.md                                  this file
├── instructions.md                            agent instructions (4,131 characters; Copilot Studio limit is 8,000)
├── dist/british-scientific-latex-review.zip   the skill packaged for upload
└── british-scientific-latex-review/           the skill
    └── SKILL.md                               purpose, rules, parameters and output format
```

## How it works

Unlike the search and extraction agents, the review agent writes no file and runs no script: its whole output is text that the authors read before deciding. The rules of the skill keep the revision from changing what the passage says.

| Step | Performed by | What happens |
|---|---|---|
| 1. Inputs | User | Sends the source language, the article section and the LaTeX passage; optionally, the cited articles with their BibTeX keys, to check whether they support the statements |
| 2. Reading | AI | Examines the central idea, the logical progression, repetitions, terminology, the placement of citations and the LaTeX constructs, in light of the section |
| 3. Revision | AI | Revises in the original language (British English for English passages): reorders, merges or splits sentences, removes repetition and refines transitions, without adding or removing content |
| 4. Self-check | AI | Checks that every citation key, label, reference, environment, macro, comment, number, unit, abbreviation, name and symbol is preserved and that the LaTeX is valid |
| 5. Answer | AI | Returns the revised passage in a `latex` code block and a short list of restructurings, removed repetitions, merges and possible divergences from the cited sources |
| 6. Decision | Authors | Compare the revision with the original and decide what enters the manuscript |

### What the skill preserves

| Element | Rule |
|---|---|
| Meaning | Certainty, scope, causality, qualification and strength of every statement are kept; no claim, datum, example, interpretation or citation is added |
| Citations | Every `\cite{}`, `\citep{}`, `\citet{}`, `\parencite{}` and `\textcite{}` and every key stays attached to its statement; merged sentences keep the union of their keys |
| LaTeX | Labels, references, footnotes, URLs, section commands, environments, mathematics, macros and comments are kept as they are |
| Data | Numbers, units, defined abbreviations, proper names and symbols are reproduced exactly |
| Style | Formal British English for English passages; no em dashes in the revised prose |
| Sources | Supplied articles are used only to check terminology and support; a possible divergence is flagged, never corrected |

### Parameters

| Parameter | Values |
|---|---|
| `source_language` | Portuguese or English |
| `article_section` | Introduction, Literature Review, Methodology, Results, Discussion, Conclusion or another named section |
| `reference_articles` | Attached or pasted articles, each with its BibTeX key (optional; needed only to check citations) |
| `latex_passage` | The complete LaTeX passage to revise |

## Use with Claude

With the `british-scientific-latex-review` skill saved to your Claude account, paste a passage in a conversation and ask, for example: "Revise this passage of the Discussion in British English". Claude follows `SKILL.md` and answers in the two-part format.

## Building the agent in Microsoft Copilot Studio

The menu names below follow the Copilot Studio interface in 2026 and may change. The skills feature depends on what your tenant administrator has enabled.

### 1. Create the agent

1. Go to [copilotstudio.microsoft.com](https://copilotstudio.microsoft.com) and select the environment you will work in.
2. Click **Create** > **New agent** and go straight to the **Configure** tab (without using the conversational assistant).
3. **Name**: `Review Agent - Scientific LaTeX Review`. **Description**: "Revises LaTeX passages of the mapping article for clarity and concision in British English, preserving meaning, citations and LaTeX structure".
4. **Instructions**: paste the content of [`instructions.md`](instructions.md). It has 4,131 characters, within the 8,000-character limit.
5. Under **Model**, choose the most capable model available in your tenant.

### 2. Enable file uploads

Turn on user file uploads (**File uploads** / *Allow users to upload files*) so that the author can attach `.tex` files and the cited articles. Code execution is not needed.

### 3. Add the skill

1. On the **Build** tab, open **Skills** and click **Add skill** > **Upload a skill**.
2. Upload [`dist/british-scientific-latex-review.zip`](dist/british-scientific-latex-review.zip). The package has `SKILL.md` at its root, which is the layout Copilot Studio accepts.
3. Check that the skill appears with the name `british-scientific-latex-review`.

To rebuild the zip after changing the skill:

```bash
cd review-agent/british-scientific-latex-review && zip -r ../dist/british-scientific-latex-review.zip SKILL.md
```

**If your tenant does not have the Skills feature:** add `SKILL.md` as knowledge (step 4).

### 4. Knowledge base

Under **Knowledge** > **Add knowledge** > **Files**, you may upload the PDF of the latest version of the article, so that the agent knows the terminology already defined. Do not upload the cited articles as permanent knowledge: send those that matter for each passage in the conversation, with their BibTeX keys. Under **Knowledge**, turn off general web knowledge (*Use general knowledge* / *Web search*), so that the agent does not import content from outside the passage and its sources.

### 5. Test and publish

1. In the **Test** pane, paste a paragraph with at least two `\cite{}` commands, a `\ref{}` and a number, and ask for a revision.
2. Check that the answer has only the two parts, that every key, reference and number is present, and that no new claim was added.
3. Paste a passage in Portuguese and check that the revision stays in Portuguese.
4. Click **Publish** and choose the channel (Teams, Microsoft 365 Copilot or a website).

## Good practice

- Send one passage of a few paragraphs at a time, with its section; long passages make it harder to check each change.
- Compare the revision with the original before accepting it, in particular the statements whose strength or scope matters (results, limitations, claims of novelty).
- Treat the list of possible divergences as a prompt to reread the source, not as a correction.
- Keep the skill identical in your Claude account and in `dist/`, so that both channels apply the same rules.
