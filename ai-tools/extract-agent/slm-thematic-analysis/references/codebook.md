# Codebook of the thematic analysis

Version of the rules: 2026-11-16 (slm_extract 1.1.0). Source: the article, sections *Thematic analysis*, *Steps of thematic analysis*, *Inter-rater reliability* and *Themes*; the dimension sheets (`Digital Objects`, `Technologies`, `Purposes`, `Domains`, `Sub-Domains`, `Architecture`), the `Equivalences` sheet and the `Kappa_Fleiss` sheet of DEF_TA (version of 24 October 2026, 153 studies).

## 1. Dimensions and stages

| Dimension (JSON key) | Sheet | Question | RQ |
|---|---|---|---|
| Tracked digital object (`digital_object`) | Digital Objects | What digital artefacts, data entities or information objects are managed, analysed or protected? | RQ1 |
| Technology (`technology`) | Technologies | Which technological solutions, frameworks or methodologies are used? | RQ2 |
| Purpose (`purpose`) | Purposes | What are the aims and intended outcomes of the tracking? | RQ3 |
| Domain (`domain`) | Domains | In which application area is the study located? | RQ4 |
| Sub-domain (`sub_domain`) | Sub-Domains | Which more specific setting within the domain? | RQ4 |
| Architecture (`architecture`) | Architecture | Which architectural elements support the classification of the architecture? | DEF |

Each dimension sheet has, for every rater, the columns `Data extraction (<role>)`, `Codes (<role>)`, `Theme (<role>)`, `Final Theme (<role>)` and `High-level Theme (<role>)`. The columns `Theme (Final decision)` and `High-level theme` hold the reconciliation of Researcher 1 and are never written by the agent. In the Architecture sheet only `Codes (<role>)` is written: its Theme columns are formulas that read `Architecture Type (<role>)` from the Data Extraction sheet (filled by the data-extraction skill).

| Stage (JSON key) | Content | Format in the cell |
|---|---|---|
| `extraction` | Verbatim text segments of the article relevant to the dimension | One segment per line, copied exactly |
| `codes` | Descriptive codes: short nouns or noun phrases (one to five words) summarising each segment | Comma-separated |
| `theme` | Candidate themes of this study: the **final themes of the codebook** (section 3) suggested by the codes, before consolidation; at most one `[NEW]` theme per dimension | Comma-separated, closed set |
| `final_theme` | The themes kept after consolidation: a subset of `theme` | Comma-separated, closed set |
| `high_level_theme` | High-level themes of the article (section 2). **Derived by the script** from the final themes through the table of section 3; the rater only chooses when a final theme has more than one possible high-level theme | Comma-separated, closed set |
| `support` | For each final theme: the codes and the excerpt numbers that license it and, for the labels marked † in section 3, the decision rule of section 6 that applies | JSON only (not written to the workbook) |

`theme` and `final_theme` take labels **only** from section 3 (sub-domain: section 2), exactly as written there; free-text themes are rejected by the validator. This is how Researcher 1 coded the 153 studies (Theme equals Final Theme in 145 to 153 of them), and it is what makes the Theme stage comparable across raters. A high-level label is not a final theme: write its final theme instead (for example `Mitigate Cybersecurity Risks`, not `Cybersecurity Risk Mitigation`), unless the label is both (for example `Access Control`, `Data Auditing`, `Metadata`).

Multiple labels per study are allowed in every stage, up to the limits of section 6. Agreement is computed on the complete normalised combination of labels (article, section *Inter-rater reliability*), so a single label too many makes the whole combination disagree: list the labels that the article states as central (section 6) and no label that the evidence does not support.

## 2. High-level themes (closed set, as defined in the article)

Labels are written exactly as in the workbook (two of them keep the American spelling used in the workbook, *Containerization* and *Authorization*; the validator accepts the British spelling as input and writes the workbook label).

### Tracked digital object

| High-level theme | Definition |
|---|---|
| Structured Records | Records stored in predefined fields: electronic health records (EHR, EMR, PHR), registration forms, judicial, financial, police and insurance records. |
| Documents | Formatted or semi-structured textual files intended for human reading: PDFs, Office files, legal documents, reports, forms. |
| Media Files | Audiovisual content: images, videos, audio, diagnostic imaging (DICOM). |
| Data Files | Structured or semi-structured files intended for processing by systems: JSON, XML, CSV, binary files, data chunks. |
| Source Code & CAD | Software engineering or design artefacts: source code, CAD files, computational models. |
| Logs & Audit Trails | System-generated event records: access logs, audit trails, transaction histories. |
| Metadata | Data about data: descriptors, indexes, integrity hashes, access policies, annotations associated with other objects. |
| IoT Data Streams | Continuous or discrete streams generated by connected devices, sensors and embedded telemetry. |

