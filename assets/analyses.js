/*
 * RQ5 classification, technology readiness assessment and study selection.
 *
 * RQ5: each study is assigned to every approach group whose attribution rule it satisfies
 * ("RQ5 Rules"), using its final codes of technologies, purposes and digital objects and the
 * technical terms ("RQ5 Terms") found in the data extraction form. The result is compared with
 * the "RQ5 Classification" sheet.
 * TRA: the TRL of each solution is read from "TRA Solutions"; the tables by technology,
 * approach group and period are derived from it and compared with the "TRL ..." sheets.
 * Selection: the records of each search come from "Data Set"; the figures of each stage that
 * the spreadsheet does not record come from data/article.js.
 */
(function () {
  'use strict';

  const { table, findSheet, text, colIndex } = window.DashboardData;

  const list = (v) => text(v).split(/\s*;\s*/).filter(Boolean);
  const groupCodes = (v) => [...new Set(text(v).toUpperCase().match(/AC-\d+/g) || [])];

  // ----------------------------------------------------------------- RQ5

  /** Condition kinds of a clause: column of the rules sheet, study field and how it is tested. */
  const CONDITIONS = [
    { key: 'technologiesAll', header: /^technologies \(all of\)$/i, field: 'technologies', mode: 'all', label: 'Technology', plural: 'Technologies' },
    { key: 'technologiesAny', header: /^technologies \(any of\)$/i, field: 'technologies', mode: 'any', label: 'Technology', plural: 'Technologies' },
    { key: 'purposesAny', header: /^purposes \(any of\)$/i, field: 'purposes', mode: 'any', label: 'Purpose', plural: 'Purposes' },
    { key: 'objectsAny', header: /^digital objects \(any of\)$/i, field: 'objects', mode: 'any', label: 'Digital object', plural: 'Digital objects' },
    { key: 'termsAny', header: /^technical terms \(any of\)$/i, field: 'terms', mode: 'any', label: 'Technical term', plural: 'Technical terms' },
  ];

  function parseRules(wb) {
    const t = table(findSheet(wb, /^RQ5 rules$/i));
    if (!t.rows.length) return null;
    const h = t.header;
    const c = {
      code: colIndex(h, /^code$/i), name: colIndex(h, /^approach group$/i), definition: colIndex(h, /^definition$/i),
      rule: colIndex(h, /^attribution rule$/i),
    };
    const groups = [];
    t.rows.forEach((r) => {
      const code = text(r[c.code]).toUpperCase();
      if (!/^AC-\d+$/.test(code)) return;
      let g = groups.find((x) => x.code === code);
      if (!g) {
        g = { code, name: text(r[c.name]), definition: text(r[c.definition]), rule: text(r[c.rule]), clauses: [] };
        groups.push(g);
      }
      const clause = {};
      CONDITIONS.forEach((k) => {
        const i = colIndex(h, k.header);
        const values = i >= 0 ? list(r[i]) : [];
        if (values.length) clause[k.key] = values;
      });
      g.clauses.push(clause);
    });
    return groups;
  }

  function parseTerms(wb) {
    const t = table(findSheet(wb, /^RQ5 terms$/i));
    const h = t.header;
    const iTerm = colIndex(h, /^technical term$/i);
    const iPattern = colIndex(h, /^pattern/i);
    const iAlso = colIndex(h, /^also requires$/i);
    const iFields = colIndex(h, /^fields searched$/i);
    return t.rows.filter((r) => text(r[iTerm])).map((r) => ({
      term: text(r[iTerm]),
      pattern: text(r[iPattern]),
      re: new RegExp(text(r[iPattern]), 'i'),
      also: text(r[iAlso]) ? new RegExp(text(r[iAlso]), 'i') : null,
      fields: list(r[iFields]),
    }));
  }

  /** Technical terms found in a study, with the DEF fields in which each was found. */
  function findTerms(study, terms, deHeader) {
    const found = [];
    terms.forEach((t) => {
      const values = t.fields.map((f) => ({ field: f, value: text(study.deRow[deHeader.indexOf(f)]) }));
      let fields = values.filter((v) => t.re.test(v.value) && (!t.also || t.also.test(v.value))).map((v) => v.field);
      if (!fields.length && t.also) {
        // The term and the word it requires may sit in different fields of the same study.
        const joined = values.map((v) => v.value).join(' ');
        if (t.re.test(joined) && t.also.test(joined)) fields = values.filter((v) => t.re.test(v.value)).map((v) => v.field);
      }
      if (fields.length) found.push({ term: t.term, fields });
    });
    return found;
  }

  /** Tests every clause of a group against a study; the group applies when any clause holds. */
  function checkGroup(group, have) {
    const clauses = group.clauses.map((clause) => {
      const conditions = CONDITIONS.filter((k) => clause[k.key]).map((k) => {
        const need = clause[k.key];
        const hit = need.filter((x) => have[k.field].includes(x));
        return { ...k, need, hit, ok: k.mode === 'all' ? hit.length === need.length : hit.length > 0 };
      });
      return { conditions, ok: conditions.every((x) => x.ok) };
    });
    return { met: clauses.some((c) => c.ok), clauses };
  }

  function buildRQ5(wb, model) {
    const groups = parseRules(wb);
    if (!groups) return null;
    const terms = parseTerms(wb);
    const cls = table(findSheet(wb, /^RQ5 classification$/i));
    const h = cls.header;
    const iId = colIndex(h, /^r[a]?y+an id$/i);
    const iPrev = colIndex(h, /^previous approach groups$/i);
    const iChanged = colIndex(h, /^changed$/i);
    const sheet = new Map(cls.rows.map((r) => [text(r[iId]), r]));

    const perStudy = new Map();
    let matches = 0;
    model.studies.forEach((s) => {
      const found = findTerms(s, terms, model.deHeader);
      const have = {
        technologies: s.cats.technologies || [], purposes: s.cats.purposes || [], objects: s.cats.objects || [],
        terms: found.map((t) => t.term),
      };
      const checks = new Map(groups.map((g) => [g.code, checkGroup(g, have)]));
      const codes = groups.filter((g) => checks.get(g.code).met).map((g) => g.code);
      const row = sheet.get(s.id);
      const reference = row ? groupCodes(row[h.findIndex((x) => /^approach groups$/i.test(x))]) : null;
      const same = reference && [...reference].sort().join() === [...codes].sort().join();
      if (same) matches++;
      perStudy.set(s.id, {
        terms: found, have, checks, groups: codes, reference, matches: Boolean(same),
        previous: row && iPrev >= 0 ? groupCodes(row[iPrev]) : null,
        changed: row && iChanged >= 0 ? /^yes$/i.test(text(row[iChanged])) : false,
      });
    });

    const of = (pred) => model.studies.filter((s) => pred(perStudy.get(s.id).groups, s));
    const dominant = groups.slice().sort((a, b) => of((g) => g.includes(b.code)).length - of((g) => g.includes(a.code)).length)
      .slice(0, 3).map((g) => g.code);
    const combos = new Map();
    model.studies.forEach((s) => {
      const key = perStudy.get(s.id).groups.join(', ');
      if (!combos.has(key)) combos.set(key, []);
      combos.get(key).push(s);
    });
    return {
      groups, terms, perStudy, dominant,
      termFields: terms.length ? terms[0].fields : [],
      matches, checked: sheet.size,
      combinations: [...combos].map(([key, studies]) => ({ key, size: key ? key.split(', ').length : 0, studies }))
        .sort((a, b) => b.studies.length - a.studies.length || a.key.localeCompare(b.key)),
      sets: {
        multi: of((g) => g.length >= 2),
        single: of((g) => g.length === 1),
        none: of((g) => g.length === 0),
        anyDominant: of((g) => g.some((c) => dominant.includes(c))),
        onlyDominant: of((g) => g.length > 0 && g.every((c) => dominant.includes(c))),
        exactDominant: of((g) => g.length === dominant.length && dominant.every((c) => g.includes(c))),
        allDominant: of((g) => dominant.every((c) => g.includes(c))),
        changed: model.studies.filter((s) => perStudy.get(s.id).changed),
      },
    };
  }

  // ----------------------------------------------------------------- TRA

  function buildTRA(wb, model) {
    const sol = table(findSheet(wb, /^TRA solutions$/i));
    if (!sol.rows.length) return null;
    const h = sol.header;
    const c = {
      id: colIndex(h, /^r[a]?y+an id$/i), trl: colIndex(h, /^trl$/i), env: colIndex(h, /environment/i), criterion: colIndex(h, /^criterion/i),
      source: colIndex(h, /^evidence source$/i), evidence: colIndex(h, /^evidence$/i), period: colIndex(h, /^period$/i),
    };
    const solutions = new Map();
    sol.rows.forEach((r) => {
      const study = model.byId.get(text(r[c.id]));
      if (!study) return;
      solutions.set(study.id, {
        study, trl: Number(r[c.trl]), environment: text(r[c.env]), criterion: text(r[c.criterion]),
        source: text(r[c.source]), evidence: text(r[c.evidence]), period: text(r[c.period]),
      });
    });

    const rub = table(findSheet(wb, /^TRL rubric$/i));
    const rh = rub.header;
    const rubric = [];
    let rule = '';
    rub.rows.forEach((r) => {
      if (/^rule$/i.test(text(r[0]))) { rule = text(r[1]); return; }
      const trl = Number(r[0]);
      if (Number.isFinite(trl) && text(r[0])) {
        rubric.push({
          trl, definition: text(r[colIndex(rh, /nasa definition/i)]), criterion: text(r[colIndex(rh, /^criterion/i)]),
          environment: text(r[colIndex(rh, /^environment$/i)]),
        });
      }
    });

    const all = [...solutions.values()];
    const levels = rubric.map((r) => r.trl);
    const used = levels.filter((l) => all.some((s) => s.trl === l));
    const summarise = (label, items) => {
      const trls = items.map((s) => s.trl).sort((a, b) => a - b);
      return {
        label, items, n: items.length,
        byLevel: new Map(used.map((l) => [l, items.filter((s) => s.trl === l)])),
        // Lower median, so that it is always one of the levels (the article reports whole levels).
        median: trls.length ? trls[Math.floor((trls.length - 1) / 2)] : null,
        max: trls.length ? trls[trls.length - 1] : null,
        atLeast4: items.filter((s) => s.trl >= 4),
      };
    };
    const dim = (id) => model.dimension(id);
    const byCategory = (id) => dim(id).categories.map((cat) => ({
      ...summarise(cat.label, all.filter((s) => (s.study.cats[id] || []).includes(cat.id))), id: cat.id,
    }));
    const periods = [...new Set(all.map((s) => s.period).filter(Boolean))].sort();

    const out = {
      solutions, rubric, rule, used, all: summarise('All solutions', all),
      byTechnology: byCategory('technologies'),
      byApproach: byCategory('approaches'),
      noApproach: summarise('No group', all.filter((s) => !(s.study.cats.approaches || []).length)),
      byPeriod: periods.map((p) => summarise(p, all.filter((s) => s.period === p))),
      fullText: all.filter((s) => /full text/i.test(s.source)),
      missing: model.studies.filter((s) => !solutions.has(s.id)),
    };
    out.check = checkTRLSheets(wb, out);
    return out;
  }

  /** Compares the derived tables with the "TRL Technologies", "TRL Approaches" and "TRL Periods" sheets. */
  function checkTRLSheets(wb, tra) {
    const results = [];
    const compare = (sheetName, rows, keyOf) => {
      const t = table(findSheet(wb, new RegExp(`^${sheetName}$`, 'i')));
      if (!t.rows.length) return;
      const iN = colIndex(t.header, /^no\. of solutions$/i);
      let same = 0;
      let total = 0;
      t.rows.forEach((r) => {
        const row = rows.find((x) => keyOf(x) === text(r[0]));
        if (!row) return;
        total++;
        const levels = tra.used.every((l) => Number(r[colIndex(t.header, new RegExp(`^TRL ${l}$`, 'i'))]) === row.byLevel.get(l).length);
        if (Number(r[iN]) === row.n && levels) same++;
      });
      results.push({ sheet: sheetName, same, total });
    };
    compare('TRL Technologies', [...tra.byTechnology, tra.all], (x) => x.id || x.label);
    compare('TRL Approaches', [...tra.byApproach, tra.noApproach, tra.all], (x) => x.label);
    compare('TRL Periods', [...tra.byPeriod, tra.all], (x) => x.label);
    return results;
  }

  // ----------------------------------------------------------- selection

  /** Records of the "Data Set" sheet, grouped by the search that retrieved them. */
  function buildSelection(wb, model) {
    const t = table(findSheet(wb, /^data set$/i));
    const h = t.header;
    const c = {
      id: colIndex(h, /^r[a]?y+an id$/i), db: colIndex(h, /^database id$/i), title: colIndex(h, /^article title$/i, /title/i),
      year: colIndex(h, /^year$/i), journal: colIndex(h, /^journal$/i), vol: colIndex(h, /^vol/i), issue: colIndex(h, /^issue$/i),
      authors: colIndex(h, /^authors$/i), doi: colIndex(h, /^doi$/i),
    };
    const sets = { seed: [], backward: [], forward: [] };
    t.rows.forEach((r) => {
      const db = text(r[c.db]);
      const set = /backward/i.test(db) ? 'backward' : /forward/i.test(db) ? 'forward' : db === '0' || !db ? 'seed' : null;
      if (!set) return;
      const rec = {
        id: text(r[c.id]), title: text(r[c.title]), year: text(r[c.year]), journal: text(r[c.journal]), vol: text(r[c.vol]),
        issue: text(r[c.issue]), authors: text(r[c.authors]), doi: text(r[c.doi]).replace(/^-$/, ''),
      };
      rec.study = model.byId.get(rec.id) || null;
      sets[set].push(rec);
    });
    return sets;
  }

  window.DashboardAnalyses = { buildRQ5, buildTRA, buildSelection };
})();
