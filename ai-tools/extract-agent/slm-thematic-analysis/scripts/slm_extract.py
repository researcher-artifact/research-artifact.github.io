#!/usr/bin/env python3
"""Deterministic support tool for the data extraction step of the systematic
literature mapping "Accountability Through Digital Object Tracing in
Information Security".

The AI agent reads each full-text PDF and makes the judgements (data
extraction, thematic coding, research type and evaluation method). This tool
does everything that must be reproducible: it finds the rater roles in
DEF_TA.xlsx, matches PDFs to rows, produces templates, validates the agent's
answers against the protocol, checks that quoted excerpts occur in the PDF,
writes the answers into the columns of the chosen role and computes Fleiss'
kappa.

Only the Python standard library is required, plus openpyxl to *read* the
workbook and pypdf (or the pdftotext command) to read PDFs. The workbook is
*written* at XML level, so charts, tables, the data model (Power Pivot) and
the existing formulas are preserved. The original file is never modified.

Subcommands
  roles      list the rater roles found in the workbook and the columns of each
  match      match PDF files to rows of the Data Extraction sheet
  status     show which fields of a role are still empty
  template   write a JSON template for the agent to fill in
  pdftext    extract the text of a PDF, with page markers
  quotes     check that the quoted excerpts of an answers file occur in the PDF
  validate   check an answers file against the workbook and the protocol
  write      write one or more answers files into a new DEF_TA workbook
  kappa      Fleiss' kappa among raters, per dimension and coding stage
  vocab      print the controlled vocabularies used by the validator
"""
import argparse
import datetime as dt
import difflib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import zipfile
from collections import Counter, OrderedDict

VERSION = "1.1.0"

# ---------------------------------------------------------------------------
# Schema of the DEF_TA workbook (keep in sync with the references/ files)
# ---------------------------------------------------------------------------

DE_SHEET = "Data Extraction"
TA_SHEET = "Thematic Analysis"

# Data extraction fields: key -> header prefix. The column is "<prefix> (<role>)".
DE_FIELDS = OrderedDict([
    ("objective", "Objective of the Study"),
    ("objective_codes", "Objective Codes"),
    ("proposed_solution", "Proposed Solution and Tracking Details"),
    ("tracked", "What is being tracked?"),
    ("architecture", "Architecture Type"),
    ("technology_stack", "Technology Stack"),
    ("purpose", "Purpose of Tracking"),
    ("responsibility", "Responsibility Attribution"),
    ("findings", "Main Findings and Conclusions"),
    ("limitations", "Study Limitations"),
    ("notes", "Notes"),
])
DE_OPTIONAL = {"objective_codes"}

CRITERIA = OrderedDict([
    ("C1", "Used in practice"),
    ("C2", "Novel solution"),
    ("C3", "Empirical evaluation"),
    ("C4", "Evaluated in practice"),
    ("C5", "Conceptual framework"),
    ("C6", "Opinion or authors' experience"),
])
RT_FIELDS = OrderedDict([
    ("research_method", "Research Method"),
    ("evaluation_type", "Evaluation Type"),
])

# Thematic dimensions: key -> (sheet, Equivalences dimension name)
DIMENSIONS = OrderedDict([
    ("digital_object", ("Digital Objects", "DigitalObject")),
    ("technology", ("Technologies", "Technology")),
    ("purpose", ("Purposes", "Purpose")),
    ("domain", ("Domains", "Domain")),
    ("sub_domain", ("Sub-Domains", "SubDomain")),
    ("architecture", ("Architecture", "Architecture")),
])
# Coding stages: key -> (header prefix, Equivalences stage name)
STAGES = OrderedDict([
    ("extraction", ("Data extraction", None)),
    ("codes", ("Codes", "InitialCodes")),
    ("theme", ("Theme", "Theme")),
    ("final_theme", ("Final Theme", "FinalTheme")),
    ("high_level_theme", ("High-level Theme", "HighLevelTheme")),
])
CORE_DIMENSIONS = ("digital_object", "technology", "purpose", "domain")

# Research type (Wieringa et al., 2006; Petersen et al., 2015, Table 7)
RESEARCH_TYPES = ["Evaluation research", "Validation research", "Solution proposal",
                  "Philosophical paper", "Opinion paper", "Experience paper"]
# Evaluation method (Petersen et al., 2015, Fig. 19; Easterbrook et al., 2008; Wohlin et al., 2012)
EVALUATION_METHODS = OrderedDict([
    ("Industrial case study", "Evaluation research"),
    ("Controlled experiment with practitioners", "Evaluation research"),
    ("Practitioner-targeted survey", "Evaluation research"),
    ("Action research", "Evaluation research"),
    ("Ethnography", "Evaluation research"),
    ("Simulation as an empirical method", "Validation research"),
    ("Laboratory experiment (machine or human)", "Validation research"),
    ("Prototyping", "Validation research"),
    ("Mathematical analysis and proof of properties", "Validation research"),
    ("Academic case study", "Validation research"),
])
NO_EVALUATION = "-"

ARCHITECTURES = ["Server-centered", "User-centered", "Hybrid (user-centered and server-centered)"]

# High-level themes reported in the article (section "Themes"). The labels are
# spelt as in the workbook, which is what the formulas and kappa compare.
HIGH_LEVEL = {
    "digital_object": ["Structured Records", "Documents", "Media Files", "Data Files", "Source Code & CAD",
                       "Logs & Audit Trails", "Metadata", "IoT Data Streams"],
    "technology": ["Cryptography", "Blockchain", "Smart Contracts", "Distributed File System",
                   "Steganography & Digital Watermarking", "Machine Learning & AI", "Honey Files",
                   "Containerization & Orchestration", "Interoperability & Authorization Standards",
                   "Knowledge Representation & Analytics", "Digital Forensics Techniques", "Digital Twin"],
    "purpose": ["Data Traceability", "Access Control", "Data Privacy", "Secure Data Sharing",
                "Healthcare Data Governance", "Cybersecurity Risk Mitigation", "Data Auditing",
                "Forensic Attribution & Post-Incident Investigation", "Data Confidentiality",
                "Digital Object Lifecycle Management", "Secure Data Retention", "Copyright Protection",
                "Automated Sensitive Data Detection", "Security-Oriented Data Analytics"],
    "domain": ["Healthcare & Medical Informatics", "Cross-Domain Cybersecurity & Computing",
               "Legal, Compliance & Digital Forensics", "Digital Media", "Industry & Supply Chain",
               "Government & Public Sector", "Financial Services & Banking",
               "Automotive & Intelligent Transportation", "Energy & Smart Grid", "Social Platforms", "Education"],
}

# Final themes of the codebook (references/codebook.md, section 3) and the high-level
# themes each one may take. One entry: the high-level theme is derived by the script.
# Several entries: the rater chooses one of them in high_level_theme (container choice).
_ALL_DO = HIGH_LEVEL["digital_object"]
_ALL_TEC = HIGH_LEVEL["technology"]
FINAL_THEMES = {
    "digital_object": OrderedDict([
        ("Health Data", ["Structured Records"]), ("Medical Data", ["Structured Records"]),
        ("Insurance Data", ["Structured Records"]), ("Financial Data", ["Structured Records"]),
        ("Police Data", ["Structured Records"]), ("Legal Data", ["Structured Records"]),
        ("Personal Data", ["Structured Records", "Data Files", "Documents"]),
        ("Sensitive Data", ["Structured Records", "Data Files", "Documents"]),
        ("Confidential Data", ["Structured Records", "Data Files", "Documents"]),
        ("Files", ["Data Files", "Documents"]), ("Data", ["Data Files", "Documents"]),
        ("Data Chunks", ["Data Files"]), ("JSONs", ["Data Files"]), ("XMLs", ["Data Files"]),
        ("Binary Files", ["Data Files"]), ("Supply Chain Data", ["Data Files"]),
        ("Plain Text", ["Documents"]),
        ("Images", ["Media Files"]), ("Videos", ["Media Files"]), ("Audios", ["Media Files"]),
        ("Copyrights Data", ["Media Files"]),
        ("Source-code", ["Source Code & CAD"]), ("CAD Files", ["Source Code & CAD"]),
        ("Engineering Supervision Data", ["Source Code & CAD", "Documents"]),
        ("Logs", ["Logs & Audit Trails"]), ("Metadata", ["Metadata"]), ("IoT Data", ["IoT Data Streams"]),
        ("Digital Objects", list(_ALL_DO)),
    ]),
    "technology": OrderedDict([
        ("Cryptography", ["Cryptography"]), ("Trusted Platform Module", ["Cryptography"]),
        ("Biometric authentication", ["Cryptography"]),
        ("Blockchain", ["Blockchain"]), ("NFT", ["Blockchain"]),
        ("Smart contracts", ["Smart Contracts"]),
        ("Distributed File System", ["Distributed File System"]), ("Virtual File System", ["Distributed File System"]),
        ("Steganography", ["Steganography & Digital Watermarking"]),
        ("Steganography & Digital Watermarking", ["Steganography & Digital Watermarking"]),
        ("Machine Learning", ["Machine Learning & AI"]), ("Non-Generative Neural Network", ["Machine Learning & AI"]),
        ("Honey Files", ["Honey Files"]),
        ("Containerization and orchestration", ["Containerization & Orchestration"]),
        ("Semantic Web", ["Interoperability & Authorization Standards"]),
        ("OAuth 2.0", ["Interoperability & Authorization Standards"]),
        ("Data Analytics", ["Knowledge Representation & Analytics"]), ("GPS", ["Knowledge Representation & Analytics"]),
        ("OCR", ["Knowledge Representation & Analytics"]),
        ("Registry Comparison", ["Digital Forensics Techniques"]),
        ("Forensic Trace Analysis", ["Digital Forensics Techniques"]),
        ("Digital Twin", ["Digital Twin"]),
        ("Infosec", list(_ALL_TEC)), ("Conceptual Model Only", list(_ALL_TEC)),
    ]),
    "purpose": OrderedDict([
        ("Data Traceability", ["Data Traceability"]), ("Access Control", ["Access Control"]),
        ("Data Privacy", ["Data Privacy"]), ("Sensitive Data Protection", ["Data Privacy"]),
        ("Secure Data Sharing", ["Secure Data Sharing"]), ("Secure Data Transactions", ["Secure Data Sharing"]),
        ("EHR Management", ["Healthcare Data Governance"]),
        ("Data Security", ["Cybersecurity Risk Mitigation"]),
        ("Mitigate Cybersecurity Risks", ["Cybersecurity Risk Mitigation"]),
        ("Data Auditing", ["Data Auditing"]), ("Data Integrity", ["Data Auditing"]),
        ("Support forensic investigations", ["Forensic Attribution & Post-Incident Investigation"]),
        ("Data Confidentiality", ["Data Confidentiality"]),
        ("Data Management", ["Digital Object Lifecycle Management"]),
        ("Legal Document Management", ["Digital Object Lifecycle Management"]),
        ("Secure Data Storage", ["Secure Data Retention"]),
        ("Copyrights Protection", ["Copyright Protection"]),
        ("Detecting Confidential or Sensitive Data", ["Automated Sensitive Data Detection"]),
        ("Data Analyzing", ["Security-Oriented Data Analytics"]),
    ]),
    "domain": OrderedDict([
        ("Healthcare and Medical Informatics", ["Healthcare & Medical Informatics"]),
        ("Technology", ["Cross-Domain Cybersecurity & Computing"]),
        ("Legal, Compliance and Digital Forensics", ["Legal, Compliance & Digital Forensics"]),
        ("Digital Media", ["Digital Media"]),
        ("Supply Chain & Logistics", ["Industry & Supply Chain"]), ("Industry", ["Industry & Supply Chain"]),
        ("Public Administration", ["Government & Public Sector"]),
        ("Financial", ["Financial Services & Banking"]),
        ("Automotive", ["Automotive & Intelligent Transportation"]),
        ("Energy", ["Energy & Smart Grid"]),
        ("Social platforms", ["Social Platforms"]),
        ("Education", ["Education"]),
    ]),
}
# Sub-domains: closed list (final theme = high-level theme); empty when there is no
# setting beyond the domain.
SUB_DOMAINS = ["Electronic Health Record Management", "Electronic Health Record Interoperability",
               "Cloud computing", "Public Health", "Internet of Medical Things",
               "Medical imaging and remote monitoring", "Internet of Things", "Data sharing",
               "Specialized Disease Data", "Files/Documents Management", "Data management", "Data auditing",
               "Telesurgery"]
