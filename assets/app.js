/*
 * Dashboard user interface: tabs, the studies-by-year chart, the DEF and
 * thematic analysis tables, one table per research question and the heatmaps.
 * The data model comes from data.js; citations come from data/references.js,
 * which follows the numbering of the article's reference list.
 */
(function () {
  'use strict';

  const CONFIG = {
    workbook: 'data/DEF_TA.xlsx',
    maxSeries: 8,
  };

  const { SOURCES, parseWorkbook, cellFor, text } = window.DashboardData;
  const $ = (id) => document.getElementById(id);

  const state = {
    model: null,
    article: null,
    references: {},
    series: [],
    stacked: false,
    chart: null,
    taIndex: 0,
    heatmap: { y: 'purposes', x: 'technologies' },
  };

  // ------------------------------------------------------------ utilities

  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([k, v]) => {
      if (v === undefined || v === null || v === false) return;
      if (k === 'class') node.className = v;
      else if (k === 'text') node.textContent = v;
      else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? '' : v);
    });
    children.flat().forEach((c) => {
      if (c === null || c === undefined || c === false) return;
      node.append(c instanceof Node ? c : document.createTextNode(String(c)));
    });
    return node;
  }

  const pct = (n, total) => (total ? (100 * n / total).toFixed(2) + '%' : '–');
  const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

  // ------------------------------------------------------------ citations

  function refOf(study) {
    return state.references[study.id] || null;
  }

  /** "[12, 14–16]" in the compressed numeric style of the article. */
  function compressNumbers(numbers) {
    const sorted = [...new Set(numbers)].sort((a, b) => a - b);
    const parts = [];
    for (let i = 0; i < sorted.length; i++) {
      let j = i;
      while (j + 1 < sorted.length && sorted[j + 1] === sorted[j] + 1) j++;
      if (j - i >= 2) parts.push(`${sorted[i]}–${sorted[j]}`);
      else for (let k = i; k <= j; k++) parts.push(String(sorted[k]));
      i = j;
    }
    return parts.length ? `[${parts.join(', ')}]` : '';
  }

  function citationLabel(study) {
    const ref = refOf(study);
    return ref ? `[${ref.number}]` : '[?]';
  }

  /** Opens the dialog listing the studies behind a number, cited as in the article. */
  function showCitations(title, studies, subtitle) {
    const list = [...studies].sort((a, b) => ((refOf(a) || {}).number || 1e9) - ((refOf(b) || {}).number || 1e9));
    const numbers = list.map(refOf).filter(Boolean).map((r) => r.number);
    const missing = list.filter((s) => !refOf(s));
    const body = el('div', { class: 'citations' },
      subtitle ? el('p', { class: 'hint', text: subtitle }) : null,
      el('p', { class: 'cite-inline' },
        el('span', { class: 'muted', text: `${list.length} ${list.length === 1 ? 'study' : 'studies'} · ` }),
        compressNumbers(numbers) || '–'),
      el('button', {
        type: 'button', class: 'btn ghost small', onclick: (e) => {
          navigator.clipboard && navigator.clipboard.writeText(compressNumbers(numbers));
          e.target.textContent = 'Copied';
        },
      }, 'Copy citation'),
      el('ol', { class: 'ref-list' }, list.map((s) => {
        const ref = refOf(s);
        return el('li', {},
          el('span', { class: 'ref-num', text: citationLabel(s) }),
          el('span', {},
            ref ? ref.reference : `${s.title} (${s.year || 'n.d.'}).`,
            ' ',
            (ref && ref.url) || s.doi
              ? el('a', { href: (ref && ref.url) || `https://doi.org/${s.doi}`, target: '_blank', rel: 'noopener', text: 'Link' })
              : null,
            el('span', { class: 'muted small', text: ` · ${s.paperId} · ${s.id}` })));
      })),
      missing.length ? el('p', { class: 'hint warn', text: `${missing.length} of these studies are not cited in the article's reference list, so they have no number.` }) : null);
    openDialog(title, body);
  }

  // --------------------------------------------------------------- dialog

  function openDialog(title, body) {
    $('dialog-title').textContent = title;
    $('dialog-body').replaceChildren(body);
    const d = $('dialog');
    if (!d.open) d.showModal();
    $('dialog-body').scrollTop = 0;
  }

  function studyHeading(study) {
    return `${study.paperId} ${citationLabel(study)} · ${study.title}${study.year ? ` (${study.year})` : ''}`;
  }

  /** Side-by-side comparison of the three coders for one field. */
  function comparison(field, row) {
    return el('div', { class: 'compare' }, SOURCES.map((src) => {
      const cols = field.cols[src.id] || [];
      const value = cols.length ? cellFor(row, cols) : null;
      return el('div', { class: `compare-col${src.id === 'r1' ? ' primary' : ''}` },
        el('h4', { text: src.label }),
        value === null ? el('p', { class: 'muted', text: 'Not recorded for this field.' })
          : el('p', { class: value ? 'pre' : 'muted', text: value || 'Empty.' }));
    }));
  }

  // ----------------------------------------------------------------- tabs

  function tabList() {
    const tabs = [
      { id: 'overview', label: 'Overview' },
      { id: 'def', label: 'Data extraction' },
      { id: 'ta', label: 'Thematic analysis' },
    ];
    state.article.researchQuestions.forEach((rq) => tabs.push({ id: rq.id.toLowerCase(), label: rq.id, rq }));
    tabs.push({ id: 'heatmaps', label: 'Heatmaps' });
    return tabs;
  }

  function buildTabs() {
    const nav = $('tabs');
    nav.replaceChildren(...tabList().map((t) => el('a', {
      href: `#${t.id}`, role: 'tab', id: `tab-${t.id}`, class: 'tab', text: t.label,
    })));
    window.addEventListener('hashchange', route);
  }

  function route() {
    const tabs = tabList();
    const id = (location.hash || '#overview').slice(1);
    const tab = tabs.find((t) => t.id === id) || tabs[0];
    document.querySelectorAll('.tab').forEach((a) => a.setAttribute('aria-selected', String(a.id === `tab-${tab.id}`)));
    document.querySelectorAll('.panel').forEach((p) => { p.hidden = true; });
    const panel = tab.rq ? 'rq' : tab.id;
    $(`panel-${panel}`).hidden = false;
    if (tab.rq) renderRQ(tab.rq);
    if (tab.id === 'overview') renderChart();
    if (tab.id === 'heatmaps') renderHeatmap();
  }

  // ------------------------------------------------------------- overview

  function renderOverview() {
    const a = state.article;
    const m = state.model;
    $('article-title').textContent = a.title;
    document.title = 'Digital Object Tracing Dashboard';
    $('article-authors').replaceChildren(...a.authors.map((au) => el('span', { class: 'author' },
      au.name, au.corresponding ? el('sup', { title: 'Corresponding author', text: '*' }) : null,
      au.orcid ? el('a', { href: `https://orcid.org/${au.orcid}`, target: '_blank', rel: 'noopener', class: 'orcid', text: 'ORCID' }) : null)));
    $('article-affiliation').textContent = a.affiliation;
    $('article-abstract').textContent = a.abstract;
    $('article-keywords').replaceChildren(el('strong', { text: 'Keywords: ' }), a.keywords.join('; '));

    const years = m.studies.map((s) => s.year).filter(Boolean);
    const bySource = (label) => m.studies.filter((s) => s.source === label).length;
    const tiles = [
      ['Primary studies', m.studies.length],
      ['Unique records screened', m.records ? m.records.toLocaleString('en-GB') : '–'],
      ['Publication years', years.length ? `${Math.min(...years)}–${Math.max(...years)}` : '–'],
      ['Seed set (Scopus)', bySource('Seed set (Scopus)')],
      ['Backward snowballing', bySource('Backward snowballing')],
      ['Forward snowballing', bySource('Forward snowballing')],
    ];
    $('overview-tiles').replaceChildren(...tiles.map(([label, value]) =>
      el('div', { class: 'tile' }, el('span', { class: 'tile-value', text: value }), el('span', { class: 'tile-label', text: label }))));
  }

  // ------------------------------------------------- studies-by-year chart

  const ALL = '__all__';

  function seriesStudies(series) {
    if (series.dim === 'total') return state.model.studies;
    return state.model.studies.filter((s) => (s.cats[series.dim] || []).includes(series.cat));
  }

  function seriesLabel(series) {
    if (series.dim === 'total') return 'Number of studies';
    const dim = state.model.dimension(series.dim);
    const cat = dim.categories.find((c) => c.id === series.cat);
    return cat ? cat.label : series.cat;
  }

  function buildSeriesBuilder() {
    const dimSel = $('sb-dimension');
    const opts = [el('option', { value: 'total', text: 'Number of studies' })]
      .concat(state.model.dimensions.map((d) => el('option', { value: d.id, text: d.label })));
    dimSel.replaceChildren(...opts);
    dimSel.onchange = fillCategories;
    fillCategories();
    $('sb-add').onclick = () => {
      const dim = dimSel.value;
      const type = $('sb-type').value;
      const cat = $('sb-category').value;
      if (dim === 'total') addSeries({ dim: 'total', type });
      else if (cat === ALL) state.model.dimension(dim).categories.forEach((c) => addSeries({ dim, cat: c.id, type }, true));
      else addSeries({ dim, cat, type });
      renderChart();
    };
    $('sb-stack').onchange = (e) => { state.stacked = e.target.checked; renderChart(); };
    $('sb-reset').onclick = () => { resetSeries(); renderChart(); };
    resetSeries();
  }

  function fillCategories() {
    const dim = $('sb-dimension').value;
    const sel = $('sb-category');
    if (dim === 'total') {
      sel.replaceChildren(el('option', { value: '', text: '–' }));
      sel.disabled = true;
      return;
    }
    sel.disabled = false;
    const d = state.model.dimension(dim);
    sel.replaceChildren(
      el('option', { value: ALL, text: `All categories (${d.categories.length})` }),
      ...d.categories.map((c) => el('option', { value: c.id, text: `${c.label} (${c.count})` })));
    sel.value = d.categories.length ? d.categories[0].id : ALL;
  }

  function resetSeries() {
    state.series = [];
    state.nextColour = 0;
    addSeries({ dim: 'total', type: 'bar' });
  }

  function addSeries(series, quiet) {
    const key = `${series.dim}|${series.cat || ''}`;
    if (state.series.some((s) => s.key === key)) return;
    if (state.series.length >= CONFIG.maxSeries) {
      if (!quiet || !state.warned) showSeriesWarning(`The chart holds up to ${CONFIG.maxSeries} series so that each one keeps a distinguishable colour. Remove a series before adding another.`);
      state.warned = true;
      return;
    }
    // Colours follow the series, never their position, so removing one does not repaint the others.
    const used = new Set(state.series.map((s) => s.colour));
    let colour = 1;
    while (used.has(colour)) colour++;
    state.series.push({ ...series, key, colour });
  }

  function showSeriesWarning(message) {
    const w = $('series-warning');
    w.textContent = message;
    w.hidden = !message;
  }

  function renderSeriesList() {
    $('series-list').replaceChildren(...state.series.map((s) => el('li', { class: 'series-chip' },
      el('span', { class: `swatch ${s.type}`, style: `--c: var(--series-${s.colour})` }),
      el('span', { class: 'chip-label', text: seriesLabel(s) }),
      el('button', {
        type: 'button', class: 'btn ghost small', title: 'Switch between bars and line',
        onclick: () => { s.type = s.type === 'bar' ? 'line' : 'bar'; renderChart(); },
      }, s.type === 'bar' ? 'Bars' : 'Line'),
      el('button', {
        type: 'button', class: 'btn ghost small', 'aria-label': `Remove ${seriesLabel(s)}`,
        onclick: () => { state.series = state.series.filter((x) => x !== s); state.warned = false; showSeriesWarning(''); renderChart(); },
      }, '×'))));
  }

  function yearRange() {
    const years = state.model.studies.map((s) => s.year).filter(Boolean);
    const out = [];
    for (let y = Math.min(...years); y <= Math.max(...years); y++) out.push(y);
    return out;
  }

  function renderChart() {
    if (!state.model || $('panel-overview').hidden) return;
    renderSeriesList();
    const years = yearRange();
    const data = state.series.map((s) => {
      const studies = seriesStudies(s);
      return years.map((y) => studies.filter((st) => st.year === y).length);
    });
    const ink = cssVar('--text-secondary');
    const grid = cssVar('--grid');
    const datasets = state.series.map((s, i) => {
      const colour = cssVar(`--series-${s.colour}`);
      const common = { label: seriesLabel(s), data: data[i], backgroundColor: colour, borderColor: colour };
      return s.type === 'bar'
        ? { ...common, type: 'bar', order: 2, borderRadius: 4, borderSkipped: 'start', maxBarThickness: 28, stack: state.stacked ? 'bars' : `bar-${i}` }
        : { ...common, type: 'line', order: 1, borderWidth: 2, pointRadius: 4, pointHoverRadius: 6, pointBackgroundColor: colour,
            pointBorderColor: cssVar('--surface'), pointBorderWidth: 2, tension: 0, stack: `line-${i}` };
    });
    const config = {
      data: { labels: years, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { position: 'top', align: 'start', labels: { color: ink, usePointStyle: true, boxWidth: 10, boxHeight: 10, sort: (a, b) => a.datasetIndex - b.datasetIndex } },
          tooltip: { itemSort: (a, b) => b.raw - a.raw },
        },
        scales: {
          x: { stacked: state.stacked, grid: { display: false }, ticks: { color: ink }, border: { color: cssVar('--axis') } },
          y: { stacked: state.stacked, beginAtZero: true, ticks: { color: ink, precision: 0 }, grid: { color: grid }, border: { display: false },
               title: { display: true, text: 'Number of studies', color: ink } },
        },
        onClick: (evt, elements, chart) => {
          const hit = chart.getElementsAtEventForMode(evt, 'nearest', { intersect: true }, false)[0];
          if (!hit) return;
          const s = state.series[hit.datasetIndex];
          const year = years[hit.index];
          const studies = seriesStudies(s).filter((st) => st.year === year);
          if (studies.length) showCitations(`${seriesLabel(s)} · ${year}`, studies);
        },
        onHover: (evt, elements, chart) => {
          const hit = chart.getElementsAtEventForMode(evt, 'nearest', { intersect: true }, false)[0];
          chart.canvas.style.cursor = hit ? 'pointer' : 'default';
        },
      },
    };
    if (state.chart) state.chart.destroy();
    state.chart = new Chart($('year-chart'), config);
    renderYearTable(years, data);
  }

  function renderYearTable(years, data) {
    const t = el('table', { class: 'data' },
      el('thead', {}, el('tr', {}, el('th', { text: 'Year' }), state.series.map((s) => el('th', { class: 'num', text: seriesLabel(s) })))),
      el('tbody', {}, years.map((y, j) => el('tr', {}, el('th', { text: y }), data.map((d) => el('td', { class: 'num', text: d[j] }))))));
    $('year-table').replaceChildren(t);
  }

  // ------------------------------------------------------ DEF and TA tables

  function filterRows(rows, query, cellsOf) {
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) => {
      const s = r.study;
      return [s.paperId, s.id, s.title, s.year, citationLabel(s), ...cellsOf(r)].join(' ').toLowerCase().includes(q);
    });
  }

  function studyCell(study) {
    return el('th', { class: 'study', scope: 'row' },
      el('span', { class: 'pid', text: study.paperId }),
      el('span', { class: 'cite', text: citationLabel(study) }),
      el('span', { class: 'stitle', text: study.title, title: study.title }));
  }

  function renderDEF() {
    const { fields, rows } = state.model.def;
    const cols = fields.filter((f) => f.cols.r1.length);
    const draw = () => {
      const shown = filterRows(rows, $('def-filter').value, (r) => cols.map((f) => cellFor(r.row, f.cols.r1)));
      $('def-count').textContent = `${shown.length} of ${rows.length} studies`;
      const t = el('table', { class: 'data grid' },
        el('thead', {}, el('tr', {}, el('th', { class: 'study', text: 'Study' }), el('th', { text: 'Year' }),
          cols.map((f) => el('th', { text: f.label })))),
        el('tbody', {}, shown.map((r) => el('tr', {}, studyCell(r.study), el('td', { class: 'num', text: r.study.year || '' }),
          cols.map((f) => {
            const v = cellFor(r.row, f.cols.r1);
            return el('td', {
              class: 'clip', tabindex: 0, title: 'Click to compare with the AI tools',
              onclick: () => openDEF(f, r), onkeydown: (e) => { if (e.key === 'Enter') openDEF(f, r); },
            }, el('div', { class: 'clamp', text: v }));
          })))));
      $('def-table').replaceChildren(t);
    };
    $('def-filter').oninput = draw;
    draw();
  }

  function openDEF(field, r) {
    const body = el('div', {},
      el('p', { class: 'hint', text: studyHeading(r.study) }),
      comparison(field, r.row),
      field.final !== undefined ? el('div', { class: 'final' }, el('h4', { text: 'Final decision' }), el('p', { text: text(r.row[field.final]) || '–' })) : null);
    openDialog(field.label, body);
  }

  function renderTASubtabs() {
    $('ta-subtabs').replaceChildren(...state.model.taSheets.map((sh, i) => el('button', {
      type: 'button', role: 'tab', class: 'subtab', 'aria-selected': String(i === state.taIndex),
      onclick: () => { state.taIndex = i; renderTASubtabs(); renderTA(); },
    }, sh.label)));
  }

  function renderTA() {
    const sh = state.model.taSheets[state.taIndex];
    if (!sh) return;
    const stages = sh.stages.filter((f) => f.cols.r1.length);
    const draw = () => {
      const shown = filterRows(sh.rows, $('ta-filter').value,
        (r) => stages.map((f) => cellFor(r.row, f.cols.r1)).concat(sh.extras.map((x) => text(r.row[x.index]))));
      $('ta-count').textContent = `${shown.length} of ${sh.rows.length} studies`;
      const t = el('table', { class: 'data grid' },
        el('thead', {}, el('tr', {}, el('th', { class: 'study', text: 'Study' }),
          stages.map((f) => el('th', {}, f.label, el('span', { class: 'sub', text: 'Researcher 1' }))),
          sh.extras.map((x) => el('th', { text: x.label })))),
        el('tbody', {}, shown.map((r) => el('tr', {}, studyCell(r.study),
          stages.map((f) => el('td', {
            class: 'clip', tabindex: 0, title: 'Click to compare with the AI tools',
            onclick: () => openTA(sh, f, r), onkeydown: (e) => { if (e.key === 'Enter') openTA(sh, f, r); },
          }, el('div', { class: 'clamp', text: cellFor(r.row, f.cols.r1) }))),
          sh.extras.map((x) => el('td', {
            class: 'clip final-col', tabindex: 0, title: 'Click to see every stage of the coding',
            onclick: () => openTA(sh, null, r), onkeydown: (e) => { if (e.key === 'Enter') openTA(sh, null, r); },
          }, el('div', { class: 'clamp', text: text(r.row[x.index]) })))))));
      $('ta-table').replaceChildren(t);
    };
    $('ta-filter').oninput = draw;
    draw();
  }

  /** Shows one stage (or every stage, when `stage` is null) for the three coders. */
  function openTA(sh, stage, r) {
    const stages = stage ? [stage] : sh.stages;
    const body = el('div', {},
      el('p', { class: 'hint', text: studyHeading(r.study) }),
      stages.map((f) => el('section', { class: 'stage' }, stages.length > 1 ? el('h3', { text: f.label }) : null, comparison(f, r.row))),
      sh.extras.length ? el('div', { class: 'final' }, sh.extras.map((x) =>
        el('div', {}, el('h4', { text: x.label }), el('p', { class: 'pre', text: text(r.row[x.index]) || '–' })))) : null);
    openDialog(stage ? `${sh.label}: ${stage.label}` : sh.label, body);
  }

  // ----------------------------------------------------- research questions

  function renderRQ(rq) {
    const dim = state.model.dimension(rq.dimension);
    const n = state.model.studies.length;
    $('rq-id').textContent = `${rq.id} · ${dim ? dim.label : ''}`;
    $('rq-question').textContent = rq.question;
    $('rq-rationale').textContent = rq.rationale;
    if (!dim) { $('rq-table').replaceChildren(el('p', { text: 'This dimension was not found in the spreadsheet.' })); return; }
    const max = Math.max(...dim.categories.map((c) => c.count), 1);
    const studiesOf = (c) => state.model.studies.filter((s) => (s.cats[dim.id] || []).includes(c.id));
    const t = el('table', { class: 'data rq' },
      el('thead', {}, el('tr', {}, el('th', { text: dim.label }), el('th', { class: 'num', text: '% of occurrence' }),
        el('th', { class: 'num', text: 'No. of studies' }), el('th', { class: 'bar-col', 'aria-hidden': 'true' }))),
      el('tbody', {}, dim.categories.map((c) => el('tr', {},
        el('th', { scope: 'row', text: c.label }),
        el('td', { class: 'num', text: pct(c.count, n) }),
        el('td', { class: 'num' }, el('button', {
          type: 'button', class: 'link-btn', title: 'List the studies',
          onclick: () => showCitations(`${rq.id} · ${c.label}`, studiesOf(c), `${c.count} of ${n} studies (${pct(c.count, n)})`),
        }, c.count)),
        el('td', { class: 'bar-col', 'aria-hidden': 'true' }, el('span', { class: 'inline-bar', style: `width:${(100 * c.count / max).toFixed(1)}%` }))))),
      el('tfoot', {}, el('tr', {}, el('th', { text: 'Primary studies' }), el('td', { class: 'num', text: '100.00%' }),
        el('td', { class: 'num' }, el('button', {
          type: 'button', class: 'link-btn', onclick: () => showCitations(`${rq.id} · all studies`, state.model.studies),
        }, n)), el('td', { class: 'bar-col' }))));
    $('rq-table').replaceChildren(t);

    const perStudy = state.model.studies.map((s) => (s.cats[dim.id] || []).length);
    const assigned = perStudy.reduce((a, b) => a + b, 0);
    const stats = [
      ['Categories', dim.categories.length],
      ['Category assignments', assigned],
      ['Average categories per study', (assigned / n).toFixed(2)],
      ['Studies with two or more categories', `${perStudy.filter((x) => x >= 2).length} (${pct(perStudy.filter((x) => x >= 2).length, n)})`],
      ['Studies with no category', perStudy.filter((x) => x === 0).length],
    ];
    $('rq-stats').replaceChildren(...stats.map(([k, v]) => el('div', {}, el('dt', { text: k }), el('dd', { text: v }))));
    $('rq-table').append(el('p', { class: 'hint small', text: 'Percentages refer to all primary studies; categories are not mutually exclusive.' }));
  }

  // -------------------------------------------------------------- heatmaps

  function buildHeatmapControls() {
    const dims = state.model.dimensions.filter((d) => !d.chartOnly);
    ['hm-y', 'hm-x'].forEach((id) => {
      $(id).replaceChildren(...dims.map((d) => el('option', { value: d.id, text: d.label })));
    });
    if (!dims.some((d) => d.id === state.heatmap.y)) state.heatmap.y = dims[0].id;
    if (!dims.some((d) => d.id === state.heatmap.x)) state.heatmap.x = dims[1 % dims.length].id;
    $('hm-y').value = state.heatmap.y;
    $('hm-x').value = state.heatmap.x;
    $('hm-y').onchange = (e) => { state.heatmap.y = e.target.value; renderHeatmap(); };
    $('hm-x').onchange = (e) => { state.heatmap.x = e.target.value; renderHeatmap(); };
    $('hm-swap').onclick = () => {
      state.heatmap = { y: state.heatmap.x, x: state.heatmap.y };
      $('hm-y').value = state.heatmap.y;
      $('hm-x').value = state.heatmap.x;
      renderHeatmap();
    };
  }

  /** Compares two lists of counts sorted from highest to lowest. */
  function compareDesc(a, b) {
    const x = [...a].sort((p, q) => q - p);
    const y = [...b].sort((p, q) => q - p);
    for (let i = 0; i < Math.max(x.length, y.length); i++) {
      const d = (x[i] || 0) - (y[i] || 0);
      if (d) return d;
    }
    return 0;
  }

  /**
   * Orders rows and columns so that the highest count is in the top-right cell
   * and low counts gather in the bottom-left corner.
   * 1. The anchor column is the one holding the highest count.
   * 2. Rows are sorted by their count in the anchor column, highest first.
   *    Ties are broken by the highest count in the remaining columns, then the
   *    next highest, and so on.
   * 3. Columns are sorted by their count in the top row, lowest on the left,
   *    with ties broken in the same way over the remaining rows.
   */
  function orderMatrix(matrix, nRows, nCols) {
    const rowsIdx = [...Array(nRows).keys()];
    const colsIdx = [...Array(nCols).keys()];
    const colValues = (c, skipRow) => rowsIdx.filter((r) => r !== skipRow).map((r) => matrix[r][c]);
    const rowValues = (r, skipCol) => colsIdx.filter((c) => c !== skipCol).map((c) => matrix[r][c]);

    let anchor = 0;
    let best = -1;
    colsIdx.forEach((c) => {
      const top = Math.max(...colValues(c));
      if (top > best || (top === best && compareDesc(colValues(c), colValues(anchor)) > 0)) { best = top; anchor = c; }
    });

    const rowOrder = [...rowsIdx].sort((a, b) =>
      (matrix[b][anchor] - matrix[a][anchor]) || compareDesc(rowValues(b, anchor), rowValues(a, anchor)) || a - b);
    const top = rowOrder[0];
    const colOrder = [...colsIdx].sort((a, b) =>
      (matrix[top][a] - matrix[top][b]) || compareDesc(colValues(a, top), colValues(b, top)) || a - b);
    return { rowOrder, colOrder };
  }

  function renderHeatmap() {
    if (!state.model || $('panel-heatmaps').hidden) return;
    const dy = state.model.dimension(state.heatmap.y);
    const dx = state.model.dimension(state.heatmap.x);
    const rows = dy.categories;
    const cols = dx.categories;
    const cell = rows.map((r) => cols.map((c) => state.model.studies.filter((s) =>
      (s.cats[dy.id] || []).includes(r.id) && (s.cats[dx.id] || []).includes(c.id))));
    const matrix = cell.map((r) => r.map((list) => list.length));
    const { rowOrder, colOrder } = orderMatrix(matrix, rows.length, cols.length);
    const max = Math.max(1, ...matrix.flat());
    const ramp = [1, 2, 3, 4, 5, 6, 7, 8, 9].map((i) => cssVar(`--seq-${i}`));

    const grid = el('div', {
      class: 'heatmap',
      style: `grid-template-columns: minmax(9rem, max-content) repeat(${cols.length}, minmax(2.6rem, 1fr))`,
      role: 'table', 'aria-label': `${dy.label} by ${dx.label}`,
    });
    rowOrder.forEach((ri) => {
      grid.append(el('div', { class: 'hm-label row', role: 'rowheader', text: rows[ri].label, title: rows[ri].label }));
      colOrder.forEach((ci) => {
        const v = matrix[ri][ci];
        const step = v ? Math.min(8, Math.floor((v / max) * 8)) : -1;
        const tip = `${rows[ri].label} × ${cols[ci].label}: ${v} ${v === 1 ? 'study' : 'studies'}`;
        grid.append(el('button', {
          type: 'button', class: `hm-cell${v ? '' : ' zero'}${step >= 5 ? ' dark' : ''}`, role: 'cell',
          style: v ? `background:${ramp[step]}` : '', 'aria-label': tip, 'data-tip': tip,
          onclick: () => { if (v) showCitations(`${rows[ri].label} × ${cols[ci].label}`, cell[ri][ci], `${dy.label} × ${dx.label}`); },
        }, v));
      });
    });
    grid.append(el('div', { class: 'hm-corner', text: `${dy.label} ↑  ·  ${dx.label} →` }));
    colOrder.forEach((ci) => grid.append(el('div', { class: 'hm-label col', role: 'columnheader', title: cols[ci].label },
      el('span', { text: cols[ci].label }))));
    const legend = el('div', { class: 'hm-legend' },
      el('span', { class: 'muted small', text: '0' }),
      el('span', { class: 'hm-ramp', style: `background: linear-gradient(90deg, ${ramp.join(', ')})` }),
      el('span', { class: 'muted small', text: `${max} studies` }));
    $('heatmap').replaceChildren(grid, legend);
  }

  // ------------------------------------------------------------- tooltip

  function setupTooltip() {
    const tip = $('tooltip');
    document.addEventListener('pointerover', (e) => {
      const t = e.target.closest('[data-tip]');
      if (!t) { tip.hidden = true; return; }
      tip.textContent = t.dataset.tip;
      tip.hidden = false;
    });
    document.addEventListener('pointermove', (e) => {
      if (tip.hidden) return;
      const x = Math.min(e.clientX + 14, window.innerWidth - tip.offsetWidth - 8);
      tip.style.left = `${x}px`;
      tip.style.top = `${e.clientY + 16}px`;
    });
  }

  // ----------------------------------------------------------------- load

  function readWorkbook(buffer) {
    // Only the sheets the dashboard uses are parsed, which keeps loading fast.
    const probe = XLSX.read(buffer, { type: 'array', bookSheets: true });
    const wanted = probe.SheetNames.filter((n) => /^(data extraction|thematic analysis|rq\d|approaches\s*analys|domains$|sub-?domains$|purposes$|technologies$|digital objects$|architecture$|data set$)/i.test(n.trim()));
    return XLSX.read(buffer, { type: 'array', sheets: wanted, cellHTML: false, cellStyles: false });
  }

  function useWorkbook(wb, sourceNote) {
    state.model = parseWorkbook(wb);
    state.model.warnings.forEach((w) => console.warn(w));
    renderOverview();
    buildSeriesBuilder();
    renderDEF();
    renderTASubtabs();
    renderTA();
    buildHeatmapControls();
    $('source-note').textContent = sourceNote;
    $('status').hidden = true;
    route();
  }

  async function init() {
    setupTooltip();
    $('dialog-close').onclick = () => $('dialog').close();
    $('dialog').addEventListener('click', (e) => { if (e.target === $('dialog')) $('dialog').close(); });
    // Article metadata and references are loaded as scripts (data/article.js and
    // data/references.js), so they are available even when the page is opened from disk.
    state.article = window.DASHBOARD_ARTICLE;
    state.references = window.DASHBOARD_REFERENCES || {};
    if (!window.DASHBOARD_REFERENCES) console.error('data/references.js was not loaded: citation numbers are unavailable.');
    $('article-title').textContent = state.article.title;
    buildTabs();
    try {
      if (location.protocol === 'file:') {
        throw new Error('the page was opened directly from disk, and browsers do not let such a page read the spreadsheet next to it');
      }
      const res = await fetch(CONFIG.workbook, { cache: 'no-cache' });
      if (!res.ok) throw new Error(`${CONFIG.workbook}: HTTP ${res.status}`);
      const modified = res.headers.get('Last-Modified');
      const wb = readWorkbook(await res.arrayBuffer());
      useWorkbook(wb, `Data read from ${CONFIG.workbook}${modified ? `, last updated ${new Date(modified).toLocaleString('en-GB')}` : ''}. Citation numbers follow the article's reference list.`);
    } catch (err) {
      console.error(err);
      $('status').textContent = `The spreadsheet could not be loaded: ${err.message}. Choose ${CONFIG.workbook} with the file picker at the bottom of the page, or serve the folder over HTTP (for example, python3 -m http.server).`;
      $('status').classList.add('error');
    }
    $('file-input').addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      try {
        $('status').classList.remove('error');
        useWorkbook(readWorkbook(await file.arrayBuffer()), `Previewing ${file.name} from this computer. Reload the page to return to ${CONFIG.workbook}. Citation numbers follow the article's reference list.`);
      } catch (err) {
        console.error(err);
        alert(`This file could not be read: ${err.message}`);
      }
    });
    matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { renderChart(); renderHeatmap(); });
  }

  window.addEventListener('DOMContentLoaded', init);
})();
