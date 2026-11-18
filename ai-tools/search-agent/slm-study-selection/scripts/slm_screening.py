#!/usr/bin/env python3
"""Deterministic support tool for the study-selection step of the systematic
literature mapping "Accountability Through Digital Object Tracing in
Information Security".

The tool does everything that must be reproducible (BibTeX parsing,
deduplication, rule-based exclusions, validation of decisions, writing the
DEF_TA.xlsx workbook). The judgement on title/abstract (0/1/2, criterion and
reason) is made by the AI agent and handed back through `apply`.

Only the Python standard library is required, plus openpyxl to *read* the
workbook. The workbook is *written* at XML level, so charts, tables, the data
model (Power Pivot) and the existing formulas are preserved.

Subcommands
  prepare   parse the .bib, deduplicate, apply rule-based exclusions, create the work state
  codes     print the criteria and the closed set of reason codes
  included  print the titles already included in the mapping (calibration)
  next      print the next batch of records that still need a decision
  apply     merge a decisions file (CSV or JSON) into the state, with validation
  status    print the counts of the iteration
  export    write the current state to CSV (e.g. for the researcher to review the 1s)
  commit    when every record is 0 or 2, write a new DEF_TA.xlsx
"""
import argparse
import csv
import datetime as dt
import html
import io
import json
import os
import re
import sys
import unicodedata
import zipfile
from urllib.parse import unquote

# ---------------------------------------------------------------------------
# Criteria and closed set of exclusion reasons (keep in sync with
# references/criteria.md)
# ---------------------------------------------------------------------------

DECISIONS = {0: "Excluded", 1: "Requires review", 2: "Included"}

CRITERIA = {
    "EC1": "Not published in a peer-reviewed venue",
    "EC2": "Duplicate record or same study already screened",
    "EC3": "Secondary study, non-primary research or grey literature",
    "EC4": "Access control without a tracking mechanism (no traceability or auditability)",
    "EC5": "Copyright protection only, without addressing the distribution of protected content",
    "EC6": "Out of scope: does not address traceability or accountability of digital objects in information security",
    "EC7": "Formal eligibility not met (language, document type or subject area)",
}

# Order in which the criteria are checked; the first one that applies is recorded.
CRITERIA_ORDER = ["EC7", "EC1", "EC2", "EC3", "EC4", "EC5", "EC6"]

REASONS = {
    "EC1-PREPRINT": ("EC1", "Preprint or non-refereed repository version (e.g. arXiv)"),
    "EC1-THESIS": ("EC1", "Thesis or dissertation"),
    "EC1-TECH-REPORT": ("EC1", "Technical report, white paper, standard or patent"),
    "EC1-OTHER": ("EC1", "Other non-peer-reviewed publication"),
    "EC2-DUP-BIB": ("EC2", "Duplicate record within the BibTeX file"),
    "EC2-PREVIOUS": ("EC2", "Record already screened in a previous iteration"),
    "EC2-SAME-STUDY": ("EC2", "Another version of a study already screened (extended, earlier or translated version)"),
    "EC3-SLR-RELATED": ("EC3", "Systematic review or mapping related to this study (tracing / accountability of digital objects)"),
    "EC3-REVIEW-RELATED": ("EC3", "Non-systematic survey or overview related to this study"),
    "EC3-SECONDARY-OTHER": ("EC3", "Secondary study on another topic"),
    "EC3-NON-PRIMARY": ("EC3", "Non-primary item (editorial, preface, keynote, front matter, erratum, abstract only)"),
    "EC3-GREY": ("EC3", "Grey literature (magazine, news, blog or other non-academic outlet)"),
    "EC4-AC-NO-TRACKING": ("EC4", "Access control or authorisation without tracking, traceability or auditability"),
    "EC5-COPYRIGHT-ONLY": ("EC5", "Copyright or ownership protection only (e.g. watermark robustness) without distribution tracing"),
    "EC6-NOT-INFOSEC": ("EC6", "Not in an information-security context"),
    "EC6-VISUAL-TRACKING": ("EC6", "Visual object or target tracking (computer vision, video surveillance)"),
    "EC6-NO-OBJECT-TRACING": ("EC6", "Security study without tracing, auditing or attribution of digital objects (e.g. intrusion or malware detection, authentication, cryptographic primitive)"),
    "EC6-OTHER": ("EC6", "Other out-of-scope topic (justification required)"),
    "EC7-LANGUAGE": ("EC7", "Not written in English"),
    "EC7-DOCUMENT-TYPE": ("EC7", "Document type other than journal article or conference paper"),
    "EC7-SUBJECT-AREA": ("EC7", "Outside Computer Science and Engineering"),
}

# Reasons set only by the deterministic steps, never by the AI.
RULE_ONLY_REASONS = {"EC2-DUP-BIB", "EC2-PREVIOUS"}

STAGES = {"RULE": "Deterministic rule", "TA": "Title, abstract and keywords", "FT": "Full text"}

ACCEPTED_DOCTYPES = {"article", "conference paper", "review"}  # "review" goes to the AI (EC3 related or not)

DATASET_HEADER = ["Article ID", "Rayyan ID", "DataBase ID", "Article Title", "Year", "Journal",
                  "Vol.", "Issue", "Authors", "Scopus URL", "Language", "Publisher", "doi"]

SCREENING_EXTRA = ["Document Type", "Abstract", "Author Keywords", "Index Keywords", "Bib Key",
                   "Screening Decision", "Decision Label", "Exclusion Criterion", "Exclusion Reason Code",
                   "Exclusion Reason", "Justification", "Confidence", "Screening Stage", "Decided By",
                   "Decision Date", "Data Extraction ID"]

