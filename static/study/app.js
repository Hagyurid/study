const $ = (id) => document.getElementById(id);
const KEY = 'lecturenote_action_key';
const SUBJECT = 'lecturenote_subject';
let currentSourceId = '';
let currentSourceType = 'generated_note';
let isRendering = false;

function actionKey() { return ($('key')?.value || '').trim(); }
function subject() { return $('subject').value.trim(); }
function headers(json = true) {
  const h = {};
  if (actionKey()) h.Authorization = 'Bearer ' + actionKey();
  if (json) h['Content-Type'] = 'application/json';
  return h;
}
function remember() { if (actionKey()) localStorage.setItem(KEY, actionKey()); if (subject()) localStorage.setItem(SUBJECT, subject()); }
function restore() {
  const params = new URLSearchParams(window.location.search);
  const queryKey = params.get('action_key') || '';
  const querySubject = params.get('subject') || '';
  if (queryKey) localStorage.setItem(KEY, queryKey);
  if (querySubject) localStorage.setItem(SUBJECT, querySubject);
  $('key').value = localStorage.getItem(KEY) || '';
  $('subject').value = localStorage.getItem(SUBJECT) || '';
}
function status(text) { $('saveState').textContent = text; }
function esc(value) { return String(value ?? '').replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m])); }
function attr(value) { return esc(value).replace(/`/g, '&#96;'); }
async function api(path, opt = {}) {
  remember();
  if (!actionKey()) {
    throw new Error('액션 키를 입력하세요. 업로드 화면에서 쓰는 ACTION_API_KEY와 같은 값입니다.');
  }
  opt.headers = opt.headers || headers(false);
  const res = await fetch(path, opt);
  if (!res.ok) {
    let detail = await res.text();
    try { detail = JSON.parse(detail).detail || detail; } catch (_) {}
    if (String(detail).includes('Invalid action key')) detail = '액션 키가 맞지 않습니다. Render의 ACTION_API_KEY와 같은 값인지 확인하세요.';
    throw new Error(detail);
  }
  return await res.json();
}

function protectMath(text) {
  const stash = [];
  let out = String(text || '');
  const put = (tex, cls) => { stash.push(`<span class="${cls}" data-tex="${attr(tex)}" contenteditable="false">${esc(tex)}</span>`); return `\u0000M${stash.length - 1}\u0000`; };
  out = out.replace(/\$\$([\s\S]+?)\$\$/g, (_, body) => put(`$$${body}$$`, 'math-block'));
  out = out.replace(/\\\[([\s\S]+?)\\\]/g, (_, body) => put(`\\[${body}\\]`, 'math-block'));
  out = out.replace(/\$([^$\n]+?)\$/g, (_, body) => put(`$${body}$`, 'math-inline'));
  out = out.replace(/\\\(([^\n]+?)\\\)/g, (_, body) => put(`\\(${body}\\)`, 'math-inline'));
  return { out, stash };
}
function restoreStash(html, stash) { return html.replace(new RegExp('\\u0000M(\\d+)\\u0000', 'g'), (_, i) => stash[Number(i)] || ''); }

function imageFigureHtml(alt, src) {
  const safeAlt = attr(alt || '이미지');
  const safeSrc = attr(src || '');
  return `<figure class="image-card" data-md-src="${safeSrc}"><button type="button" class="image-delete" contenteditable="false" aria-label="이미지 삭제">삭제</button><img alt="${safeAlt}" src="${safeSrc}" contenteditable="false"><figcaption contenteditable="true">${esc(alt || '이미지')}</figcaption></figure>`;
}
function parseSlideMarker(line) {
  const m = String(line || '').trim().match(/^\[\[SLIDE_IMAGE\s+([\s\S]*?)\]\]$/);
  if (!m) return null;
  const attrs = {};
  const re = /([A-Za-z_][\w-]*)=(?:"([^"]*)"|'([^']*)'|([^\s]+))/g;
  let hit;
  while ((hit = re.exec(m[1])) !== null) attrs[hit[1]] = hit[2] ?? hit[3] ?? hit[4] ?? '';
  const sourceId = attrs.source_id || attrs.sourceId || attrs.source || '';
  const page = Math.max(1, parseInt(attrs.page || attrs.p || '1', 10) || 1);
  const zoom = Math.min(4, Math.max(0.5, parseFloat(attrs.zoom || '2') || 2));
  const caption = attrs.caption || attrs.label || `슬라이드 ${sourceId} p.${page}`;
  if (!sourceId) return null;
  return { sourceId, page, zoom, caption };
}
function slideMarkerMarkdown(sourceId, page, caption, zoom) {
  const cap = String(caption || `슬라이드 ${sourceId} p.${page}`).replace(/"/g, '&quot;');
  const z = zoom ? ` zoom="${String(zoom).replace(/"/g, '&quot;')}"` : '';
  return `[[SLIDE_IMAGE source_id="${String(sourceId).replace(/"/g, '&quot;')}" page="${page}" caption="${cap}"${z}]]`;
}
function slideFigureHtml(info) {
  const safeSource = attr(info.sourceId);
  const safePage = attr(info.page || 1);
  const safeZoom = attr(info.zoom || 2);
  const safeCaption = attr(info.caption || `슬라이드 ${info.sourceId} p.${info.page || 1}`);
  return `<figure class="image-card slide-card" data-slide-source-id="${safeSource}" data-slide-page="${safePage}" data-slide-zoom="${safeZoom}" data-slide-caption="${safeCaption}"><button type="button" class="image-delete" contenteditable="false" aria-label="슬라이드 삭제">삭제</button><div class="slide-placeholder" contenteditable="false">슬라이드 불러오는 중 · ${safeSource} p.${safePage}</div><figcaption contenteditable="true">${esc(info.caption || `슬라이드 ${info.sourceId} p.${info.page || 1}`)}</figcaption></figure>`;
}
async function hydrateSlideImages() {
  const cards = Array.from(document.querySelectorAll('#doc figure.slide-card'));
  if (!cards.length) return;
  if (!actionKey()) {
    cards.forEach(card => {
      const ph = card.querySelector('.slide-placeholder');
      if (ph) ph.textContent = '슬라이드 자동 삽입 대기: 액션 키 입력 후 다시 열면 자동 로드됩니다.';
    });
    return;
  }
  await Promise.all(cards.map(async (card) => {
    if (card.dataset.loaded === 'true') return;
    const sourceId = card.dataset.slideSourceId;
    const page = Math.max(1, parseInt(card.dataset.slidePage || '1', 10) || 1);
    const zoom = Math.min(4, Math.max(0.5, parseFloat(card.dataset.slideZoom || '2') || 2));
    const caption = card.querySelector('figcaption')?.textContent?.trim() || card.dataset.slideCaption || `${sourceId} p.${page}`;
    try {
      const data = await api('/sources/' + encodeURIComponent(sourceId) + '/slide-image?page=' + page + '&zoom=' + zoom, { headers: headers(false) });
      card.dataset.loaded = 'true';
      card.dataset.mdSrc = data.data_url || '';
      const ph = card.querySelector('.slide-placeholder');
      if (ph) ph.remove();
      let img = card.querySelector('img');
      if (!img) {
        img = document.createElement('img');
        img.setAttribute('contenteditable', 'false');
        const capEl = card.querySelector('figcaption');
        card.insertBefore(img, capEl || null);
      }
      img.alt = caption;
      img.src = data.data_url;
      status('슬라이드 자동 삽입 완료');
    } catch (e) {
      const ph = card.querySelector('.slide-placeholder');
      if (ph) ph.textContent = '슬라이드 로드 실패: ' + (e.message || String(e));
      card.classList.add('slide-error');
    }
  }));
}
function enhanceImageCards() {
  document.querySelectorAll('#doc figure.image-card').forEach((figure) => {
    if (!figure.querySelector('.image-delete')) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'image-delete';
      btn.setAttribute('contenteditable', 'false');
      btn.setAttribute('aria-label', '이미지 삭제');
      btn.textContent = '삭제';
      figure.insertBefore(btn, figure.firstChild);
    }
  });
}
function inlineMarkdownToHtml(text) {
  const { out, stash } = protectMath(text);
  let html = esc(out);
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  html = html.replace(/&lt;mark&gt;([\s\S]*?)&lt;\/mark&gt;/g, '<mark>$1</mark>');
  return restoreStash(html, stash);
}

