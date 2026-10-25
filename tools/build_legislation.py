#!/usr/bin/env python3
"""Extract the GDPR and LGPD provisions cited in the "Data Protection Requirements" sheet.

Reads the official HTML pages, saved from a browser:
  GDPR: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0679
  LGPD: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm
and writes data/legislation.js with the text of every article (and recital) the sheet cites.
In the LGPD consolidated text, struck-through wording (superseded versions) is left out, and
the notes on amendments ("Redação dada pela Lei nº ...") are removed from the text.

Usage:
    python3 build_legislation.py --workbook ../data/DEF_TA.xlsx --gdpr gdpr.html \
        --lgpd lgpd.html --retrieved "25 October 2026" --out ../data/legislation.js
"""
import argparse
import json
import re
import warnings

import openpyxl
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings('ignore', category=XMLParsedAsHTMLWarning)  # EUR-Lex serves XHTML
SMALL = {'de', 'do', 'da', 'dos', 'das', 'e', 'pelo', 'pela'}

DASH = r'\s*[–—-]+\s*'


def clean(s):
    return ' '.join(s.replace('\xa0', ' ').split())


# ------------------------------------------------------------- cited articles

def cited(workbook):
    """Article and recital numbers cited in the GDPR and LGPD columns of the sheet."""
    ws = openpyxl.load_workbook(workbook, read_only=True)['Data Protection Requirements']
    rows = list(ws.iter_rows(values_only=True))
    head = [str(h or '') for h in rows[0]]
    gi = next(i for i, h in enumerate(head) if h.startswith('GDPR'))
    li = next(i for i, h in enumerate(head) if h.startswith('LGPD equivalent'))
    out = {'gdpr': set(), 'lgpd': set(), 'recitals': set()}

    def numbers(body):
        found = set()
        for m in re.finditer(r'(\d+)(?:' + DASH + r'(\d+))?', body):
            a, b = int(m.group(1)), int(m.group(2) or m.group(1))
            found.update(range(a, b + 1))
        return found

    for r in rows[1:]:
        for item in str(r[gi] or '').split(';'):
            ref = item.split(':')[0]
            for kind, body in re.findall(r'(Recitals?|Arts?\.)\s*([^A-Z]*)', ref):
                body = re.sub(r'\([^)]*\)', '', body)  # paragraph and point numbers
                (out['recitals'] if kind.startswith('Recital') else out['gdpr']).update(numbers(body))
        for item in str(r[li] or '').split(';'):
            ref = item.split(':')[0]
            for body in re.findall(r'Arts?\.\s*(\d+(?:' + DASH + r'\d+)?)', ref):
                out['lgpd'].update(numbers(body))
    return out


# ----------------------------------------------------------------------- GDPR

def gdpr_text(node):
    """Text of a cell, with nested points written inline as "(i) ...", "(ii) ..."."""
    parts = []
    for child in node.children:
        if getattr(child, 'name', None) == 'table':
            tds = child.find_all('td', recursive=False) or child.find('tr').find_all('td', recursive=False)
            parts.append(f'{clean(tds[0].get_text(" "))} {gdpr_text(tds[1])}')
        elif getattr(child, 'name', None):
            parts.append(gdpr_text(child) if child.find('table') else clean(child.get_text(' ')))
        else:
            parts.append(clean(str(child)))
    return clean(' '.join(p for p in parts if p))


def gdpr_paragraph(container, num=None):
    para = {'num': num, 'text': '', 'points': [], 'after': []}
    for child in container.find_all(['p', 'table'], recursive=False):
        if child.name == 'table':
            tds = child.find('tr').find_all('td', recursive=False)
            pid = clean(tds[0].get_text(' ')).strip('()')
            para['points'].append({'id': pid, 'text': gdpr_text(tds[1])})
        elif 'oj-normal' in (child.get('class') or []):
            t = clean(child.get_text(' '))
            if para['points']:
                para['after'].append(t)
            else:
                para['text'] = clean(f"{para['text']} {t}")
    if num:
        para['text'] = re.sub(rf'^{num}\.\s*', '', para['text'])
    return para


def parse_gdpr(path, arts, recitals):
    soup = BeautifulSoup(open(path, encoding='utf-8').read(), 'lxml')
    out = {'articles': {}, 'recitals': {}}
    for n in sorted(arts):
        div = soup.find(id=f'art_{n}')
        title = div.find(class_='oj-sti-art')
        subs = [d for d in div.find_all('div', recursive=False) if re.match(r'^\d{3}\.\d{3}$', d.get('id', ''))]
        if subs:
            paras = [gdpr_paragraph(d, str(int(d['id'].split('.')[1]))) for d in subs]
        else:
            paras = [gdpr_paragraph(div)]
        out['articles'][str(n)] = {'title': clean(title.get_text(' ')) if title else '', 'paragraphs': paras}
    for n in sorted(recitals):
        div = soup.find(id=f'rct_{n}')
        tds = div.find('tr').find_all('td', recursive=False)
        out['recitals'][str(n)] = gdpr_text(tds[1])
    return out