### Technology

| High-level theme | Definition |
|---|---|
| Cryptography | Cryptographic primitives (symmetric and asymmetric encryption, attribute-based encryption, digital signatures, hashing) and hardware implementations (trusted platform modules, biometrics) for confidentiality, authenticity, integrity and revocable access control. |
| Blockchain | Distributed, immutable ledgers (public, permissioned or consortium) providing tamper-evident tracking of access events, consent and provenance; includes NFTs and multi-ledger architectures. |
| Smart Contracts | Deterministic programs on distributed ledgers that encode and enforce access policies, consent workflows, delegation and compliance obligations. |
| Distributed File System | Peer-to-peer repositories with content-based addressing (IPFS) and abstraction layers such as virtual file systems, for verifiable off-chain storage. |
| Steganography & Digital Watermarking | Content-bound techniques embedding identifiers, provenance metadata or forensic marks into the object itself. |
| Machine Learning & AI | Supervised, unsupervised and neural-network models for anomaly detection, insider-threat classification, sensitive-data localisation or robustness evaluation. |
| Honey Files | Decoy objects that trigger alerts and produce forensic evidence when accessed improperly. |
| Containerization & Orchestration | Services packaged in isolated containers (Docker) and coordinated by orchestrators. |
| Interoperability & Authorization Standards | Standardised delegated-authorisation protocols (OAuth 2.0) and knowledge-representation technologies (ontologies, RDF, Data Privacy Vocabulary) for semantic interoperability and fine-grained authorisation. |
| Knowledge Representation & Analytics | Methods for extracting, structuring and analysing heterogeneous information: privacy analysis, behaviour monitoring, OCR, linkage of geospatial metadata (GPS). |
| Digital Forensics Techniques | Post-incident investigation techniques on digital objects and systems, for example comparison of operating-system records such as the Windows registry. |
| Digital Twin | Dynamic virtual replica of a cyber-physical system for monitoring, scenario analysis and threat simulation. |

### Purpose

| High-level theme | Definition |
|---|---|
| Data Traceability | Following digital objects through their lifecycle, recording origin, operations and the entity responsible for each operation, so that provenance and custody can be reconstructed. |
| Access Control | Governance of access through policies on who may access which resource, under which conditions and privileges, with delegation, revocation and smart-contract enforcement. |
| Data Privacy | Collection, processing and sharing of personal or sensitive data in compliance with regulations (GDPR, LGPD), preserving data subjects' rights. |
| Secure Data Sharing | Exchange of objects between parties preserving confidentiality, integrity and authenticity, with consent management and non-repudiation. |
| Healthcare Data Governance | Secure, traceable and compliant management of EHR, EMR and PHR, with patient consent, interoperability and sector-specific compliance. |
| Cybersecurity Risk Mitigation | Reducing the likelihood and impact of attacks through preventive, detective and responsive controls across the object lifecycle. |
| Data Auditing | Systematic, independent verification of the states, operations and usage of objects over time through tamper-evident audit trails and consistency checks. |
| Forensic Attribution & Post-Incident Investigation | *Ex post* investigation of incidents and attribution of unauthorised disclosures: watermarking, collusion-resistant fingerprinting, audit-trail analysis, legally admissible evidence. |
| Data Confidentiality | Technical protection against unauthorised disclosure through encryption, ABE and proxy re-encryption. |
| Digital Object Lifecycle Management | Controlled, traceable handling of objects through creation, storage, access, modification, distribution, retention and deletion. |
| Secure Data Retention | Secure storage with guarantees of availability, integrity and confidentiality, at-rest integrity verification, retention and deletion policies. |
| Copyright Protection | Protection of intellectual property over distributed objects by binding copies to the rights holder's identity. |
| Automated Sensitive Data Detection | Automatic identification and classification of sensitive information through ML, NLP and pattern analysis. |
| Security-Oriented Data Analytics | Extraction of security-relevant patterns and anomalies from data on the use and events of objects. |

### Domain

