# Study selection protocol for the mapping

Source: the article "Accountability Through Digital Object Tracing in Information Security: A Systematic Literature Mapping", sections Planning (research questions, search strategy, criteria) and Study selection.

## Research question

**RQ.** What approaches can be used to trace digital objects for accountability in the context of information security?

- **RQ1.** What types of digital objects are being tracked?
- **RQ2.** What technologies are involved in the proposed solution?
- **RQ3.** What is the purpose of the tracking mechanism?
- **RQ4.** What is the application domain of the proposed solution?
- **RQ5.** What is the approach or solution proposed?

A study is useful to the mapping only if it allows RQ1, RQ3 and RQ5 to be answered: **what** is tracked (the digital object), **how** it is tracked (the approach or solution) and **why** (the purpose: accountability, auditing, attribution or traceability).

## Search string (Scopus, title, abstract and keywords)

```
TITLE-ABS-KEY ( ( "digital object*" OR document OR file* OR archive* OR media OR "electronic object*"
  OR "digital information" OR "virtual object*" OR "cyber object" OR "digital asset*" )
AND ( approach* OR method* OR technique* OR solution* OR framework* OR model* OR system* OR application* )
AND ( track* OR monitor* OR accountability OR audit* OR trace* OR "log analysis" OR "user activity"
  OR "data breach" OR "incident response" OR "data leak*" )
AND ( "information security" OR "cybersecurity" OR "data security" ) )
AND ( LIMIT-TO ( DOCTYPE , "cp" ) OR LIMIT-TO ( DOCTYPE , "ar" ) )
AND ( LIMIT-TO ( LANGUAGE , "English" ) )
AND ( LIMIT-TO ( SUBJAREA , "COMP" ) OR LIMIT-TO ( SUBJAREA , "ENGI" ) )
```

Filters: Computer Science and Engineering; Conference Paper and Article; English. The original search was run on 21 January 2025, followed by one iteration of backward and forward snowballing on 4 May 2025.

Broad terms such as *media*, *file*, *track* and *monitor* return many false positives: visual object tracking in video, network monitoring, malware and intrusion detection, and physical logistics. These studies do not trace digital objects for accountability.

## Inclusion criteria (all must be met)

| Code | Criterion |
|---|---|
| IC1 | Written in English |
| IC2 | Published in a peer-reviewed venue |
| IC3 | Primary research |
| IC4 | Within Computer Science or Engineering |
| IC5 | Addresses traceability or accountability in the context of information security, including what is tracked, the proposed approach or solution and the purpose of tracking |

## Exclusion criteria

EC1 to EC5 are the criteria stated in the article. EC6 and EC7 make failure to meet the inclusion criteria explicit, so that every exclusion has a code.

| Code | Criterion | Origin |
|---|---|---|
| EC1 | Not published in a peer-reviewed venue | Article |
| EC2 | Duplicate record | Article |
| EC3 | Secondary study, non-primary research or grey literature | Article |
| EC4 | Implements access control but provides no tracking mechanism (neither traceability nor auditability) | Article |
| EC5 | Focuses solely on copyright protection without addressing the distribution of protected content | Article |
| EC6 | Out of scope: does not address traceability or accountability of digital objects in information security (fails IC5) | Derived from IC5 |
| EC7 | Formal eligibility: language, document type or subject area (fails IC1, IC4 or the document-type filter) | Derived from IC1 and IC4 |

**Order of checking:** EC7, EC1, EC2, EC3, EC4, EC5, EC6. Record the **first** criterion that applies. EC4 and EC5 come before EC6 because they are more specific.

## Exclusion reasons (closed set)

Use only these codes. The criterion is inferred from the code prefix.

| Reason code | Criterion | When to use |
|---|---|---|
| EC1-PREPRINT | EC1 | Preprint or non-refereed version (arXiv, SSRN, TechRxiv) |
| EC1-THESIS | EC1 | Thesis or dissertation |
| EC1-TECH-REPORT | EC1 | Technical report, white paper, standard or patent |
| EC1-OTHER | EC1 | Other non-peer-reviewed publication |
| EC2-DUP-BIB | EC2 | Duplicate within the .bib file (used by the tool only) |
| EC2-PREVIOUS | EC2 | Already screened in a previous iteration (used by the tool only) |
| EC2-SAME-STUDY | EC2 | Another version of a study already screened (extended, earlier or translated version) |
| EC3-SLR-RELATED | EC3 | **Systematic review or mapping related to this study** (tracing, provenance, auditing or accountability of digital objects) |
| EC3-REVIEW-RELATED | EC3 | Survey, overview or non-systematic review related to this study |
| EC3-SECONDARY-OTHER | EC3 | Secondary study on another topic |
| EC3-NON-PRIMARY | EC3 | Editorial, preface, keynote, front matter, erratum, abstract only |
| EC3-GREY | EC3 | Grey literature (non-academic magazine, news item, blog) |
| EC4-AC-NO-TRACKING | EC4 | Access control or authorisation without tracking, traceability or auditing |
| EC5-COPYRIGHT-ONLY | EC5 | Copyright or ownership protection (e.g. watermark robustness) without tracing distribution |
| EC6-NOT-INFOSEC | EC6 | Outside the information-security context |
| EC6-VISUAL-TRACKING | EC6 | Visual object or target tracking (computer vision, video surveillance) |
| EC6-NO-OBJECT-TRACING | EC6 | Security work that does not trace, audit or attribute digital objects (intrusion or malware detection, authentication, cryptographic primitive, network monitoring) |
| EC6-OTHER | EC6 | Other out-of-scope topic (justification required) |
| EC7-LANGUAGE | EC7 | Not written in English |
| EC7-DOCUMENT-TYPE | EC7 | Document type other than journal article or conference paper |
| EC7-SUBJECT-AREA | EC7 | Outside Computer Science and Engineering |

## Decisions

| Value | Meaning | When to use |
|---|---|---|
| 2 | Included | The title, abstract and keywords clearly show the digital object tracked, the mechanism (tracking, audit trail, provenance, tamper-evident log, forensic watermark, fingerprinting, traitor tracing, blockchain for auditing, etc.) and the security or accountability purpose |
| 1 | Requires review | Genuine doubt: abstract missing or short; tracking mentioned only in passing (borderline with EC4 or EC5); unclear whether the study is primary; possible version of a study already screened |
| 0 | Excluded | An exclusion criterion applies; a reason code is mandatory |

When in doubt between 0 and 2, use 1. In the article, studies scored 1 were retained and reclassified after in-depth reading.

## Calibration examples (studies included in the first round)

- Secure cloud storage auditing with deduplication and efficient data transfer: integrity auditing of files in the cloud; included.
- Security Architectures for Controlled Digital Information Dissemination: marking to trace redistribution; included.
- Towards Usage Control Models: Beyond Traditional Access Control: usage control with obligations and usage records; included (not EC4, because usage is monitored).
- Preventing Information Leakage between Collaborating Organisations: sharing with traceability through domain keys; included.
- Enhancing data leakage tracing: A novel digital watermarking method for document files: watermarking of documents to trace leaks; included.
- DataSafe: Copyright Protection with PUF Watermarking and Blockchain Tracking: concerns copyright but traces circulation on a blockchain; included (not EC5).
- Leveraging Fine-grained Access Control in Blockchain-based Healthcare System: access control with an auditable record on a blockchain; included (not EC4, because there is an audit trail).

For the full list of included studies, run `python scripts/slm_screening.py included --def DEF_TA.xlsx`.
