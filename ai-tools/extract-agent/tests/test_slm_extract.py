"""Tests of slm_extract.py on a small synthetic DEF_TA workbook.

Run from the extract-agent folder:  python -m unittest discover -s tests -v
Requires openpyxl.
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import openpyxl  # noqa: E402
from openpyxl.worksheet.table import Table  # noqa: E402

import slm_extract as sx  # noqa: E402

R1, GPT = "Researcher 1", "AI Tool - OpenAI GPT"
IDS = ["2-s2.0-1", "2-s2.0-2", "2-s2.0-3"]


def build_workbook(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data Extraction"
    header = ["Article ID", "Ryyan ID", "Dataset", "Papper", "DOI", "Titlle", "Year"]
    for prefix in sx.DE_FIELDS.values():
        if prefix == "Objective Codes":
            header.append(f"{prefix} ({R1})")
            continue
        header += [f"{prefix} ({R1})", f"{prefix} ({GPT})"]
    for c in sx.CRITERIA:
        header += [f"{c} ({R1})", f"{c} - Value ({GPT})", f"{c} - Justification ({GPT})"]
    for prefix in sx.RT_FIELDS.values():
        header += [f"{prefix} ({R1})", f"{prefix} ({GPT})"]
    ws.append(header)
    for i, aid in enumerate(IDS, 2):
        row = [aid, f"=VLOOKUP(A{i},'Data Set'!A:C,2,FALSE)", f"=VLOOKUP(A{i},'Data Set'!A:D,3,FALSE)",
               f"P00{i - 1}", f"10.1/{i}", f"Title {i}", 2024] + [None] * (len(header) - 7)
        ws.append(row)
    # Researcher 1 has already filled study 1
    ws.cell(row=2, column=header.index(f"Research Method ({R1})") + 1, value="Validation research")
    ws.cell(row=2, column=header.index(f"Architecture Type ({R1})") + 1, value="Server-centered")
    ws.add_table(Table(displayName="Articles", ref=f"A1:{sx.col_letter(len(header))}{len(IDS) + 1}"))

    ds = wb.create_sheet("Data Set")
    ds.append(["Article ID", "Rayyan ID", "DataBase ID"])
    for i, aid in enumerate(IDS):
        ds.append([aid, f"rayyan-{i + 1}", "Seed 0"])

    dims = [("Digital Objects", "ArticlesDigitalObjects"), ("Technologies", "ArticlesTechnologies"),
            ("Purposes", "ArticlesPurposes"), ("Domains", "ArticlesDomains"), ("Sub-Domains", "ArticlesSubDomains")]
    for name, tname in dims:
        s = wb.create_sheet(name)
        h = ["Article ID", "Papper ID", "Rayyan ID"]
        for st in ["Data extraction", "Codes", "Theme", "Final Theme"]:
            h += [f"{st} ({R1})", f"{st} ({GPT})"]
        h += ["Theme (Final decision)", f"High-level Theme ({R1})", f"High-level Theme ({GPT})", "High-level theme"]
        s.append(h)
        for i, aid in enumerate(IDS[:2], 2):  # study 3 is not yet in the dimension sheets
            s.append([aid, f"=VLOOKUP(A{i},'Data Extraction'!A:D,4,FALSE)",
                      f"=VLOOKUP(A{i},'Data Extraction'!A:D,2,FALSE)"] + [None] * (len(h) - 3))
        s.add_table(Table(displayName=tname, ref=f"A1:{sx.col_letter(len(h))}3"))
    # Researcher 1 coded study 1 and 2 in Technologies
    t = wb["Technologies"]
    hdr = [c.value for c in t[1]]
    t.cell(row=2, column=hdr.index(f"High-level Theme ({R1})") + 1, value="Blockchain, Smart Contracts")
    t.cell(row=3, column=hdr.index(f"High-level Theme ({R1})") + 1, value="Cryptography")

    a = wb.create_sheet("Architecture")
    ah = ["Article ID", "Papper ID", "Ryyan ID", f"Data extraction ({R1})", f"Codes ({R1})", f"Codes ({GPT})",
          f"Theme ({R1})", f"Theme ({GPT})", "Theme (final decision)"]
    a.append(ah)
    for i, aid in enumerate(IDS, 2):
        a.append([aid, f"=VLOOKUP(A{i},'Data Extraction'!A:D,4,FALSE)", "x", None, None, None,
                  f"=_xlfn.XLOOKUP(A{i},Articles[Article ID],Articles[Architecture Type ({R1})])&\"\"",
                  f"=_xlfn.XLOOKUP(A{i},Articles[Article ID],Articles[Architecture Type ({GPT})])&\"\"", None])
    a.add_table(Table(displayName="ArticlesArchitecture", ref=f"A1:{sx.col_letter(len(ah))}4"))

    ta = wb.create_sheet("Thematic Analysis")
    ta.append(["Article ID", "Papper ID", "Domains"])
    for i, aid in enumerate(IDS[:2], 2):
        ta.append([aid, f"=VLOOKUP(A{i},'Data Extraction'!A:D,4,FALSE)",
                   f"=_xlfn.XLOOKUP(A{i},ArticlesDomains[Article ID],ArticlesDomains[High-level theme])"])
    ta.add_table(Table(displayName="ThematicAnalysis", ref="A1:C3"))
    eq = wb.create_sheet("Equivalences")
    for _ in range(3):
        eq.append([None])
    eq.append(["Active", "Dimension", "Stage", "Original term", "Canonical term"])
    eq.append(["Yes", "Technology", "HighLevelTheme", "smart contract", "smart contracts"])
    wb.save(path)


def answers(aid=IDS[0], **over):
    art = {
        "article_id": aid,
        "source_pdf": "x.pdf",
        "data_extraction": {
            "objective": "To propose a scheme.", "proposed_solution": "The study proposes ...",
            "tracked": "Health records", "architecture": "user-centred", "technology_stack": "Ethereum, IPFS",
            "purpose": "Tracking is implemented to audit access.", "responsibility": "Yes. Signed transactions.",
            "findings": "Gas cost grows linearly.", "limitations": "Inferred: testnet only.", "notes": "None.",
            "architecture_decision": {"subject": "patient", "subject_actions": ["grant", "revoke", "view"],
                                      "controller_decides": "none",
                                      "evidence": "Section 3: patients grant and revoke access to their records."},
        },
        "research_type": {
            "C1": {"value": False, "justification": "Ganache only (Section 5)."},
            "C2": {"value": True, "justification": "New scheme."},
            "C3": {"value": True, "justification": "Gas and latency measured (Section 6)."},
            "C4": {"value": False, "justification": "Laboratory."},
            "C5": {"value": False, "justification": "Concrete scheme."},
            "C6": {"value": False, "justification": "Not opinion."},
            "research_method": "Validation research",
            "evaluation_type": "Laboratory experiment (machine or human)",
        },
        "thematic": {
            "digital_object": {"extraction": ["records are stored on IPFS"], "codes": ["EHR"], "theme": ["Health Data"],
                               "final_theme": ["Health Data"], "high_level_theme": ["Structured Records"],
                               "support": {"Health Data": {"codes": ["EHR"], "excerpts": [1]}}},
            "technology": {"extraction": ["smart contracts on Ethereum"], "codes": ["Ethereum", "smart contracts"],
                           "theme": ["Blockchain", "Smart contracts"], "final_theme": ["Blockchain", "Smart contracts"],
                           "high_level_theme": ["Blockchain", "Smart Contracts"],
                           "support": {"Blockchain": {"codes": ["Ethereum"], "excerpts": [1]},
                                       "Smart contracts": {"codes": ["smart contracts"], "excerpts": [1]}}},
            "purpose": {"extraction": ["audit every access"], "codes": ["auditing"], "theme": ["Data Auditing"],
                        "final_theme": ["Data Auditing"], "high_level_theme": ["Data Auditing"],
                        "support": {"Data Auditing": {"codes": ["auditing"], "excerpts": [1],
                                                      "rule": "PUR-3: verification of accesses is a stated aim"}}},
            "domain": {"extraction": ["hospital"], "codes": ["hospital", "court"],
                       "theme": ["Healthcare and Medical Informatics", "Legal, Compliance and Digital Forensics"],
                       "final_theme": ["Healthcare and Medical Informatics", "Legal, Compliance and Digital Forensics"],
                       "high_level_theme": ["Legal, Compliance & Digital Forensics", "Healthcare & Medical Informatics"],
                       "support": {"Healthcare and Medical Informatics": {"codes": ["hospital"], "excerpts": [1]},
                                   "Legal, Compliance and Digital Forensics": {"codes": ["court"], "excerpts": [1]}}},
            "sub_domain": {"extraction": ["EHR"], "codes": ["EHR"], "theme": ["Electronic Health Record Management"],
                           "final_theme": ["Electronic Health Record Management"], "high_level_theme": [],
                           "support": {"Electronic Health Record Management": {"codes": ["EHR"], "excerpts": [1]}}},
            "architecture": {"codes": ["patient-held keys"]},
            "self_verification": "Excerpts on p. 3.",
        },
    }
    for k, v in over.items():
        sect, _, key = k.partition("__")
        art[sect][key] = v
    return {"role": GPT, "model": "test-model", "articles": [art]}


def run(*args):
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            sx.main(list(args))
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
            if isinstance(e.code, str):
                err.write(e.code)
    return code, out.getvalue() + err.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.wb = os.path.join(self.dir, "DEF_TA.xlsx")
        build_workbook(self.wb)
        self.txt = os.path.join(self.dir, "x.txt")
        with open(self.txt, "w") as f:
            f.write("\n===== page 1 =====\nThe electronic health records are stored on IPFS and smart contracts on "
                    "Ethereum audit every access in the hospital.\n")

    def tearDown(self):
        shutil.rmtree(self.dir)

    def dump(self, doc, name="a.json"):
        p = os.path.join(self.dir, name)
        with open(p, "w") as f:
            json.dump(doc, f)
        return p

    def cell(self, path, sheet, aid, header, values=False):
        wb = openpyxl.load_workbook(path, data_only=values)
        ws = wb[sheet]
        hdr = [c.value for c in ws[1]]
        for r in ws.iter_rows(min_row=2):
            if r[0].value == aid:
                return r[hdr.index(header)].value
        raise KeyError(aid)


class TestRolesAndTemplate(Base):
    def test_roles(self):
        code, out = run("roles", "--def", self.wb)
        self.assertEqual(code, 0)
        self.assertIn("1. Researcher 1", out)
        self.assertIn("2. AI Tool - OpenAI GPT", out)
        self.assertNotIn("final decision", out.lower().split("roles found")[1].split("\n")[1])

    def test_match_by_rayyan_and_doi(self):
        code, out = run("match", "--def", self.wb, "rayyan-2.pdf", "10.1_4.pdf", "unknown.pdf")
        self.assertIn("rayyan-2.pdf\t2-s2.0-2", out)
        self.assertIn("10.1_4.pdf\t2-s2.0-3", out)
        self.assertIn("unknown.pdf\tNOT FOUND", out)

    def test_template(self):
        p = os.path.join(self.dir, "t.json")
        code, _ = run("template", "--def", self.wb, "--role", "ai tool - openai gpt", "--ids", IDS[0], "--out", p)
        self.assertEqual(code, 0)
        with open(p) as f:
            doc = json.load(f)
        self.assertEqual(doc["role"], GPT)
        art = doc["articles"][0]
        self.assertEqual(set(art["data_extraction"]), set(sx.DE_FIELDS) | {"architecture_decision"})
        self.assertIn("support", art["thematic"]["purpose"])
        self.assertIn("model", doc)
        self.assertIn("C6", art["research_type"])
        self.assertEqual(list(art["thematic"]["architecture"]), ["codes"])


class TestValidation(Base):
    def validate(self, doc):
        return run("validate", "--def", self.wb, "--input", self.dump(doc))

    def test_valid(self):
        code, out = self.validate(answers())
        self.assertEqual(code, 0, out)
        self.assertIn("Valid.", out)

    def test_decision_table_contradiction(self):
        doc = answers(research_type__research_method="Evaluation research")
        code, out = self.validate(doc)
        self.assertEqual(code, 1)
        self.assertIn("contradicts the decision table", out)

    def test_used_in_practice_but_lab_evaluation(self):
        doc = answers(research_type__C1={"value": True, "justification": "Implemented."})
        code, out = self.validate(doc)
        self.assertEqual(code, 1)
        self.assertIn("C4 is False", out)

    def test_method_must_match_type(self):
        doc = answers(research_type__evaluation_type="Industrial case study")
        code, out = self.validate(doc)
        self.assertEqual(code, 1)
        self.assertIn("evaluation research method", out)

    def test_solution_proposal_needs_dash(self):
        rt = answers()["articles"][0]["research_type"]
        rt["C3"] = {"value": False, "justification": "Only a scenario."}
        rt["research_method"] = "Solution proposal"
        doc = answers(research_type__C3=rt["C3"], research_type__research_method="Solution proposal")
        code, out = self.validate(doc)
        self.assertIn("use '-'", out)
        doc["articles"][0]["research_type"]["evaluation_type"] = "-"
        code, out = self.validate(doc)
        self.assertEqual(code, 0, out)

    def test_opinion_requires_prefix(self):
        doc = answers()
        rt = doc["articles"][0]["research_type"]
        for k in ("C1", "C2", "C3", "C4", "C5"):
            rt[k]["value"] = False
        rt["C6"] = {"value": True, "justification": "The authors argue that ..."}
        rt["research_method"], rt["evaluation_type"] = "Opinion paper", "-"
        code, out = self.validate(doc)
        self.assertIn("'Opinion:' or 'Experience:'", out)
        rt["C6"]["justification"] = "Opinion: the authors argue that ..."
        code, out = self.validate(doc)
        self.assertEqual(code, 0, out)

    def test_high_level_theme_closed_set(self):
        doc = answers()
        doc["articles"][0]["thematic"]["purpose"]["high_level_theme"] = ["Accountability"]
        code, out = self.validate(doc)
        self.assertEqual(code, 1)
        self.assertIn("'Accountability' is not a high-level theme", out)

    def test_architecture_closed_set(self):
        code, out = self.validate(answers(data_extraction__architecture="Decentralised"))
        self.assertEqual(code, 1)
        self.assertIn("is not one of", out)

    def test_unknown_article(self):
        code, out = self.validate(answers(aid="nope"))
        self.assertEqual(code, 1)
        self.assertIn("not found", out)

    def test_british_spelling_accepted(self):
        doc = answers()
        t = doc["articles"][0]["thematic"]["technology"]
        t["theme"] = t["final_theme"] = ["Blockchain", "Smart contracts", "Containerisation and orchestration"]
        t["codes"].append("Docker swarm")
        t["support"]["Containerisation and orchestration"] = {"codes": ["Docker swarm"], "excerpts": [1],
                                                              "rule": "TEC-2: deployed services"}
        t["high_level_theme"] = ["Blockchain"]
        code, out = self.validate(doc)
        self.assertEqual(code, 0, out)

    def test_theme_must_come_from_codebook(self):
        doc = answers()
        doc["articles"][0]["thematic"]["purpose"]["theme"] = ["Auditing of every access to the records"]
        code, out = self.validate(doc)
        self.assertEqual(code, 1)
        self.assertIn("is not in the codebook", out)

    def test_high_level_label_in_final_theme(self):
        doc = answers()
        p = doc["articles"][0]["thematic"]["purpose"]
        p["theme"] = p["final_theme"] = ["Cybersecurity Risk Mitigation"]
        code, out = self.validate(doc)
        self.assertEqual(code, 1)
        self.assertIn("is a high-level theme; use its final theme(s): Data Security; Mitigate Cybersecurity Risks", out)

    def test_high_level_derived_and_extra_rejected(self):
        doc = answers()
        doc["articles"][0]["thematic"]["technology"]["high_level_theme"] = ["Blockchain", "Cryptography"]
        code, out = self.validate(doc)
        self.assertEqual(code, 1)
        self.assertIn("Cryptography not licensed by the final themes", out)

    def test_container_choice_required(self):
        doc = answers()
        o = doc["articles"][0]["thematic"]["digital_object"]
        o["theme"] = o["final_theme"] = ["Personal Data"]
        o["support"] = {"Personal Data": {"codes": ["EHR"], "excerpts": [1], "rule": "DO-4: records"}}
        o["high_level_theme"] = []
        code, out = self.validate(doc)
        self.assertIn("'Personal Data' can be Structured Records or Data Files or Documents", out)
        o["high_level_theme"] = ["Structured Records"]
        code, out = self.validate(doc)
        self.assertEqual(code, 0, out)

    def test_guarded_label_needs_rule(self):
        doc = answers()
        del doc["articles"][0]["thematic"]["purpose"]["support"]["Data Auditing"]["rule"]
        code, out = self.validate(doc)
        self.assertEqual(code, 1)
        self.assertIn("needs the decision rule PUR-3", out)

    def test_support_required(self):
        doc = answers()
        doc["articles"][0]["thematic"]["digital_object"]["support"] = {}
        code, out = self.validate(doc)
        self.assertEqual(code, 1)
        self.assertIn("support['Health Data']: missing", out)

    def test_final_must_be_in_theme(self):
        doc = answers()
        doc["articles"][0]["thematic"]["technology"]["theme"] = ["Blockchain"]
        code, out = self.validate(doc)
        self.assertIn("Smart contracts not in theme", out)

    def test_sub_domain_rejects_domain_and_zero(self):
        doc = answers()
        s = doc["articles"][0]["thematic"]["sub_domain"]
        s["theme"] = s["final_theme"] = ["Healthcare and Medical Informatics", "0"]
        code, out = self.validate(doc)
        self.assertEqual(code, 1)
        self.assertIn("is a domain, not a sub-domain", out)
        self.assertIn("'0' is not a label", out)

    def test_tooling_rejected_as_new_technology(self):
        doc = answers()
        t = doc["articles"][0]["thematic"]["technology"]
        t["theme"].append("[NEW] Performance Benchmarking")
        code, out = self.validate(doc)
        self.assertIn("is tooling, not a tracking technology", out)

    def test_label_cap(self):
        doc = answers()
        p = doc["articles"][0]["thematic"]["purpose"]
        labs = ["Data Traceability", "Access Control", "Data Privacy", "Secure Data Sharing", "Copyrights Protection",
                "Support forensic investigations", "Data Confidentiality"]
        p["theme"] = p["final_theme"] = labs
        p["support"] = {l: {"codes": ["auditing"], "excerpts": [1]} for l in labs}
        code, out = self.validate(doc)
        self.assertIn("7 labels; at most 6", out)

    def test_architecture_decision(self):
        doc = answers(data_extraction__architecture="Hybrid (user-centered and server-centered)")
        code, out = self.validate(doc)
        self.assertEqual(code, 1)
        self.assertIn("give 'User-centered' (rule ARC-2)", out)
        dec = doc["articles"][0]["data_extraction"]["architecture_decision"]
        dec["controller_decides"] = "some"  # e.g. emergency access by the hospital without consent
        code, out = self.validate(doc)
        self.assertEqual(code, 0, out)
        self.assertEqual(sx.derive_architecture(["view", "trace"], "none")[0], "Server-centered")
        self.assertEqual(sx.derive_architecture(["notified"], "all")[0], "Server-centered")
        self.assertIsNone(sx.derive_architecture(["grant"], "all")[0])
        dec["subject_actions"] = ["decentralised storage"]
        code, out = self.validate(doc)
        self.assertIn("unknown: decentralised_storage", out)
        del doc["articles"][0]["data_extraction"]["architecture_decision"]
        code, out = self.validate(doc)
        self.assertIn("architecture_decision: missing", out)


class TestWrite(Base):
    def write(self, doc, *extra, out="out.xlsx"):
        o = os.path.join(self.dir, out)
        code, txt = run("write", "--def", self.wb, "--input", self.dump(doc), "--out", o, "--pdf", self.txt, *extra)
        return code, txt, o

    def test_write_values_and_formats(self):
        code, txt, o = self.write(answers())
        self.assertEqual(code, 0, txt)
        self.assertEqual(self.cell(o, "Data Extraction", IDS[0], f"Architecture Type ({GPT})"), "User-centered")
        self.assertEqual(self.cell(o, "Data Extraction", IDS[0], f"C1 - Value ({GPT})"), "False")
        self.assertEqual(self.cell(o, "Data Extraction", IDS[0], f"C1 - Justification ({GPT})"), "Ganache only (Section 5).")
        self.assertEqual(self.cell(o, "Technologies", IDS[0], f"High-level Theme ({GPT})"), "Blockchain, Smart Contracts")
        self.assertEqual(self.cell(o, "Domains", IDS[0], f"High-level Theme ({GPT})"),
                         "Legal, Compliance & Digital Forensics, Healthcare & Medical Informatics")
        self.assertEqual(self.cell(o, "Architecture", IDS[0], f"Codes ({GPT})"), "patient-held keys")
        # never touched: other raters, final decision, formulas
        self.assertIsNone(self.cell(o, "Technologies", IDS[0], "Theme (Final decision)"))
        self.assertEqual(self.cell(o, "Technologies", IDS[0], f"High-level Theme ({R1})"), "Blockchain, Smart Contracts")
        self.assertTrue(str(self.cell(o, "Data Extraction", IDS[0], "Ryyan ID")).startswith("=VLOOKUP"))
        self.assertTrue(str(self.cell(o, "Architecture", IDS[0], f"Theme ({GPT})")).startswith("=_xlfn.XLOOKUP"))
        # the original file is unchanged
        self.assertIsNone(self.cell(self.wb, "Data Extraction", IDS[0], f"Architecture Type ({GPT})"))
        self.assertTrue(os.path.exists(os.path.splitext(o)[0] + "_report.md"))

    def test_single_column_criteria_for_researcher(self):
        doc = answers()
        doc["role"] = R1
        doc["articles"][0]["article_id"] = IDS[1]
        code, txt, o = self.write(doc)
        self.assertEqual(code, 0, txt)
        self.assertEqual(self.cell(o, "Data Extraction", IDS[1], f"C3 ({R1})"),
                         "True. Justification: Gas and latency measured (Section 6).")

    def test_existing_cells_kept_unless_overwrite(self):
        doc = answers()
        doc["role"] = R1
        code, txt, o = self.write(doc)
        self.assertEqual(code, 0, txt)
        self.assertEqual(self.cell(o, "Data Extraction", IDS[0], f"Architecture Type ({R1})"), "Server-centered")
        self.assertIn("already filled were kept", txt)
        code, txt, o = self.write(doc, "--overwrite", out="out2.xlsx")
        self.assertEqual(self.cell(o, "Data Extraction", IDS[0], f"Architecture Type ({R1})"), "User-centered")

    def test_rows_appended_for_new_study(self):
        code, txt, o = self.write(answers(aid=IDS[2]))
        self.assertEqual(code, 0, txt)
        self.assertEqual(self.cell(o, "Purposes", IDS[2], f"High-level Theme ({GPT})"), "Data Auditing")
        self.assertEqual(self.cell(o, "Purposes", IDS[2], "Papper ID"), "=VLOOKUP(A4,'Data Extraction'!A:D,4,FALSE)")
        self.assertEqual(self.cell(o, "Thematic Analysis", IDS[2], "Domains"),
                         "=_xlfn.XLOOKUP(A4,ArticlesDomains[Article ID],ArticlesDomains[High-level theme])")
        with zipfile.ZipFile(o) as z:
            tables = {n: z.read(n).decode() for n in z.namelist() if n.startswith("xl/tables/")}
        purposes = [t for t in tables.values() if 'name="ArticlesPurposes"' in t][0]
        self.assertIn('ref="A1:O4"', purposes)
        self.assertIn('<autoFilter ref="A1:O4"', purposes)

    def test_missing_columns_skipped_or_added(self):
        doc = answers()
        doc["role"] = "AI Tool 3"
        code, txt, o = self.write(doc)
        self.assertEqual(code, 1)  # nothing to write without --add-columns
        code, txt, o = self.write(doc, "--add-columns", out="out3.xlsx")
        self.assertEqual(code, 0, txt)
        self.assertEqual(self.cell(o, "Data Extraction", IDS[0], "Research Method (AI Tool 3)"), "Validation research")
        self.assertEqual(self.cell(o, "Data Extraction", IDS[0], "C2 (AI Tool 3)"), "True. Justification: New scheme.")
        self.assertEqual(self.cell(o, "Digital Objects", IDS[0], "Codes (AI Tool 3)"), "EHR")
        with zipfile.ZipFile(o) as z:
            t = [z.read(n).decode() for n in z.namelist() if n.startswith("xl/tables/")]
        art = [x for x in t if 'name="Articles"' in x][0]
        self.assertIn('name="Research Method (AI Tool 3)"', art)
        # the new role is now discovered
        code, out = run("roles", "--def", o)
        self.assertIn("AI Tool 3", out)

    def test_invalid_answers_not_written(self):
        code, txt, o = self.write(answers(research_type__research_method="Opinion paper"))
        self.assertEqual(code, 1)
        self.assertFalse(os.path.exists(o))

    def test_write_requires_pdf_and_model(self):
        o = os.path.join(self.dir, "g.xlsx")
        code, txt = run("write", "--def", self.wb, "--input", self.dump(answers()), "--out", o)
        self.assertEqual(code, 1)
        self.assertIn("pass the PDFs", txt)
        doc = answers()
        doc["model"] = ""
        code, txt, o = self.write(doc, out="g2.xlsx")
        self.assertEqual(code, 1)
        self.assertIn("record the AI model", txt)
        doc = answers()
        doc["articles"][0]["thematic"]["purpose"]["extraction"] = ["every access is written to a public ledger"]
        code, txt, o = self.write(doc, out="g3.xlsx")
        self.assertEqual(code, 1)
        self.assertIn("excerpt not found in the PDF", txt)

    def test_report_records_model_and_derived_high_level(self):
        doc = answers()
        doc["articles"][0]["thematic"]["technology"]["high_level_theme"] = []
        code, txt, o = self.write(doc)
        self.assertEqual(code, 0, txt)
        self.assertEqual(self.cell(o, "Technologies", IDS[0], f"High-level Theme ({GPT})"), "Blockchain, Smart Contracts")
        rep = open(os.path.splitext(o)[0] + "_report.md").read()
        self.assertIn("- Model: test-model", rep)
        self.assertIn("1 checked" if False else "checked, 0 not found", rep)

    def test_output_must_differ_from_input(self):
        code, txt = run("write", "--def", self.wb, "--input", self.dump(answers()), "--out", self.wb)
        self.assertEqual(code, 1)
        self.assertIn("never modified", txt)


class TestKappaAndQuotes(Base):
    def test_kappa_matches_manual_value(self):
        doc = answers()
        doc["articles"][0]["thematic"]["technology"]["high_level_theme"] = ["Smart Contracts", "Blockchain"]
        d2 = answers(aid=IDS[1])
        t2 = d2["articles"][0]["thematic"]["technology"]
        t2["theme"] = t2["final_theme"] = ["Blockchain"]
        t2["high_level_theme"] = ["Blockchain"]
        del t2["support"]["Smart contracts"]
        p = os.path.join(self.dir, "k.xlsx")
        run("write", "--def", self.wb, "--input", self.dump(doc, "1.json"), self.dump(d2, "2.json"), "--out", p,
            "--no-quote-check")
        code, out = run("kappa", "--def", p, "--raters", f"{R1},{GPT}")
        line = [x for x in out.splitlines() if x.startswith("Technology\tHigh-level Theme")][0]
        # study 1 agrees (order ignored), study 2 disagrees: Po = 0.5; categories bc x3, c x1, b x1 -> Pe = 0.375+...
        n, po, pe, k = line.split("\t")[2:6]
        self.assertEqual(n, "2")
        self.assertEqual(po, "0.500")
        exp_pe = (2 / 4) ** 2 + (1 / 4) ** 2 + (1 / 4) ** 2
        self.assertAlmostEqual(float(pe), exp_pe, places=3)
        self.assertAlmostEqual(float(k), (0.5 - exp_pe) / (1 - exp_pe), places=3)

    def test_quote_matching(self):
        pages = ["The electronic health re-\ncords are stored on IPFS, while the\nhash is written to the ledger."]
        folds = [(sx.fold_text(p), sx.squeeze(sx.fold_text(p))) for p in pages]
        self.assertEqual(sx.quote_found("electronic health records are stored on IPFS", folds)[0], "exact")
        self.assertEqual(sx.quote_found("the hash is written to the ledger", folds)[0], "exact")
        self.assertEqual(sx.quote_found("records are encrypted with CP-ABE before upload", folds)[0], "missing")


class TestPackaging(unittest.TestCase):
    def test_script_copies_are_identical(self):
        src = open(os.path.join(ROOT, "tools", "slm_extract.py"), "rb").read()
        for skill in ("slm-data-extraction", "slm-thematic-analysis", "slm-research-type"):
            self.assertEqual(open(os.path.join(ROOT, skill, "scripts", "slm_extract.py"), "rb").read(), src,
                             f"{skill}: run tools/build.sh")
            with zipfile.ZipFile(os.path.join(ROOT, "dist", f"{skill}.zip")) as z:
                self.assertEqual(z.read("scripts/slm_extract.py"), src, f"dist/{skill}.zip: run tools/build.sh")
                self.assertEqual(z.read("SKILL.md"), open(os.path.join(ROOT, skill, "SKILL.md"), "rb").read())

    def test_instructions_within_limit(self):
        n = len(open(os.path.join(ROOT, "instructions.md"), encoding="utf-8").read())
        self.assertLessEqual(n, 8000)


if __name__ == "__main__":
    unittest.main()