| High-level theme | Definition |
|---|---|
| Healthcare & Medical Informatics | EHR, EMR, PHR, medical imaging and clinical data; patient consent, cross-institutional interoperability, health regulations (HIPAA, GDPR). |
| Cross-Domain Cybersecurity & Computing | Cloud, IoT and general-purpose distributed systems without a primary sectoral context. |
| Legal, Compliance & Digital Forensics | Legal documents, forensic investigation of artefacts, judicial and law-enforcement contexts, chain of custody, admissible audit trails. |
| Digital Media | Management, protection and trading of images, videos and multimedia; copyright, content-bound accountability. Excludes generic security without a media context. |
| Industry & Supply Chain | Industrial manufacturing (Industry 4.0, additive manufacturing) and supply networks; provenance across multi-tier chains. |
| Government & Public Sector | E-government, public agencies, smart cities, inter-agency cooperation, official documents and citizen data. |
| Financial Services & Banking | Banking transactions, open banking, digital assets, audit trails of financial records. Excludes generic security not anchored in financial operations. |
| Automotive & Intelligent Transportation | Vehicular edge computing, connected vehicles, V2I and V2V. |
| Energy & Smart Grid | Smart grids, energy informatics, critical energy infrastructure. |
| Social Platforms | Online social networks and user-generated content; behavioural data and social-graph privacy. |
| Education | Digital learning environments, LMS, educational records. |

### Sub-domain

Closed set (the sub-domain has one level: final theme = high-level theme, and the script copies it): Electronic Health Record Management; Electronic Health Record Interoperability; Cloud computing; Public Health; Internet of Medical Things; Medical imaging and remote monitoring; Internet of Things; Data sharing; Specialized Disease Data; Files/Documents Management; Data management; Data auditing; Telesurgery. A new sub-domain takes the prefix `[NEW]`. Leave `theme`, `final_theme` and `high_level_theme` of the sub-domain empty when the study has no sub-domain beyond its domain (rule SUB-1).

## 3. Final themes in use and their high-level theme

Final themes are the granular themes that Researcher 1 grouped under each high-level theme. This table is the closed vocabulary of `theme` and `final_theme` and is coded in `slm_extract.py` (`FINAL_THEMES`): the script derives the high-level theme from it. When a row offers several high-level themes, choose one in `high_level_theme`. When no final theme fits, propose one with the prefix `[NEW]` (at most one per dimension) and choose its high-level theme. Labels marked † need the decision rule of section 6 in `support`.

### Tracked digital object

| Final theme | High-level theme |
|---|---|
| Health Data; Medical Data; Insurance Data; Financial Data; Police Data; Legal Data | Structured Records (when held as records in predefined fields) |
| Personal Data†; Sensitive Data†; Confidential Data† | Choose the container (DO-4): Structured Records, Data Files or Documents |
| Files†; Data† | Choose (DO-4): Data Files (files for processing) or Documents (for human reading) |
| Data Chunks; JSONs; XMLs; Binary Files; Supply Chain Data | Data Files |
| Plain Text (legal documents, reports, forms) | Documents |
| Images; Videos; Audios; Copyrights Data (media) | Media Files |
| Source-code; CAD Files | Source Code & CAD |
| Engineering Supervision Data | Choose: Source Code & CAD (design artefacts) or Documents (official documents for human reading) |
| Logs† | Logs & Audit Trails |
| Metadata† | Metadata |
| IoT Data | IoT Data Streams |
| Digital Objects† (generic) | Choose the most specific high-level theme supported by the text (DO-4) |

### Technology

| Final theme | High-level theme |
|---|---|
| Cryptography; Trusted Platform Module; Biometric authentication | Cryptography |
| Blockchain; NFT | Blockchain |
| Smart contracts | Smart Contracts |
| Distributed File System; Virtual File System | Distributed File System |
| Steganography; Steganography & Digital Watermarking | Steganography & Digital Watermarking |
| Machine Learning; Non-Generative Neural Network | Machine Learning & AI |
| Honey Files | Honey Files |
| Containerization and orchestration† | Containerization & Orchestration |
| Semantic Web†; OAuth 2.0† | Interoperability & Authorization Standards |
| Data Analytics†; GPS†; OCR† | Knowledge Representation & Analytics |
| Registry Comparison; Forensic Trace Analysis | Digital Forensics Techniques |
| Digital Twin | Digital Twin |
| Infosec† (generic security controls); Conceptual Model Only† | Choose the high-level theme of the mechanisms the study actually describes (TEC-5) |

### Purpose

