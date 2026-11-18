/*
 * AI Tools section: the AI agents and skills used in the study, read from the snapshot in ai-tools/.
 *
 * The tools live in a private repository. A workflow there copies the files of each tool, with a
 * manifest (ai-tools/manifest.json), to this site on every push, so this section shows the current
 * version of each tool, and new tools appear as new cards. Routes:
 *   #ai-tools                    the cards, one per tool;
 *   #ai-tools/<tool>             the tool's README, with the file tree;
 *   #ai-tools/<tool>/<path>      one file of the tool.
 */
(function () {
  'use strict';

  const BASE = 'ai-tools/';
  const $ = (id) => document.getElementById(id);
  const state = { manifest: null, loading: null, error: null, cache: new Map(), closedDirs: new Set() };

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

  const encodePath = (p) => p.split('/').map(encodeURIComponent).join('/');
  const decodePath = (p) => p.split('/').map((s) => { try { return decodeURIComponent(s); } catch (e) { return s; } }).join('/');
  const fileUrl = (tool, path) => `${BASE}${encodePath(tool.id)}/${encodePath(path)}`;
  const toolHash = (tool, path) => `#ai-tools/${encodePath(tool.id)}${path ? `/${encodePath(path)}` : ''}`;

  function size(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  function dateOf(iso) {
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? iso : d.toLocaleString('en-GB', { dateStyle: 'long', timeStyle: 'short', timeZone: 'UTC' }) + ' UTC';
  }

  // ------------------------------------------------------------ data

  function load() {
    if (state.manifest || state.error) return Promise.resolve();
    if (!state.loading) {
      state.loading = (async () => {
        try {
          if (location.protocol === 'file:') throw new Error('the page was opened directly from disk, and browsers do not let such a page read the files next to it');
          const res = await fetch(`${BASE}manifest.json`, { cache: 'no-cache' });
          if (!res.ok) throw new Error(`${BASE}manifest.json: HTTP ${res.status}`);
          state.manifest = await res.json();
        } catch (err) {
          console.error(err);
          state.error = err;
        }
      })();
    }
    return state.loading;
  }

  async function fileText(tool, path) {
    const url = fileUrl(tool, path);
    if (!state.cache.has(url)) {
      state.cache.set(url, fetch(url, { cache: 'no-cache' }).then((res) => {
        if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
        return res.text();
      }));
    }
    try {
      return await state.cache.get(url);
    } catch (err) {
      state.cache.delete(url);
      throw err;
    }
  }

  // ------------------------------------------------------------ markdown

  /** Markdown to HTML. Raw HTML in the source is shown as text, and links between files of a tool open in the viewer. */
  function markdown(src, tool, path) {
    if (!window.marked) return el('pre', { class: 'ai-code', text: src });
    const dir = path.includes('/') ? path.slice(0, path.lastIndexOf('/') + 1) : '';
    const escape = (s) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    const md = new window.marked.Marked({ gfm: true, breaks: false });
    md.use({ renderer: { html: (token) => escape(typeof token === 'string' ? token : token.text || '') } });
    const html = md.parse(src.replace(/^---\s*\n([\s\S]*?)\n---\s*\n/, (m, fm) => `\`\`\`yaml\n${fm}\n\`\`\`\n\n`));
    const box = el('div', { class: 'ai-md' });
    box.innerHTML = html;
    box.querySelectorAll('a[href]').forEach((a) => {
      const href = a.getAttribute('href');
      if (/^[a-z][a-z0-9+.-]*:/i.test(href) || href.startsWith('//')) {
        if (/^javascript:/i.test(href)) a.removeAttribute('href');
        else { a.target = '_blank'; a.rel = 'noopener'; }
        return;
      }
      if (href.startsWith('#')) { a.removeAttribute('href'); return; }
      const target = resolve(dir, href.split('#')[0]);
      const link = linkTarget(tool, target);
      if (link) a.setAttribute('href', link);
      else { a.removeAttribute('href'); a.title = 'Not published in the dashboard'; }
    });
    return box;
  }

  function resolve(dir, rel) {
    const parts = (dir + rel).split('/');
    const out = [];
    parts.forEach((p) => { if (p === '..') out.pop(); else if (p && p !== '.') out.push(p); });
    return out;
  }

  /** Hash of a file of this tool or of another tool (a "../other-tool/..." link), or null. */
  function linkTarget(tool, parts) {
    const tools = state.manifest.tools;
    const asPath = parts.join('/');
    const has = (t, p) => t.files.some((f) => f.path === p);
    if (asPath === '' || asPath === '.') return toolHash(tool);
    if (parts.length && parts[parts.length - 1] && !parts[parts.length - 1].includes('.')) {
      const dirFiles = tool.files.filter((f) => f.path.startsWith(`${asPath}/`));
      if (dirFiles.length) return toolHash(tool, (dirFiles.find((f) => /readme\.md$/i.test(f.path)) || dirFiles[0]).path);
    }
    if (has(tool, asPath)) return toolHash(tool, asPath);
    // Paths are resolved from the tool folder, so "../search-agent/README.md" arrives as ["search-agent", ...] after one "..".
    const other = tools.find((t) => t.id === parts[0]);
    if (other) {
      const rest = parts.slice(1).join('/');
      if (!rest) return toolHash(other);
      if (has(other, rest)) return toolHash(other, rest);
    }
    return null;
  }

  // ------------------------------------------------------------ views

  function renderStatus(panel, text, isError) {
    panel.replaceChildren(el('div', { class: `status${isError ? ' error' : ''}`, text }));
  }

  function inlineMd(text) {
    const span = el('span');
    // Only **bold** and `code` are used in the summaries.
    text.split(/(\*\*[^*]+\*\*|`[^`]+`)/).forEach((part) => {
      if (/^\*\*.+\*\*$/.test(part)) span.append(el('strong', { text: part.slice(2, -2) }));
      else if (/^`.+`$/.test(part)) span.append(el('code', { text: part.slice(1, -1) }));
      else if (part) span.append(part);
    });
    return span;
  }

  function renderCards(panel) {
    const m = state.manifest;
    const cards = m.tools.map((t) => el('a', { class: 'ai-card', href: toolHash(t) },
      el('div', { class: 'ai-card-head' },
        el('span', { class: 'ai-card-icon', 'aria-hidden': 'true' }),
        el('div', {}, el('h3', { text: t.name }), t.summary ? el('p', { class: 'ai-card-summary', text: t.summary }) : null)),
      t.description ? el('p', { class: 'ai-card-desc' }, inlineMd(t.description)) : null,
      el('div', { class: 'ai-card-meta' },
        t.skills.length ? el('div', { class: 'ai-chips' }, t.skills.map((s) => el('span', { class: 'ai-chip', title: s.description || s.name, text: s.name }))) : null,
        el('span', { class: 'muted small', text: `${t.files.length} files · ${size(t.files.reduce((a, f) => a + f.size, 0))}` })),
      el('span', { class: 'ai-card-open', text: 'Open the tool →' })));
    panel.replaceChildren(
      el('div', { class: 'card-head' },
        el('h2', { text: 'AI Tools' }),
        el('p', { class: 'hint', text: 'The AI agents used in this study, with their instructions, skills, reference material and scripts, so that each step they supported can be inspected and repeated. Select a tool to browse its files; each tool opens on its README.' })),
      el('div', { class: 'ai-cards' }, cards),
      el('p', { class: 'hint small' },
        `Snapshot of the tools repository, updated automatically whenever a tool changes. Last update: ${dateOf(m.generated)}`,
        m.commit ? ` (version ${m.commit}).` : '.'));
  }

  /** Files of a tool as a nested tree of folders. */
  function treeOf(files) {
    const root = { dirs: new Map(), files: [] };
    files.forEach((f) => {
      const parts = f.path.split('/');
      let node = root;
      parts.slice(0, -1).forEach((p, i) => {
        if (!node.dirs.has(p)) node.dirs.set(p, { name: p, path: parts.slice(0, i + 1).join('/'), dirs: new Map(), files: [] });
        node = node.dirs.get(p);
      });
      node.files.push({ ...f, name: parts[parts.length - 1] });
    });
    return root;
  }

  function fileIcon(name) {
    if (/\.md$/i.test(name)) return 'md';
    if (/\.(py|sh|js|json|ya?ml)$/i.test(name)) return 'code';
    if (/\.zip$/i.test(name)) return 'zip';
    return 'file';
  }

  function renderTree(tool, current) {
    const build = (node, depth) => {
      const items = [];
      const dirs = [...node.dirs.values()].sort((a, b) => a.name.localeCompare(b.name, 'en'));
      const files = node.files.slice().sort((a, b) => (b.name === 'README.md') - (a.name === 'README.md') || a.name.localeCompare(b.name, 'en'));
      dirs.forEach((d) => {
        const key = `${tool.id}/${d.path}`;
        // Folders start open (the trees are small); a folder the reader closes stays closed, unless it holds the open file.
        const open = !state.closedDirs.has(key) || current.startsWith(`${d.path}/`);
        const details = el('details', { class: 'ai-dir', open },
          el('summary', { style: `--depth:${depth}` }, el('span', { class: 'ai-ico dir', 'aria-hidden': 'true' }), d.name),
          el('ul', { role: 'group' }, build(d, depth + 1)));
        details.addEventListener('toggle', () => { if (details.open) state.closedDirs.delete(key); else state.closedDirs.add(key); });
        items.push(el('li', { role: 'treeitem', 'aria-expanded': String(open) }, details));
      });
      files.forEach((f) => items.push(el('li', { role: 'treeitem' },
        el('a', {
          href: toolHash(tool, f.path), class: `ai-file${f.path === current ? ' active' : ''}`, style: `--depth:${depth}`,
          'aria-current': f.path === current ? 'page' : null, title: f.path,
        }, el('span', { class: `ai-ico ${fileIcon(f.name)}`, 'aria-hidden': 'true' }), el('span', { class: 'ai-file-name', text: f.name })))));
      return items;
    };
    return el('ul', { class: 'ai-tree', role: 'tree', 'aria-label': `Files of ${tool.name}` }, build(treeOf(tool.files), 0));
  }

  async function renderFile(viewer, tool, file) {
    const head = el('div', { class: 'ai-viewer-head' },
      el('nav', { class: 'ai-crumbs', 'aria-label': 'Path' },
        el('a', { href: toolHash(tool), text: tool.id }),
        file.path.split('/').flatMap((p) => [el('span', { class: 'muted', text: ' / ' }), p])),
      el('span', { class: 'muted small', text: size(file.size) }),
      el('a', { class: 'btn ghost small', href: fileUrl(tool, file.path), download: file.path.split('/').pop(), text: 'Download' }));
    const body = el('div', { class: 'ai-viewer-body' }, el('p', { class: 'muted', text: 'Loading…' }));
    viewer.replaceChildren(head, body);
    if (!file.text) {
      body.replaceChildren(el('div', { class: 'ai-binary' },
        el('p', { text: /\.zip$/i.test(file.path) ? 'Skill package for upload to Microsoft Copilot Studio or to Claude. Its contents are the files of the skill folder shown in the tree.' : 'This file is not a text file.' }),
        el('a', { class: 'btn', href: fileUrl(tool, file.path), download: file.path.split('/').pop(), text: `Download ${file.path.split('/').pop()} (${size(file.size)})` })));
      return;
    }
    try {
      let text = await fileText(tool, file.path);
      if (viewer.dataset.path !== `${tool.id}/${file.path}`) return; // another file was opened meanwhile
      if (/\.md$/i.test(file.path)) {
        body.replaceChildren(markdown(text, tool, file.path));
      } else {
        if (/\.json$/i.test(file.path)) { try { text = JSON.stringify(JSON.parse(text), null, 2); } catch (e) { /* keep as is */ } }
        const lines = text.replace(/\n$/, '').split('\n');
        const code = el('code', {});
        lines.forEach((line, i) => code.append(el('span', { class: 'ai-line', 'data-n': i + 1 }, line), '\n'));
        body.replaceChildren(el('pre', { class: 'ai-code', tabindex: 0, 'aria-label': file.path }, code));
      }
    } catch (err) {
      console.error(err);
      body.replaceChildren(el('p', { class: 'status error', text: `This file could not be loaded: ${err.message}.` }));
    }
  }

  function renderTool(panel, tool, path) {
    const readme = tool.files.find((f) => f.path === 'README.md') || tool.files.find((f) => /readme\.md$/i.test(f.path)) || tool.files[0];
    const file = tool.files.find((f) => f.path === path) || readme;
    const viewer = el('article', { class: 'ai-viewer card', 'data-path': `${tool.id}/${file.path}`, 'aria-live': 'polite' });
    const others = state.manifest.tools.filter((t) => t.id !== tool.id);
    panel.replaceChildren(
      el('div', { class: 'ai-tool-head' },
        el('a', { class: 'btn ghost small', href: '#ai-tools', text: '← All AI tools' }),
        el('div', {}, el('h2', { text: tool.name }), tool.summary ? el('p', { class: 'hint', text: tool.summary }) : null)),
      el('div', { class: 'ai-browser' },
        viewer,
        el('aside', { class: 'ai-side card', 'aria-label': 'Files' },
          el('h3', { class: 'ai-side-title', text: 'Files' }),
          renderTree(tool, file.path),
          tool.skills.length ? el('div', { class: 'ai-side-skills' }, el('h4', { text: 'Skills' }),
            el('ul', {}, tool.skills.map((s) => el('li', {}, el('a', { href: toolHash(tool, s.path), text: s.name }))))) : null,
          others.length ? el('div', { class: 'ai-side-skills' }, el('h4', { text: 'Other tools' }),
            el('ul', {}, others.map((t) => el('li', {}, el('a', { href: toolHash(t), text: t.name }))))) : null)));
    renderFile(viewer, tool, file);
  }

  async function show(rest) {
    const panel = $('panel-ai-tools');
    if (!state.manifest && !state.error) renderStatus(panel, 'Loading the AI tools…');
    await load();
    if (state.error) {
      renderStatus(panel, `The AI tools could not be loaded: ${state.error.message}. Serve the folder over HTTP (for example, python3 -m http.server) or open the published dashboard.`, true);
      return;
    }
    const [toolId, ...pathParts] = decodePath(rest || '').split('/');
    const tool = toolId && state.manifest.tools.find((t) => t.id === toolId);
    const prev = panel.dataset.view;
    if (!tool) renderCards(panel);
    else renderTool(panel, tool, pathParts.join('/'));
    const view = tool ? tool.id : '';
    if (prev !== undefined && prev !== view) window.scrollTo({ top: 0 });
    panel.dataset.view = view;
  }

  window.DashboardAITools = { show };
})();
