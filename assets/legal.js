/* Parses the legal provisions cited in the "Data Protection Requirements" sheet and finds
   their text in data/legislation.js (excerpts of the GDPR and the LGPD).

   A cell holds items separated by "; ", each "<provisions>: <summary>", for example
   "Art. 5(1)(f): protection against unauthorised processing" (GDPR) or
   "Art. 18, §§3–5: express request, reasoned response" (LGPD). */
(function () {
  'use strict';

  const SOURCES = {
    gdpr: {
      name: 'GDPR',
      title: 'Regulation (EU) 2016/679 (General Data Protection Regulation)',
      url: 'https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0679',
      anchor: (p) => (p.recital ? `#rct_${p.recital}` : `#art_${p.art}`),
    },
    lgpd: {
      name: 'LGPD',
      title: 'Lei nº 13.709, de 14 de agosto de 2018 (Lei Geral de Proteção de Dados Pessoais)',
      url: 'https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm',
      anchor: (p) => `#art${p.art}`,
    },
  };

  const ROMAN = /^[IVXLC]+$/;
  const DASH = /\s*[–—-]+\s*/;

  function romanValue(s) {
    const v = { I: 1, V: 5, X: 10, L: 50, C: 100 };
    let total = 0;
    for (let i = 0; i < s.length; i++) {
      const a = v[s[i]];
      const b = v[s[i + 1]] || 0;
      total += a < b ? -a : a;
    }
    return total;
  }

  function toRoman(n) {
    const map = [[100, 'C'], [90, 'XC'], [50, 'L'], [40, 'XL'], [10, 'X'], [9, 'IX'], [5, 'V'], [4, 'IV'], [1, 'I']];
    let out = '';
    map.forEach(([v, r]) => { while (n >= v) { out += r; n -= v; } });
    return out;
  }

  /** "a–c" → [a, b, c]; "1–3" → [1, 2, 3]; "VII–VIII" → [VII, VIII]. */
  function expand(token) {
    const [a, b] = token.split(DASH);
    if (b === undefined) return [a];
    if (/^\d+$/.test(a) && /^\d+$/.test(b)) return range(+a, +b).map(String);
    if (ROMAN.test(a) && ROMAN.test(b)) return range(romanValue(a), romanValue(b)).map(toRoman);
    if (/^[a-z]$/.test(a) && /^[a-z]$/.test(b)) return range(a.charCodeAt(0), b.charCodeAt(0)).map((c) => String.fromCharCode(c));
    return [a, b];
  }

  function range(a, b) {
    const out = [];
    for (let i = a; i <= b; i++) out.push(i);
    return out;
  }

  /** Splits "x, y and z" into its parts. */
  const parts = (s) => s.split(/\s*,\s*|\s+and\s+/).map((x) => x.trim()).filter(Boolean);

  /** GDPR: "29 and 32(4)", "15–21", "32(1)(a)–(c)", "25(1)–(2)". */
  function parseGDPRBody(body) {
    const out = [];
    parts(body).forEach((p) => {
      const m = p.match(/^(\d+)(?:\s*[–—-]+\s*(\d+))?((?:\([0-9a-z]+\))*)(?:\s*[–—-]+\s*((?:\([0-9a-z]+\))+))?$/);
      if (!m) return;
      const arts = m[2] ? range(+m[1], +m[2]) : [+m[1]];
      const subs = [...m[3].matchAll(/\(([0-9a-z]+)\)/g)].map((x) => x[1]);
      let options = subs.map((s) => [s]);
      if (m[4]) {
        const end = [...m[4].matchAll(/\(([0-9a-z]+)\)/g)].map((x) => x[1]);
        // The range applies to the last subdivision: (1)(a)–(c) or (1)–(2).
        const last = options.length - 1;
        options[last] = expand(`${subs[last]}–${end[end.length - 1]}`);
      }
      arts.forEach((art) => {
        if (!options.length) { out.push({ law: 'gdpr', art }); return; }
        const paras = options[0];
        const points = options[1] || [null];
        paras.forEach((para) => points.forEach((point) => {
          // A letter directly after the article number is a point of an article without paragraphs.
          if (/^[a-z]$/.test(para)) out.push({ law: 'gdpr', art, point: para });
          else out.push({ law: 'gdpr', art, para, point: point || undefined });
        }));
      });
    });
    return out;
  }

  /** LGPD: "6, VII–VIII", "14, §§1 and 5", "18, I, II and V", "50, §2, I(h)", "33–36". */
  function parseLGPDBody(body) {
    const out = [];
    const tokens = parts(body);
    if (!tokens.length) return out;
    const arts = expand(tokens[0]).map(Number);
    let para = null;
    let inParas = false;
    let added = false;
    tokens.slice(1).forEach((tok) => {
      const sec = tok.match(/^(§§?)\s*(.+)$/);
      if (sec) {
        inParas = sec[1] === '§§';
        const list = expand(sec[2].replace(/\s+/g, ''));
        para = list[list.length - 1];
        list.forEach((p) => arts.forEach((art) => out.push({ law: 'lgpd', art, para: p })));
        added = true;
        return;
      }
      if (inParas && /^\d+$/.test(tok)) {
        arts.forEach((art) => out.push({ law: 'lgpd', art, para: tok }));
        return;
      }
      const inc = tok.match(/^([IVXLC]+(?:\s*[–—-]+\s*[IVXLC]+)?)(?:\(([a-z])\))?$/);
      if (!inc) return;
      // An inciso after a single paragraph belongs to it ("§2, I(h)"), so the paragraph entry is replaced.
      const owner = inParas ? undefined : para || undefined;
      const last = out[out.length - 1];
      if (owner && last && last.para === owner && !last.inciso) out.pop();
      expand(inc[1].replace(/\s+/g, '')).forEach((roman) => arts.forEach((art) => out.push({
        law: 'lgpd', art, para: owner, inciso: roman, alinea: inc[2] || undefined,
      })));
      added = true;
    });
    if (!added) arts.forEach((art) => out.push({ law: 'lgpd', art }));
    return out;
  }

  /** "Art. 8, §5 and Art. 18, IX" → ["Art. 8, §5", "Art. 18, IX"]. */
  function splitArticles(ref) {
    return ref.split(/\s+and\s+(?=(?:Arts?\.|Recitals?)\s)/).map((s) => s.trim()).filter(Boolean);
  }

  function parseReference(ref, law) {
    const out = [];
    splitArticles(ref).forEach((chunk) => {
      const rec = chunk.match(/^Recitals?\s+(.+)$/);
      if (rec) { parts(rec[1]).forEach((p) => expand(p).forEach((n) => out.push({ law, recital: +n }))); return; }
      const art = chunk.match(/^Arts?\.\s*(.+)$/);
      if (!art) return;
      out.push(...(law === 'gdpr' ? parseGDPRBody(art[1]) : parseLGPDBody(art[1])));
    });
    return out;
  }

  /** One sheet cell → [{ ref, summary, provisions }]. */
  function parseCell(value, law) {
    return String(value || '').replace(/\.\s*$/, '').split(/;\s+/).map((item) => {
      const i = item.indexOf(': ');
      const ref = (i >= 0 ? item.slice(0, i) : item).replace(/^\(partial\)\s*/i, '').trim();
      const summary = i >= 0 ? item.slice(i + 2).trim() : '';
      return { ref, summary, provisions: parseReference(ref, law) };
    }).filter((x) => x.ref);
  }

  function label(p) {
    if (p.recital) return `Recital ${p.recital}`;
    if (p.law === 'gdpr') return `Art. ${p.art}${p.para ? `(${p.para})` : ''}${p.point ? `(${p.point})` : ''}`;
    return `Art. ${p.art}${p.para ? `, § ${p.para}` : ''}${p.inciso ? `, ${p.inciso}` : ''}${p.alinea ? `, ${p.alinea}` : ''}`;
  }

  function link(p) {
    const s = SOURCES[p.law];
    return s.url + s.anchor(p);
  }

  /**
   * Text of a provision from data/legislation.js, or null when it is not there.
   * Returns { heading, lead, text } where lead is the enclosing text of a point or inciso
   * (for example, the opening words of the paragraph that lists it).
   */
  function excerpt(p) {
    const lib = window.DASHBOARD_LEGISLATION;
    const law = lib && lib[p.law];
    if (!law) return null;
    if (p.recital) {
      const r = law.recitals && law.recitals[p.recital];
      return r ? { heading: `Recital ${p.recital}`, blocks: [{ text: r }] } : null;
    }
    const a = law.articles && law.articles[p.art];
    if (!a) return null;
    const heading = `${p.law === 'gdpr' ? 'Article' : 'Art.'} ${p.art}${a.title ? ` · ${a.title}` : ''}`;
    if (p.law === 'gdpr') return { heading, blocks: gdprBlocks(a, p) };
    return { heading, blocks: lgpdBlocks(a, p) };
  }

  function gdprBlocks(a, p) {
    const paras = a.paragraphs || [];
    const para = p.para ? paras.find((x) => String(x.num) === String(p.para)) : null;
    if (p.para && !para) return null;
    const scope = para || (p.point ? paras[0] : null);
    if (!scope) return paras.map(blockOf);
    if (!p.point) return [blockOf(scope)];
    const point = (scope.points || []).find((x) => x.id === p.point);
    if (!point) return null;
    return [{ num: scope.num, text: scope.text, points: [point] }];
  }

  function lgpdBlocks(a, p) {
    let scope = { text: a.caput, incisos: a.incisos || [] };
    let num = null;
    if (p.para) {
      const para = (a.paragraphs || []).find((x) => String(x.id) === String(p.para));
      if (!para) return null;
      scope = para;
      num = para.id === 'único' ? 'Parágrafo único' : `§ ${para.id}º`;
    }
    if (!p.inciso) {
      if (p.para) return [{ num, text: scope.text, points: scope.incisos || [] }];
      return [{ text: a.caput, points: a.incisos || [] }, ...(a.paragraphs || []).map((x) => ({
        num: x.id === 'único' ? 'Parágrafo único' : `§ ${x.id}º`, text: x.text, points: x.incisos || [],
      }))];
    }
    const inc = (scope.incisos || []).find((x) => x.id === p.inciso);
    if (!inc) return null;
    const item = p.alinea ? { id: inc.id, text: inc.text, points: (inc.alineas || []).filter((x) => x.id === p.alinea) } : inc;
    return [{ num, text: scope.text, points: [item] }];
  }

  function blockOf(x) {
    return { num: x.num, text: x.text, points: x.points || [] };
  }

  window.DashboardLegal = { SOURCES, parseCell, parseReference, label, link, excerpt };
})();