| Final theme | High-level theme |
|---|---|
| Data Traceability | Data Traceability |
| Access Control | Access Control |
| Data Privacy; Sensitive Data Protection | Data Privacy |
| Secure Data Sharing; Secure Data Transactions | Secure Data Sharing |
| EHR Management† | Healthcare Data Governance |
| Data Security†; Mitigate Cybersecurity Risks† | Cybersecurity Risk Mitigation |
| Data Auditing†; Data Integrity† | Data Auditing |
| Support forensic investigations | Forensic Attribution & Post-Incident Investigation |
| Data Confidentiality† | Data Confidentiality |
| Data Management†; Legal Document Management† | Digital Object Lifecycle Management |
| Secure Data Storage† | Secure Data Retention |
| Copyrights Protection | Copyright Protection |
| Detecting Confidential or Sensitive Data | Automated Sensitive Data Detection |
| Data Analyzing† | Security-Oriented Data Analytics |

### Domain

| Final theme | High-level theme |
|---|---|
| Healthcare and Medical Informatics | Healthcare & Medical Informatics |
| Technology | Cross-Domain Cybersecurity & Computing |
| Legal, Compliance and Digital Forensics | Legal, Compliance & Digital Forensics |
| Digital Media | Digital Media |
| Supply Chain & Logistics; Industry | Industry & Supply Chain |
| Public Administration | Government & Public Sector |
| Financial | Financial Services & Banking |
| Automotive | Automotive & Intelligent Transportation |
| Energy | Energy & Smart Grid |
| Social platforms | Social Platforms |
| Education | Education |

## 4. Architecture codes

Code the elements that show how the data subject (the owner of the tracked object) stands in relation to the application, since the architecture is seen from the subject and not from the technical construction (`def-fields.md`, Architecture Type): what the subject can do over the object ("patient grants and revokes access", "patient sets sharing policies", "user deletes own data", "patient only views access log") and what the controller decides ("hospital approves every request", "emergency access without consent", "provider defines access policies"). Technical elements (servers, ledger nodes, IPFS, key servers) are coded only when they explain who decides. The label itself (`Server-centered`, `User-centered`, `Hybrid (user-centered and server-centered)`) is recorded in `Architecture Type` by the data-extraction skill.

## 5. Normalisation and equivalences

Before kappa, labels are converted to lower case, whitespace is standardised, ligatures, curly apostrophes and en dashes are replaced, `&` becomes `and`, labels are split at line breaks, commas and semicolons, mapped through the active rules of the `Equivalences` sheet, deduplicated and sorted. To avoid spurious disagreements:

- copy codebook labels exactly (`Smart Contracts`, not `Smart-contracts`);
- do not put commas inside a label (except the domain `Legal, Compliance & Digital Forensics`, kept as in the workbook);
- use the singular or plural form used in the codebook.

## 6. Decision rules

These rules were added on 16 November 2026 after the comparison of the GPT and Claude codings of the 153 studies, where the labels with overlapping or residual definitions had the lowest agreement (per-label kappa below 0.45). A final theme marked † in section 3 is accepted only if its `support` entry cites one of its rules (for example `"rule": "PUR-2: resisting collusion attacks is a stated aim (abstract)"`).

**General**

- **G-1 Stated, not mentioned.** Code what the article states as part of its contribution (abstract, introduction, contributions, design, conclusion). A benefit, technology or setting mentioned in passing, in related work or in future work is not coded.
- **G-2 Limits.** At most 4 high-level themes for the tracked object, 5 for technology, 5 for purpose, 2 for domain and 2 sub-domains. When more are supported, keep the ones the article treats as central.
- **G-3 One `[NEW]`.** At most one `[NEW]` theme per dimension, explained in `self_verification`. A new high-level theme is never proposed by a rater: keep the closest one and record the doubt.

**Tracked digital object**

- **DO-1 The object, not the trace.** Code the data or artefacts that the solution tracks, protects or attributes. The records that the proposed mechanism itself produces in order to track them (hashes of the objects, ledger transactions, access logs, audit trails, event records written by the solution) are **not** tracked objects. Decision of Researcher 1, 16 November 2026.
- **DO-2 Metadata.** Code Metadata only when metadata are an object of the tracking in their own right: access policies or consent records managed and shared as objects, provenance descriptors of datasets exchanged between parties, annotations attached to other objects. Integrity hashes, indexes and identifiers created by the mechanism follow DO-1 and are not coded.
- **DO-3 Logs.** Code Logs only when pre-existing logs or audit trails are themselves the object that the study protects, analyses or traces (log-integrity schemes, forensic analysis of system logs, tamper-proof storage of logs produced by other systems). The logs written by the proposed solution follow DO-1.
- **DO-4 Containers.** Personal, sensitive and confidential data, and generic files or data, take the container that holds them: Structured Records when kept in predefined fields (EHR, registers, forms), Data Files when files are processed by systems (JSON, binary, chunks, datasets), Documents when files are for human reading (PDF, Office, reports). Digital Objects (generic) only when the article names no type; then choose the most specific container described.