# ----------------------------------------------------------------------- LGPD

NOTE = re.compile(r'\((?:Redação dada|Incluíd[oa]|Revogad[oa]|Vide|Promulgação|Produção de efeitos|Vigência)[^)]*\)', re.I)
ART = re.compile(r'^Art\.\s*(\d+)(?:-([A-Z]))?\s*[º°o.]*\s*')
INCISO = re.compile(r'^([IVXLC]+(?:-[A-Z])?)\s*[-–]\s*')
PARA = re.compile(r'^(?:§\s*(\d+)\s*[º°.]*|Parágrafo único\.?)\s*')
ALINEA = re.compile(r'^([a-z])\)\s*')


def chapter_title(raw):
    """'CAPÍTULO III DOS DIREITOS DO TITULAR' → 'Capítulo III – Dos Direitos do Titular'."""
    m = re.match(r'CAPÍTULO\s+([IVXLC]+)\s*(.*)', raw)
    if not m:
        return raw
    words = [w.lower() if i and w.lower() in SMALL else w.capitalize() for i, w in enumerate(m.group(2).split())]
    return f"Capítulo {m.group(1)}" + (f" – {' '.join(words)}" if words else '')


def lgpd_clean(t):
    t = NOTE.sub('', t)
    t = re.sub(r'\s*\bVigência\s*$', '', t)
    return clean(t)


def parse_lgpd(path, arts):
    soup = BeautifulSoup(open(path, encoding='cp1252').read(), 'lxml')
    articles, chapter, current, scope, inciso = {}, '', None, None, None
    for p in soup.find_all('p'):
        for x in p.find_all(['strike', 's', 'del']):
            x.decompose()
        raw = clean(p.get_text(' '))
        if not raw:
            continue
        if raw.startswith('CAPÍTULO'):
            chapter, current = raw, None
            continue
        m = ART.match(raw)
        if m and not raw.startswith('“'):
            key = m.group(1) + (f'-{m.group(2)}' if m.group(2) else '')
            current = {'title': chapter_title(chapter), 'caput': lgpd_clean(raw[m.end():]), 'incisos': [], 'paragraphs': []}
            if key not in articles:  # the first, current version of the article
                articles[key] = current
            scope, inciso = current, None
            continue
        if current is None:
            continue
        m = PARA.match(raw)
        if m:
            scope = {'id': m.group(1) or 'único', 'text': lgpd_clean(raw[m.end():]) or '(Revogado)', 'incisos': []}
            current['paragraphs'].append(scope)
            inciso = None
            continue
        m = INCISO.match(raw)
        if m:
            inciso = {'id': m.group(1), 'text': lgpd_clean(raw[m.end():]) or '(Revogado)', 'alineas': []}
            scope['incisos'].append(inciso)
            continue
        m = ALINEA.match(raw)
        if m and inciso is not None:
            inciso['alineas'].append({'id': m.group(1), 'text': lgpd_clean(raw[m.end():]) or '(Revogado)'})
            continue
        if raw.startswith(('Seção', 'Subseção')) or NOTE.fullmatch(raw.strip()):
            continue
        current = None  # any other text closes the article
    out = {}
    for n in sorted(arts):
        a = articles[str(n)]
        for x in [a] + a['paragraphs']:
            for i in x['incisos']:
                if not i['alineas']:
                    del i['alineas']
        out[str(n)] = a
    return {'articles': out}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--workbook', required=True)
    ap.add_argument('--gdpr', required=True)
    ap.add_argument('--lgpd', required=True)
    ap.add_argument('--retrieved', required=True, help='date on which the pages were saved, e.g. "25 October 2026"')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    c = cited(args.workbook)
    data = {
        'gdpr': {'retrieved': args.retrieved, **parse_gdpr(args.gdpr, c['gdpr'], c['recitals'])},
        'lgpd': {'retrieved': args.retrieved, **parse_lgpd(args.lgpd, c['lgpd'])},
    }
    with open(args.out, 'w', encoding='utf-8') as f:
        f.write('// Generated by tools/build_legislation.py from the official texts of the GDPR (EUR-Lex)\n'
                '// and the LGPD (Planalto, consolidated text). Do not edit by hand.\n')
        f.write('window.DASHBOARD_LEGISLATION = ')
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write(';\n')
    print(f"GDPR: {len(data['gdpr']['articles'])} articles, {len(data['gdpr']['recitals'])} recitals; "
          f"LGPD: {len(data['lgpd']['articles'])} articles")


if __name__ == '__main__':
    main()
