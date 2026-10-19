/*
 * Reads the DEF/TA workbook and turns it into the model used by the dashboard.
 *
 * Nothing here is hard-coded to the current figures: categories, studies and
 * counts are all derived from the workbook, so replacing data/DEF_TA.xlsx is
 * enough to update every view. Sheet and column names are matched loosely
 * because some headers carry spelling variants (e.g. "Ryyan ID", "Titlle").
 */
(function () {
  'use strict';

  /** The three coders whose output is recorded side by side. */
  const SOURCES = [
    { id: 'r1', label: 'Researcher 1', pattern: /researcher\s*1/i },
    { id: 'gpt', label: 'AI tool: OpenAI GPT', pattern: /openai|gpt/i },
    { id: 'claude', label: 'AI tool: Anthropic Claude', pattern: /anthropic|claude/i },
  ];

  /**
   * Dimensions of the thematic analysis that can be counted, charted and
   * crossed in heatmaps. `column` is the column in the "Thematic Analysis"
   * sheet; `summary` is the RQ summary sheet that lists the category names.
   */
  const DIMENSIONS = [
    { id: 'objects', label: 'Digital objects', column: /^digital\s*objects?$/i, summary: /^RQ1\b/i },
    { id: 'technologies', label: 'Technologies', column: /^technolog/i, summary: /^RQ2\b/i },
    { id: 'purposes', label: 'Purposes', column: /^purposes?$/i, summary: /^RQ3\b/i },
    { id: 'domains', label: 'Domains', column: /^domains?$/i, summary: /^RQ4\b/i },
    { id: 'approaches', label: 'Approach groups' },
    { id: 'architecture', label: 'Architecture type', column: /^architecture/i, single: true },
    { id: 'source', label: 'Selection source', single: true, chartOnly: true },
  ];

  /** Per-dimension sheets with the coding of each rater, shown in the thematic analysis tab. */
  const TA_SHEETS = [
    { label: 'Domains', sheet: /^domains$/i },
    { label: 'Sub-domains', sheet: /^sub-?domains$/i },
    { label: 'Purposes', sheet: /^purposes$/i },
    { label: 'Technologies', sheet: /^technologies$/i },
    { label: 'Digital objects', sheet: /^digital objects$/i },
    { label: 'Architecture', sheet: /^architecture$/i },
  ];

  const ID_COLUMNS = /^(article id|r[a]?y+an id|pap+er( id)?|doi|tit+le|year|dataset)$/i;

  // ---------------------------------------------------------------- helpers

  function findSheet(wb, pattern) {
    const name = wb.SheetNames.find((n) => pattern.test(n.trim()));
    return name ? wb.Sheets[name] : null;
  }

  /** Returns the sheet as { header: string[], rows: any[][] }, skipping empty rows. */
  function table(ws) {
    if (!ws) return { header: [], rows: [] };
    const all = XLSX.utils.sheet_to_json(ws, { header: 1, defval: null, raw: true, blankrows: false });
    const header = (all[0] || []).map((h) => (h == null ? '' : String(h).trim()));
    const rows = all.slice(1).filter((r) => r.some((v) => v !== null && String(v).trim() !== ''));
    return { header, rows };
  }

  function colIndex(header, ...patterns) {
    for (const p of patterns) {
      const i = header.findIndex((h) => p.test(h));
      if (i >= 0) return i;
    }
    return -1;
  }

  function text(v) {
    if (v === null || v === undefined) return '';
    if (typeof v === 'boolean') return v ? 'True' : 'False';
    return String(v).trim();
  }

  /** Rayyan IDs identify a study across all sheets. */
  function rayyanIndex(header) {
    return colIndex(header, /^r[a]?y+an id$/i);
  }

  /**
   * Splits a cell such as "Access Control, Data Traceability" into category
   * names. Known names are matched first (longest first), because some of
   * them contain commas, e.g. "Legal, Compliance & Digital Forensics".
   * Anything left over is kept as its own category so no coding is lost.
   */
  function splitCategories(value, vocabulary) {
    let rest = text(value);
    if (!rest || rest === '0') return [];
    const found = [];
    const sorted = [...vocabulary].sort((a, b) => b.length - a.length);
    for (const name of sorted) {
      const re = new RegExp(name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i');
      if (re.test(rest)) {
        found.push(name);
        rest = rest.replace(new RegExp(re.source, 'gi'), ' ');
      }
    }
    rest.split(/[,;\n]+/).map((s) => s.trim()).filter((s) => s && s !== '0').forEach((s) => {
      console.warn('Category not listed in the summary sheet:', s);
      found.push(s);
    });
    return found;
  }

  /** Reads the category names listed in the first column of an RQ summary sheet. */
  function summaryCategories(ws) {
    const { rows } = table(ws);
    const out = [];
    for (const r of rows) {
      const name = text(r[0]);
      const n = Number(r[1]);
      if (!name) break;
      if (Number.isFinite(n)) out.push(name);
    }
    return out;
  }

  function sourceLabel(dataset) {
    const s = text(dataset);
    if (!s || s === '0') return 'Seed set (Scopus)';
    if (/backward/i.test(s)) return 'Backward snowballing';
    if (/forward/i.test(s)) return 'Forward snowballing';
    return s;
  }

  /**
   * Groups columns named "<field> (<coder>)" into fields with one entry per
   * coder. GPT columns named "C1 - Value" and "C1 - Justification" are joined
   * to field "C1". Columns without a coder (other than identifiers) are kept as
   * "extra" columns, e.g. the final decision.
   */
  function groupColumns(header) {
    const fields = [];
    const byName = new Map();
    const extras = [];
    header.forEach((h, i) => {
      if (!h) return;
      const m = h.match(/^(.*?)\s*\(([^()]*)\)\s*$/);
      const source = m && SOURCES.find((s) => s.pattern.test(m[2]));
      if (source) {
        let base = m[1].trim();
        let part = '';
        const sub = base.match(/^(.*?)\s+-\s+(value|justification)$/i);
        if (sub) { base = sub[1].trim(); part = sub[2][0].toUpperCase() + sub[2].slice(1).toLowerCase(); }
        let f = byName.get(base.toLowerCase());
        if (!f) {
          f = { label: base, cols: { r1: [], gpt: [], claude: [] } };
          byName.set(base.toLowerCase(), f);
          fields.push(f);
        }
        f.cols[source.id].push({ index: i, part });
      } else if (!ID_COLUMNS.test(h)) {
        const f = byName.get(h.toLowerCase());
        if (f) f.final = i; // e.g. "Architecture Type" next to its per-coder columns
        else extras.push({ label: h, index: i });
      }
    });
    return { fields, extras };
  }

  /** Joins the cells of one coder for a field (value and justification, if both exist). */
  function cellFor(row, cols) {
    return cols
      .map((c) => ({ part: c.part, value: text(row[c.index]) }))
      .filter((c) => c.value)
      .map((c) => (c.part && cols.length > 1 ? `${c.part}: ${c.value}` : c.value))
      .join('\n\n');
  }

  // ------------------------------------------------------------------ parse

  function parseWorkbook(wb) {
    const warnings = [];
    const ta = table(findSheet(wb, /^thematic analysis$/i));
    const de = table(findSheet(wb, /^data extraction$/i));
    if (!ta.rows.length) throw new Error('The sheet "Thematic Analysis" was not found or is empty.');
    if (!de.rows.length) throw new Error('The sheet "Data Extraction" was not found or is empty.');

    // Studies, keyed by Rayyan ID.
    const taId = rayyanIndex(ta.header);
    const deId = rayyanIndex(de.header);
    const deById = new Map(de.rows.map((r) => [text(r[deId]), r]));
    const iPaper = colIndex(ta.header, /^pap+er id$/i);
    const iArticle = colIndex(ta.header, /^article id$/i);
    const iTitleTA = colIndex(ta.header, /^tit+le$/i);
    const iYear = colIndex(de.header, /^year$/i);
    const iDoi = colIndex(de.header, /^doi$/i);
    const iTitle = colIndex(de.header, /^tit+le$/i);
    const iDataset = colIndex(de.header, /^dataset$/i);

    const studies = [];
    for (const r of ta.rows) {
      const id = text(r[taId]);
      if (!id) continue;
      const d = deById.get(id) || [];
      const year = parseInt(text(d[iYear]), 10);
      studies.push({
        id,
        paperId: text(r[iPaper]),
        articleId: text(r[iArticle]),
        title: text(d[iTitle]) || text(r[iTitleTA]),
        year: Number.isFinite(year) ? year : null,
        doi: text(d[iDoi]).replace(/^-$/, ''),
        source: sourceLabel(d[iDataset]),
        cats: {},
        taRow: r,
        deRow: d,
      });
      if (!deById.has(id)) warnings.push(`${id} is in "Thematic Analysis" but not in "Data Extraction".`);
    }
    studies.sort((a, b) => a.paperId.localeCompare(b.paperId, 'en', { numeric: true }));
    const byId = new Map(studies.map((s) => [s.id, s]));

    // Dimensions and their categories.
    const dimensions = [];
    for (const def of DIMENSIONS) {
      const dim = { ...def, categories: [] };
      if (def.id === 'approaches') {
        parseApproaches(wb, dim, byId);
      } else if (def.id === 'source') {
        studies.forEach((s) => { s.cats.source = [s.source]; });
      } else {
        const col = colIndex(ta.header, def.column);
        if (col < 0) { warnings.push(`Column for ${def.label} not found in "Thematic Analysis".`); continue; }
        const vocabulary = def.summary ? summaryCategories(findSheet(wb, def.summary)) : [];
        dim.order = vocabulary;
        studies.forEach((s) => {
          s.cats[def.id] = def.single ? [text(s.taRow[col])].filter(Boolean) : splitCategories(s.taRow[col], vocabulary);
        });
      }
      // Category list sorted by frequency, as in the article's tables.
      const counts = new Map();
      studies.forEach((s) => (s.cats[dim.id] || []).forEach((c) => counts.set(c, (counts.get(c) || 0) + 1)));
      dim.categories = [...counts.keys()].map((name) => ({
        id: name,
        label: (dim.labels && dim.labels.get(name)) || name,
        count: counts.get(name),
      })).sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
      dimensions.push(dim);
    }

    // Data extraction form fields.
    const defColumns = groupColumns(de.header);
    const def = {
      fields: defColumns.fields,
      rows: studies.map((s) => ({ study: s, row: s.deRow })),
    };

    // Per-dimension thematic analysis sheets.
    const taSheets = [];
    for (const t of TA_SHEETS) {
      const sh = table(findSheet(wb, t.sheet));
      if (!sh.rows.length) continue;
      const idx = rayyanIndex(sh.header);
      const grouped = groupColumns(sh.header);
      const rows = sh.rows
        .map((r) => ({ study: byId.get(text(r[idx])), row: r }))
        .filter((r) => r.study)
        .sort((a, b) => a.study.paperId.localeCompare(b.study.paperId, 'en', { numeric: true }));
      taSheets.push({ label: t.label, stages: grouped.fields, extras: grouped.extras, rows });
    }

    // Number of unique records retrieved (sheet "Data Set").
    const dataSet = table(findSheet(wb, /^data set$/i));

    return {
      studies,
      byId,
      dimensions,
      dimension: (id) => dimensions.find((d) => d.id === id),
      def,
      taSheets,
      records: dataSet.rows.length,
      warnings,
    };
  }

  /** Approach groups (RQ5): assignments in "ApproachesAnalyses", names in "RQ5. Approaches". */
  function parseApproaches(wb, dim, byId) {
    const names = new Map();
    const rq5 = table(findSheet(wb, /^RQ5\b/i));
    const iCode = colIndex(rq5.header, /approach/i);
    const iDesc = colIndex(rq5.header, /description/i);
    rq5.rows.forEach((r) => {
      const code = text(r[iCode]);
      if (/^AC-\d+$/i.test(code)) names.set(code.toUpperCase(), text(r[iDesc]));
    });
    dim.labels = new Map([...names].map(([code, desc]) => [code, desc ? `${code} ${desc}` : code]));
    const aa = table(findSheet(wb, /^approaches\s*analys/i));
    const idx = rayyanIndex(aa.header);
    const iCluster = colIndex(aa.header, /cluster|approach/i);
    byId.forEach((s) => { s.cats.approaches = []; });
    aa.rows.forEach((r) => {
      const s = byId.get(text(r[idx]));
      if (!s) return;
      s.cats.approaches = (text(r[iCluster]).toUpperCase().match(/AC-\d+/g) || []);
    });
  }

  window.DashboardData = { SOURCES, parseWorkbook, cellFor, text };
})();