**Technology**

- **TEC-1 Mechanism, not tooling.** Code the technologies that implement the tracking, protection or attribution mechanism. Do not code the tooling used to build or evaluate it: benchmarks and performance or security testing tools, programming languages, web and application frameworks, generic databases, simulators, development environments and test networks. The validator rejects such `[NEW]` themes.
- **TEC-2 Containers.** Containerization and orchestration only when containers are part of the proposed or deployed architecture, not when Docker only hosts the test set-up.
- **TEC-3 Standards.** OAuth 2.0 for delegated-authorisation protocols (OAuth, OpenID Connect, UMA) used by the mechanism; Semantic Web for ontologies, RDF and vocabularies (such as the Data Privacy Vocabulary) used to represent policies or provenance. Health data formats (HL7, FHIR) alone are not coded here.
- **TEC-4 Analytics.** Data Analytics, GPS and OCR only when the analysis or extraction of information is part of the mechanism (behaviour monitoring, privacy analysis, linkage of location metadata), not when the article only reports statistics of its evaluation.
- **TEC-5 Generic.** Infosec and Conceptual Model Only only when the article describes no specific technology; choose the high-level theme of the mechanisms it does describe.
- **TEC-6 Cryptography.** Code hashing, signatures, encryption and key management used by the mechanism; incidental mentions (TLS of the test environment, a password hash of the login page) are not coded.

**Purpose**

- **PUR-1 Aims of the tracking.** Code the aims that the article states for the tracking or for the proposed solution (G-1), at most five.
- **PUR-2 Residual security labels.** Data Security and Mitigate Cybersecurity Risks only when protection against attacks or threats is a stated aim **and** no more specific purpose (Access Control, Data Confidentiality, Data Integrity, Data Privacy, Support forensic investigations) already covers it.
- **PUR-3 Traceability and auditing.** Data Traceability: following objects and recording who did what (provenance, custody, access history). Data Auditing: verifying, after the fact, records, states or compliance, when that verification is a stated aim. Data Integrity: detecting tampering with the objects, when it is a stated aim. Recording access on a ledger is Data Traceability; it is Data Auditing only if the article also verifies or audits those records.
- **PUR-4 Storage and confidentiality.** Secure Data Storage only when the secure storage of the objects is an aim in itself (availability, retention, deletion, integrity at rest), not merely because data are kept on IPFS or in the cloud. Data Confidentiality only when protection against disclosure through encryption is a stated aim.
- **PUR-5 Health records.** EHR Management only when the study is in healthcare and managing health records (consent, interoperability, patient control) is a stated aim.
- **PUR-6 Analysis and lifecycle.** Data Analyzing only when the analysis of usage or event data for security is the contribution. Data Management and Legal Document Management only when handling the objects through their lifecycle (creation to deletion) is a stated aim.

**Domain and sub-domain**

- **DOM-1 Primary domain.** Code the sector where the solution is applied or evaluated; a second domain only when the article applies or evaluates it in two sectors. Generic security without a sector is Technology.
- **DOM-2 Illustrative scenarios.** An example scenario used only to illustrate a generic scheme does not make the domain (a healthcare example in a generic access-control model is Technology).
- **SUB-1 Sub-domain.** Use the closed list of section 2; never a domain label; leave the lists empty (never `0`) when there is no setting beyond the domain.

## 7. Answers format of a dimension

```json
"purpose": {
  "extraction": ["the hash of each access is written to the ledger so that every access can be traced", "patients grant and revoke access"],
  "codes": ["access history on ledger", "patient-granted access"],
  "theme": ["Data Traceability", "Access Control", "Data Auditing"],
  "final_theme": ["Data Traceability", "Access Control"],
  "high_level_theme": [],
  "support": {
    "Data Traceability": {"codes": ["access history on ledger"], "excerpts": [1]},
    "Access Control": {"codes": ["patient-granted access"], "excerpts": [2]}
  }
}
```

`high_level_theme` may be left empty: the script fills it from the final themes (here Data Traceability, Access Control). Fill it only to choose among the options of a † row with several high-level themes or for a `[NEW]` final theme. `support.codes` are copied from `codes`; `support.excerpts` are the 1-based positions in `extraction`.