STATE_FILE = "state.json"

# ---------------------------------------------------------------------------
# BibTeX parsing (no external dependency)
# ---------------------------------------------------------------------------


def _read_value(s, i):
    """Read a BibTeX field value starting at s[i]; return (value, new_index)."""
    parts = []
    n = len(s)
    while i < n:
        while i < n and s[i] in " \t\r\n":
            i += 1
        if i >= n:
            break
        c = s[i]
        if c == "{":
            depth, j = 1, i + 1
            while j < n and depth:
                if s[j] == "\\":
                    j += 2
                    continue
                if s[j] == "{":
                    depth += 1
                elif s[j] == "}":
                    depth -= 1
                j += 1
            parts.append(s[i + 1:j - 1])
            i = j
        elif c == '"':
            depth, j = 0, i + 1
            while j < n:
                if s[j] == "\\":
                    j += 2
                    continue
                if s[j] == "{":
                    depth += 1
                elif s[j] == "}":
                    depth -= 1
                elif s[j] == '"' and depth == 0:
                    break
                j += 1
            parts.append(s[i + 1:j])
            i = j + 1
        else:
            m = re.match(r"[^\s,#}]+", s[i:])
            parts.append(m.group(0) if m else "")
            i += len(m.group(0)) if m else 1
        while i < n and s[i] in " \t\r\n":
            i += 1
        if i < n and s[i] == "#":
            i += 1
            continue
        break
    return "".join(parts), i


def parse_bibtex(text):
    entries = []
    i, n = 0, len(text)
    while True:
        at = text.find("@", i)
        if at < 0:
            break
        m = re.match(r"@\s*([A-Za-z]+)\s*([{(])", text[at:])
        if not m:
            i = at + 1
            continue
        etype = m.group(1).lower()
        i = at + m.end()
        if etype in ("comment", "preamble", "string"):
            depth = 1
            while i < n and depth:
                depth += {"{": 1, "}": -1}.get(text[i], 0)
                i += 1
            continue
        km = re.match(r"\s*([^,\s]*)\s*,", text[i:])
        key = km.group(1) if km else ""
        i += km.end() if km else 0
        fields = {}
        while i < n:
            while i < n and text[i] in " \t\r\n,":
                i += 1
            if i >= n or text[i] in "})":
                i += 1
                break
            fm = re.match(r"([A-Za-z0-9_\-:.]+)\s*=\s*", text[i:])
            if not fm:
                nxt = text.find(",", i)
                i = n if nxt < 0 else nxt + 1
                continue
            name = fm.group(1).lower()
            i += fm.end()
            value, i = _read_value(text, i)
            fields[name] = clean_latex(value)
        entries.append({"entry_type": etype, "key": key, "fields": fields})
    return entries


def clean_latex(v):
    v = re.sub(r"\\[`'^\"~=.uvHtcdbk]\s*\{?([A-Za-z])\}?", r"\1", v)
    v = v.replace("\\&", "&").replace("\\%", "%").replace("\\_", "_").replace("\\$", "$")
    v = v.replace("{", "").replace("}", "")
    v = re.sub(r"\s+", " ", v)
    return v.strip()


# ---------------------------------------------------------------------------
# Normalisation used for deduplication
# ---------------------------------------------------------------------------


def norm_doi(v):
    if not v:
        return ""
    v = unquote(str(v)).strip().lower()
    v = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", v)
    v = v.split()[0] if v.split() else ""
    return v.rstrip(".,;")


def doi_from_url(url):
    m = re.search(r"[?&]doi=([^&]+)", url or "")
    return norm_doi(m.group(1)) if m else ""


def eid_from_url(url):
    m = re.search(r"eid=(2-s2\.0-\d+)", url or "")
    return m.group(1) if m else ""


def norm_title(v):
    v = unicodedata.normalize("NFKD", str(v or ""))
    v = "".join(c for c in v if not unicodedata.combining(c)).lower()
    v = re.sub(r"<[^>]+>", " ", v)
    v = re.sub(r"[^a-z0-9]+", " ", v)
    return re.sub(r"\s+", " ", v).strip()


def norm_year(v):
    m = re.search(r"\d{4}", str(v or ""))
    return m.group(0) if m else ""


# ---------------------------------------------------------------------------
# Reading the DEF_TA workbook
# ---------------------------------------------------------------------------


def read_previous(def_path):
    """Return the records already screened (sheet 'Data Set') and the included studies."""
    try:
        import openpyxl
    except ImportError:
        sys.exit("openpyxl is required to read the workbook: pip install openpyxl")
    wb = openpyxl.load_workbook(def_path, read_only=True, data_only=True)
    if "Data Set" not in wb.sheetnames:
        sys.exit("The workbook has no 'Data Set' sheet.")
    rows = wb["Data Set"].iter_rows(values_only=True)
    header = [str(h).strip() if h is not None else "" for h in next(rows)]
    col = {h: k for k, h in enumerate(header)}
    prev = []
    for r in rows:
        if not r or r[col["Article ID"]] in (None, ""):
            continue
        get = lambda h: r[col[h]] if h in col and col[h] < len(r) else None
        url = str(get("Scopus URL") or "")
        prev.append({
            "id": str(get("Article ID")).strip(),
            "database": "" if get("DataBase ID") is None else str(get("DataBase ID")),
            "title": str(get("Article Title") or ""),
            "year": norm_year(get("Year")),
            "doi": norm_doi(get("doi")) or doi_from_url(url),
            "eid": eid_from_url(url) or (str(get("Article ID")) if str(get("Article ID")).startswith("2-s2.0-") else ""),
        })
    included = []
    if "Data Extraction" in wb.sheetnames:
        rows = wb["Data Extraction"].iter_rows(values_only=True)
        header = [str(h).strip() if h is not None else "" for h in next(rows)]
        col = {h: k for k, h in enumerate(header)}
        for r in rows:
            if r and r[0]:
                included.append({"id": r[0], "paper": r[col.get("Papper", 3)],
                                 "title": r[col.get("Titlle", 5)], "year": r[col.get("Year", 6)]})
    return prev, included, wb.sheetnames


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------


