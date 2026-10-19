#!/usr/bin/env python3
"""Build data/references.js from the article's LaTeX source and BibTeX file.

The article uses natbib with the elsarticle-num style, so each reference is numbered by the
order of its first citation in the manuscript. This script reproduces that numbering and
formats every cited entry in the same style as the article's reference list.

Usage:
    python3 build_references.py --tex "Tracking and Accountability for Digital Objects.tex" \
        --bib cas-refs.bib --out ../data/references.js
"""
import argparse
import json
import re

CITE_RE = re.compile(r"\\(?:no)?cite[a-zA-Z]*\*?(?:\[[^\]]*\])*\{([^}]*)\}")

ACCENTS = {
    "'": {"a": "á", "e": "é", "i": "í", "o": "ó", "u": "ú", "c": "ć", "n": "ń", "s": "ś", "z": "ź", "y": "ý",
          "A": "Á", "E": "É", "I": "Í", "O": "Ó", "U": "Ú", "C": "Ć", "S": "Ś", "Z": "Ź"},
    "`": {"a": "à", "e": "è", "i": "ì", "o": "ò", "u": "ù", "A": "À", "E": "È"},
    "^": {"a": "â", "e": "ê", "i": "î", "o": "ô", "u": "û", "A": "Â", "E": "Ê", "O": "Ô"},
    '"': {"a": "ä", "e": "ë", "i": "ï", "o": "ö", "u": "ü", "A": "Ä", "O": "Ö", "U": "Ü"},
    "~": {"a": "ã", "o": "õ", "n": "ñ", "A": "Ã", "O": "Õ", "N": "Ñ"},
    "c": {"c": "ç", "C": "Ç", "s": "ş", "S": "Ş"},
    "v": {"c": "č", "s": "š", "z": "ž", "r": "ř", "e": "ě", "C": "Č", "S": "Š", "Z": "Ž"},
}


def strip_comments(tex):
    """Remove LaTeX comments (an unescaped % to the end of the line)."""
    return "\n".join(re.sub(r"(?<!\\)%.*", "", line) for line in tex.splitlines())


def citation_order(tex):
    """Return the cited keys in order of first appearance."""
    order, seen = [], set()
    for match in CITE_RE.finditer(strip_comments(tex)):
        for key in match.group(1).split(","):
            key = key.strip()
            if key and key not in seen:
                seen.add(key)
                order.append(key)
    return order


def parse_bib(text):
    """Minimal BibTeX parser: returns {key: {"type": ..., field: value}}."""
    entries, i = {}, 0
    while True:
        at = text.find("@", i)
        if at < 0:
            break
        brace = text.find("{", at)
        if brace < 0:
            break
        etype = text[at + 1:brace].strip().lower()
        if etype in ("comment", "preamble", "string"):
            i = brace + 1
            continue
        comma = text.find(",", brace)
        key = text[brace + 1:comma].strip()
        # Find the end of the entry by brace matching.
        depth, j = 1, brace + 1
        while j < len(text) and depth:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        body = text[comma + 1:j - 1]
        entries[key] = dict(parse_fields(body), type=etype)
        i = j
    return entries


def parse_fields(body):
    fields, i, n = {}, 0, len(body)
    while i < n:
        m = re.compile(r"\s*,?\s*([A-Za-z_\-]+)\s*=\s*").match(body, i)
        if not m:
            break
        name, i = m.group(1).lower(), m.end()
        if i < n and body[i] == "{":
            depth, j = 1, i + 1
            while j < n and depth:
                if body[j] == "{":
                    depth += 1
                elif body[j] == "}":
                    depth -= 1
                j += 1
            value, i = body[i + 1:j - 1], j
        elif i < n and body[i] == '"':
            j = body.find('"', i + 1)
            value, i = body[i + 1:j], j + 1
        else:
            m2 = re.compile(r"[^,]*").match(body, i)
            value, i = m2.group(0).strip(), m2.end()
        fields[name] = re.sub(r"\s+", " ", value).strip()
    return fields


def sentence_case(title):
    """Emulate BibTeX's "t" change.case$: lower-case everything outside braces,
    except the first character and the first character after a colon."""
    out, depth, after_colon = [], 0, False
    for idx, ch in enumerate(title):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif depth == 0 and idx > 0 and not after_colon:
            ch = ch.lower()
        if ch == ":":
            after_colon = True
        elif not ch.isspace() and ch not in "{}":
            after_colon = False if ch != ":" else after_colon
        out.append(ch)
    return "".join(out)