# Final themes that need an explicit decision rule (codebook section 6): the support
# entry of the label must cite one of these rule identifiers.
GUARDED = {
    "digital_object": {"Metadata": ["DO-2"], "Logs": ["DO-3"], "Personal Data": ["DO-4"], "Sensitive Data": ["DO-4"],
                       "Confidential Data": ["DO-4"], "Files": ["DO-4"], "Data": ["DO-4"],
                       "Digital Objects": ["DO-4"]},
    "technology": {"Containerization and orchestration": ["TEC-2"], "Semantic Web": ["TEC-3"],
                   "OAuth 2.0": ["TEC-3"], "Data Analytics": ["TEC-4"], "GPS": ["TEC-4"], "OCR": ["TEC-4"],
                   "Infosec": ["TEC-5"], "Conceptual Model Only": ["TEC-5"]},
    "purpose": {"Data Security": ["PUR-2"], "Mitigate Cybersecurity Risks": ["PUR-2"], "Data Auditing": ["PUR-3"],
                "Data Integrity": ["PUR-3"], "Secure Data Storage": ["PUR-4"], "Data Confidentiality": ["PUR-4"],
                "EHR Management": ["PUR-5"], "Data Analyzing": ["PUR-6"], "Data Management": ["PUR-6"],
                "Legal Document Management": ["PUR-6"]},
    "domain": {},
    "sub_domain": {},
}
# Maximum number of high-level themes (final themes for the sub-domain) per study.
MAX_LABELS = {"digital_object": 4, "technology": 5, "purpose": 5, "domain": 2, "sub_domain": 2}
MAX_EXCERPTS = 10
MAX_CODE_WORDS = 8
MAX_NEW = 1
# Tooling that is not a tracking technology (codebook rule TEC-1): rejected as [NEW] themes.
NOT_TRACKING_TECH = re.compile(r"benchmark|performance|testing|test ?net|programming|language|web app|"
                               r"database|sql|simulat|ide\b|development tool", re.I)
# Architecture decision (references/def-fields.md): the architecture is seen from the
# data subject (the owner of the tracked object), not from the technical construction.
# Active actions give the subject control over the object; passive ones only let the
# subject follow what the controller allows.
SUBJECT_ACTIVE = ("grant", "revoke", "consent", "set_policy", "share", "delete", "correct", "export")
SUBJECT_PASSIVE = ("view", "trace", "notified", "none")
CONTROLLER_DECIDES = ("none", "some", "all")
RULES_VERSION = "2026-11-16"

MISSING_TOKENS = ["NOT REPORTED", "NOT APPLICABLE"]
NOT_ADDRESSED = "Not addressed in the article."
CRITERION_NAMES = {k: v for k, v in CRITERIA.items()}

# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def norm_space(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def norm_header(s):
    return norm_space(s).lower()


def norm_label(s):
    """Normalisation used for comparisons (and for kappa, as in the article)."""
    s = str(s).replace(" ", " ").replace("\t", " ").replace("ﬁ", "fi").replace("ﬂ", "fl")
    s = s.replace("’", "'").replace("‘", "'").replace("–", "-").replace("&", "and")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def uk_us(s):
    """Fold British and American spellings so that either is accepted as input."""
    s = norm_label(s)
    for a, b in (("isation", "ization"), ("ise ", "ize "), ("centred", "centered"), ("centric", "centered"),
                 ("organis", "organiz"), ("behaviour", "behavior")):
        s = s.replace(a, b)
    return s


def as_list(v):
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return [norm_space(x) for x in v if norm_space(x)]
    return [norm_space(x) for x in re.split(r"[\n;]", str(v)) if norm_space(x)]


def split_labels(value, known=()):
    """Split a cell of comma-separated labels, keeping known labels that contain commas."""
    text = str(value or "")
    out = []
    for k in sorted(known, key=len, reverse=True):
        if "," in k:
            pat = re.compile(re.escape(k), re.I)
            if pat.search(text):
                out.append(k)
                text = pat.sub("\n", text)
    out += [norm_space(x) for x in re.split(r"[\n,;]", text) if norm_space(x)]
    return out


def is_formula(v):
    if v is None:
        return False
    if hasattr(v, "text"):  # openpyxl ArrayFormula
        return True
    return isinstance(v, str) and v.startswith("=")


def formula_text(v):
    if hasattr(v, "text"):
        return v.text
    return v


def today():
    return dt.date.today().isoformat()


def load_openpyxl():
    try:
        import openpyxl  # noqa: F401
        return openpyxl
    except ImportError:
        sys.exit("openpyxl is required to read the workbook: pip install openpyxl")


# ---------------------------------------------------------------------------
# Reading the workbook
# ---------------------------------------------------------------------------


class Workbook:
    """Read-only view of DEF_TA: headers, rows by Article ID, formulas and cached values."""

    def __init__(self, path):
        if not os.path.exists(path):
            sys.exit(f"Workbook not found: {path}")
        openpyxl = load_openpyxl()
        self.path = path
        self.wb = openpyxl.load_workbook(path, read_only=True, data_only=False)
        self.wbv = openpyxl.load_workbook(path, read_only=True, data_only=True)
        self.sheetnames = list(self.wb.sheetnames)
        self._cache = {}

    def sheet(self, name):
        """Return dict with header list, rows (list of tuples) and index by Article ID."""
        if name in self._cache:
            return self._cache[name]
        if name not in self.sheetnames:
            self._cache[name] = None
            return None
        ws, wsv = self.wb[name], self.wbv[name]
        rows = list(ws.iter_rows(values_only=True))
        vals = list(wsv.iter_rows(values_only=True))
        header = [norm_space(h) if h is not None else "" for h in (rows[0] if rows else [])]
        index = OrderedDict()
        for i, r in enumerate(rows[1:], start=2):
            if r and r[0] not in (None, "") and not is_formula(r[0]):
                index.setdefault(str(r[0]).strip(), i)
        info = {"name": name, "header": header, "rows": rows, "values": vals, "index": index}
        self._cache[name] = info
        return info

    def column(self, sheet_name, header_text):
        info = self.sheet(sheet_name)
        if not info:
            return None
        target = norm_header(header_text)
        for i, h in enumerate(info["header"]):
            if norm_header(h) == target:
                return i
        return None

    def cell(self, sheet_name, row, col, values=False):
        info = self.sheet(sheet_name)
        data = info["values"] if values else info["rows"]
        if row - 1 >= len(data):
            return None
        r = data[row - 1]
        return r[col] if col < len(r) else None

    def last_data_row(self, sheet_name):
        info = self.sheet(sheet_name)
        return max(info["index"].values()) if info and info["index"] else 1

    def de_record(self, article_id):
        info = self.sheet(DE_SHEET)
        row = info["index"].get(article_id)
        if not row:
            return None
        def g(h):
            c = self.column(DE_SHEET, h)
            return self.cell(DE_SHEET, row, c, values=True) if c is not None else None
        rayyan = g("Ryyan ID")
        if rayyan in (None, "") and self.sheet("Data Set"):  # formula without a cached value
            r = self.sheet("Data Set")["index"].get(article_id)
            rayyan = self.cell("Data Set", r, 1, values=True) if r else None
        return {"article_id": article_id, "row": row, "rayyan_id": rayyan, "dataset": g("Dataset"),
                "paper": g("Papper"), "doi": g("DOI"), "title": g("Titlle"), "year": g("Year")}


ROLE_RE = re.compile(r"\(([^()]*)\)\s*$")
NOT_ROLES = {"final decision", "inferred"}


def discover_roles(wb):
    """Roles are the parenthesised suffixes of the rater columns, e.g. 'Researcher 1'."""
    roles = OrderedDict()
    for sheet in [DE_SHEET] + [d[0] for d in DIMENSIONS.values()]:
        info = wb.sheet(sheet)
        if not info:
            continue
        for h in info["header"]:
            m = ROLE_RE.search(h)
            if not m:
                continue
            role = norm_space(m.group(1))
            if role.lower() in NOT_ROLES:
                continue
            roles.setdefault(role, []).append(f"{sheet}: {h}")
    return roles


def resolve_role(wb, role):
    roles = discover_roles(wb)
    for r in roles:
        if r.lower() == norm_space(role).lower():
            return r
    return norm_space(role)  # a new role: columns may be added with --add-columns


# ---------------------------------------------------------------------------
# Targets: where each answer goes
# ---------------------------------------------------------------------------


def criterion_columns(wb, key, role):
    """C1..C6 are stored either as one column '<C> (<role>)' with 'True. Justification: ...'
    or as two columns '<C> - Value (<role>)' and '<C> - Justification (<role>)'."""
    single = wb.column(DE_SHEET, f"{key} ({role})")
    value = wb.column(DE_SHEET, f"{key} - Value ({role})")
    just = wb.column(DE_SHEET, f"{key} - Justification ({role})")
    if value is not None or just is not None:
        return {"mode": "split", "value": value, "justification": just,
                "headers": [f"{key} - Value ({role})", f"{key} - Justification ({role})"]}
    return {"mode": "single", "col": single, "headers": [f"{key} ({role})"]}


