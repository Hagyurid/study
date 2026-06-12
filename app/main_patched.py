from __future__ import annotations

from collections import Counter
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import quote

from fastapi import HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.routing import APIRoute

from app import main as _main

app = _main.app


def _drop_route(path: str, methods: Optional[Set[str]] = None) -> None:
    methods = {m.upper() for m in (methods or {"GET"})}
    kept = []
    for route in app.router.routes:
        if isinstance(route, APIRoute) and route.path == path:
            route_methods = {m.upper() for m in (route.methods or set())}
            if route_methods & methods:
                continue
        kept.append(route)
    app.router.routes[:] = kept


@lru_cache(maxsize=6)
def _render_pdf_page_png_bytes(stored_path: str, mtime_ns: int, page: int, zoom: float) -> Dict[str, Any]:
    try:
        import fitz  # PyMuPDF
    except Exception:
        raise HTTPException(status_code=500, detail="PDF slide rendering package is not installed. Add PyMuPDF to requirements.txt and redeploy.")
    try:
        doc = fitz.open(stored_path)
        try:
            if page > len(doc):
                raise HTTPException(status_code=400, detail=f"Page out of range. This PDF has {len(doc)} pages.")
            pdf_page = doc[page - 1]
            matrix = fitz.Matrix(zoom, zoom)
            pix = pdf_page.get_pixmap(matrix=matrix, alpha=False)
            png = pix.tobytes("png")
            return {"page_count": len(doc), "png_bytes": png}
        finally:
            doc.close()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to render slide page: {exc}")


def _render_slide_data(source_id: str, page: int = 1, zoom: float = 2.0) -> dict:
    source = _main.get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    stored_path = Path(source.get("stored_path") or "")
    if not stored_path.exists():
        raise HTTPException(status_code=404, detail="Stored file not found")
    suffix = stored_path.suffix.lower()
    if suffix != ".pdf" and "pdf" not in (source.get("mime_type") or "").lower():
        raise HTTPException(status_code=400, detail="Slide image rendering currently supports PDF lecture slides only")
    page = max(1, int(page or 1))
    zoom = min(4.0, max(0.5, float(zoom or 2.0)))
    stat = stored_path.stat()
    rendered = _render_pdf_page_png_bytes(str(stored_path), int(stat.st_mtime_ns), page, zoom)
    label = f"{source.get('title') or source.get('original_name') or source_id} p.{page}"
    return {
        "source_id": source_id,
        "page": page,
        "page_count": rendered["page_count"],
        "label": label,
        "png_bytes": rendered["png_bytes"],
    }


_drop_route("/slides/render.png")


@app.get("/slides/render.png")
def render_slide_png(
    source_id: str = Query(...),
    page: int = Query(default=1),
    zoom: float = Query(default=2.0),
):
    data = _render_slide_data(source_id, page, zoom)
    return Response(
        content=data["png_bytes"],
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )


def _slide_image_src(marker: Dict[str, Any]) -> str:
    source_id = quote(str(marker["source_id"]), safe="")
    page = max(1, int(marker["page"]))
    zoom = min(4.0, max(0.5, float(marker["zoom"])))
    return f"/slides/render.png?source_id={source_id}&page={page}&zoom={zoom:g}"


def _slide_marker_html(line: str, render_image: bool = True) -> Optional[str]:
    marker = _main._parse_slide_marker(line)
    if not marker:
        return None
    caption = marker.get("caption") or f"{marker['source_id']} p.{marker['page']}"
    attrs = _main._image_figure_attrs(marker.get("size", 100))
    if not render_image:
        return (
            f"<figure class='image-card slide-card'{attrs}>"
            f"<div class='flow-box'>슬라이드 이미지: {escape(caption)} · source_id={escape(marker['source_id'])} · page={escape(marker['page'])}</div>"
            f"<figcaption>{escape(caption)}</figcaption>"
            "</figure>"
        )
    try:
        src = _slide_image_src(marker)
        return (
            f"<figure class='image-card slide-card'{attrs}>"
            f"<img alt='{escape(caption)}' src='{escape(src)}' loading='lazy'/>"
            f"<figcaption>{escape(caption)}</figcaption>"
            "</figure>"
        )
    except Exception as exc:
        return (
            f"<figure class='image-card slide-card slide-error'{attrs}>"
            f"<div class='flow-box'>슬라이드 삽입 실패: {escape(str(exc))}</div>"
            f"<figcaption>{escape(caption)}</figcaption>"
            "</figure>"
        )


