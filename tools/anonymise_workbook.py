#!/usr/bin/env python3
"""Remove the details that identify the authors from an xlsx package, for double-anonymised review.

The workbook is edited inside the xlsx package, entry by entry, so that charts, tables, formulas and
the data model (Power Pivot) are kept. What is removed:

* docProps/core.xml and docProps/app.xml: creator, last modified by, manager and company;
* xl/workbook.xml: the absolute path of the file (x15ac:absPath), which names the folder where it was saved;
* xl/model/item.data: user names in Windows paths (C:\\Users\\<name>\\...) recorded by the data model,
  replaced by a placeholder of the same length so that the binary layout does not change;
* threaded comments and their authors (xl/persons), when present, are reported but not changed.

Usage:
    python3 tools/anonymise_workbook.py --in DEF_TA_new.xlsx --out data/DEF_TA.xlsx [--check]

With --check, nothing is written: the script only lists what it would remove. Extra terms to look for
(names, e-mail addresses, institutions) can be given with --term, repeatedly; they are reported, never
replaced, because they may also be part of the data (for example, the author list of a screened record).
"""
import argparse
import re
import sys
import zipfile

CORE_FIELDS = ("dc:creator", "cp:lastModifiedBy")
APP_FIELDS = ("Manager", "Company")
ABS_PATH = re.compile(r"<mc:AlternateContent[^>]*><mc:Choice Requires=\"x15\"><x15ac:absPath [^>]*/></mc:Choice></mc:AlternateContent>")
# C:\Users\<name>\ in UTF-16LE, as written by the data model.


def clear_xml_fields(xml, fields):
    changes = []
    for f in fields:
        pattern = re.compile(rf"<{f}>([^<]+)</{f}>")
        m = pattern.search(xml)
        if m:
            changes.append(f"{f}: {m.group(1)!r} removed")
            xml = pattern.sub(f"<{f}></{f}>", xml)
    return xml, changes


def user_path_placeholder(name_bytes):
    """Same length as the original UTF-16LE name, e.g. 'myname' -> 'author' (padded or cut)."""
    n = len(name_bytes) // 2
    word = ("author" * (n // 6 + 1))[:n]
    return word.encode("utf-16-le")


def anonymise_model(data):
    changes = {}
    pattern = re.compile(rb"(\\\x00[Uu]\x00[Ss]\x00[Ee]\x00[Rr]\x00[Ss]\x00\\\x00)((?:[^\\\x00]\x00)+?)(\\\x00)")

    def repl(m):
        name = m.group(2)
        if name.decode("utf-16-le").lower() in ("public", "default", "author"):
            return m.group(0)
        changes[name.decode("utf-16-le")] = changes.get(name.decode("utf-16-le"), 0) + 1
        return m.group(1) + user_path_placeholder(name) + m.group(3)

    out = pattern.sub(repl, data)
    assert len(out) == len(data)
    return out, [f"data model: Windows user name {k!r} replaced in {v} paths" for k, v in changes.items()]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--term", action="append", default=[], help="extra term to report (case-insensitive)")
    args = ap.parse_args()
    if not args.check and not args.out:
        ap.error("--out is required unless --check is given")

    report = []
    found_terms = {}
    zin = zipfile.ZipFile(args.src)
    entries = []
    for info in zin.infolist():
        data = zin.read(info.filename)
        name = info.filename
        if name == "docProps/core.xml":
            xml, ch = clear_xml_fields(data.decode("utf-8"), CORE_FIELDS)
            data, report = xml.encode("utf-8"), report + ch
        elif name == "docProps/app.xml":
            xml, ch = clear_xml_fields(data.decode("utf-8"), APP_FIELDS)
            data, report = xml.encode("utf-8"), report + ch
        elif name == "xl/workbook.xml":
            xml = data.decode("utf-8")
            if ABS_PATH.search(xml):
                report.append("workbook.xml: absolute path of the file removed")
                xml = ABS_PATH.sub("", xml)
            data = xml.encode("utf-8")
        elif name == "xl/model/item.data":
            data, ch = anonymise_model(data)
            report += ch
        elif name.startswith("xl/persons/") and b"<person " in data:
            report.append(f"{name}: comment authors present (not changed; delete the comments in Excel)")
        for term in args.term:
            for enc in ("utf-8", "utf-16-le"):
                n = data.lower().count(term.lower().encode(enc))
                if n:
                    found_terms.setdefault(term, []).append(f"{name} ({enc}): {n}")
        entries.append((info, data))

    for line in report or ["nothing to remove"]:
        print(line)
    for term, where in found_terms.items():
        print(f"term {term!r} found in: " + "; ".join(where))

    if args.check:
        return 0
    with zipfile.ZipFile(args.out, "w") as zout:
        for info, data in entries:
            zout.writestr(info, data, compress_type=info.compress_type)
    print(f"written {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
