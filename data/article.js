// Article metadata shown on the overview tab (anonymised for double-anonymised review: no authors or affiliation), and the figures of the study selection that the
// spreadsheet does not record (records retrieved and retained at each stage). Edit the values below to update the page.
window.DASHBOARD_ARTICLE = {
  "title": "Accountability Through Digital Object Tracing in Information Security: A Systematic Literature Mapping",
  "authors": [],
  "affiliation": "",
  "anonymised": true,
  "abstract": "Organisations routinely exchange high-value digital objects across institutions. Existing security mechanisms record access and verify transactions but do not necessarily identify who is responsible for misuse after an object has been delivered. This study maps the technical approaches used to trace digital objects and support accountability in information security. Following a systematic literature mapping protocol, we searched Scopus and performed one iteration of backward and forward snowballing. From 4,958 unique records, 153 primary studies were included, classified by digital object, technology, purpose, application domain, and approach group, and assessed against fourteen technical requirements derived from the European Union General Data Protection Regulation (GDPR), with their counterparts in the Brazilian General Data Protection Law (LGPD). The solutions converge on cryptography (77.78% of the studies), blockchain (76.47%), smart contracts (66.01%), and distributed file systems (49.02%), applied mostly to structured records (61.44%) and healthcare (53.59%). They log and restrict access rather than attribute disclosures: data traceability is addressed in 64.71% of the studies, but forensic attribution in only 13.07%. Likewise, requirements that can be met within the organisation, such as access control, have broad counterparts, whereas those that must reach disclosed copies, such as erasure and rectification, have few or none. Only one study combines access control, tamper-evident auditing, decentralised storage, and embedded marking, and it does not mark the copy of each authorised recipient. Future research should attribute each leaked copy to its authorised recipient, verify that erasure reaches every recipient, and validate solutions with real operational data, which only 2.61% of the solutions have used.",
  "keywords": [
    "Digital object tracing",
    "Accountability",
    "Information security",
    "Blockchain-based systems",
    "Data protection",
    "GDPR",
    "LGPD"
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
      "rationale": "Clarifies the specific accountability goals, aligning each approach with real-world needs and motivations."
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