def load_state(workdir):
    p = os.path.join(workdir, STATE_FILE)
    if not os.path.exists(p):
        sys.exit(f"{p} not found: run 'prepare' first.")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_state(workdir, state):
    p = os.path.join(workdir, STATE_FILE)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def now():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def set_decision(rec, decision, reason_code="", justification="", confidence="", stage="TA", decided_by="AI"):
    criterion = REASONS[reason_code][0] if reason_code else ""
    rec["history"].append({k: rec.get(k) for k in ("decision", "reason_code", "stage", "decided_by", "decided_at")})
    rec.update(decision=decision, criterion=criterion, reason_code=reason_code,
               justification=justification, confidence=confidence, stage=stage,
               decided_by=decided_by, decided_at=now())


# ---------------------------------------------------------------------------
# prepare
# ---------------------------------------------------------------------------


def next_iteration_name(sheetnames):
    nums = [int(m.group(1)) for s in sheetnames for m in [re.fullmatch(r"Update\.(\d+)", s)] if m]
    return f"Update.{max(nums) + 1 if nums else 1}"


def rule_exclusion(rec, entry_type):
    """Deterministic exclusions; return a reason code or ''."""
    lang = rec["language"].strip().lower()
    if lang and not lang.startswith("english"):
        return "EC7-LANGUAGE"
    if entry_type in ("phdthesis", "mastersthesis", "thesis"):
        return "EC1-THESIS"
    if entry_type in ("techreport", "patent", "standard"):
        return "EC1-TECH-REPORT"
    if rec["doi"].lower().startswith("10.48550/arxiv") or re.search(r"\barxiv\b", rec["journal"].lower()):
        return "EC1-PREPRINT"
    dtype = rec["document_type"].strip().lower()
    if dtype and dtype not in ACCEPTED_DOCTYPES:
        return "EC7-DOCUMENT-TYPE"
    if not dtype and entry_type in ("book", "inbook", "incollection", "booklet", "manual", "unpublished"):
        return "EC7-DOCUMENT-TYPE"
    return ""


