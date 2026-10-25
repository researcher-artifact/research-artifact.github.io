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
  "abstract": "Organisations increasingly exchange high-value digital objects across technical and institutional boundaries. Existing security mechanisms can record access and verify transactions, but they do not necessarily identify the party responsible for misuse after an object has been delivered. This study maps the technical approaches used to trace digital objects and support accountability in information security. Following a systematic literature mapping protocol, we searched Scopus and performed one iteration of backward and forward snowballing. From 4,958 unique records, 153 primary studies were included, classified by digital object, technology, purpose, application domain, and technical approach, and assessed against fourteen technical requirements derived from the GDPR, with their LGPD counterparts. The solutions converge on cryptography (83.66% of the studies), blockchain (77.12%), smart contracts (66.67%), and distributed file systems (54.25%), applied mostly to structured records (58.17%) and in healthcare (56.86%). They log and restrict access rather than attribute disclosures: data traceability is addressed in 67.97% of the studies, but forensic attribution in only 11.76%. The regulatory assessment shows the same imbalance: requirements that can be met within the organisation, such as access control and traceability logging, have broad counterparts, whereas those that must reach disclosed copies, such as erasure and rectification, have few or none. Only one study combined access control, tamper-evident auditing, decentralised storage, and embedded marking, and it targeted copyright protection rather than attribution to an authorised recipient. These findings show that the literature supports authorisation-time auditability more extensively than post-delivery forensic attribution. Future research should aim to attribute each leaked copy to its authorised recipient, to verify that erasure reaches every recipient, and to demonstrate solutions with real operational data, which only 2.61% of the proposed solutions have done.",
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