def targets_for(wb, role, skills):
    """List of dicts: skill, key, sheet, header, col (None if the column is missing)."""
    out = []
    if "extraction" in skills:
        for key, prefix in DE_FIELDS.items():
            h = f"{prefix} ({role})"
            out.append({"skill": "extraction", "key": key, "sheet": DE_SHEET, "header": h,
                        "col": wb.column(DE_SHEET, h), "optional": key in DE_OPTIONAL})
    if "research_type" in skills:
        for key in CRITERIA:
            cc = criterion_columns(wb, key, role)
            if cc["mode"] == "split":
                out.append({"skill": "research_type", "key": f"{key}.value", "sheet": DE_SHEET,
                            "header": cc["headers"][0], "col": cc["value"]})
                out.append({"skill": "research_type", "key": f"{key}.justification", "sheet": DE_SHEET,
                            "header": cc["headers"][1], "col": cc["justification"]})
            else:
                out.append({"skill": "research_type", "key": key, "sheet": DE_SHEET,
                            "header": cc["headers"][0], "col": cc["col"]})
        for key, prefix in RT_FIELDS.items():
            h = f"{prefix} ({role})"
            out.append({"skill": "research_type", "key": key, "sheet": DE_SHEET, "header": h,
                        "col": wb.column(DE_SHEET, h)})
    if "thematic" in skills:
        for dim, (sheet, _) in DIMENSIONS.items():
            if not wb.sheet(sheet):
                continue
            for stage, (prefix, _) in STAGES.items():
                h = f"{prefix} ({role})"
                col = wb.column(sheet, h)
                if dim == "architecture" and stage != "codes" and not (stage == "extraction" and col is not None):
                    continue  # the Architecture themes are formulas over Architecture Type
                out.append({"skill": "thematic", "key": f"{dim}.{stage}", "sheet": sheet, "header": h,
                            "col": col, "optional": dim == "sub_domain" and stage in ("final_theme", "high_level_theme")})
    return out


SKILL_ALIASES = {"extraction": "extraction", "data-extraction": "extraction", "de": "extraction",
                 "thematic": "thematic", "thematic-analysis": "thematic", "ta": "thematic",
                 "research-type": "research_type", "research_type": "research_type", "rt": "research_type",
                 "all": "all"}


def parse_skills(s):
    out = set()
    for x in (s or "all").split(","):
        k = SKILL_ALIASES.get(x.strip().lower())
        if not k:
            sys.exit(f"Unknown skill '{x}'. Use extraction, thematic, research-type or all.")
        out |= {"extraction", "thematic", "research_type"} if k == "all" else {k}
    return out


# ---------------------------------------------------------------------------
# roles, match, status, template, vocab
# ---------------------------------------------------------------------------


def cmd_roles(a):
    wb = Workbook(a.defta)
    roles = discover_roles(wb)
    if not roles:
        sys.exit("No rater columns found. Is this a DEF_TA workbook?")
    print(f"Workbook: {os.path.basename(a.defta)}")
    print(f"Studies in '{DE_SHEET}': {len(wb.sheet(DE_SHEET)['index'])}")
    print("Roles found (the agent writes only in the columns of the role chosen by the user):")
    for i, (role, cols) in enumerate(roles.items(), 1):
        print(f"  {i}. {role}  ({len(cols)} columns)")
        missing = [t["header"] for t in targets_for(wb, role, {"extraction", "thematic", "research_type"})
                   if t["col"] is None and not t.get("optional")]
        if missing:
            print(f"     no column for: {'; '.join(missing)}")
    if a.verbose:
        for role, cols in roles.items():
            print(f"\n[{role}]")
            for c in cols:
                print(f"  {c}")


def pdf_keys(path):
    stem = os.path.splitext(os.path.basename(path))[0]
    keys = {stem, stem.replace("_", "/")}
    m = re.match(r"(10\.\d{4,9})_(.+)$", stem)
    if m:
        keys.add(m.group(1) + "/" + m.group(2).replace("_", "/"))
        keys.add(m.group(1) + "/" + m.group(2))
    return {k.lower() for k in keys}


def match_pdf(wb, path):
    keys = pdf_keys(path)
    info = wb.sheet(DE_SHEET)
    for aid in info["index"]:
        rec = wb.de_record(aid)
        cand = {str(aid).lower(), str(rec["rayyan_id"] or "").lower(), str(rec["paper"] or "").lower(),
                str(rec["doi"] or "").lower().replace("https://doi.org/", "")}
        if keys & {c for c in cand if c}:
            return rec
    return None


def cmd_match(a):
    wb = Workbook(a.defta)
    unmatched = 0
    print("pdf\tarticle_id\tpaper\trayyan_id\tdoi\ttitle")
    for p in a.pdfs:
        rec = match_pdf(wb, p)
        if rec:
            print(f"{os.path.basename(p)}\t{rec['article_id']}\t{rec['paper']}\t{rec['rayyan_id']}\t{rec['doi']}\t{rec['title']}")
        else:
            unmatched += 1
            print(f"{os.path.basename(p)}\tNOT FOUND\t\t\t\t")
    if unmatched:
        print(f"\n{unmatched} PDF(s) not found in '{DE_SHEET}'. The file name must be the Article ID, the "
              "Rayyan ID, the Papper code or the DOI (with '/' replaced by '_'). Ask the user which row it is, "
              "or run the study-selection agent first so that the study is in Data Extraction.", file=sys.stderr)


def filled(v):
    return v is not None and str(v).strip() not in ("", "0", "None")


def cmd_status(a):
    wb = Workbook(a.defta)
    role = resolve_role(wb, a.role)
    skills = parse_skills(a.skill)
    tg = targets_for(wb, role, skills)
    ids = a.ids.split(",") if a.ids else list(wb.sheet(DE_SHEET)["index"])
    print(f"Role: {role}")
    missing_cols = sorted({t["header"] for t in tg if t["col"] is None and not t.get("optional")})
    if missing_cols:
        print("Columns that do not exist for this role (write with --add-columns, or skip):")
        for h in missing_cols:
            print(f"  - {h}")
    print("\narticle_id\tpaper\t" + "\t".join(sorted(skills)) + "\tempty fields")
    done = 0
    for aid in ids:
        rec = wb.de_record(aid)
        if not rec:
            print(f"{aid}\tNOT IN {DE_SHEET}")
            continue
        per = Counter()
        tot = Counter()
        empty = []
        for t in tg:
            if t["col"] is None:
                continue
            info = wb.sheet(t["sheet"])
            row = info["index"].get(aid)
            v = wb.cell(t["sheet"], row, t["col"]) if row else None
            tot[t["skill"]] += 1
            if filled(v):
                per[t["skill"]] += 1
            elif not t.get("optional"):
                empty.append(t["key"])
        if not empty:
            done += 1
            if a.only_pending:
                continue
        cells = "\t".join(f"{per[s]}/{tot[s]}" for s in sorted(skills))
        print(f"{aid}\t{rec['paper']}\t{cells}\t{len(empty)}")
    print(f"\n{done} of {len(ids)} studies complete for this role.")


def cmd_template(a):
    wb = Workbook(a.defta)
    role = resolve_role(wb, a.role)
    skills = parse_skills(a.skill)
    ids = []
    for x in a.ids.split(","):
        x = x.strip()
        rec = wb.de_record(x) or (match_pdf(wb, x) if x else None)
        if not rec:
            sys.exit(f"'{x}' not found in '{DE_SHEET}'.")
        ids.append(rec)
    arts = []
    for rec in ids:
        art = OrderedDict([("article_id", rec["article_id"]), ("paper", rec["paper"]), ("title", rec["title"]),
                           ("doi", rec["doi"]), ("year", rec["year"]), ("source_pdf", "")])
        if "extraction" in skills:
            art["data_extraction"] = OrderedDict((k, "") for k in DE_FIELDS)
            art["data_extraction"]["architecture_decision"] = OrderedDict([
                ("subject", ""), ("subject_actions", []), ("controller_decides", ""), ("evidence", "")])
        if "research_type" in skills:
            rt = OrderedDict((k, {"value": None, "justification": ""}) for k in CRITERIA)
            rt["research_method"] = ""
            rt["evaluation_type"] = ""
            art["research_type"] = rt
        if "thematic" in skills:
            th = OrderedDict()
            for dim in DIMENSIONS:
                if dim == "architecture":
                    th[dim] = OrderedDict([("codes", [])])
                else:
                    th[dim] = OrderedDict((s, []) for s in STAGES)
                    th[dim]["support"] = OrderedDict()
            th["self_verification"] = ""
            art["thematic"] = th
        arts.append(art)
    doc = OrderedDict([("tool", f"slm_extract {VERSION}"), ("rules", RULES_VERSION), ("role", role),
                       ("model", ""), ("created", today()), ("articles", arts)])
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"Template written: {a.out} ({len(arts)} article(s), role '{role}', skills: {', '.join(sorted(skills))})")


def vocab_from_workbook(wb, dim):
    """Final themes and high-level themes already used in the workbook for a dimension."""
    sheet = DIMENSIONS[dim][0]
    info = wb.sheet(sheet)
    final, high = Counter(), Counter()
    if not info:
        return final, high
    known = HIGH_LEVEL.get(dim, [])
    for i, h in enumerate(info["header"]):
        hl = norm_header(h)
        target = None
        if hl.startswith("final theme") or hl == "theme (final decision)":
            target = final
        elif hl.startswith("high-level theme"):
            target = high
        if target is None:
            continue
        for r in info["values"][1:]:
            if i < len(r) and r[i] not in (None, "", 0, "0", "None"):
                for lab in split_labels(r[i], known):
                    if lab and lab.lower() not in ("none", "0"):
                        target[lab] += 1
    return final, high


def cmd_vocab(a):
    wb = Workbook(a.defta) if a.defta else None
    print("Research types:", "; ".join(RESEARCH_TYPES))
    print("Evaluation methods:")
    for m, t in EVALUATION_METHODS.items():
        print(f"  {m}  [{t}]")
    print(f"  {NO_EVALUATION}  [no empirical evaluation]")
    print("Architecture types:", "; ".join(ARCHITECTURES))
    for dim in DIMENSIONS:
        if dim in HIGH_LEVEL:
            print(f"\nHigh-level themes, {dim}: " + "; ".join(HIGH_LEVEL[dim]))
        if wb:
            final, high = vocab_from_workbook(wb, dim)
            if final:
                print(f"Final themes in the workbook, {dim}: " + "; ".join(f"{k} ({v})" for k, v in final.most_common()))
            if dim not in HIGH_LEVEL and high:
                print(f"High-level themes in the workbook, {dim}: " + "; ".join(f"{k} ({v})" for k, v in high.most_common()))


# ---------------------------------------------------------------------------
# PDF text and quote verification
# ---------------------------------------------------------------------------


