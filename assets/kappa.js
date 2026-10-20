/*
 * Inter-rater reliability of the thematic analysis (Fleiss' kappa).
 *
 * Follows the method described in the article: each rater's cell is split into
 * labels, normalised, mapped through the "Equivalences" sheet, deduplicated and
 * sorted; the resulting combination is one nominal category. Kappa is computed
 * for every dimension and coding stage that has three rater columns, and
 * compared with Table 1 of the "Kappa_Fleiss" sheet where that sheet has a value.
 */
(function () {
  'use strict';

  const { table, findSheet, text } = window.DashboardData;

  const RATERS = [
    { id: 'r1', label: 'Researcher 1' },
    { id: 'gpt', label: 'OpenAI GPT' },
    { id: 'claude', label: 'Anthropic Claude' },
  ];
  /** Rater pairs, in the order used by the article's formula for Pi. */
  const PAIRS = [[0, 1], [0, 2], [1, 2]];

  /** Coding stages: sheet header label, key used in the Equivalences sheet, and the article's name. */
  const STAGES = [
    { key: 'InitialCodes', header: /^codes$/i, label: 'Initial Codes' },
    { key: 'Theme', header: /^theme$/i, label: 'Theme' },
    { key: 'FinalTheme', header: /^final theme$/i, label: 'Final Theme' },
    { key: 'HighLevelTheme', header: /^high-?level theme$/i, label: 'High-level Theme' },
  ];

  /** Dimensions: key used in the Equivalences and Kappa_Fleiss sheets, and the article's name. */
  const DIMENSIONS = [
    { key: 'Domain', sheet: /^domains$/i, label: 'Domain', inArticle: true },
    { key: 'SubDomain', sheet: /^sub-?domains$/i, label: 'Sub-domain' },
    { key: 'Purpose', sheet: /^purposes$/i, label: 'Purpose', inArticle: true },
    { key: 'Technology', sheet: /^technologies$/i, label: 'Technology', inArticle: true },
    { key: 'DigitalObject', sheet: /^digital objects$/i, label: 'Digital object', inArticle: true },
    { key: 'Architecture', sheet: /^architecture$/i, label: 'Architecture' },
  ];

  const stageOf = (label) => STAGES.find((s) => s.header.test(String(label).trim())) || null;
  const stageByKey = (key) => STAGES.find((s) => s.key.toLowerCase() === String(key).replace(/[\s-]/g, '').toLowerCase()
    || s.header.test(String(key).trim())) || null;
  const dimensionByKey = (key) => DIMENSIONS.find((d) => d.key.toLowerCase() === String(key).trim().toLowerCase()) || null;

  /** Landis and Koch (1977) benchmarks. */
  function interpret(k) {
    if (!Number.isFinite(k)) return '–';
    if (k < 0) return 'Poor';
    if (k <= 0.20) return 'Slight';
    if (k <= 0.40) return 'Fair';
    if (k <= 0.60) return 'Moderate';
    if (k <= 0.80) return 'Substantial';
    return 'Almost perfect';
  }

  // -------------------------------------------------------- normalisation

  /** Standardises one label: spaces, ligatures, apostrophes, en dashes, "&", case. */
  function normalise(s) {
    return String(s)
      .replace(/ |\t/g, ' ')
      .replace(/ﬁ/g, 'fi').replace(/ﬂ/g, 'fl')
      .replace(/[‘’]/g, "'")
      .replace(/–/g, '-')
      .replace(/&/g, 'and')
      .replace(/\s+/g, ' ')
      .trim()
      .toLowerCase();
  }

  /** Reads the "Equivalences" sheet: rules, the K1 switch and a look-up by scope. */
  function parseEquivalences(wb) {
    const ws = findSheet(wb, /^equivalences$/i);
    const out = { found: Boolean(ws), apply: true, rules: [], lookup: new Map() };
    if (!ws) return out;
    const all = XLSX.utils.sheet_to_json(ws, { header: 1, defval: null, raw: true, blankrows: true });
    const switchCol = (all[0] || []).findIndex((v) => /apply equivalences/i.test(text(v)));
    if (switchCol >= 0) out.apply = !/^no$/i.test(text(all[0][switchCol + 1]) || 'Yes');
    const h = all.findIndex((r) => r && /^active$/i.test(text(r[0])));
    if (h < 0) return out;
    const header = all[h].map(text);
    const col = (re) => header.findIndex((x) => re.test(x));
    const c = {
      active: 0, dimension: col(/^dimension$/i), stage: col(/^stage$/i), original: col(/^original/i),
      canonical: col(/^canonical term$/i), type: col(/^type$/i), confidence: col(/^confidence$/i), note: col(/^note$/i),
    };
    all.slice(h + 1).forEach((r, i) => {
      if (!r || !text(r[c.original])) return;
      const rule = {
        row: h + i + 2,
        active: /^yes$/i.test(text(r[c.active])),
        dimension: text(r[c.dimension]) || 'ALL',
        stage: text(r[c.stage]) || 'ALL',
        original: text(r[c.original]),
        canonical: text(r[c.canonical]),
        type: text(r[c.type]),
        confidence: text(r[c.confidence]),
        note: text(r[c.note]),
      };
      rule.key = `${rule.dimension}|${rule.stage}|${normalise(rule.original)}`;
      out.rules.push(rule);
      if (rule.active) out.lookup.set(rule.key, rule); // a later rule with the same scope and term wins
    });
    return out;
  }

  /** Finds the rule for a normalised label, most specific scope first. */
  function findRule(eq, dim, stage, label) {
    if (!eq.apply) return null;
    for (const [d, s] of [[dim, stage], [dim, 'ALL'], ['ALL', stage], ['ALL', 'ALL']]) {
      const rule = eq.lookup.get(`${d}|${s}|${label}`);
      if (rule) return rule;
    }
    return null;
  }

  /**
   * Splits one cell into labels and builds its normalised combination.
   * `segments` keeps the original text, separators included, so the cell can be
   * shown as written with each label marked.
   */
  function parseCell(value, dim, stage, eq) {
    const raw = value === null || value === undefined ? '' : String(value);
    const segments = [];
    const items = new Set();
    raw.replace(/\r\n?/g, '\n').split(/([\n,;])/).forEach((part, i) => {
      if (i % 2 === 1) { segments.push({ text: part, separator: true }); return; }
      const norm = normalise(part);
      if (!norm) { segments.push({ text: part, separator: true }); return; }
      const rule = findRule(eq, dim, stage, norm);
      const canonical = rule ? normalise(rule.canonical) : norm;
      items.add(canonical);
      segments.push({ text: part, norm, canonical, rule });
    });
    const sorted = [...items].sort(); // code-point order, as in the spreadsheet's SORT
    return { raw, segments, items: sorted, combination: sorted.join(', ') };
  }

  // ---------------------------------------------------------------- kappa

  /** Computes Fleiss' kappa for one dimension and stage of a thematic analysis sheet. */
  function computeCombination(sheet, field, dim, stage, eq) {
    const cols = RATERS.map((r) => (field.cols[r.id] || [])[0]);
    const perStudy = new Map();
    const counts = new Map();
    let n = 0;
    let sumPi = 0;
    let rawFull = 0;
    const pairHits = [0, 0, 0];
    sheet.rows.forEach((r) => {
      const cells = cols.map((c) => parseCell(r.row[c.index], dim.key, stage.key, eq));
      const included = cells.every((c) => c.combination);
      const entry = { cells, included };
      if (included) {
        entry.pairs = PAIRS.map(([a, b]) => cells[a].combination === cells[b].combination);
        entry.rawPairs = PAIRS.map(([a, b]) => cells[a].raw === cells[b].raw);
        entry.pi = entry.pairs.filter(Boolean).length / 3;
        entry.pairs.forEach((hit, i) => { if (hit) pairHits[i]++; });
        if (entry.rawPairs.every(Boolean)) rawFull++;
        cells.forEach((c) => counts.set(c.combination, (counts.get(c.combination) || 0) + 1));
        sumPi += entry.pi;
        n++;
      }
      perStudy.set(r.study.id, entry);
    });
    const po = n ? sumPi / n : NaN;
    const pe = n ? [...counts.values()].reduce((acc, v) => acc + (v / (3 * n)) ** 2, 0) : NaN;
    const kappa = pe === 1 ? 1 : (po - pe) / (1 - pe); // reported as 1 when every rating falls in one category
    const normFull = [...perStudy.values()].filter((e) => e.included && e.pi === 1).length;
    return {
      id: `${dim.key}|${stage.key}`,
      dim, stage, sheet, field,
      n, po, pe, kappa,
      interpretation: interpret(kappa),
      rawFull, normFull, recovered: normFull - rawFull,
      pairRates: pairHits.map((h) => (n ? h / n : NaN)),
      counts, perStudy,
      inArticle: Boolean(dim.inArticle),
    };
  }

  /** Reads Table 1 of the "Kappa_Fleiss" sheet, keyed like the computed combinations. */
  function parseKappaSheet(wb) {
    const ws = findSheet(wb, /^kappa[_\s]*fleiss$/i);
    const out = new Map();
    if (!ws) return out;
    const all = XLSX.utils.sheet_to_json(ws, { header: 1, defval: null, raw: true, blankrows: true });
    const h = all.findIndex((r) => r && /^dimension$/i.test(text(r[0])) && /^stage$/i.test(text(r[1])));
    if (h < 0) return out;
    const header = all[h].map(text);
    const col = (re) => header.findIndex((x) => re.test(x));
    const iK = col(/kappa/i);
    const iPo = col(/observed/i);
    const iPe = col(/expected/i);
    for (const r of all.slice(h + 1)) {
      if (!r || !text(r[0])) break;
      const dim = dimensionByKey(r[0]);
      const stage = stageByKey(text(r[1]) === 'Codes' ? 'InitialCodes' : r[1]);
      if (!dim || !stage) continue;
      out.set(`${dim.key}|${stage.key}`, { kappa: Number(r[iK]), po: Number(r[iPo]), pe: Number(r[iPe]) });
    }
    return out;
  }

  /** Builds every combination from the thematic analysis sheets already parsed by data.js. */
  function build(wb, taSheets) {
    const eq = parseEquivalences(wb);
    const reference = parseKappaSheet(wb);
    const combinations = [];
    DIMENSIONS.forEach((dim) => {
      const sheet = taSheets.find((s) => dim.sheet.test(s.sheetName));
      if (!sheet) return;
      sheet.kappaDim = dim;
      STAGES.forEach((stage) => {
        const field = sheet.stages.find((f) => stage.header.test(f.label) && RATERS.every((r) => (f.cols[r.id] || []).length));
        if (!field) return;
        const combo = computeCombination(sheet, field, dim, stage, eq);
        combo.reference = reference.get(combo.id) || null;
        combo.matchesReference = combo.reference ? Math.abs(combo.reference.kappa - combo.kappa) < 1e-9 : null;
        if (combo.matchesReference === false) {
          console.warn(`Fleiss' kappa for ${dim.label} · ${stage.label} is ${combo.kappa}, but the Kappa_Fleiss sheet reports ${combo.reference.kappa}.`);
        }
        field.kappa = combo;
        combinations.push(combo);
      });
    });
    return {
      equivalences: eq,
      referenceFound: reference.size > 0,
      combinations,
      get: (id) => combinations.find((c) => c.id === id) || null,
    };
  }

  window.DashboardKappa = { RATERS, PAIRS, STAGES, DIMENSIONS, interpret, normalise, parseCell, build, stageOf, dimensionByKey, stageByKey };
})();