_main._render_slide_data = _render_slide_data
_main._slide_marker_html = _slide_marker_html


def _home_body() -> str:
    return """
<section class="top">
  <div>
    <h1>LectureNote Suite</h1>
    <p>자료 업로드, 정리본, 문제팩, 계산기 프로젝트를 한 흐름으로 다루는 작업 허브입니다.</p>
    <div class="nav">
      <a class="btn" href="/upload">자료 업로드</a>
      <a class="btn secondary" href="/sources/manage">파일 관리</a>
      <a class="btn secondary" href="/status">상태판</a>
    </div>
  </div>
</section>
<section class="grid">
  <div class="card"><h2>업로드</h2><p>강의자료·교재·전사본·기출을 과목별로 정리해 올립니다.</p><div class="actions"><a class="btn" href="/upload">열기</a></div></div>
  <div class="card"><h2>정리본</h2><p>GPT 생성 정리본, 외부 정리본, 시험 직전 정리를 확인하고 수정합니다.</p><div class="actions"><a class="btn secondary" href="/static/study/index.html">정리본 보기</a></div></div>
  <div class="card"><h2>SolvePad</h2><p>문제팩을 불러와 문제지와 해설지 흐름으로 관리합니다.</p><div class="actions"><a class="btn secondary" href="/static/solvepad/index.html">열기</a></div></div>
  <div class="card"><h2>계산기 PRGM</h2><p>계산기 코드, 사용법, 분석 문서를 한 곳에서 관리합니다.</p><div class="actions"><a class="btn secondary" href="/static/casio/index.html">열기</a></div></div>
</section>
"""


_drop_route("/", {"GET"})


@app.get("/", response_class=HTMLResponse)
def root():
    return _main._page("LectureNote Suite", _home_body())


_drop_route("/notes/upload", {"GET"})


@app.get("/notes/upload")
def notes_upload_page():
    return RedirectResponse(url="/upload", status_code=307)


_drop_route("/status", {"GET"})