def pdf_pages(path):
    """Return the text of each page. Tries pypdf, then pdftotext. A .txt file written by
    the pdftext command is read back page by page."""
    if path.lower().endswith(".txt"):
        with open(path, encoding="utf-8") as f:
            return [x for x in re.split(r"\n===== page \d+ =====\n", "\n" + f.read()) if x.strip()]
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        pages = [(p.extract_text() or "") for p in reader.pages]
        if sum(len(p.strip()) for p in pages) > 200:
            return pages
    except Exception:
        pass
    if shutil.which("pdftotext"):
        out = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True)
        if out.returncode == 0:
            return out.stdout.split("\f")
    try:
        from pypdf import PdfReader  # noqa: F811
        return [(p.extract_text() or "") for p in PdfReader(path).pages]
    except Exception as e:
        sys.exit(f"Cannot read {path}: {e}. Install pypdf (pip install pypdf) or poppler-utils.")


def cmd_pdftext(a):
    pages = pdf_pages(a.pdf)
    chars = sum(len(p.strip()) for p in pages)
    with open(a.out, "w", encoding="utf-8") as f:
        for i, p in enumerate(pages, 1):
            f.write(f"\n===== page {i} =====\n{unicodedata.normalize('NFKC', p)}")
    print(f"{len(pages)} page(s), {chars} characters written to {a.out}")
    if chars < 500 * max(1, len(pages)) / 4:
        print("WARNING: very little text. The PDF may be scanned; without OCR, treat it as UNREADABLE.")


def fold_text(s):
    s = unicodedata.normalize("NFKC", str(s))
    s = s.replace("­", "")
    s = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", s)  # hyphenation at line breaks
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", " ", s).lower()
    return s


def squeeze(s):
    return re.sub(r"[^a-z0-9]", "", s)


def quote_found(quote, page_folds):
    """Return (status, page, ratio). status: exact, approximate or missing."""
    q = fold_text(quote).strip(" .;,\"'")
    if len(q) < 8:
        return "exact", None, 1.0
    qs = squeeze(q)
    for i, (t, ts) in enumerate(page_folds, 1):
        if q in t or (qs and qs in ts):
            return "exact", i, 1.0
    best = (0.0, None)
    for i, (t, ts) in enumerate(page_folds, 1):
        if not ts:
            continue
        m = difflib.SequenceMatcher(None, qs, ts, autojunk=False).find_longest_match(0, len(qs), 0, len(ts))
        ratio = m.size / max(1, len(qs))
        if ratio < 0.5:
            continue
        lo = max(0, m.b - m.a - 10)
        window = ts[lo: lo + len(qs) + 20]
        ratio = max(ratio, difflib.SequenceMatcher(None, qs, window, autojunk=False).ratio())
        if ratio > best[0]:
            best = (ratio, i)
    if best[0] >= 0.9:
        return "approximate", best[1], best[0]
    return "missing", best[1], best[0]


def article_quotes(art):
    """Yield (location, quote) for every verbatim excerpt in an answers record."""
    th = art.get("thematic") or {}
    for dim in DIMENSIONS:
        for q in as_list((th.get(dim) or {}).get("extraction")):
            if q != NOT_ADDRESSED:
                yield f"thematic.{dim}.extraction", q.strip().strip('"').strip("“”")
    de = art.get("data_extraction") or {}
    for key in DE_FIELDS:
        for q in re.findall(r"[\"“]([^\"”]{12,})[\"”]", str(de.get(key) or "")):
            yield f"data_extraction.{key}", q


def find_pdf(art, pdfs, single):
    by_id = {}
    for p in pdfs:
        by_id[os.path.splitext(os.path.basename(p))[0].lower()] = p
    src = art.get("source_pdf") or ""
    for k in (os.path.splitext(os.path.basename(src))[0].lower(), str(art.get("article_id")).lower()):
        if k in by_id:
            return by_id[k]
    return pdfs[0] if single and len(pdfs) == 1 else None


def check_quotes(doc, pdfs, rep, verbose=False, out=None):
    """Check every verbatim excerpt against its PDF (or pdftext .txt). Missing excerpts are
    errors, approximate ones warnings. Returns (total, missing)."""
    total = bad = 0
    single = len(doc["articles"]) == 1
    for art in doc["articles"]:
        aid = art.get("article_id")
        path = find_pdf(art, pdfs, single)
        if not path:
            rep.err(aid, "source_pdf", "no PDF given for this study (set source_pdf and pass the file)")
            bad += 1
            continue
        folds = [(fold_text(p), squeeze(fold_text(p))) for p in pdf_pages(path)]
        for loc, q in article_quotes(art):
            total += 1
            status, page, ratio = quote_found(q, folds)
            if out is not None and (status != "exact" or verbose):
                out.append(f"{aid}\t{loc}\t{status}\tpage {page}\t{ratio:.2f}\t{q[:90]}")
            if status == "missing":
                bad += 1
                rep.err(aid, loc, f"excerpt not found in the PDF, copy it verbatim: '{q[:70]}'")
            elif status == "approximate":
                rep.warn(aid, loc, f"excerpt found only approximately (page {page}, {ratio:.2f}): '{q[:70]}'")
    return total, bad


def cmd_quotes(a):
    doc = read_answers(a.input)
    rep, lines = Report(), []
    total, bad = check_quotes(doc, a.pdf, rep, a.verbose, lines)
    for line in lines:
        print(line)
    for e in rep.errors:
        if "source_pdf" in e:
            print(e)
    print(f"\n{total} excerpt(s) checked; {bad} not found in the PDF.")
    if bad:
        print("Every excerpt must be copied verbatim from the article. Correct or remove the excerpts "
              "marked 'missing' and run the check again.")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Answers files and validation
# ---------------------------------------------------------------------------


def read_answers(paths):
    if isinstance(paths, str):
        paths = [paths]
    role, model, arts = None, None, OrderedDict()
    for p in paths:
        with open(p, encoding="utf-8") as f:
            try:
                doc = json.load(f, object_pairs_hook=OrderedDict)
            except json.JSONDecodeError as e:
                sys.exit(f"{p}: invalid JSON ({e})")
        if isinstance(doc, list):
            doc = {"articles": doc}
        r = doc.get("role")
        if r:
            if role and norm_space(r).lower() != norm_space(role).lower():
                sys.exit(f"{p}: role '{r}' differs from '{role}' in another file.")
            role = r
        mdl = norm_space(doc.get("model"))
        if mdl:
            if model and mdl.lower() != model.lower():
                sys.exit(f"{p}: model '{mdl}' differs from '{model}' in another file; one model per run.")
            model = mdl
        for art in doc.get("articles", []):
            aid = str(art.get("article_id") or "").strip()
            if not aid:
                sys.exit(f"{p}: an article has no article_id.")
            merged = arts.setdefault(aid, OrderedDict([("article_id", aid)]))
            for k, v in art.items():
                if k in ("data_extraction", "research_type", "thematic") and isinstance(v, dict):
                    merged.setdefault(k, OrderedDict()).update(v)
                elif v not in (None, ""):
                    merged[k] = v
    return {"role": role, "model": model, "articles": list(arts.values())}


def truth(v):
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("true", "t", "yes", "1"):
        return True
    if s in ("false", "f", "no", "0"):
        return False
    return None


def expected_research_type(c, c6_kind):
    """Petersen et al. (2015), Table 7, with C4 making 'in practice' explicit for the evaluation.
    c: dict C1..C6 -> bool. c6_kind: 'opinion', 'experience' or ''. Returns (type, rule) or (None, message)."""
    C1, C2, C3, C4, C5, C6 = (c[k] for k in CRITERIA)
    if C4 and not (C1 and C3):
        return None, "C4 (evaluated in practice) requires C1 (used in practice) and C3 (empirical evaluation)."
    if C6:
        if C3:
            return None, "C6 (opinion or experience) excludes C3: a paper with an empirical evaluation is not an opinion or experience paper."
        if c6_kind == "opinion":
            if C1 or C2:
                return None, "An opinion paper (R6) has C1 and C2 False."
            return "Opinion paper", "R6"
        if c6_kind == "experience":
            if not C1 or C2:
                return None, "An experience paper (R3) reports a solution used in practice (C1 True) that is not novel (C2 False)."
            return "Experience paper", "R3"
        return None, "With C6 True, start the C6 justification with 'Opinion:' or 'Experience:'."
    if C3 and C4:
        return "Evaluation research", "R1"
    if C3 and C1:
        return None, ("C1 and C3 are True but C4 is False. If the solution is used in practice and the evaluation "
                      "investigates that use, set C4 True (Evaluation research); if the evaluation was done in a "
                      "laboratory, testnet or simulation, the solution is not used in practice: set C1 False "
                      "(Validation research).")
    if C3:
        return "Validation research", "R4"
    if C2:
        return "Solution proposal", "R2"
    if C5:
        return "Philosophical paper", "R5"
    return None, "No rule of the decision table applies (all of C2, C3, C5 and C6 are False)."


class Report:
    def __init__(self):
        self.errors, self.warnings, self.notes = [], [], []

    def err(self, aid, where, msg):
        self.errors.append(f"{aid} | {where}: {msg}")

    def warn(self, aid, where, msg):
        self.warnings.append(f"{aid} | {where}: {msg}")


def check_text(rep, aid, key, v, required=True):
    s = norm_space(v)
    if not s:
        if required:
            rep.err(aid, key, "empty; write the content or one of " + ", ".join(MISSING_TOKENS))
        return
    if "|" in s and key != "notes":
        rep.warn(aid, key, "contains '|'; it is kept as is in the workbook")


def match_vocab(label, vocab):
    """Return the vocabulary entry equal to label (ignoring case, '&'/'and' and UK/US spelling)."""
    key = uk_us(label)
    for v in vocab:
        if uk_us(v) == key:
            return v
    return None


def derive_architecture(actions, controller):
    """Rules ARC-1 to ARC-3 of references/def-fields.md, from the data subject's point of view.
    Returns (label, rule) or (None, message)."""
    active = [a for a in actions if a in SUBJECT_ACTIVE]
    if not active:
        return "Server-centered", "ARC-1"
    if controller == "none":
        return "User-centered", "ARC-2"
    if controller == "some":
        return "Hybrid (user-centered and server-centered)", "ARC-3"
    return None, ("the subject has active actions (" + ", ".join(active) + ") but the controller takes all the "
                  "decisions: if the controller can override or must approve every action, those actions are not "
                  "control; answer controller_decides 'some', or list only the passive actions")


