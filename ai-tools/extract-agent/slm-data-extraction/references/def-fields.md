# Data Extraction Form (DEF): fields and rules

Source: the article "Accountability Through Digital Object Tracing in Information Security: A Systematic Literature Mapping", section *Data extraction* (the DEF fields), section *Planning* (research questions) and section *User-centric and server-centric architectures*; the `Data Extraction` sheet of DEF_TA; and the data-extraction prompt of the first round.

## Research questions served by the DEF

| RQ | Question | DEF fields that feed it |
|---|---|---|
| RQ1 | What types of digital objects are being tracked? | What is being tracked? |
| RQ2 | What technologies are involved in the proposed solution? | Technology Stack |
| RQ3 | What is the purpose of the tracking mechanism? | Purpose of Tracking, Responsibility Attribution |
| RQ4 | What is the application domain of the proposed solution? | Objective, Proposed Solution (context) |
| RQ5 | What is the approach or solution proposed? | Proposed Solution and Tracking Details, Technology Stack (the RQ5 rules search these two fields for technical terms such as "usage control", "zero-knowledge", "self-sovereign", "verifiable credential", "Idemix", "decentralised identifier") |
| TRL | Maturity of the solution | Proposed Solution, Main Findings, Study Limitations, research-type fields |

Because the RQ5 rules and the TRL assessment read these cells, name the mechanisms and technologies exactly as the authors do (for example "usage control (UCON)", "zero-knowledge proof", "Hyperledger Fabric 2.2", "Ganache").

## Columns

The column of each field is `<field> (<role>)`, for example `Technology Stack (AI Tool - OpenAI GPT)`. The JSON key is the one the `template` command writes.