function normalizeMarkdownArtifacts(md) {
  return String(md || '')
    .replace(/\r\n/g, '\n')
    .split('\n')
    .map((line) => /^M\d+$/.test(line.trim()) ? '없음' : line)
    .join('\n');
}
function isTableSeparator(line) {
  return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line || '');
}
function isTableRow(line) {
  return /^\s*\|.*\|\s*$/.test(line || '');
}
function splitTableRow(line) {
  let raw = String(line || '').trim();
  if (raw.startsWith('|')) raw = raw.slice(1);
  if (raw.endsWith('|')) raw = raw.slice(0, -1);
  return raw.split('|').map((cell) => cell.trim());
}
function tableToHtml(tableLines) {
  const header = splitTableRow(tableLines[0]);
  const bodyLines = tableLines.slice(2).filter(isTableRow);
  const head = `<thead><tr>${header.map((cell) => `<th>${inlineMarkdownToHtml(cell)}</th>`).join('')}</tr></thead>`;
  const body = bodyLines.length
    ? `<tbody>${bodyLines.map((line) => `<tr>${splitTableRow(line).map((cell) => `<td>${inlineMarkdownToHtml(cell)}</td>`).join('')}</tr>`).join('')}</tbody>`
    : '<tbody></tbody>';
  return `<div class="table-wrap"><table>${head}${body}</table></div>`;
}