def delatex(s):
    s = re.sub(r"\\url\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\{\\([`'^\"~cv])\s*\{?(\w)\}?\}", lambda m: ACCENTS.get(m.group(1), {}).get(m.group(2), m.group(2)), s)
    s = re.sub(r"\\([`'^\"~])\{?(\w)\}?", lambda m: ACCENTS.get(m.group(1), {}).get(m.group(2), m.group(2)), s)
    s = re.sub(r"\\([cv])\{(\w)\}", lambda m: ACCENTS.get(m.group(1), {}).get(m.group(2), m.group(2)), s)
    s = re.sub(r"\\(?:textit|textbf|emph|textsc|mbox)\{([^}]*)\}", r"\1", s)
    s = s.replace("\\&", "&").replace("\\%", "%").replace("\\_", "_").replace("\\$", "$")
    s = s.replace("---", "—").replace("--", "–").replace("~", " ")
    s = s.replace("{", "").replace("}", "")
    s = re.sub(r"\\[a-zA-Z]+\s*", "", s)
    return re.sub(r"\s+", " ", s).strip()


def split_names(field):
    names, depth, cur, i = [], 0, "", 0
    while i < len(field):
        ch = field[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        if depth == 0 and field[i:i + 5].lower() == " and ":
            names.append(cur.strip())
            cur, i = "", i + 5
            continue
        cur += ch
        i += 1
    if cur.strip():
        names.append(cur.strip())
    return names


def format_name(name):
    """Format a name as {f.~}{vv~}{ll}{, jj} (initials, then surname)."""
    if name.lower() == "others":
        return "others"
    if name.startswith("{") and name.endswith("}") and name.count("{") == 1:
        return delatex(name)  # Corporate author.
    parts = [p.strip() for p in name.split(",")]
    if len(parts) >= 2:
        last, first = parts[0], parts[-1]
        jr = parts[1] if len(parts) == 3 else ""
    else:
        words = name.split()
        last, first, jr = (words[-1], " ".join(words[:-1]), "") if words else (name, "", "")
    initials = []
    for word in re.split(r"\s+", delatex(first)):
        if not word:
            continue
        initials.append("-".join(w[0] + "." for w in word.split("-") if w))
    text = " ".join(initials + [delatex(last)])
    return text + (", " + delatex(jr) if jr else "")


def format_authors(field):
    names = [format_name(n) for n in split_names(field)]
    if names and names[-1] == "others":
        return ", ".join(names[:-1]) + " et al."
    return ", ".join(names)


def dashify(pages):
    return re.sub(r"\s*(?:–|—|-{1,3})\s*", "–", pages)


def format_entry(e):
    """Format an entry in the elsarticle-num style used by the article."""
    get = lambda f: delatex(e.get(f, ""))
    authors = format_authors(e.get("author", "")) if e.get("author") else format_authors(e.get("editor", ""))
    title = delatex(sentence_case(e.get("title", "")))
    year, pages = get("year"), dashify(get("pages"))
    t = e["type"]
    parts = [p for p in (authors, title) if p]
    if t == "article":
        venue = get("journal")
        if get("volume"):
            venue += " " + get("volume")
        if get("number"):
            venue += " (" + get("number") + ")"
        if year:
            venue += " (" + year + ")"
        if pages:
            venue += " " + pages
        parts.append(venue.strip())
        text = ", ".join(parts)
    elif t in ("inproceedings", "incollection", "inbook"):
        bits = []
        if get("booktitle"):
            bits.append("in: " + get("booktitle"))
        bits += [x for x in (get("publisher"), get("address"), year) if x]
        if pages:
            bits.append(("pp. " if "–" in pages else "p. ") + pages)
        text = ", ".join(parts + bits)
    else:
        bits = [x for x in (get("howpublished"), get("publisher") or get("institution") or get("organization"),
                            get("address")) if x]
        text = ", ".join(parts + bits) + (" (" + year + ")" if year else "")
    text = text.rstrip(".") + "."
    if e.get("doi"):
        text += " doi:" + e["doi"].strip() + "."
    return text


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tex", required=True)
    ap.add_argument("--bib", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    tex = open(args.tex, encoding="utf-8").read()
    bib = parse_bib(open(args.bib, encoding="utf-8").read())
    refs, n = {}, 0
    for key in citation_order(tex):
        if key not in bib:
            continue  # BibTeX skips undefined keys without consuming a number.
        n += 1
        e = bib[key]
        doi = e.get("doi", "").strip()
        refs[key] = {
            "number": n,
            "reference": format_entry(e),
            "year": delatex(e.get("year", "")),
            "url": ("https://doi.org/" + doi) if doi else delatex(e.get("url", "")),
        }
    # Written as a script (not JSON) so that it also loads when the page is opened from disk.
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write("// Generated by tools/build_references.py. Do not edit by hand.\n")
        fh.write("window.DASHBOARD_REFERENCES = ")
        json.dump(refs, fh, ensure_ascii=False, indent=1)
        fh.write(";\n")
    print(f"{len(refs)} references written to {args.out}")


if __name__ == "__main__":
    main()