@app.get("/status", response_class=HTMLResponse)
def status_page():
    body = """
<section class="top">
  <div>
    <h1>상태판</h1>
    <p>요약을 먼저 보고, 필요할 때만 매핑 상세를 추가로 불러오도록 정리했습니다.</p>
  </div>
  <div class="nav">
    <a class="btn secondary" href="/">홈</a>
    <a class="btn secondary" href="/sources/manage">파일 관리</a>
  </div>
</section>
<section class="card">
  <label>액션 키</label>
  <input name="action_key" type="password" placeholder="Render 환경변수 ACTION_API_KEY" autocomplete="off"/>
  <div class="keybox"><span class="key-status" data-key-status></span><button class="btn secondary" type="button" data-clear-key>저장된 키 지우기</button></div>
  <label>과목명</label>
  <input name="subject" placeholder="예: CRE, 반응공학"/>
  <div class="actions">
    <button type="button" id="loadOverview">요약 불러오기</button>
    <button type="button" class="btn secondary" id="loadMapping">매핑 상세 불러오기</button>
  </div>
</section>
<section class="grid" style="margin-top:16px">
  <div class="card"><h2>총 자료</h2><div id="sumSource" class="muted">-</div></div>
  <div class="card"><h2>정리본</h2><div id="sumNotes" class="muted">-</div></div>
  <div class="card"><h2>문제팩</h2><div id="sumPacks" class="muted">-</div></div>
  <div class="card"><h2>미매핑 자료</h2><div id="sumUnmapped" class="muted">-</div></div>
</section>
<section class="grid" style="margin-top:16px">
  <div class="card"><h2>요약 상세</h2><div id="overviewPanel" class="muted">요약을 불러오세요.</div></div>
  <div class="card"><h2>매핑 상세</h2><div id="mappingPanel" class="muted">매핑 상세를 불러오세요.</div></div>
</section>
<script>
(function(){
  function el(id){return document.getElementById(id);}
  function key(){return (document.querySelector("input[name='action_key']")?.value || '').trim();}
  function subject(){return (document.querySelector("input[name='subject']")?.value || '').trim();}
  function esc(v){return String(v ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
  function headers(){return {Authorization: 'Bearer ' + key()};}
  function qs(){return subject() ? '?subject=' + encodeURIComponent(subject()) : '';}
  function badge(label, value){return '<div style="display:flex;justify-content:space-between;gap:12px;padding:10px 0;border-bottom:1px solid #e4e7ec"><span>'+esc(label)+'</span><b>'+esc(value)+'</b></div>';}
  function recentList(items){
    if(!items || !items.length) return '<p class="muted">없음</p>';
    return '<ul>' + items.map(item => '<li><b>'+esc(item.title || item.sourceId || item.id || '항목')+'</b><div class="hint">'+esc(item.createdAt || item.created_at || '')+'</div></li>').join('') + '</ul>';
  }
  async function loadOverview(){
    if(!key()){ alert('액션 키를 입력하세요.'); return; }
    el('overviewPanel').textContent = '불러오는 중...';
    try {
      const res = await fetch('/dashboard' + qs(), {headers: headers()});
      if(!res.ok) throw new Error(await res.text());
      const data = await res.json();
      const summary = data.summary || {};
      el('sumSource').textContent = summary.sourceCount ?? 0;
      el('sumNotes').textContent = summary.studyNoteCount ?? 0;
      el('sumPacks').textContent = summary.problemPackCount ?? 0;
      el('sumUnmapped').textContent = summary.unmappedSourceCount ?? 0;
      let html = '';
      html += badge('자료 유형 수', summary.sourceTypeCount ?? 0);
      html += badge('단원 맵 수', summary.unitMapCount ?? 0);
      html += badge('단원 수', summary.unitCount ?? 0);
      html += badge('진행 중 workflow', summary.activeWorkflowRunCount ?? 0);
      html += '<details style="margin-top:14px" open><summary>최근 자료</summary>' + recentList(data.recentSources || []) + '</details>';
      html += '<details style="margin-top:10px"><summary>경고</summary>' + ((data.warnings || []).length ? '<ul>' + data.warnings.map(w => '<li>'+esc(w.message || w.type || 'warning')+'</li>').join('') + '</ul>' : '<p class="muted">없음</p>') + '</details>';
      el('overviewPanel').innerHTML = html;
    } catch (e) {
      el('overviewPanel').textContent = '오류';
      alert(String(e.message || e));
    }
  }
  async function loadMapping(){
    if(!key()){ alert('액션 키를 입력하세요.'); return; }
    el('mappingPanel').textContent = '불러오는 중...';
    try {
      const res = await fetch('/mapping/status' + qs(), {headers: headers()});
      if(!res.ok) throw new Error(await res.text());
      const data = await res.json();
      const summary = data.summary || {};
      let html = '';
      html += badge('매핑된 자료', summary.mappedSourceCount ?? 0);
      html += badge('미매핑 자료', summary.unmappedSourceCount ?? 0);
      html += badge('누락 참조', summary.deletedOrMissingReferenceCount ?? 0);
      html += '<details style="margin-top:14px" open><summary>미매핑 자료</summary>' + recentList(data.unmappedSources || []) + '</details>';
      html += '<details style="margin-top:10px"><summary>단원 맵</summary>' + recentList(data.unitMaps || []) + '</details>';
      el('mappingPanel').innerHTML = html;
      el('sumUnmapped').textContent = summary.unmappedSourceCount ?? 0;
    } catch (e) {
      el('mappingPanel').textContent = '오류';
      alert(String(e.message || e));
    }
  }
  document.addEventListener('DOMContentLoaded', function(){
    el('loadOverview')?.addEventListener('click', loadOverview);
    el('loadMapping')?.addEventListener('click', loadMapping);
  });
})();
</script>
"""
    return _main._page("LectureNote Suite 상태판", body)