function removeImageInsertionPlanSections(md) {
  const lines = String(md || '').split('\n');
  const out = [];
  for (let i = 0; i < lines.length; i += 1) {
    const trimmed = lines[i].trim();
    const isImagePlanHeading = /^#{1,6}\s*\d*\.?\s*(이미지|도표|표).*삽입\s*위치/.test(trimmed)
      || /^#{1,6}\s*\d*\.?\s*이미지\s*\/\s*도표\s*\/\s*표\s*삽입\s*위치/.test(trimmed);
    if (isImagePlanHeading) {
      i += 1;
      while (i < lines.length && !/^#{1,3}\s+/.test(lines[i].trim())) i += 1;
      i -= 1;
      continue;
    }
    if (/^\[이미지\s*삽입\s*위치\s+IMG[-_ ]?\d+\]/.test(trimmed)) {
      i += 1;
      while (i < lines.length && (lines[i].trim() === '' || /^[-*]\s+/.test(lines[i].trim()))) i += 1;
      i -= 1;
      continue;
    }
    out.push(lines[i]);
  }
  return out.join('\n').replace(/\n{3,}/g, '\n\n');
}
function visibleText(value) {
  return String(value || '').replace(/[\s\u00a0\u200b\u200c\u200d\ufeff]+/g, ' ').trim();
}
function isDecorativeCodeBlock(code) {
  const visible = visibleText(code);
  if (!visible) return true;
  if (/^[─━_\-=|+•·.\[\](){}\\/]+$/.test(visible)) return true;
  return false;
}
function looksLikeRealCode(code, lang) {
  const l = String(lang || '').trim().toLowerCase();
  if (['python','py','javascript','js','typescript','ts','json','yaml','yml','html','css','sql','bash','sh','xml','toml','ini','prgm','casio'].includes(l)) return true;
  const c = String(code || '');
  if (/^\s*[{\[]/.test(c) && /[}\]]\s*$/.test(c)) return true;
  if (/\b(function|class|def|import|from|const|let|var|return|SELECT|INSERT|UPDATE|DELETE|CREATE|for\s*\(|while\s*\()\b/.test(c)) return true;
  if (/[{};]\s*$/.test(c.trim()) && /[=<>]/.test(c)) return true;
  return false;
}
function codeBlockToHtml(code, lang = '') {
  if (isDecorativeCodeBlock(code)) return '';
  const normalized = String(code || '').replace(/\n{3,}/g, '\n\n').trim();
  if (!looksLikeRealCode(normalized, lang)) {
    const rows = normalized.split('\n').map((line) => `<div>${inlineMarkdownToHtml(line || ' ')}</div>`).join('');
    return `<div class="flow-box">${rows}</div>`;
  }
  return `<pre class="code-block"><code>${esc(normalized)}</code></pre>`;
}

function markdownToHtml(md) {
  md = normalizeMarkdownArtifacts(md);
  const blocks = [];
  const lines = md.split('\n');
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i += 1; continue; }
    if (line.startsWith('```')) {
      const lang = line.replace(/^```/, '').trim();
      const code = [];
      i += 1;
      while (i < lines.length && !lines[i].startsWith('```')) { code.push(lines[i]); i += 1; }
      i += 1;
      const block = codeBlockToHtml(code.join('\n'), lang);
      if (block) blocks.push(block);
      continue;
    }
    const slideMarker = parseSlideMarker(line);
    if (slideMarker) {
      blocks.push(slideFigureHtml(slideMarker));
      i += 1; continue;
    }
    const image = line.match(/^!\[([^\]]*)\]\((.+)\)$/);
    if (image) {
      blocks.push(imageFigureHtml(image[1] || '이미지', image[2]));
      i += 1; continue;
    }
    if (isTableRow(line) && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      const tableLines = [line, lines[i + 1]];
      i += 2;
      while (i < lines.length && isTableRow(lines[i])) { tableLines.push(lines[i]); i += 1; }
      blocks.push(tableToHtml(tableLines));
      continue;
    }
    const heading = line.match(/^(#{1,6})\s+(.+)$/);
    if (heading) { const level = heading[1].length; blocks.push(`<h${level}>${inlineMarkdownToHtml(heading[2])}</h${level}>`); i += 1; continue; }
    if (/^[-*]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i])) { items.push(`<li>${inlineMarkdownToHtml(lines[i].replace(/^[-*]\s+/, ''))}</li>`); i += 1; }
      blocks.push(`<ul>${items.join('')}</ul>`); continue;
    }
    const para = [line]; i += 1;
    while (i < lines.length && lines[i].trim() && !/^(#{1,6})\s+/.test(lines[i]) && !/^[-*]\s+/.test(lines[i]) && !lines[i].startsWith('```') && !/^!\[/.test(lines[i]) && !parseSlideMarker(lines[i])) { para.push(lines[i]); i += 1; }
    blocks.push(`<p>${inlineMarkdownToHtml(para.join('\n')).replace(/\n/g, '<br>')}</p>`);
  }
  return blocks.join('\n') || '<p class="placeholder">왼쪽 목록에서 정리본을 열거나 새 정리본을 만드세요.</p>';
}
async function typesetDocument() { if (window.MathJax?.typesetPromise) { try { await MathJax.typesetPromise([$('doc')]); } catch (_) {} } }
async function renderMarkdown(md) { isRendering = true; md = normalizeMarkdownArtifacts(md); $('markdown').value = String(md || ''); $('doc').innerHTML = markdownToHtml(md); enhanceImageCards(); await hydrateSlideImages(); await typesetDocument(); isRendering = false; }

function inlineToMarkdown(node) {
  if (node.nodeType === Node.TEXT_NODE) return node.nodeValue || '';
  if (node.nodeType !== Node.ELEMENT_NODE) return '';
  const el = node, tag = el.tagName.toLowerCase();
  if (el.dataset?.tex) return el.dataset.tex;
  if (tag === 'mjx-container') return el.closest('[data-tex]')?.dataset?.tex || '';
  if (tag === 'br') return '\n';
  const body = Array.from(el.childNodes).map(inlineToMarkdown).join('');
  if (tag === 'strong' || tag === 'b') return `**${body}**`;
  if (tag === 'code') return '`' + body + '`';
  if (tag === 'mark') return `<mark>${body}</mark>`;
  return body;
}

function tableElementToMarkdown(table) {
  const rows = Array.from(table.querySelectorAll('tr'));
  if (!rows.length) return '';
  const matrix = rows.map((tr) => Array.from(tr.children).map((cell) => inlineToMarkdown(cell).replace(/\n/g, ' ').trim()));
  const colCount = Math.max(...matrix.map((row) => row.length));
  const pad = (row) => Array.from({ length: colCount }, (_, idx) => row[idx] || '');
  const header = pad(matrix[0]);
  const sep = header.map(() => '---');
  const body = matrix.slice(1).map(pad);
  return [header, sep, ...body].map((row) => '| ' + row.join(' | ') + ' |').join('\n');
}

function blockToMarkdown(el) {
  if (el.nodeType === Node.TEXT_NODE) return (el.nodeValue || '').trim();
  if (el.nodeType !== Node.ELEMENT_NODE) return '';
  const tag = el.tagName.toLowerCase();
  if (el.dataset?.tex) return el.dataset.tex;
  if (tag === 'h1') return '# ' + inlineToMarkdown(el);
  if (tag === 'h2') return '## ' + inlineToMarkdown(el);
  if (tag === 'h3') return '### ' + inlineToMarkdown(el);
  if (tag === 'h4') return '#### ' + inlineToMarkdown(el);
  if (tag === 'h5') return '##### ' + inlineToMarkdown(el);
  if (tag === 'h6') return '###### ' + inlineToMarkdown(el);
  if (tag === 'table') return tableElementToMarkdown(el);
  if (tag === 'div' && el.classList.contains('table-wrap')) { const table = el.querySelector('table'); return table ? tableElementToMarkdown(table) : ''; }
  if (tag === 'ul') return Array.from(el.children).filter(li => li.tagName.toLowerCase() === 'li').map(li => '- ' + inlineToMarkdown(li)).join('\n');
  if (tag === 'ol') return Array.from(el.children).filter(li => li.tagName.toLowerCase() === 'li').map((li, idx) => `${idx + 1}. ${inlineToMarkdown(li)}`).join('\n');
  if (tag === 'div' && el.classList.contains('flow-box')) return inlineToMarkdown(el).trim();
  if (tag === 'pre') return '```\n' + (el.textContent || '') + '\n```';
  if (tag === 'figure') {
    const cap = el.querySelector('figcaption')?.textContent?.trim() || el.dataset.slideCaption || '이미지';
    if (el.classList.contains('slide-card')) {
      const sourceId = el.dataset.slideSourceId || '';
      const page = Math.max(1, parseInt(el.dataset.slidePage || '1', 10) || 1);
      const zoom = el.dataset.slideZoom || '2';
      return sourceId ? slideMarkerMarkdown(sourceId, page, cap, zoom) : '';
    }
    const img = el.querySelector('img');
    const src = el.dataset.mdSrc || img?.src || '';
    return src ? `![${cap}](${src})` : '';
  }
  if (tag === 'img') return `![${el.alt || '이미지'}](${el.src})`;
  if (tag === 'p' || tag === 'div') return inlineToMarkdown(el).trim();
  return inlineToMarkdown(el).trim();
}
function documentToMarkdown() { const blocks = Array.from($('doc').childNodes).map(blockToMarkdown).filter(v => v && v.trim()); return blocks.join('\n\n').replace(/\n{3,}/g, '\n\n').trim() + '\n'; }
function syncMarkdownFromDocument() { if (isRendering) return; $('markdown').value = documentToMarkdown(); status('수정됨'); }

async function listNotes() {
  try { remember(); const params = new URLSearchParams(); if (subject()) params.set('subject', subject()); if ($('sourceType').value) params.set('source_type', $('sourceType').value); const data = await api('/study/notes?' + params, { headers: headers(false) }); const list = data.notes || []; $('list').innerHTML = list.length ? '' : '<div class="item"><span>저장된 정리본이 없습니다.</span></div>'; for (const n of list) { const div = document.createElement('button'); div.type = 'button'; div.className = 'item'; div.onclick = () => openNote(n.source_id); div.innerHTML = `<b>${esc(n.title)}</b><span>${esc(n.subject || '미지정')} · ${esc(n.source_type)} · ${esc(n.source_id)}</span>`; $('list').appendChild(div); } status('목록 불러옴'); } catch (e) { status('오류'); alert(e.message); }
}
async function openNote(id) { try { const data = await api('/study/notes/' + encodeURIComponent(id), { headers: headers(false) }); currentSourceId = id; currentSourceType = data.source?.source_type || 'generated_note'; $('title').value = data.source?.title || ''; await renderMarkdown(data.markdown || ''); status('열림: ' + id); } catch (e) { alert(e.message); } }
async function newNote(type) { currentSourceId = ''; currentSourceType = type; $('title').value = type === 'exam_cram' ? '시험 직전 정리' : '새 정리본'; const initial = type === 'exam_cram' ? '# 시험 직전 정리\n\n## 1. 직전 암기\n\n## 2. 오답 주의사항\n\n## 3. 주요 개념\n\n## 4. 마지막 확인\n' : '# 새 정리본\n\n내용을 입력하세요. 수식은 $...$ 또는 $$...$$ 형태로 유지됩니다.\n'; await renderMarkdown(initial); status('새 문서'); }
async function saveNote() { try { syncMarkdownFromDocument(); const payload = { title: $('title').value.trim() || 'Untitled', content_markdown: $('markdown').value, change_summary: 'edited in Study Note Studio' }; let data; if (currentSourceId) data = await api('/study/notes/' + encodeURIComponent(currentSourceId), { method: 'PUT', headers: headers(), body: JSON.stringify(payload) }); else { data = await api('/study/notes', { method: 'POST', headers: headers(), body: JSON.stringify({ ...payload, subject: subject(), source_type: currentSourceType, replace_latest: false }) }); currentSourceId = data.source_id; } status('저장됨'); await listNotes(); return data; } catch (e) { status('오류'); alert(e.message); } }

function wrapRangeWithMark(range) { const mark = document.createElement('mark'); try { range.surroundContents(mark); } catch (_) { const contents = range.extractContents(); mark.appendChild(contents); range.insertNode(mark); } }
function highlightSelection() { const sel = window.getSelection(); if (!sel || !sel.rangeCount || sel.isCollapsed) return alert('형광펜 칠할 텍스트를 먼저 드래그해서 선택하세요.'); const range = sel.getRangeAt(0); if (!$('doc').contains(range.commonAncestorContainer)) return alert('정리본 본문 안의 텍스트를 선택하세요.'); wrapRangeWithMark(range); sel.removeAllRanges(); syncMarkdownFromDocument(); }
function clearHighlight() { document.querySelectorAll('#doc mark').forEach(mark => mark.replaceWith(...mark.childNodes)); syncMarkdownFromDocument(); }
function insertNodeAtSelection(node) { const sel = window.getSelection(); if (sel && sel.rangeCount && $('doc').contains(sel.getRangeAt(0).commonAncestorContainer)) { const range = sel.getRangeAt(0); range.deleteContents(); range.insertNode(node); range.setStartAfter(node); range.setEndAfter(node); sel.removeAllRanges(); sel.addRange(range); } else $('doc').appendChild(node); }
function insertImage(ev) { const file = ev.target.files?.[0]; if (!file) return; const reader = new FileReader(); reader.onload = () => { const figure = document.createElement('figure'); figure.className = 'image-card'; figure.dataset.mdSrc = reader.result; figure.innerHTML = `<button type="button" class="image-delete" contenteditable="false" aria-label="이미지 삭제">삭제</button><img alt="${attr(file.name)}" src="${attr(reader.result)}" contenteditable="false"><figcaption contenteditable="true">${esc(file.name)}</figcaption>`; insertNodeAtSelection(figure); syncMarkdownFromDocument(); }; reader.readAsDataURL(file); ev.target.value = ''; }
async function insertSlideImage() {
  try {
    const sourceId = prompt('삽입할 강의자료 PDF source_id를 입력하세요.\n파일 관리/상태판에서 확인할 수 있습니다.');
    if (!sourceId) return;
    const pageRaw = prompt('삽입할 슬라이드 페이지 번호를 입력하세요.', '1');
    if (!pageRaw) return;
    const page = Math.max(1, parseInt(pageRaw, 10) || 1);
    const caption = prompt('이미지 캡션을 입력하세요.', `${sourceId.trim()} p.${page}`) || `${sourceId.trim()} p.${page}`;
    const wrap = document.createElement('div');
    wrap.innerHTML = slideFigureHtml({ sourceId: sourceId.trim(), page, zoom: 2, caption });
    const figure = wrap.firstElementChild;
    insertNodeAtSelection(figure);
    await hydrateSlideImages();
    syncMarkdownFromDocument();
    status('슬라이드 삽입됨');
  } catch (e) {
    alert(e.message || String(e));
  }
}

async function toggleSource() { const dialog = $('sourceDialog'); if (dialog.open) { await renderMarkdown($('markdown').value); dialog.close(); } else { syncMarkdownFromDocument(); dialog.showModal(); } }
function downloadMd() { if (!currentSourceId) return alert('먼저 저장하세요.'); location.href = '/study/notes/' + encodeURIComponent(currentSourceId) + '/download.md'; }
function downloadDocx() { if (!currentSourceId) return alert('먼저 저장하세요.'); window.open('/study/notes/' + encodeURIComponent(currentSourceId) + '/download.docx', '_blank'); }
function printPdf() { if (!currentSourceId) return alert('먼저 저장하세요.'); window.open('/study/notes/' + encodeURIComponent(currentSourceId) + '/print', '_blank'); }


$('doc').addEventListener('click', (ev) => {
  const btn = ev.target.closest?.('.image-delete');
  if (!btn || !$('doc').contains(btn)) return;
  ev.preventDefault();
  ev.stopPropagation();
  const figure = btn.closest('figure.image-card');
  if (figure && confirm('이 이미지를 삭제할까요?')) {
    figure.remove();
    syncMarkdownFromDocument();
  }
});
$('doc').addEventListener('input', syncMarkdownFromDocument);
$('doc').addEventListener('paste', (ev) => { ev.preventDefault(); const text = ev.clipboardData?.getData('text/plain') || ''; document.execCommand('insertText', false, text); });
$('markdown').addEventListener('input', () => status('원문 수정됨'));
restore(); renderMarkdown(''); if (actionKey()) listNotes(); else status('액션 키 입력 후 목록 불러오기');