def check_architecture(rep, aid, label, dec):
    where = "data_extraction.architecture_decision"
    if not isinstance(dec, dict):
        rep.err(aid, where, "missing: name the data subject, list the subject's actions over the tracked objects, say "
                "whether the controller decides, and give the evidence (references/def-fields.md, Architecture Type)")
        return
    ok = True
    if not norm_space(dec.get("subject")):
        rep.err(aid, f"{where}.subject", "name the data subject (the owner of the tracked object, e.g. patient)")
    acts = [norm_space(x).lower().replace(" ", "_") for x in as_list(dec.get("subject_actions"))] if isinstance(
        dec.get("subject_actions"), list) else [norm_space(x).lower().replace(" ", "_")
                                                for x in str(dec.get("subject_actions") or "").split(",") if norm_space(x)]
    bad = [x for x in acts if x not in SUBJECT_ACTIVE + SUBJECT_PASSIVE]
    if not acts or bad:
        ok = False
        rep.err(aid, f"{where}.subject_actions", (f"unknown: {', '.join(bad)}; " if bad else "empty; ") +
                f"use active actions {', '.join(SUBJECT_ACTIVE)} or passive ones {', '.join(SUBJECT_PASSIVE)}")
    ctl = norm_space(dec.get("controller_decides")).lower()
    if ctl not in CONTROLLER_DECIDES:
        ok = False
        rep.err(aid, f"{where}.controller_decides", f"'{ctl}' must be one of: {', '.join(CONTROLLER_DECIDES)}")
    if not norm_space(dec.get("evidence")):
        rep.err(aid, f"{where}.evidence", "cite the sections or pages that show the subject's actions and the controller's role")
    if not ok:
        return
    exp, rule = derive_architecture(acts, ctl)
    if exp is None:
        rep.err(aid, where, rule)
    elif exp != label:
        rep.err(aid, "data_extraction.architecture", f"'{label}' contradicts the decision questions, which give "
                f"'{exp}' (rule {rule}); the architecture is seen from the data subject, not from the technical "
                "construction")


def label_key(s):
    return uk_us(str(s).replace("[NEW]", "").strip())


def find_final(dim, label):
    """Return the codebook final theme equal to label, or None."""
    k = label_key(label)
    for f in FINAL_THEMES.get(dim, {}):
        if uk_us(f) == k:
            return f
    if dim == "sub_domain":
        for f in SUB_DOMAINS:
            if uk_us(f) == k:
                return f
    return None


def finals_of_high_level(dim, hl):
    return [f for f, hls in FINAL_THEMES.get(dim, {}).items() if hl in hls]


def theme_labels(dim, value):
    known = list(FINAL_THEMES.get(dim, {})) + HIGH_LEVEL.get(dim, [])
    return split_labels(", ".join(value) if isinstance(value, list) else value, known)


def validate_thematic(art, aid, rep):
    th = art["thematic"]
    for dim in DIMENSIONS:
        d = th.get(dim)
        if d is None:
            if dim in CORE_DIMENSIONS:
                rep.err(aid, f"thematic.{dim}", "dimension missing")
            continue
        pre = f"thematic.{dim}"
        if dim == "architecture":
            acodes = theme_labels(dim, d.get("codes"))
            if not acodes:
                rep.err(aid, f"{pre}.codes", "empty")
            for c in acodes:
                if len(c.split()) > MAX_CODE_WORDS + 4:
                    rep.err(aid, f"{pre}.codes", f"'{c[:60]}' is too long; name the architectural element")
            continue
        excerpts = as_list(d.get("extraction")) if isinstance(d.get("extraction"), list) else \
            [norm_space(x) for x in str(d.get("extraction") or "").split("\n") if norm_space(x)]
        if not excerpts:
            rep.err(aid, f"{pre}.extraction", f"empty; use '{NOT_ADDRESSED}' when the article gives no evidence")
        elif len(excerpts) > MAX_EXCERPTS:
            rep.err(aid, f"{pre}.extraction", f"{len(excerpts)} excerpts; keep the {MAX_EXCERPTS} most informative")
        codes = theme_labels(dim, d.get("codes"))
        if not codes:
            rep.err(aid, f"{pre}.codes", "empty")
        for c in codes:
            if len(c.split()) > MAX_CODE_WORDS:
                rep.err(aid, f"{pre}.codes", f"'{c[:60]}' has {len(c.split())} words; a descriptive code is a noun "
                        f"phrase of one to five words (at most {MAX_CODE_WORDS})")
        no_sub = dim == "sub_domain"
        themes, finals, new = [], [], 0
        for stage, out in (("theme", themes), ("final_theme", finals)):
            for lab in theme_labels(dim, d.get(stage)):
                if lab.lower() in ("0", "none", "-"):
                    rep.err(aid, f"{pre}.{stage}", f"'{lab}' is not a label; leave the list empty instead")
                    continue
                is_new = lab.startswith("[NEW]")
                f = find_final(dim, lab)
                if f:
                    out.append(f)
                elif is_new:
                    clean = lab.replace("[NEW]", "").strip()
                    out.append("[NEW] " + clean)
                    if dim == "technology" and NOT_TRACKING_TECH.search(clean):
                        rep.err(aid, f"{pre}.{stage}", f"'{clean}' is tooling, not a tracking technology (rule TEC-1)")
                else:
                    hl = match_vocab(lab, HIGH_LEVEL.get(dim, []))
                    dom = (match_vocab(lab, HIGH_LEVEL["domain"]) or find_final("domain", lab)) if no_sub else None
                    if hl:
                        hint = f"'{lab}' is a high-level theme; use its final theme(s): {'; '.join(finals_of_high_level(dim, hl))}"
                    elif dom:
                        hint = f"'{lab}' is a domain, not a sub-domain (rule SUB-1); use one of: {'; '.join(SUB_DOMAINS)}"
                    else:
                        opts = SUB_DOMAINS if no_sub else list(FINAL_THEMES[dim])
                        hint = f"'{lab}' is not in the codebook; use one of: {'; '.join(opts)} (or '[NEW] {lab}')"
                    rep.err(aid, f"{pre}.{stage}", hint)
        themes = list(OrderedDict.fromkeys(themes))
        finals = list(OrderedDict.fromkeys(finals))
        new = sum(1 for f in themes + finals if f.startswith("[NEW]"))
        if len({f for f in themes + finals if f.startswith("[NEW]")}) > MAX_NEW:
            rep.err(aid, pre, f"more than {MAX_NEW} [NEW] theme; reuse the codebook or record the doubt in self_verification")
        if not themes and not no_sub:
            rep.err(aid, f"{pre}.theme", "empty; themes are codebook final themes (or one [NEW] theme)")
        if not finals and not no_sub:
            rep.err(aid, f"{pre}.final_theme", "empty")
        extra = [f for f in finals if f not in themes]
        if extra:
            rep.err(aid, f"{pre}.final_theme", f"{'; '.join(extra)} not in theme: final themes consolidate the themes "
                    "of the study, so each one must also be listed in theme")
        # support: every final theme is licensed by codes and excerpts, guarded ones cite their rule
        sup = d.get("support") or {}
        sup = {(find_final(dim, k) or ("[NEW] " + k.replace("[NEW]", "").strip())): v for k, v in sup.items()} \
            if isinstance(sup, dict) else {}
        code_keys = {uk_us(c) for c in codes}
        for f in finals:
            s = sup.get(f)
            where = f"{pre}.support['{f}']"
            if not isinstance(s, dict):
                rep.err(aid, where, "missing: give the codes and the excerpt numbers (1 = first excerpt) that support it")
                continue
            sc = as_list(s.get("codes"))
            if not sc or any(uk_us(c) not in code_keys for c in sc):
                rep.err(aid, f"{where}.codes", "list one or more codes of this dimension, copied from codes")
            ex = s.get("excerpts") or []
            ex = ex if isinstance(ex, list) else [ex]
            if not ex or any(not str(i).isdigit() or not 1 <= int(i) <= len(excerpts) for i in ex) \
                    or excerpts == [NOT_ADDRESSED]:
                rep.err(aid, f"{where}.excerpts", f"give excerpt numbers between 1 and {len(excerpts)}")
            rules = GUARDED.get(dim, {}).get(f)
            if rules and not any(r in str(s.get("rule") or "") for r in rules):
                rep.err(aid, f"{where}.rule", f"'{f}' needs the decision rule {' or '.join(rules)} of the codebook: "
                        "write the rule identifier and why it applies")
        # high-level themes: derived from the final themes
        if no_sub:
            hl_out = [f for f in finals if not f.startswith("[NEW]")] + \
                     [f.replace("[NEW] ", "") for f in finals if f.startswith("[NEW]")]
            given = theme_labels(dim, d.get("high_level_theme"))
            if given and {uk_us(x.replace("[NEW]", "")) for x in given} != {uk_us(x) for x in hl_out}:
                rep.warn(aid, f"{pre}.high_level_theme", "replaced by the final themes (the sub-domain has one level)")
            d["high_level_theme"] = hl_out
        else:
            given = []
            for lab in theme_labels(dim, d.get("high_level_theme")):
                m = match_vocab(lab.replace("[NEW]", "").strip(), HIGH_LEVEL[dim])
                if m:
                    given.append(m)
                elif lab.startswith("[NEW]"):
                    rep.err(aid, f"{pre}.high_level_theme", "a new high-level theme is decided by R1, not by the rater; "
                            "keep the closest high-level theme and record the doubt in self_verification")
                else:
                    rep.err(aid, f"{pre}.high_level_theme", f"'{lab}' is not a high-level theme of the article; use one "
                            f"of: {'; '.join(HIGH_LEVEL[dim])}")
            derived = []
            for f in finals:
                if f.startswith("[NEW]"):
                    pick = [g for g in given if g not in derived]
                    if not pick:
                        rep.err(aid, f"{pre}.high_level_theme", f"choose the high-level theme of '{f}'")
                    derived += pick[:1]
                    continue
                allowed = FINAL_THEMES[dim][f]
                if len(allowed) == 1:
                    derived.append(allowed[0])
                else:
                    pick = [g for g in given if g in allowed]
                    if not pick:
                        rep.err(aid, f"{pre}.high_level_theme", f"'{f}' can be {' or '.join(allowed)}: choose one "
                                "(rule DO-4 for the containers of personal, sensitive and generic data)")
                    derived += pick
            derived = list(OrderedDict.fromkeys(derived))
            extra = [g for g in given if g not in derived]
            if extra:
                rep.err(aid, f"{pre}.high_level_theme", f"{'; '.join(extra)} not licensed by the final themes "
                        f"({'; '.join(finals) or 'none'}); the high-level themes follow the codebook section 3")
            d["high_level_theme"] = derived
        n = len(d["high_level_theme"])
        if n > MAX_LABELS[dim]:
            rep.err(aid, pre, f"{n} labels; at most {MAX_LABELS[dim]} (keep the ones the article states as central, "
                    "codebook section 6)")
        d["theme"] = [x for x in themes]
        d["final_theme"] = [x for x in finals]


