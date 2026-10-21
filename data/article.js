// Article metadata shown on the overview tab, and the figures of the study selection that the
// spreadsheet does not record (records retrieved and retained at each stage). Edit the values below to update the page.
window.DASHBOARD_ARTICLE = {
  "title": "Accountability Through Digital Object Tracing in Information Security: A Systematic Literature Mapping",
  "authors": [
    {
      "name": "E.C. Dos Santos",
      "orcid": "0000-0002-8275-5540",
      "corresponding": true
    },
    {
      "name": "F. B. V. Benitti",
      "orcid": "0000-0003-2747-9931"
    },
    {
      "name": "P. Vilain",
      "orcid": "0000-0003-1416-6354"
    }
  ],
  "affiliation": "Graduate Program in Computer Science, Department of Informatics and Statistics, Federal University of Santa Catarina, Florianópolis, Santa Catarina, Brazil",
  "abstract": "Organisations increasingly exchange high-value digital objects across technical and institutional boundaries. Existing security mechanisms can record access and verify transactions, but they do not necessarily identify the party responsible for misuse after an object has been delivered. This study maps the technical approaches used to trace digital objects and support accountability in information security. Following a systematic literature mapping protocol, we searched Scopus and performed one iteration of backward and forward snowballing. From 4,958 unique records, 153 primary studies were included and classified by digital object, technology, purpose, application domain, and technical approach. We then assessed the coverage of six accountability requirements derived from the LGPD and the GDPR as an interpretive regulatory lens. Cryptography appeared in 128 studies, blockchain in 118, smart contracts in 102, and distributed file systems in 83. Healthcare was the dominant domain, with 87 studies, and structured records were the most frequent object type, with 89. Data traceability was addressed in 104 studies, whereas forensic attribution appeared in only 18. Only one study combined access control, tamper-evident auditing, decentralised storage, and embedded marking in a single solution, and it targeted copyright protection rather than the attribution of a disclosure to an authorised recipient. These findings show that the literature supports authorisation-time auditability more extensively than post-delivery forensic attribution. Future research should integrate privacy-preserving audit evidence, revocable off-chain storage, interoperable identity and policy formats, and recipient-specific forensic marking.",
  "keywords": [
    "Digital object tracing",
    "Accountability",
    "Information security",
    "Blockchain-based systems",
    "Data protection",
    "GDPR"
  ],
  "selection": {
    "searchDate": "21 January 2025",
    "snowballingDate": "4 May 2025",
    "sources": [
      { "id": "seed", "label": "Scopus search", "inText": "the Scopus search", "setLabel": "Start set", "records": 1413, "screened": 128, "included": 78 },
      { "id": "backward", "label": "Backward snowballing", "inText": "backward snowballing", "short": "BS", "detail": "Reference lists", "setLabel": "BS set", "records": 2324, "screened": 50, "included": 46 },
      { "id": "forward", "label": "Forward snowballing", "inText": "forward snowballing", "short": "FS", "detail": "Citing articles", "setLabel": "FS set", "records": 1318, "screened": 34, "included": 29 }
    ],
    "duplicates": 97,
    "unique": 4958,
    "total": 153
  },
  "researchQuestions": [
    {
      "id": "RQ1",
      "dimension": "objects",
      "question": "What types of digital objects are being tracked?",
      "rationale": "Defines the scope of each solution, ensuring that the approaches are applicable to the various types of digital objects in use."
    },
    {
      "id": "RQ2",
      "dimension": "technologies",
      "question": "What technologies are involved in the proposed solution?",
      "rationale": "Explains the technical foundation of each solution, showing how the approach is implemented, and assessing its feasibility and innovation."
    },
    {
      "id": "RQ3",
      "dimension": "purposes",
      "question": "What is the purpose of the tracking mechanism?",
      "rationale": "Clarifies the specific accountability goals aligning each approach with real-world needs and motivations."
    },
    {
      "id": "RQ4",
      "dimension": "domains",
      "question": "What is the application domain of the proposed solution?",
      "rationale": "Identifies the context in which each approach is applied, ensuring relevance across sectors."
    },
    {
      "id": "RQ5",
      "dimension": "approaches",
      "question": "What is the approach or solution proposed?",
      "rationale": "Details the actual method used for tracing digital objects."
    }
  ]
};