def cmd_prepare(a):
    os.makedirs(a.workdir, exist_ok=True)
    if os.path.exists(os.path.join(a.workdir, STATE_FILE)) and not a.force:
        sys.exit("A state already exists in this workdir; use --force to overwrite it.")
    prev, included, sheetnames = read_previous(a.defta)
    iteration = a.iteration or next_iteration_name(sheetnames)
    if iteration in sheetnames:
        sys.exit(f"The workbook already has a sheet named '{iteration}'.")
    if len(iteration) > 31 or re.search(r"[\[\]:*?/\\]", iteration):
        sys.exit("Invalid sheet name for the iteration.")
    with open(a.bib, encoding="utf-8-sig", errors="replace") as f:
        entries = parse_bibtex(f.read())

    by_doi, by_eid, by_title = {}, {}, {}
    for p in prev:
        if p["doi"]:
            by_doi.setdefault(p["doi"], p)
        if p["eid"]:
            by_eid.setdefault(p["eid"], p)
        if norm_title(p["title"]):
            by_title.setdefault(norm_title(p["title"]), []).append(p)

    seen_doi, seen_eid, seen_ty = {}, {}, {}
    records, dedup = [], []
    seq = 0
    for e in entries:
        f = e["fields"]
        url = f.get("url", "")
        doi_shown = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", str(f.get("doi") or ""), flags=re.I).strip()
        doi = norm_doi(f.get("doi")) or doi_from_url(url)
        doi_shown = doi_shown or doi
        eid = (f.get("eid") if str(f.get("eid", "")).startswith("2-s2.0-") else "") or eid_from_url(url)
        title = f.get("title", "")
        year = norm_year(f.get("year"))
        tkey = norm_title(title)
        base = {"bib_key": e["key"], "title": title, "year": year, "doi": doi, "eid": eid}

        # 1) duplicate within the .bib
        hit = (doi and seen_doi.get(doi)) or (eid and seen_eid.get(eid)) or (tkey and seen_ty.get((tkey, year)))
        if hit:
            how = "DOI" if doi and seen_doi.get(doi) else "EID" if eid and seen_eid.get(eid) else "TITLE+YEAR"
            dedup.append({**base, "reason_code": "EC2-DUP-BIB", "match": how, "matched_with": hit})
            continue
        # 2) already screened in a previous iteration
        p = (doi and by_doi.get(doi)) or (eid and by_eid.get(eid))
        how = "DOI" if doi and by_doi.get(doi) else "EID"
        if not p and tkey:
            p = next((x for x in by_title.get(tkey, []) if x["year"] == year or not x["year"] or not year), None)
            how = "TITLE+YEAR"
        if p:
            dedup.append({**base, "reason_code": "EC2-PREVIOUS", "match": how,
                          "matched_with": f"{p['id']} ({p['database']})"})
            continue

        seq += 1
        rid = eid or f"{iteration}-{seq:04d}"
        rec = {
            "record_id": rid, "bib_key": e["key"], "entry_type": e["entry_type"],
            "title": title, "year": year,
            "journal": f.get("journal") or f.get("booktitle") or f.get("source_title") or "",
            "volume": f.get("volume", ""), "issue": f.get("number") or f.get("issue", ""),
            "authors": f.get("author", ""), "url": url,
            "language": f.get("language") or f.get("language_of_original_document") or "",
            "publisher": f.get("publisher", ""), "doi": doi_shown,
            "document_type": f.get("type") or f.get("document_type") or "",
            "abstract": f.get("abstract", ""),
            "author_keywords": f.get("author_keywords", ""),
            "index_keywords": f.get("keywords", ""),
            "hints": [],
            "decision": None, "criterion": "", "reason_code": "", "justification": "",
            "confidence": "", "stage": "", "decided_by": "", "decided_at": "", "history": [],
        }
        if not rec["abstract"].strip():
            rec["hints"].append("no abstract in the .bib")
        if rec["document_type"].strip().lower() == "review":
            rec["hints"].append("Scopus document type: Review")
        same_title = [x for x in by_title.get(tkey, []) if x["year"] != year]
        if same_title:
            x = same_title[0]
            rec["hints"].append(f"same title as {x['id']} ({x['database']}, {x['year']}): possible other version")
        reason = rule_exclusion(rec, e["entry_type"])
        if reason:
            set_decision(rec, 0, reason, f"Rule: {REASONS[reason][1]}", "high", "RULE", "rule")
        records.append(rec)
        if doi:
            seen_doi[doi] = rid
        if eid:
            seen_eid[eid] = rid
        if tkey:
            seen_ty[(tkey, year)] = rid

    state = {"iteration": iteration, "bib_file": os.path.basename(a.bib),
             "defta_file": os.path.basename(a.defta), "created_at": now(),
             "entries_in_bib": len(entries), "previously_screened": len(prev),
             "included_so_far": len(included), "records": records, "deduplicated": dedup}
    save_state(a.workdir, state)
    with open(os.path.join(a.workdir, "dedup_report.csv"), "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, ["bib_key", "title", "year", "doi", "eid", "reason_code", "match", "matched_with"])
        w.writeheader()
        w.writerows(dedup)
    print_status(state)


# ---------------------------------------------------------------------------
# codes / included / next / status / export
# ---------------------------------------------------------------------------


def cmd_codes(a):
    print("Decisions: 0 = Excluded, 1 = Requires review, 2 = Included")
    print("Check the criteria in this order; record the first that applies: " + " > ".join(CRITERIA_ORDER))
    for c in CRITERIA_ORDER:
        print(f"\n{c}  {CRITERIA[c]}")
        for code, (crit, label) in REASONS.items():
            if crit == c:
                tag = "  (set by the tool only)" if code in RULE_ONLY_REASONS else ""
                print(f"   {code:22s} {label}{tag}")


def cmd_included(a):
    _, included, _ = read_previous(a.defta)
    for s in included:
        print(f"{s['paper']}\t{s['year']}\t{s['title']}")
    print(f"\n{len(included)} included studies.")


def pending(state, stage):
    if stage == "FT":
        return [r for r in state["records"] if r["decision"] == 1]
    return [r for r in state["records"] if r["decision"] is None]


def cmd_next(a):
    state = load_state(a.workdir)
    todo = pending(state, a.stage)
    batch = todo[: a.size]
    out = [{"record_id": r["record_id"], "title": r["title"], "year": r["year"], "venue": r["journal"],
            "document_type": r["document_type"], "keywords": "; ".join(x for x in (r["author_keywords"], r["index_keywords"]) if x)[:600],
            "abstract": r["abstract"][: a.max_abstract], "hints": r["hints"],
            **({"previous_decision": r["decision"], "previous_justification": r["justification"]} if a.stage == "FT" else {})}
           for r in batch]
    print(json.dumps({"stage": a.stage, "remaining_including_this_batch": len(todo), "batch": out},
                     ensure_ascii=False, indent=1))


def counts(state):
    recs = state["records"]
    c = {"pending": sum(r["decision"] is None for r in recs)}
    for d in DECISIONS:
        c[d] = sum(r["decision"] == d for r in recs)
    by_reason = {}
    for r in recs:
        if r["decision"] == 0:
            by_reason[r["reason_code"]] = by_reason.get(r["reason_code"], 0) + 1
    return c, by_reason


def print_status(state):
    c, by_reason = counts(state)
    dd = {}
    for d in state["deduplicated"]:
        dd[d["reason_code"]] = dd.get(d["reason_code"], 0) + 1
    print(f"Iteration: {state['iteration']}  (bib: {state['bib_file']})")
    print(f"Entries in the .bib: {state['entries_in_bib']}")
    print(f"Removed before screening: {len(state['deduplicated'])}  {dd}")
    print(f"Records to screen: {len(state['records'])}")
    print(f"  without decision: {c['pending']}")
    print(f"  0 excluded: {c[0]}  {dict(sorted(by_reason.items()))}")
    print(f"  1 requires review: {c[1]}")
    print(f"  2 included: {c[2]}")
    ready = c["pending"] == 0 and c[1] == 0
    print("Ready to commit: " + ("YES" if ready else "NO"))


def cmd_status(a):
    print_status(load_state(a.workdir))


def cmd_export(a):
    state = load_state(a.workdir)
    recs = state["records"]
    if a.only is not None:
        recs = [r for r in recs if (r["decision"] if r["decision"] is not None else -1) == a.only]
    cols = ["record_id", "decision", "reason_code", "justification", "confidence", "stage", "decided_by",
            "title", "year", "journal", "doi", "url", "document_type", "hints", "abstract"]
    with open(a.out, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in recs:
            w.writerow(["; ".join(r[c]) if c == "hints" else ("" if r[c] is None else r[c]) for c in cols])
    print(f"{len(recs)} records written to {a.out}")


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------


def read_decisions(path):
    if path.lower().endswith(".json") or path.lower().endswith(".jsonl"):
        with open(path, encoding="utf-8-sig") as f:
            txt = f.read().strip()
        if txt.startswith("["):
            return json.loads(txt)
        if txt.startswith("{"):
            try:
                obj = json.loads(txt)
                return obj.get("decisions", [obj])
            except json.JSONDecodeError:
                pass
        return [json.loads(line) for line in txt.splitlines() if line.strip()]
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def cmd_apply(a):
    state = load_state(a.workdir)
    idx = {r["record_id"]: r for r in state["records"]}
    errors, ok = [], 0
    rows = read_decisions(a.decisions)
    for n, d in enumerate(rows, 1):
        rid = str(d.get("record_id", "")).strip()
        rec = idx.get(rid)
        where = f"line {n} ({rid or 'no record_id'})"
        if not rec:
            errors.append(f"{where}: unknown record_id")
            continue
        try:
            dec = int(str(d.get("decision", "")).strip())
        except ValueError:
            errors.append(f"{where}: decision must be 0, 1 or 2")
            continue
        if dec not in DECISIONS:
            errors.append(f"{where}: decision must be 0, 1 or 2")
            continue
        reason = str(d.get("reason_code") or "").strip().upper()
        just = str(d.get("justification") or "").strip()
        conf = str(d.get("confidence") or "").strip().lower()
        stage = str(d.get("stage") or a.stage).strip().upper()
        by = str(d.get("decided_by") or a.decided_by).strip()
        if dec == 0:
            if reason not in REASONS:
                errors.append(f"{where}: exclusion requires a valid reason_code (see 'codes'); got '{reason}'")
                continue
            if reason in RULE_ONLY_REASONS:
                errors.append(f"{where}: {reason} is set by the tool only")
                continue
            crit = str(d.get("criterion") or "").strip().upper()
            if crit and crit != REASONS[reason][0]:
                errors.append(f"{where}: reason {reason} belongs to {REASONS[reason][0]}, not {crit}")
                continue
            if reason == "EC6-OTHER" and len(just) < 15:
                errors.append(f"{where}: EC6-OTHER requires a justification")
                continue
        elif reason:
            errors.append(f"{where}: reason_code must be empty when decision is {dec}")
            continue
        if not just:
            errors.append(f"{where}: justification is required")
            continue
        if conf and conf not in ("high", "medium", "low"):
            errors.append(f"{where}: confidence must be high, medium or low")
            continue
        if stage not in ("TA", "FT"):
            errors.append(f"{where}: stage must be TA or FT")
            continue
        if rec["stage"] == "RULE" and not a.override_rules:
            errors.append(f"{where}: record was excluded by a deterministic rule; use --override-rules to change it")
            continue
        set_decision(rec, dec, reason, just, conf, stage, by)
        ok += 1
    if errors and not a.partial:
        print("No decision applied. Fix the errors below (or use --partial):", file=sys.stderr)
        for e in errors:
            print("  - " + e, file=sys.stderr)
        sys.exit(1)
    save_state(a.workdir, state)
    print(f"{ok} decisions applied; {len(errors)} rejected.")
    for e in errors:
        print("  - " + e)
    print_status(state)


# ---------------------------------------------------------------------------
# XLSX writing at XML level
# ---------------------------------------------------------------------------

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_SHEET = NS_R + "/worksheet"
REL_TABLE = NS_R + "/table"
CT_SHEET = "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"
CT_TABLE = "application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml"
_ILLEGAL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")


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
    s = f' s="{style}"' if style is not None else ""
    if value is None or value == "":
        return f'<c r="{ref}"{s}/>' if style is not None else ""
    if isinstance(value, dict) and "f" in value:
        return f'<c r="{ref}"{s} t="str"><f>{esc(value["f"])}</f></c>'
    if isinstance(value, bool):
        return f'<c r="{ref}"{s} t="b"><v>{int(value)}</v></c>'
    if isinstance(value, (int, float)):
        return f'<c r="{ref}"{s}><v>{value}</v></c>'
    return f'<c r="{ref}"{s} t="inlineStr"><is><t xml:space="preserve">{esc(value)}</t></is></c>'


def as_number(v):
    return int(v) if re.fullmatch(r"\d{1,9}", str(v or "")) else (v or "")


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

    # -- lookups ------------------------------------------------------------
    def sheets(self):
        wb = self.text("xl/workbook.xml")
        rels = self.text("xl/_rels/workbook.xml.rels")
        targets = {m.group(1): m.group(2) for m in re.finditer(r'<Relationship [^>]*?Id="([^"]+)"[^>]*?Target="([^"]+)"', rels)}
        targets.update({m.group(2): m.group(1) for m in re.finditer(r'<Relationship [^>]*?Target="([^"]+)"[^>]*?Id="([^"]+)"', rels)})
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
        out = []
        for m in re.finditer(r'Target="\.\./tables/(table\d+\.xml)"', self.text(rel)):
            out.append("xl/tables/" + m.group(1))
        return out


def last_row_info(sheet_xml):
    rows = list(re.finditer(r'<row r="(\d+)"[^>]*>(.*?)</row>', sheet_xml, re.S))
    if not rows:
        return 1, {}
    last = rows[-1]
    styles = {}
    for c in re.finditer(r'<c r="([A-Z]+)\d+"(?: s="(\d+)")?', last.group(2)):
        if c.group(2):
            styles[c.group(1)] = c.group(2)
    return int(last.group(1)), styles


def append_rows(pkg, sheet_name, rows_values):
    """Append rows to a sheet whose data is a single Excel table starting at A1.
    rows_values: list of {column_letter: value}. Returns (first_row, last_row)."""
    path = pkg.sheet_path(sheet_name)
    xml = pkg.text(path)
    last, styles = last_row_info(xml)
    tables = pkg.sheet_tables(path)
    table_path, tref = None, None
    for t in tables:
        m = re.search(r'<table\b[^>]*\bref="A1:([A-Z]+)(\d+)"', pkg.text(t))
        if m:
            table_path, tref = t, m
    last_col = tref.group(1) if tref else max(styles, key=col_number, default="A")
    ncols = col_number(last_col)
    out = []
    r = last
    for vals in rows_values:
        r += 1
        cells = "".join(cell_xml(f"{col_letter(k)}{r}", vals.get(col_letter(k)), styles.get(col_letter(k)))
                        for k in range(1, ncols + 1))
        out.append(f'<row r="{r}" spans="1:{ncols}">{cells}</row>')
    if not out:
        return None
    xml = xml.replace("</sheetData>", "".join(out) + "</sheetData>", 1) if "</sheetData>" in xml \
        else xml.replace("<sheetData/>", "<sheetData>" + "".join(out) + "</sheetData>", 1)
    xml = re.sub(r'<dimension ref="[^"]*"/>', f'<dimension ref="A1:{last_col}{r}"/>', xml, count=1)
    pkg.put(path, xml)
    if table_path:
        t = pkg.text(table_path)
        old = f"A1:{last_col}{tref.group(2)}"
        new = f"A1:{last_col}{r}"
        t = t.replace(f'ref="{old}"', f'ref="{new}"')
        t = re.sub(r'<sortState\b.*?</sortState>|<sortState\b[^>]*/>', "", t, flags=re.S)
        pkg.put(table_path, t)
        wb = pkg.text("xl/workbook.xml")
        q = "'" + sheet_name.replace("'", "''") + "'" if re.search(r"[^A-Za-z0-9_.]", sheet_name) else sheet_name
        qx = html.escape(q, quote=False).replace("'", "&apos;")
        for qq in {q, qx}:
            wb = wb.replace(f"{qq}!$A$1:${last_col}${tref.group(2)}<", f"{qq}!$A$1:${last_col}${r}<")
        pkg.put("xl/workbook.xml", wb)
    return last + 1, r


def add_sheet(pkg, name, header, rows):
    """Add a new worksheet with a formatted Excel table."""
    sheet_files = [n for n in pkg.files if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)]
    sn = max(int(re.search(r"(\d+)", n.split("/")[-1]).group(1)) for n in sheet_files) + 1
    table_files = [n for n in pkg.files if re.fullmatch(r"xl/tables/table\d+\.xml", n)]
    tn = max([int(re.search(r"(\d+)", n.split("/")[-1]).group(1)) for n in table_files] or [0]) + 1
    table_ids = [int(m.group(1)) for n in table_files for m in [re.search(r'<table\b[^>]*\bid="(\d+)"', pkg.text(n))] if m]
    tid = max(table_ids or [0]) + 1
    sheet_path = f"xl/worksheets/sheet{sn}.xml"
    ncols, nrows = len(header), len(rows) + 1
    last_col = col_letter(ncols)
    widths = {"Article Title": 60, "Abstract": 80, "Justification": 60, "Authors": 30, "Exclusion Reason": 45,
              "Journal": 35, "Scopus URL": 30, "Author Keywords": 35, "Index Keywords": 35}
    cols = "".join(f'<col min="{k}" max="{k}" width="{widths.get(h, 16)}" customWidth="1"/>' for k, h in enumerate(header, 1))
    body = ['<row r="1">' + "".join(cell_xml(f"{col_letter(k)}1", h) for k, h in enumerate(header, 1)) + "</row>"]
    for i, row in enumerate(rows, 2):
        body.append(f'<row r="{i}">' + "".join(cell_xml(f"{col_letter(k)}{i}", v) for k, v in enumerate(row, 1)) + "</row>")
    sheet = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
             f'<worksheet xmlns="{NS_MAIN}" xmlns:r="{NS_R}"><dimension ref="A1:{last_col}{nrows}"/>'
             f'<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
             f'<sheetFormatPr defaultRowHeight="12.5"/><cols>{cols}</cols><sheetData>{"".join(body)}</sheetData>'
             f'<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>'
             f'<tableParts count="1"><tablePart r:id="rId1"/></tableParts></worksheet>')
    pkg.put(sheet_path, sheet)
    tname = "Screening_" + re.sub(r"[^A-Za-z0-9_]", "_", name)
    tcols = "".join(f'<tableColumn id="{k}" name="{html.escape(h)}"/>' for k, h in enumerate(header, 1))
    table = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
             f'<table xmlns="{NS_MAIN}" id="{tid}" name="{tname}" displayName="{tname}" ref="A1:{last_col}{nrows}" totalsRowShown="0">'
             f'<autoFilter ref="A1:{last_col}{nrows}"/><tableColumns count="{ncols}">{tcols}</tableColumns>'
             f'<tableStyleInfo name="TableStyleMedium2" showFirstColumn="0" showLastColumn="0" showRowStripes="1" showColumnStripes="0"/></table>')
    pkg.put(f"xl/tables/table{tn}.xml", table)
    pkg.put(f"xl/worksheets/_rels/sheet{sn}.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{REL_TABLE}" Target="../tables/table{tn}.xml"/></Relationships>')
    ct = pkg.text("[Content_Types].xml")
    ct = ct.replace("</Types>", f'<Override PartName="/{sheet_path}" ContentType="{CT_SHEET}"/>'
                                f'<Override PartName="/xl/tables/table{tn}.xml" ContentType="{CT_TABLE}"/></Types>')
    pkg.put("[Content_Types].xml", ct)
    rels = pkg.text("xl/_rels/workbook.xml.rels")
    rids = [int(x) for x in re.findall(r'Id="rId(\d+)"', rels)]
    rid = f"rId{max(rids) + 1}"
    rels = rels.replace("</Relationships>", f'<Relationship Id="{rid}" Type="{REL_SHEET}" Target="worksheets/sheet{sn}.xml"/></Relationships>')
    pkg.put("xl/_rels/workbook.xml.rels", rels)
    wb = pkg.text("xl/workbook.xml")
    sid = max(int(x) for x in re.findall(r'<sheet\b[^>]*\bsheetId="(\d+)"', wb)) + 1
    wb = wb.replace("</sheets>", f'<sheet name="{html.escape(name)}" sheetId="{sid}" r:id="{rid}"/></sheets>', 1)
    if "<calcPr" in wb and "fullCalcOnLoad" not in wb:
        wb = wb.replace("<calcPr", '<calcPr fullCalcOnLoad="1"', 1)
    pkg.put("xl/workbook.xml", wb)
    if "docProps/app.xml" in pkg.files:
        app = pkg.text("docProps/app.xml")
        m = re.search(r'<TitlesOfParts><vt:vector size="(\d+)" baseType="lpstr">(.*?)</vt:vector>', app, re.S)
        h = re.search(r"(<HeadingPairs><vt:vector[^>]*><vt:variant><vt:lpstr>[^<]*</vt:lpstr></vt:variant><vt:variant><vt:i4>)(\d+)(</vt:i4>)", app)
        if m and h:
            nsheets = int(h.group(2))
            items = re.findall(r"<vt:lpstr>.*?</vt:lpstr>", m.group(2), re.S)
            items.insert(nsheets, f"<vt:lpstr>{html.escape(name)}</vt:lpstr>")
            app = app[:m.start()] + f'<TitlesOfParts><vt:vector size="{len(items)}" baseType="lpstr">{"".join(items)}</vt:vector>' + app[m.end():]
            app = app.replace(h.group(0), f"{h.group(1)}{nsheets + 1}{h.group(3)}", 1)
            pkg.put("docProps/app.xml", app)


# ---------------------------------------------------------------------------
# commit
# ---------------------------------------------------------------------------


def cmd_commit(a):
    state = load_state(a.workdir)
    recs = state["records"]
    bad = [r["record_id"] for r in recs if r["decision"] not in (0, 2)]
    if bad:
        sys.exit(f"Not ready: {len(bad)} records still without decision or with decision 1, e.g. {bad[:5]}")
    for r in recs:
        if r["decision"] == 0 and r["reason_code"] not in REASONS:
            sys.exit(f"Record {r['record_id']} is excluded without a valid reason code.")
    pkg = Package(a.defta)
    names = [n for n, _ in pkg.sheets()]
    iteration = state["iteration"]
    if iteration in names:
        sys.exit(f"The workbook already has a sheet named '{iteration}'.")
    for needed in ("Data Set", "Data Extraction"):
        if needed not in names:
            sys.exit(f"Sheet '{needed}' not found.")

    prev, included, _ = read_previous(a.defta)
    known = {p["id"] for p in prev}
    clash = [r["record_id"] for r in recs if r["record_id"] in known]
    if clash:
        sys.exit(f"Records already present in 'Data Set': {clash[:5]} (wrong DEF_TA file?)")
    pnums = [int(m.group(1)) for s in included for m in [re.fullmatch(r"P(\d+)", str(s["paper"] or ""))] if m]
    next_p = max(pnums or [0]) + 1
    width = max(3, len(str(next_p + len(recs))))

    for r in recs:
        r["extraction_id"] = ""
    for r in recs:
        if r["decision"] == 2:
            r["extraction_id"] = f"P{next_p:0{width}d}"
            next_p += 1

    # 1) the iteration sheet
    header = DATASET_HEADER + SCREENING_EXTRA
    rows = []
    for r in recs:
        rows.append([r["record_id"], "", iteration, r["title"], as_number(r["year"]), r["journal"],
                     as_number(r["volume"]), as_number(r["issue"]), r["authors"], r["url"], r["language"],
                     r["publisher"], r["doi"], r["document_type"], r["abstract"], r["author_keywords"],
                     r["index_keywords"], r["bib_key"], r["decision"], DECISIONS[r["decision"]], r["criterion"],
                     r["reason_code"], REASONS[r["reason_code"]][1] if r["reason_code"] else "",
                     r["justification"], r["confidence"], STAGES.get(r["stage"], r["stage"]), r["decided_by"],
                     r["decided_at"], r["extraction_id"]])
    add_sheet(pkg, iteration, header, rows)

    # 2) Data Set: every new record (so that the next iteration deduplicates against it)
    ds = [{"A": r["record_id"], "B": "", "C": iteration, "D": r["title"], "E": as_number(r["year"]),
           "F": r["journal"], "G": as_number(r["volume"]), "H": as_number(r["issue"]), "I": r["authors"],
           "J": r["url"], "K": r["language"], "L": r["publisher"], "M": r["doi"]} for r in recs]
    append_rows(pkg, "Data Set", ds)

    # 3) Data Extraction: references of the included studies, ready to be filled in
    de = []
    first = last_row_info(pkg.text(pkg.sheet_path("Data Extraction")))[0] + 1
    for k, r in enumerate([x for x in recs if x["decision"] == 2]):
        row = first + k
        de.append({"A": r["record_id"],
                   "B": {"f": f"VLOOKUP(A{row},'Data Set'!A:C,2,FALSE)&\"\""},
                   "C": {"f": f"VLOOKUP(A{row},'Data Set'!A:D,3,FALSE)"},
                   "D": r["extraction_id"], "E": r["doi"], "F": r["title"], "G": as_number(r["year"])})
    if de:
        append_rows(pkg, "Data Extraction", de)
    pkg.save(a.out)

    # 4) report
    c, by_reason = counts(state)
    dd = {}
    for d in state["deduplicated"]:
        dd[d["reason_code"]] = dd.get(d["reason_code"], 0) + 1
    lines = [f"# Study selection report: {iteration}", "",
             f"- BibTeX file: {state['bib_file']}", f"- Base workbook: {os.path.basename(a.defta)}",
             f"- Output workbook: {os.path.basename(a.out)}", f"- Date: {now()}", "",
             "| Step | Records |", "|---|---:|",
             f"| Entries in the .bib | {state['entries_in_bib']} |",
             f"| Duplicates within the .bib (EC2-DUP-BIB) | {dd.get('EC2-DUP-BIB', 0)} |",
             f"| Already screened in previous iterations (EC2-PREVIOUS) | {dd.get('EC2-PREVIOUS', 0)} |",
             f"| Screened in this iteration | {len(recs)} |",
             f"| Excluded (0) | {c[0]} |", f"| Included (2) | {c[2]} |", "",
             "## Exclusions by reason", "", "| Criterion | Reason code | Reason | Records |", "|---|---|---|---:|"]
    for code in REASONS:
        if by_reason.get(code):
            lines.append(f"| {REASONS[code][0]} | {code} | {REASONS[code][1]} | {by_reason[code]} |")
    related = [r for r in recs if r["reason_code"] in ("EC3-SLR-RELATED", "EC3-REVIEW-RELATED")]
    if related:
        lines += ["", "## Related secondary studies (for the related-work section)", ""]
        lines += [f"- {r['title']} ({r['year']}), {r['doi'] or r['record_id']} [{r['reason_code']}]" for r in related]
    lines += ["", "## Included studies added to Data Extraction", ""]
    lines += [f"- {r['extraction_id']}: {r['title']} ({r['year']}), {r['doi'] or r['record_id']}" for r in recs if r["decision"] == 2]
    report = os.path.join(a.workdir, f"report_{re.sub(r'[^A-Za-z0-9_.-]', '_', iteration)}.md")
    with open(report, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Workbook written: {a.out}")
    print(f"Report written: {report}")
    print(f"Sheet '{iteration}' added with {len(recs)} records; {len(ds)} rows appended to 'Data Set'; "
          f"{len(de)} rows appended to 'Data Extraction'.")


# ---------------------------------------------------------------------------


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("prepare")
    s.add_argument("--bib", required=True)
    s.add_argument("--def", dest="defta", required=True)
    s.add_argument("--workdir", required=True)
    s.add_argument("--iteration", help="name of the new sheet (default: Update.N)")
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_prepare)

    s = sub.add_parser("codes")
    s.set_defaults(fn=cmd_codes)

    s = sub.add_parser("included")
    s.add_argument("--def", dest="defta", required=True)
    s.set_defaults(fn=cmd_included)

    s = sub.add_parser("next")
    s.add_argument("--workdir", required=True)
    s.add_argument("--size", type=int, default=20)
    s.add_argument("--stage", choices=["TA", "FT"], default="TA")
    s.add_argument("--max-abstract", type=int, default=3000)
    s.set_defaults(fn=cmd_next)

    s = sub.add_parser("apply")
    s.add_argument("--workdir", required=True)
    s.add_argument("--decisions", required=True)
    s.add_argument("--stage", choices=["TA", "FT"], default="TA")
    s.add_argument("--decided-by", default="AI")
    s.add_argument("--partial", action="store_true", help="apply the valid lines even if some are rejected")
    s.add_argument("--override-rules", action="store_true")
    s.set_defaults(fn=cmd_apply)

    s = sub.add_parser("status")
    s.add_argument("--workdir", required=True)
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("export")
    s.add_argument("--workdir", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--only", type=int, choices=[0, 1, 2], help="only records with this decision")
    s.set_defaults(fn=cmd_export)

    s = sub.add_parser("commit")
    s.add_argument("--workdir", required=True)
    s.add_argument("--def", dest="defta", required=True)
    s.add_argument("--out", required=True)
    s.set_defaults(fn=cmd_commit)

    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