def validate(wb, role, doc, rep, skills):
    known_ids = wb.sheet(DE_SHEET)["index"]
    vocab_cache = {}
    for art in doc["articles"]:
        aid = art["article_id"]
        if aid not in known_ids:
            rep.err(aid, "article_id", f"not found in '{DE_SHEET}' (column A)")
            continue
        if "extraction" in skills and "data_extraction" in art:
            de = art["data_extraction"]
            for key in DE_FIELDS:
                check_text(rep, aid, f"data_extraction.{key}", de.get(key), required=key not in DE_OPTIONAL)
            obj = norm_space(de.get("objective"))
            if obj and not obj.startswith("To ") and obj not in MISSING_TOKENS and not obj.startswith("UNREADABLE"):
                rep.warn(aid, "data_extraction.objective", "should begin with an infinitive ('To propose ...')")
            arch = norm_space(de.get("architecture"))
            if arch:
                m = match_vocab(arch, ARCHITECTURES)
                if m:
                    de["architecture"] = m
                    check_architecture(rep, aid, m, de.get("architecture_decision"))
                elif arch not in MISSING_TOKENS:
                    rep.err(aid, "data_extraction.architecture",
                            f"'{arch}' is not one of: {'; '.join(ARCHITECTURES)}")
            resp = norm_space(de.get("responsibility"))
            if resp and not re.match(r"^(Yes|Partially|No|Not explicitly addressed)\b", resp):
                rep.warn(aid, "data_extraction.responsibility",
                         "should begin with 'Yes.', 'Partially.' or 'Not explicitly addressed.'")
        if "research_type" in skills and "research_type" in art:
            rt = art["research_type"]
            c, kinds = {}, ""
            for key in CRITERIA:
                item = rt.get(key)
                if isinstance(item, dict):
                    val, just = truth(item.get("value")), norm_space(item.get("justification"))
                else:
                    m = re.match(r"^\s*(true|false)\b[.;:,\s-]*(?:justification:)?\s*(.*)$", str(item or ""), re.I | re.S)
                    val, just = (truth(m.group(1)), norm_space(m.group(2))) if m else (None, "")
                if val is None:
                    rep.err(aid, f"research_type.{key}", "value must be true or false")
                    continue
                if not just:
                    rep.err(aid, f"research_type.{key}", "justification is required (cite the section or page)")
                c[key] = val
                rt[key] = {"value": val, "justification": just}
                if key == "C6" and val:
                    kinds = "opinion" if just.lower().startswith("opinion") else (
                        "experience" if just.lower().startswith("experience") else "")
            method = norm_space(rt.get("research_method"))
            evalt = norm_space(rt.get("evaluation_type"))
            mm = match_vocab(method, RESEARCH_TYPES) if method else None
            if method.lower().rstrip("s") == "experience paper":
                mm = "Experience paper"
            if not mm:
                rep.err(aid, "research_type.research_method", f"'{method}' is not one of: {'; '.join(RESEARCH_TYPES)}")
            else:
                rt["research_method"] = mm
            em = NO_EVALUATION if evalt in (NO_EVALUATION, "", "None", "NOT APPLICABLE") else match_vocab(evalt, EVALUATION_METHODS)
            if not em:
                rep.err(aid, "research_type.evaluation_type",
                        f"'{evalt}' is not one of: {'; '.join(EVALUATION_METHODS)}; or '{NO_EVALUATION}'")
            else:
                rt["evaluation_type"] = em
            if len(c) == len(CRITERIA):
                exp, rule = expected_research_type(c, kinds)
                if exp is None:
                    rep.err(aid, "research_type.C1-C6", rule)
                elif mm and exp != mm:
                    rep.err(aid, "research_type.research_method",
                            f"'{mm}' contradicts the decision table: C1-C6 give '{exp}' (rule {rule}).")
                if mm and em:
                    if mm in ("Evaluation research", "Validation research"):
                        if em == NO_EVALUATION:
                            rep.err(aid, "research_type.evaluation_type", f"'{mm}' requires an evaluation method")
                        elif EVALUATION_METHODS[em] != mm:
                            rep.err(aid, "research_type.evaluation_type",
                                    f"'{em}' is a {EVALUATION_METHODS[em].lower()} method, but the research type is '{mm}'")
                    elif em != NO_EVALUATION:
                        rep.err(aid, "research_type.evaluation_type", f"'{mm}' has no empirical evaluation: use '{NO_EVALUATION}'")
        if "thematic" in skills and "thematic" in art:
            validate_thematic(art, aid, rep)


def cell_values_for(wb, role, art, skills):
    """Map each answer to (sheet, header, value). Missing columns keep col None."""
    out = []
    tg = {t["key"]: t for t in targets_for(wb, role, skills)}
    if "extraction" in skills and "data_extraction" in art:
        for key, v in art["data_extraction"].items():
            if key in DE_FIELDS and norm_space(v):
                out.append((tg[key], str(v).strip()))
    if "research_type" in skills and "research_type" in art:
        rt = art["research_type"]
        for key in CRITERIA:
            item = rt.get(key)
            if not isinstance(item, dict) or item.get("value") is None:
                continue
            word = "True" if item["value"] else "False"
            if f"{key}.value" in tg:
                out.append((tg[f"{key}.value"], word))
                out.append((tg[f"{key}.justification"], item["justification"]))
            else:
                out.append((tg[key], f"{word}. Justification: {item['justification']}"))
        for key in RT_FIELDS:
            if norm_space(rt.get(key)):
                out.append((tg[key], norm_space(rt[key])))
    if "thematic" in skills and "thematic" in art:
        th = art["thematic"]
        for dim in DIMENSIONS:
            d = th.get(dim) or {}
            for st, v in d.items():
                k = f"{dim}.{st}"
                if k not in tg:
                    continue
                if st == "extraction":
                    val = "\n".join(q.strip() for q in as_list(v))
                else:
                    labels = v if isinstance(v, list) else split_labels(v, HIGH_LEVEL.get(dim, []))
                    val = ", ".join(norm_space(x).replace("[NEW]", "").strip() for x in labels if norm_space(x))
                if val:
                    out.append((tg[k], val))
    return out


def cmd_validate(a):
    wb = Workbook(a.defta)
    doc = read_answers(a.input)
    role = resolve_role(wb, a.role or doc["role"] or sys.exit("No role given (--role) and none in the file."))
    skills = parse_skills(a.skill)
    rep = Report()
    validate(wb, role, doc, rep, skills)
    if a.pdf:
        check_quotes(doc, a.pdf, rep)
    missing = OrderedDict()
    for art in doc["articles"]:
        for t, v in cell_values_for(wb, role, art, skills):
            if t["col"] is None:
                missing.setdefault(f"{t['sheet']}: {t['header']}", set()).add(art["article_id"])
    for h, ids in missing.items():
        rep.warn(f"{len(ids)} article(s)", h, "column does not exist for this role; "
                 "skipped unless write is run with --add-columns")
    print_report(rep, role, doc)
    if rep.errors:
        sys.exit(1)


def print_report(rep, role, doc):
    print(f"Role: {role}; articles: {len(doc['articles'])}")
    for e in rep.errors:
        print(f"ERROR   {e}")
    for w in rep.warnings:
        print(f"WARNING {w}")
    for n in rep.notes:
        print(f"NOTE    {n}")
    print(f"{len(rep.errors)} error(s), {len(rep.warnings)} warning(s).")
    if not rep.errors:
        print("Valid.")


# ---------------------------------------------------------------------------
# Writing at XML level
# ---------------------------------------------------------------------------

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_ILLEGAL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff￾￿]")