| JSON key | DEF_TA column (prefix) | What to write |
|---|---|---|
| `objective` | Objective of the Study | The stated research goal: what the authors set out to investigate, design, propose or evaluate. Begin with an infinitive ("To propose ...", "To evaluate ..."). Do not describe the method. 1 to 3 sentences. |
| `objective_codes` | Objective Codes | Optional (only Researcher 1 has this column in the current workbook). Comma-separated descriptive codes of the objective. |
| `proposed_solution` | Proposed Solution and Tracking Details | A self-contained description of the artefact (framework, scheme, protocol, model, system or method) and of **how tracking, logging, monitoring, auditing or attribution is performed**: components, data flows, where records are kept (on-chain or off-chain, server, client), which events are recorded and by whom. Begin with "The study proposes ..." or "The authors introduce ...". Up to about 8 sentences. |
| `tracked` | What is being tracked? | A short noun-phrase enumeration of the specific data, records, files, events or artefacts that the solution records, monitors or audits ("Electronic health records and access events to them"; "Leaked images and the identity of the recipient embedded as a watermark"). Only **what**, not why. |
| `architecture` | Architecture Type | Exactly one of the three labels below, consistent with `architecture_decision`. |
| `architecture_decision` | (not written; checked by the script) | The answers to the three decision questions below, with the evidence. |
| `technology_stack` | Technology Stack | The technologies, protocols, standards, platforms, libraries, languages, cryptographic primitives and hardware that the article names, comma-separated (for example "Hyperledger Fabric, chaincode in Go, IPFS, CP-ABE, SHA-256, Docker, Node.js"). Only items named in the article. |
| `purpose` | Purpose of Tracking | Why the tracking exists: the security, accountability, regulatory or operational goals it serves. Begin with "Tracking is implemented to ..." or "The purpose of tracking is ...". Mention laws or standards only if the article does. |
| `responsibility` | Responsibility Attribution | Whether and how the solution attributes responsibility for actions, disclosures or misuse to a specific party. Begin with `Yes.`, `Partially.` or `Not explicitly addressed.` and then explain the mechanism (signed transactions, identity-bound logs, watermark carrying the recipient's identity, non-repudiation) or, when it is not addressed, whether related concepts (auditability, access logging, non-repudiation) are discussed. |
| `findings` | Main Findings and Conclusions | The principal results (with the figures the authors report, when they report them) and the authors' own conclusions. No evaluative commentary. |
| `limitations` | Study Limitations | Limitations acknowledged by the authors and, prefixed with `Inferred:`, limitations evident from the scope (for example "Inferred: evaluated only on a local test network with synthetic data"). |
| `notes` | Notes | Any salient observation that does not fit elsewhere: methodological caveats, design choices, relation to prior work, mismatch between the PDF and the metadata. `None.` if nothing applies. |

### Architecture Type

The article classifies the 153 solutions into three architectures (section *User-centric and server-centric architectures*): Server-centered 86, User-centered 43, Hybrid 24. Use exactly these labels; they are compared across raters by the Architecture sheet and by Fleiss' kappa.

**Point of view.** The architecture is **not** the technical construction of the solution (client-server, decentralised, blockchain, who runs the servers or the ledger nodes, where the data are stored). It is how the **data subject**, the owner of the tracked digital object (patient, citizen, user, author), stands in relation to the application: whether the subject is at the centre, with actions that give control over the object (active behaviour), or only follows what the controller (the organisation that processes the data) decides and allows (passive behaviour). A fully decentralised system can be Server-centered, and a solution running on institutional servers can be User-centered.

| Label | Use when |
|---|---|
| `Server-centered` | The controller takes the decisions about the subject's objects. The subject is passive: at most views the data, sees who accessed them, or is notified, within what the controller allows. |
| `User-centered` | The subject is the centre of the application: grants, revokes or consents to access and use, sets policies, shares, deletes, corrects or exports the objects, and the controller executes those decisions without overriding them. |
| `Hybrid (user-centered and server-centered)` | The subject has active control over part of the decisions, and the controller keeps its own authority over another part (approval of the subject's requests, override, emergency access, institutional policies applied without the subject). |

#### Decision questions (rules ARC-1 to ARC-3)

The two AI raters of the first comparison disagreed on 98 of the 153 architectures, partly because they read the architecture from the technical construction. The label is therefore derived by the script from `architecture_decision`:

| Key | Question | Answer |
|---|---|---|
| `subject` | Who is the data subject, the owner of the tracked object? | Text, for example `patient` |
| `subject_actions` | What can the subject do over the tracked objects in the proposed solution? | List. Active: `grant`, `revoke`, `consent`, `set_policy`, `share`, `delete`, `correct`, `export`. Passive: `view`, `trace` (see who accessed or used the object), `notified`, `none` |
| `controller_decides` | Does the controller take decisions about the subject's objects without the subject, or approve or override the subject's decisions? | `none`, `some` or `all` |
| `evidence` | Sections or pages that support the answers | Text |

| Rule | Answers | Label |
|---|---|---|
| ARC-1 | No active action (the subject only views, traces or is notified) | Server-centered |
| ARC-2 | At least one active action, and `controller_decides` = none | User-centered |
| ARC-3 | At least one active action, and `controller_decides` = some | Hybrid (user-centered and server-centered) |

An active action counts only if the subject performs it in the proposed solution; an action that the controller must approve every time, or that the controller can always override, is not control (answer `some` if this applies to part of the decisions; `all` with active actions is rejected as inconsistent). User-held keys, wallets or personal data stores are evidence of control only when the subject uses them to grant, revoke or share. The script rejects a label that contradicts the answers.

```json
"architecture": "Hybrid (user-centered and server-centered)",
"architecture_decision": {"subject": "patient", "subject_actions": ["grant", "revoke", "trace"],
                          "controller_decides": "some",
                          "evidence": "Section 3.2: the patient grants and revokes access to each doctor and sees the access log; Section 3.4: the hospital can open the record in emergencies without consent."}
```

If the article does not describe the subject's role explicitly, answer from the described workflow and add a sentence to `notes` starting with `Architecture inferred:`.

## Missing data

Use exactly `NOT REPORTED` when the article does not provide the information and `NOT APPLICABLE` when the field does not apply. Never leave a field of your role empty. If the PDF cannot be read (scanned without a text layer, corrupted, wrong file), write `UNREADABLE - extraction not possible` in `objective` and `NOT REPORTED` in the other fields, and tell the user.

## Guardrails

1. **No fabrication.** Every name, number, technology and claim must be present in the article. Never reconstruct a DOI or a figure.
2. **No external knowledge.** Do not complete a cell with what you know about a technology or a venue.
3. **No silent inference.** Mark inferences with `Inferred:` (limitations) or `Architecture inferred:` (notes).
4. **Faithful translation.** If the article is not in English, translate faithfully and keep the authors' hedging ("may", "could", "suggests").
5. **Neutral voice.** No "interestingly", "the authors convincingly show", "as expected".
6. **Short quotes only.** A verbatim phrase of up to 15 words may be quoted in double quotes; quoted phrases are checked against the PDF by the `quotes` command.
7. **One study at a time.** Never copy content between studies, even when they look alike.
8. **Metadata.** Article ID, Rayyan ID, Dataset, Papper, DOI, title and year already exist in DEF_TA (they were written by the study-selection step) and are never rewritten by this skill. If the PDF's title or year differs from the row, say so in `notes`: `Article title differs: "<title in the PDF>"`.
9. **British English**, formal and in the third person, one paragraph per cell (no bullet lists).