_drop_route("/sources/manage", {"GET"})


@app.get("/sources/manage", response_class=HTMLResponse)
def manage_sources_page(subject: str = Query(default=""), source_type: str = Query(default=""), action_key: str = Query(default="")):
    valid_types = {value for value, _label in _main.SOURCE_TYPES}
    if source_type and source_type not in valid_types:
        source_type = ""

    rows: List[str] = []
    for s in _main.list_sources(source_type=source_type, subject=subject):
        raw_sid = s.get("id", "")
        sid = escape(raw_sid)
        title = escape(s.get("title", ""))
        subject_label = escape(s.get("subject", "") or "미지정")
        source_label = escape(_main._source_type_label(s.get("source_type", "")))
        original_name = escape(s.get("original_name", ""))
        created_at = escape(s.get("created_at", ""))
        search_text = escape(" ".join([str(s.get("title", "")), str(s.get("original_name", "")), str(s.get("subject", "")), str(s.get("source_type", "")), raw_sid]).lower())
        rows.append(
            "<tr class='source-row' "
            f"data-search='{search_text}' data-source-id='{sid}' data-title='{title}' data-subject='{subject_label}' data-type-label='{source_label}' data-file='{original_name}' data-created='{created_at}' onclick='window.previewSourceRow(this)'>"
            f"<td><input type='checkbox' name='source_ids' value='{sid}' data-source-check data-type-label='{source_label}' data-title='{title}' onclick='event.stopPropagation()'/></td>"
            f"<td><span class='pill subject-pill'>{subject_label}</span></td>"
            f"<td><span class='type-label'>{source_label}</span><div class='hint'>{escape(s.get('source_type',''))}</div></td>"
            f"<td><b>{title}</b><div class='hint'><code>{sid}</code></div></td>"
            f"<td>{original_name}</td>"
            f"<td>{created_at}</td>"
            f"<td><button class='danger' type='submit' name='source_ids' value='{sid}' data-action='delete' formaction='/sources/delete-batch' onclick='event.stopPropagation(); return confirm(\'이 자료를 삭제할까요?\');'>삭제</button></td>"
            "</tr>"
        )
    table_rows = "\n".join(rows) or "<tr><td colspan='7' class='muted'>업로드된 자료가 없습니다.</td></tr>"

    body = f"""
<section class='top'>
  <div>
    <h1>업로드 파일 관리</h1>
    <p>필터, 선택 작업, 출력, 이름 변경, 삭제를 한 흐름으로 정리했습니다.</p>
  </div>
  <div class='nav'>
    <a class='btn secondary' href='/upload'>자료 업로드</a>
    <a class='btn secondary' href='/status?subject={escape(subject)}'>상태판</a>
    <a class='btn secondary' href='/'>홈</a>
  </div>
</section>
<section class='card'>
  <form method='get' action='/sources/manage'>
    <label>과목 필터</label>
    <input name='subject' value='{escape(subject)}' placeholder='예: CRE, 반응공학'/>
    <label>유형 필터</label>
    <select name='source_type'><option value='' {'selected' if not source_type else ''}>전체 유형</option>{_main._options(source_type)}</select>
    <label>액션 키</label>
    <input name='action_key' type='password' value='{escape(action_key)}' placeholder='처음 한 번 입력하면 자동 저장'/>
    <div class='keybox'><span class='key-status' data-key-status></span><button class='btn secondary' type='button' data-clear-key>저장된 키 지우기</button></div>
    <label>목록 검색</label>
    <input id='tableFilter' placeholder='제목, 파일명, 과목, source_id 검색'/>
    <div class='actions'>
      <button type='submit'>적용</button>
      <a class='btn secondary' href='/sources/manage?action_key={escape(action_key)}'>필터 초기화</a>
    </div>
  </form>
</section>
<section id='sourcePreview' class='card' style='margin-top:16px'>
  <h2>선택 미리보기</h2>
  <p class='muted'>행을 눌러 제목, 과목, 유형, 파일명을 빠르게 확인하세요.</p>
</section>
<section class='card' style='margin-top:16px;overflow:auto'>
  <form method='post' id='bulkForm'>
    <input type='hidden' name='action_key' value='{escape(action_key)}'/>
    <input type='hidden' name='subject' value='{escape(subject)}'/>
    <input type='hidden' name='source_type' value='{escape(source_type)}'/>

    <div id='selectionBar' class='card' style='display:none;position:sticky;top:12px;z-index:12;margin:0 0 14px;border-radius:18px;border:1px solid #c7d7fe;background:#f8faff'>
      <div style='display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap;align-items:flex-start'>
        <div>
          <h2 style='margin:0 0 6px'>선택 작업</h2>
          <div id='selectionSummary' class='muted'>0개 선택됨</div>
          <div id='selectionTitles' class='hint' style='margin-top:6px'></div>
        </div>
        <label style='margin:0;display:flex;gap:8px;align-items:center'><input type='checkbox' id='selectAllSources'/> 전체 선택</label>
      </div>
      <div class='grid' style='margin-top:14px'>
        <div class='card' style='padding:16px'>
          <h2 style='font-size:16px'>문서 출력</h2>
          <div class='actions'>
            <button class='btn secondary bulk-action' type='submit' data-action='print-docs' formaction='/sources/print-bundle' formtarget='_blank'>통합 PDF</button>
            <button class='btn secondary bulk-action' type='submit' data-action='download-pdf' formaction='/sources/download-bundle.pdf'>바로 다운로드</button>
          </div>
        </div>
        <div class='card' style='padding:16px'>
          <h2 style='font-size:16px'>문제팩 출력</h2>
          <div class='actions'>
            <button class='btn secondary bulk-action' type='submit' data-action='print-questions' formaction='/sources/problem-packs/print?mode=questions' formtarget='_blank'>문제지 PDF</button>
            <button class='btn secondary bulk-action' type='submit' data-action='print-solutions' formaction='/sources/problem-packs/print?mode=solutions' formtarget='_blank'>해설지 PDF</button>
          </div>
        </div>
        <div class='card' style='padding:16px'>
          <h2 style='font-size:16px'>이름 변경 / 정리</h2>
          <label style='margin:0 0 6px'>새 표시 파일명</label>
          <input name='new_name' placeholder='여러 개면 {{n}} 사용 가능'/>
          <div class='hint'>예: 전재설 Week{{n}} 강의자료</div>
          <label style='margin:12px 0 6px'>변경 대상</label>
          <select name='rename_target'><option value='title'>제목만</option><option value='original_name'>파일명 표시만</option><option value='both'>제목+파일명 표시</option></select>
          <div class='actions'>
            <button class='btn secondary bulk-action' type='submit' data-action='rename' formaction='/sources/rename-batch'>선택 파일명 변경</button>
            <button class='danger bulk-action' type='submit' data-action='delete' formaction='/sources/delete-batch'>선택 삭제</button>
          </div>
        </div>
      </div>
    </div>

    <table>
      <thead>
        <tr><th>선택</th><th>과목</th><th>유형</th><th>제목/source_id</th><th>파일</th><th>생성일</th><th>작업</th></tr>
      </thead>
      <tbody id='sourceTableBody'>
        {table_rows}
      </tbody>
    </table>
  </form>
</section>
<script>
(function(){{
  function q(sel, root=document){{ return Array.from(root.querySelectorAll(sel)); }}
  function el(id){{ return document.getElementById(id); }}
  function checkedBoxes(){{ return q('[data-source-check]:checked'); }}
  function updateSelectionBar(){{
    const boxes = checkedBoxes();
    const bar = el('selectionBar');
    const count = boxes.length;
    if (!bar) return;
    bar.style.display = count ? 'block' : 'none';
    const types = new Counter();
    const typeCount = {{}};
    boxes.forEach(cb => {{
      const t = cb.dataset.typeLabel || '기타';
      typeCount[t] = (typeCount[t] || 0) + 1;
    }});
    const typeSummary = Object.entries(typeCount).map(([k,v]) => `${{k}} ${{v}}`).join(' · ');
    el('selectionSummary').textContent = `${{count}}개 선택됨${{typeSummary ? ' · ' + typeSummary : ''}}`;
    el('selectionTitles').textContent = boxes.slice(0, 4).map(cb => cb.dataset.title || cb.value).join(' / ');
  }}
  function preview(row){{
    if(!row) return;
    const panel = el('sourcePreview');
    if(!panel) return;
    panel.innerHTML = `
      <h2>선택 미리보기</h2>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-top:10px">
        <div><div class="hint">제목</div><b>${{row.dataset.title || '-'}}</b></div>
        <div><div class="hint">과목</div><b>${{row.dataset.subject || '-'}}</b></div>
        <div><div class="hint">유형</div><b>${{row.dataset.typeLabel || '-'}}</b></div>
        <div><div class="hint">파일명</div><b>${{row.dataset.file || '-'}}</b></div>
      </div>
      <div class="hint" style="margin-top:10px"><code>${{row.dataset.sourceId || '-'}}</code> · ${{row.dataset.created || ''}}</div>
    `;
  }}
  window.previewSourceRow = preview;
  function applyFilter(){{
    const term = (el('tableFilter')?.value || '').trim().toLowerCase();
    q('.source-row').forEach(row => {{
      row.style.display = !term || (row.dataset.search || '').includes(term) ? '' : 'none';
    }});
  }}
  document.addEventListener('DOMContentLoaded', function(){{
    q('[data-source-check]').forEach(cb => cb.addEventListener('change', updateSelectionBar));
    el('tableFilter')?.addEventListener('input', applyFilter);
    el('selectAllSources')?.addEventListener('change', function(){{
      q('[data-source-check]').forEach(cb => {{ if(cb.closest('tr')?.style.display !== 'none') cb.checked = this.checked; }});
      updateSelectionBar();
    }});
    const form = el('bulkForm');
    form?.addEventListener('submit', function(event){{
      const submitter = event.submitter;
      const action = submitter?.dataset.action || '';
      const checked = checkedBoxes().length;
      if(!checked && !submitter?.value){{
        event.preventDefault();
        alert('대상 자료를 선택하세요.');
        return;
      }}
      if(action === 'rename'){{
        const name = form.querySelector('[name=new_name]')?.value?.trim() || '';
        if(!name){{
          event.preventDefault();
          alert('새 표시 파일명을 입력하세요.');
          return;
        }}
        if(!confirm(`${{checked}}개 자료의 표시 파일명을 변경할까요?`)) event.preventDefault();
        return;
      }}
      if(action === 'delete' && !submitter?.value){{
        if(!confirm(`${{checked}}개 자료를 삭제할까요?`)) event.preventDefault();
      }}
    }});
    const firstVisible = q('.source-row')[0];
    if(firstVisible) preview(firstVisible);
    updateSelectionBar();
  }});
}})();
</script>
"""
    return _main._page("업로드 파일 관리", body)