def col_letter(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def col_number(letters):
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n


def esc(v):
    v = _ILLEGAL.sub("", str(v))
    if len(v) > 32000:
        v = v[:32000] + " [truncated]"
    return html.escape(v, quote=False)


def cell_xml(ref, value, style=None):
    s = f' s="{style}"' if style else ""
    if value is None or value == "":
        return f'<c r="{ref}"{s}/>'
    if isinstance(value, dict) and "f" in value:
        return f'<c r="{ref}"{s}><f>{esc(value["f"])}</f></c>'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{ref}"{s}><v>{value}</v></c>'
    return f'<c r="{ref}"{s} t="inlineStr"><is><t xml:space="preserve">{esc(value)}</t></is></c>'


class Package:
    def __init__(self, path):
        with zipfile.ZipFile(path) as z:
            self.order = [i.filename for i in z.infolist()]
            self.files = {n: z.read(n) for n in self.order}

    def text(self, name):
        return self.files[name].decode("utf-8")

    def put(self, name, txt):
        if name not in self.files:
            self.order.append(name)
        self.files[name] = txt.encode("utf-8")

    def save(self, path):
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            for n in self.order:
                z.writestr(n, self.files[n])

    def sheets(self):
        wb = self.text("xl/workbook.xml")
        rels = self.text("xl/_rels/workbook.xml.rels")
        targets = {}
        for m in re.finditer(r"<Relationship\b[^>]*>", rels):
            tag = m.group(0)
            i, t = re.search(r'Id="([^"]+)"', tag), re.search(r'Target="([^"]+)"', tag)
            if i and t:
                targets[i.group(1)] = t.group(1)
        out = []
        for m in re.finditer(r"<sheet\b[^>]*/>", wb):
            tag = m.group(0)
            name = html.unescape(re.search(r'name="([^"]*)"', tag).group(1))
            rid = re.search(r'r:id="([^"]+)"', tag).group(1)
            t = targets[rid].lstrip("/")
            out.append((name, t if t.startswith("xl/") else "xl/" + t))
        return out

    def sheet_path(self, name):
        for n, p in self.sheets():
            if n == name:
                return p
        sys.exit(f"Sheet '{name}' not found in the workbook.")

    def sheet_tables(self, sheet_path):
        rel = sheet_path.replace("worksheets/", "worksheets/_rels/") + ".rels"
        if rel not in self.files:
            return []
        return ["xl/tables/" + m.group(1) for m in re.finditer(r'Target="(?:\.\./|/xl/)tables/(table\d+\.xml)"', self.text(rel))]


ROW_RE = re.compile(r'<row\b[^>]*\br="(\d+)"[^>]*?(?:/>|>(.*?)</row>)', re.S)
CELL_RE = re.compile(r'<c\b[^>]*\br="([A-Z]+)(\d+)"[^>]*?(?:/>|>.*?</c>)', re.S)


def cell_style(cell):
    m = re.search(r'\bs="(\d+)"', cell[:cell.find(">") + 1])
    return m.group(1) if m else None


class SheetEditor:
    """Edits cells of one worksheet XML: set values, append rows, add columns."""

    def __init__(self, pkg, sheet_name):
        self.pkg, self.name = pkg, sheet_name
        self.path = pkg.sheet_path(sheet_name)
        self.xml = pkg.text(self.path)
        self.rows = OrderedDict()  # row number -> OrderedDict(col letter -> cell xml)
        self.row_attrs = {}
        m = re.search(r"<sheetData\s*/>|<sheetData>(.*?)</sheetData>", self.xml, re.S)
        self.data_span = m.span()
        for rm in ROW_RE.finditer(m.group(1) or ""):
            r = int(rm.group(1))
            open_tag = re.match(r"<row\b[^>]*?(?=/?>)", rm.group(0)).group(0)
            self.row_attrs[r] = open_tag
            cells = OrderedDict()
            for cm in CELL_RE.finditer(rm.group(2) or ""):
                cells[cm.group(1)] = cm.group(0)
            self.rows[r] = cells

    def get_cell(self, row, col):
        return self.rows.get(row, {}).get(col)

    def has_formula(self, row, col):
        c = self.get_cell(row, col)
        return bool(c and "<f" in c)

    def set(self, row, col, value, style=None):
        cells = self.rows.setdefault(row, OrderedDict())
        if row not in self.row_attrs:
            self.row_attrs[row] = f'<row r="{row}"'
        old = cells.get(col)
        st = cell_style(old) if old else style
        cells[col] = cell_xml(f"{col}{row}", value, st)
        self.rows[row] = OrderedDict(sorted(cells.items(), key=lambda kv: col_number(kv[0])))

    def save(self):
        parts = []
        for r in sorted(self.rows):
            tag = re.sub(r'\sspans="[^"]*"', "", self.row_attrs[r])
            cells = "".join(self.rows[r].values())
            parts.append(f"{tag}>{cells}</row>" if cells else f"{tag}/>")
        data = "<sheetData>" + "".join(parts) + "</sheetData>"
        xml = self.xml[:self.data_span[0]] + data + self.xml[self.data_span[1]:]
        max_row = max(self.rows) if self.rows else 1
        max_col = max((col_number(c) for cells in self.rows.values() for c in cells), default=1)
        xml = re.sub(r'<dimension ref="[^"]*"/>', f'<dimension ref="A1:{col_letter(max_col)}{max_row}"/>', xml, count=1)
        self.pkg.put(self.path, xml)


def main_table(pkg, sheet_path):
    """The table that starts at A1 of the sheet (the data table of the DEF_TA sheets)."""
    for t in pkg.sheet_tables(sheet_path):
        m = re.search(r'<table\b[^>]*\bref="A1:([A-Z]+)(\d+)"', pkg.text(t))
        if m:
            return t, m.group(1), int(m.group(2))
    return None, None, None


def set_table_ref(pkg, table_path, sheet_name, old_col, old_row, new_col, new_row):
    t = pkg.text(table_path)
    old, new = f"A1:{old_col}{old_row}", f"A1:{new_col}{new_row}"
    t = t.replace(f'ref="{old}"', f'ref="{new}"')
    t = re.sub(r"<sortState\b.*?</sortState>|<sortState\b[^>]*/>", "", t, flags=re.S)
    pkg.put(table_path, t)
    wb = pkg.text("xl/workbook.xml")
    q = "'" + sheet_name.replace("'", "''") + "'" if re.search(r"[^A-Za-z0-9_.]", sheet_name) else sheet_name
    qx = html.escape(q, quote=False).replace("'", "&apos;")
    for qq in {q, qx}:
        wb = wb.replace(f"{qq}!$A$1:${old_col}${old_row}<", f"{qq}!$A$1:${new_col}${new_row}<")
    pkg.put("xl/workbook.xml", wb)


def add_table_column(pkg, table_path, header):
    t = pkg.text(table_path)
    ids = [int(x) for x in re.findall(r'<tableColumn\b[^>]*\bid="(\d+)"', t)]
    nid = max(ids or [0]) + 1
    count = len(ids) + 1
    t = re.sub(r'<tableColumns count="\d+">', f'<tableColumns count="{count}">', t, count=1)
    t = t.replace("</tableColumns>", f'<tableColumn id="{nid}" name="{html.escape(header)}"/></tableColumns>', 1)
    pkg.put(table_path, t)


def translate_formula(formula, origin, dest):
    try:
        from openpyxl.formula.translate import Translator
        return Translator(formula, origin=origin).translate_formula(dest)
    except Exception:
        return formula


def ensure_row(wb, pkg, editors, sheet_name, article_id, appended):
    """Return the row of article_id in sheet_name, appending a row (with the formulas of the
    last row translated) when the study is not yet in the sheet."""
    info = wb.sheet(sheet_name)
    row = info["index"].get(article_id) or appended.get((sheet_name, article_id))
    if row:
        return row
    ed = editors.setdefault(sheet_name, SheetEditor(pkg, sheet_name))
    table_path, last_col, last_row = main_table(pkg, ed.path)
    template_row = wb.last_data_row(sheet_name)
    new_row = max([template_row] + [r for (s, _), r in appended.items() if s == sheet_name]) + 1
    tpl = info["rows"][template_row - 1]
    styles = {c: cell_style(x) for c, x in ed.rows.get(template_row, {}).items()}
    ncols = col_number(last_col) if last_col else len(tpl)
    for k in range(1, ncols + 1):
        col = col_letter(k)
        v = tpl[k - 1] if k - 1 < len(tpl) else None
        if k == 1:
            ed.set(new_row, col, article_id, styles.get(col))
        elif is_formula(v):
            f = translate_formula(formula_text(v), f"{col}{template_row}", f"{col}{new_row}")
            ed.set(new_row, col, {"f": f.lstrip("=")}, styles.get(col))
        else:
            ed.set(new_row, col, "", styles.get(col))
    if table_path:
        cur = re.search(r'<table\b[^>]*\bref="A1:([A-Z]+)(\d+)"', pkg.text(table_path))
        set_table_ref(pkg, table_path, sheet_name, cur.group(1), int(cur.group(2)), cur.group(1), new_row)
    appended[(sheet_name, article_id)] = new_row
    return new_row


def add_column(wb, pkg, editors, sheet_name, header, added):
    """Append a column with this header at the right edge of the sheet's main table."""
    key = (sheet_name, norm_header(header))
    if key in added:
        return added[key][0]
    ed = editors.setdefault(sheet_name, SheetEditor(pkg, sheet_name))
    table_path, last_col, last_row = main_table(pkg, ed.path)
    if not table_path:
        sys.exit(f"Cannot add a column to '{sheet_name}': no table starting at A1.")
    new_k = col_number(last_col) + 1
    new_col = col_letter(new_k)
    hdr_style = cell_style(ed.get_cell(1, last_col) or "")
    ed.set(1, new_col, header, hdr_style)
    add_table_column(pkg, table_path, header)
    set_table_ref(pkg, table_path, sheet_name, last_col, last_row, new_col, last_row)
    t = pkg.text(table_path)
    t = re.sub(r'(<autoFilter ref=")A1:[A-Z]+(\d+)"', lambda m: f'{m.group(1)}A1:{new_col}{m.group(2)}"', t, count=1)
    pkg.put(table_path, t)
    added[key] = (new_k - 1, header)
    return new_k - 1


def tool_digest():
    import hashlib
    h = hashlib.sha256()
    here = os.path.dirname(os.path.abspath(__file__))
    for p in [os.path.abspath(__file__)] + sorted(
            os.path.join(here, "..", "references", f) for f in (os.listdir(os.path.join(here, "..", "references"))
                                                                 if os.path.isdir(os.path.join(here, "..", "references")) else [])):
        with open(p, "rb") as f:
            h.update(f.read())
    return h.hexdigest()[:12]


def cmd_write(a):
    wb = Workbook(a.defta)
    doc = read_answers(a.input)
    role = resolve_role(wb, a.role or doc["role"] or sys.exit("No role given (--role) and none in the file."))
    skills = parse_skills(a.skill)
    if os.path.abspath(a.out) == os.path.abspath(a.defta):
        sys.exit("The output must be a new file; the original DEF_TA is never modified.")
    rep = Report()
    validate(wb, role, doc, rep, skills)
    model = doc.get("model") or norm_space(a.model)
    if not model:
        rep.err("answers", "model", "record the AI model that produced the answers ('model' in the answers file "
                "or --model), so that the runs of the raters can be compared")
    quote_info = "not checked (--no-quote-check)"
    if a.no_quote_check:
        rep.warn("answers", "excerpts", "verbatim excerpts NOT checked against the PDFs (--no-quote-check)")
    elif not a.pdf:
        rep.err("answers", "excerpts", "pass the PDFs (or the pdftext .txt files) with --pdf: write checks every "
                "excerpt before writing")
    else:
        total, bad = check_quotes(doc, a.pdf, rep)
        quote_info = f"{total} checked, {bad} not found"
    if rep.errors:
        print_report(rep, role, doc)
        sys.exit("Nothing written: correct the errors and run again.")
    pkg = Package(a.defta)
    editors, appended, added = {}, {}, {}
    written, skipped, kept = Counter(), [], []
    for art in doc["articles"]:
        aid = art["article_id"]
        values = cell_values_for(wb, role, art, skills)
        if any(t["sheet"] != DE_SHEET for t, _ in values) and wb.sheet(TA_SHEET):
            ensure_row(wb, pkg, editors, TA_SHEET, aid, appended)
        for t, v in values:
            col = t["col"]
            if col is None:
                if not a.add_columns:
                    skipped.append(f"{aid} | {t['header']}")
                    continue
                col = add_column(wb, pkg, editors, t["sheet"], t["header"], added)
            row = ensure_row(wb, pkg, editors, t["sheet"], aid, appended)
            ed = editors.setdefault(t["sheet"], SheetEditor(pkg, t["sheet"]))
            letter = col_letter(col + 1)
            if ed.has_formula(row, letter):
                skipped.append(f"{aid} | {t['header']} (formula cell, left unchanged)")
                continue
            existing = wb.cell(t["sheet"], row, col) if (t["sheet"], aid) not in appended and row <= len(wb.sheet(t["sheet"])["rows"]) else None
            if filled(existing) and norm_space(existing) != norm_space(v) and not a.overwrite:
                kept.append(f"{aid} | {t['header']}")
                continue
            ed.set(row, letter, v)
            written[t["sheet"]] += 1
    if not written:
        print_report(rep, role, doc)
        print("Nothing to write." + (f" {len(kept)} cell(s) already filled (use --overwrite)." if kept else ""))
        for k in kept[:20]:
            print(f"  kept: {k}")
        sys.exit(1)
    for ed in editors.values():
        ed.save()
    wbx = pkg.text("xl/workbook.xml")
    if "<calcPr" in wbx and "fullCalcOnLoad" not in wbx:
        pkg.put("xl/workbook.xml", wbx.replace("<calcPr", '<calcPr fullCalcOnLoad="1"', 1))
    pkg.save(a.out)
    lines = [f"# Data extraction write report", "", f"- Base workbook: {os.path.basename(a.defta)}",
             f"- Output workbook: {os.path.basename(a.out)}", f"- Role: {role}", f"- Date: {today()}",
             f"- Tool: slm_extract {VERSION} (rules {RULES_VERSION}, sha256 {tool_digest()})",
             f"- Model: {model}", f"- Verbatim excerpts: {quote_info}", f"- Studies: {', '.join(x['article_id'] for x in doc['articles'])}", "",
             "| Sheet | Cells written |", "|---|---:|"]
    lines += [f"| {s} | {n} |" for s, n in written.items()]
    if appended:
        lines += ["", "## Rows appended (study not yet in the sheet)", ""]
        lines += [f"- {s}: {aid} (row {r})" for (s, aid), r in appended.items()]
    if added:
        lines += ["", "## Columns added", ""] + [f"- {s}: {h}" for (s, _), (_, h) in added.items()]
    if kept:
        lines += ["", "## Cells already filled and kept (run with --overwrite to replace)", ""] + [f"- {k}" for k in kept]
    if skipped:
        lines += ["", "## Answers not written", ""] + [f"- {k}" for k in skipped]
    if rep.warnings or rep.notes:
        lines += ["", "## Warnings and notes for Researcher 1", ""] + [f"- {w}" for w in rep.warnings + rep.notes]
    sv = [(x["article_id"], norm_space((x.get("thematic") or {}).get("self_verification"))) for x in doc["articles"]]
    if any(v for _, v in sv) and "thematic" in skills:
        lines += ["", "## Self-verification of the thematic analysis", ""] + [f"- {k}: {v}" for k, v in sv if v]
    lines += ["", "Formula-driven sheets (Thematic Analysis, RQ summaries, Kappa_Fleiss, RQ5, TRL) are recalculated "
              "when the workbook is opened in Excel. The Kappa_Fleiss ranges cover the original rows only; use the "
              "kappa command for the updated coefficients."]
    rpath = a.report or os.path.splitext(a.out)[0] + "_report.md"
    with open(rpath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Workbook written: {a.out}")
    print(f"Report written: {rpath}")
    print("Cells written: " + ", ".join(f"{s} {n}" for s, n in written.items()))
    if appended:
        print(f"Rows appended: {len(appended)}")
    if added:
        print(f"Columns added: {len(added)}")
    if kept:
        print(f"{len(kept)} cell(s) already filled were kept (use --overwrite to replace them).")
    if skipped:
        print(f"{len(skipped)} answer(s) not written (no column for this role or formula cell); see the report.")


# ---------------------------------------------------------------------------
# Fleiss' kappa (step 4 of the thematic analysis)
# ---------------------------------------------------------------------------


def cmd_kappa(a):
    wb = Workbook(a.defta)
    roles = list(discover_roles(wb))
    raters = [resolve_role(wb, r) for r in a.raters.split(",")] if a.raters else roles
    if len(raters) < 2:
        sys.exit("At least two raters are needed.")
    rules, apply_eq = {}, True
    eq = wb.sheet("Equivalences")
    if eq:
        try:
            apply_eq = str(wb.wbv["Equivalences"]["K1"].value or "Yes").strip().lower() != "no"
        except Exception:
            pass
        for r in eq["values"][4:]:
            if r and len(r) > 4 and r[3] is not None and str(r[0]).strip().lower() == "yes":
                rules[(str(r[1]), str(r[2]), norm_label(r[3]))] = norm_label(r[4])

    def label(dim, stage, value):
        if value is None or not str(value).strip() or str(value).strip() in ("0", "None"):
            return None
        out = set()
        for x in filter(None, (norm_label(x) for x in re.split(r"[\n,;]", str(value).replace("\r", "\n")))):
            if apply_eq:
                for key in ((dim, stage, x), (dim, "ALL", x), ("ALL", stage, x), ("ALL", "ALL", x)):
                    if key in rules:
                        x = rules[key]
                        break
            out.add(x)
        return ", ".join(sorted(out))

    ids = set(a.ids.split(",")) if a.ids else None
    targets = []
    for dim, (sheet, eqdim) in DIMENSIONS.items():
        for st, (prefix, eqst) in STAGES.items():
            if eqst:
                targets.append((eqdim, prefix, sheet, [f"{prefix} ({r})" for r in raters], eqst))
    targets.append(("Architecture", "Architecture Type", DE_SHEET, [f"Architecture Type ({r})" for r in raters], "Theme"))
    targets.append(("ResearchType", "Research Method", DE_SHEET, [f"Research Method ({r})" for r in raters], "Theme"))
    targets.append(("Evaluation", "Evaluation Type", DE_SHEET, [f"Evaluation Type ({r})" for r in raters], "Theme"))
    print(f"Raters: {', '.join(raters)}" + (f"; studies: {len(ids)}" if ids else ""))
    print("dimension\tstage\tN\tPo\tPe\tkappa\tinterpretation\talpha_MASI")
    per_label = []
    for dim, stage, sheet, headers, eqst in targets:
        info = wb.sheet(sheet)
        if not info:
            continue
        cols = [wb.column(sheet, h) for h in headers]
        if None in cols:
            continue
        labs = []
        for aid, row in info["index"].items():
            if ids and aid not in ids:
                continue
            ls = [label(dim, eqst, wb.cell(sheet, row, c, values=True)) for c in cols]
            if all(ls):
                labs.append(ls)
        n, m = len(labs), len(raters)
        if not n:
            continue
        pairs = m * (m - 1) / 2
        p_o = sum(sum(1 for i in range(m) for j in range(i + 1, m) if l[i] == l[j]) / pairs for l in labs) / n
        p_e = sum((v / (m * n)) ** 2 for v in Counter(x for l in labs for x in l).values())
        k = 1.0 if p_e == 1 else (p_o - p_e) / (1 - p_e)
        sets = [[frozenset(x.split(", ")) for x in l] for l in labs]
        alpha = masi_alpha(sets)
        print(f"{dim}\t{stage}\t{n}\t{p_o:.3f}\t{p_e:.3f}\t{k:.3f}\t{landis_koch(k)}\t{alpha:.3f}")
        if a.per_label and eqst in ("FinalTheme", "HighLevelTheme"):
            for lab in sorted(set().union(*[x for l in sets for x in l])):
                per_label.append((dim, stage, lab, [sum(lab in l[i] for l in sets) for i in range(m)],
                                  fleiss([[lab in x for x in l] for l in sets])))
    if per_label:
        print("\nPer-label Fleiss' kappa (label present or absent in each study)")
        print("dimension\tstage\tlabel\tstudies per rater\tkappa")
        for dim, stage, lab, cnt, k in per_label:
            print(f"{dim}\t{stage}\t{lab}\t{'/'.join(map(str, cnt))}\t{k:.3f}")


def fleiss(rows):
    """Fleiss' kappa for rows of categorical ratings (one list per study, one value per rater)."""
    n, m = len(rows), len(rows[0])
    pairs = m * (m - 1) / 2
    p_o = sum(sum(1 for i in range(m) for j in range(i + 1, m) if r[i] == r[j]) / pairs for r in rows) / n
    p_e = sum((v / (m * n)) ** 2 for v in Counter(x for r in rows for x in r).values())
    return 1.0 if p_e == 1 else (p_o - p_e) / (1 - p_e)


def masi(a, b):
    """MASI distance between two label sets (Passonneau, 2006)."""
    if a == b:
        return 0.0
    inter = len(a & b)
    if not inter:
        return 1.0
    mono = 2 / 3 if (a <= b or b <= a) else 1 / 3
    return 1 - inter / len(a | b) * mono


def masi_alpha(units):
    """Krippendorff's alpha with MASI distance, for complete data (every rater codes every unit)."""
    m = len(units[0])
    if m < 2 or len(units) < 2:
        return 1.0
    d_o = sum(sum(masi(u[i], u[j]) for i in range(m) for j in range(m) if i != j) / (m - 1) for u in units)
    d_o /= len(units) * m
    pool = Counter(v for u in units for v in u)
    vals, tot = list(pool), sum(pool.values())
    d_e = sum(pool[x] * pool[y] * masi(x, y) for x in vals for y in vals) / (tot * (tot - 1))
    return 1.0 if d_e == 0 else 1 - d_o / d_e


def landis_koch(k):
    if k < 0:
        return "Poor"
    for lim, name in ((0.2, "Slight"), (0.4, "Fair"), (0.6, "Moderate"), (0.8, "Substantial")):
        if k <= lim:
            return name
    return "Almost perfect"


# ---------------------------------------------------------------------------


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=VERSION)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("roles", help="list the rater roles in the workbook")
    s.add_argument("--def", dest="defta", required=True)
    s.add_argument("--verbose", action="store_true")
    s.set_defaults(func=cmd_roles)

    s = sub.add_parser("match", help="match PDF files to rows of Data Extraction")
    s.add_argument("--def", dest="defta", required=True)
    s.add_argument("pdfs", nargs="+")
    s.set_defaults(func=cmd_match)

    s = sub.add_parser("status", help="show the empty fields of a role")
    s.add_argument("--def", dest="defta", required=True)
    s.add_argument("--role", required=True)
    s.add_argument("--skill", default="all")
    s.add_argument("--ids", help="comma-separated Article IDs")
    s.add_argument("--only-pending", action="store_true")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("template", help="write a JSON template to fill in")
    s.add_argument("--def", dest="defta", required=True)
    s.add_argument("--role", required=True)
    s.add_argument("--skill", default="all")
    s.add_argument("--ids", required=True, help="comma-separated Article IDs or PDF file names")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_template)

    s = sub.add_parser("pdftext", help="extract the text of a PDF with page markers")
    s.add_argument("pdf")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_pdftext)

    s = sub.add_parser("quotes", help="check that quoted excerpts occur in the PDF")
    s.add_argument("--input", nargs="+", required=True)
    s.add_argument("--pdf", nargs="+", required=True)
    s.add_argument("--verbose", action="store_true")
    s.set_defaults(func=cmd_quotes)

    for name, func in (("validate", cmd_validate), ("write", cmd_write)):
        s = sub.add_parser(name)
        s.add_argument("--def", dest="defta", required=True)
        s.add_argument("--input", nargs="+", required=True)
        s.add_argument("--role")
        s.add_argument("--skill", default="all")
        if name == "validate":
            s.add_argument("--pdf", nargs="+", help="also check the excerpts against these PDFs or pdftext .txt files")
        if name == "write":
            s.add_argument("--out", required=True)
            s.add_argument("--report")
            s.add_argument("--overwrite", action="store_true", help="replace cells that are already filled")
            s.add_argument("--add-columns", action="store_true", help="append missing role columns to the tables")
            s.add_argument("--pdf", nargs="+", help="PDFs or pdftext .txt files: every excerpt is checked before writing")
            s.add_argument("--no-quote-check", action="store_true", help="skip the excerpt check (recorded in the report)")
            s.add_argument("--model", help="AI model that produced the answers (if not in the answers file)")
        s.set_defaults(func=func)

    s = sub.add_parser("kappa", help="Fleiss' kappa among raters")
    s.add_argument("--def", dest="defta", required=True)
    s.add_argument("--raters", help="comma-separated roles (default: all roles found)")
    s.add_argument("--ids", help="restrict to these Article IDs")
    s.add_argument("--per-label", action="store_true", help="also print the kappa of each final and high-level theme")
    s.set_defaults(func=cmd_kappa)

    s = sub.add_parser("vocab", help="print the controlled vocabularies")
    s.add_argument("--def", dest="defta")
    s.set_defaults(func=cmd_vocab)

    a = p.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
