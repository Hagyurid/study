from io import BytesIO
from pathlib import Path
from typing import List, Optional
from html import escape
import shutil
import tempfile
import zipfile
import base64
import re

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import ACTION_API_KEY, PUBLIC_BASE_URL, UPLOAD_DIR
from app.db import (
    create_project, create_workflow_plan, create_workflow_run, delete_source, delete_calculator_blueprint,
    export_project_note_as_source, final_bundle, get_latest_note_version,
    get_mapping_status, get_next_section, get_source_markdown, get_problem_pack_by_token, get_source,
    get_calculator_blueprint, get_unit_map, get_workflow_options, init_db, list_external_notes,
    list_note_versions, list_sources, list_study_notes, list_unit_maps, list_unmapped_sources,
    list_calculator_blueprints, list_workflow_checkpoints, list_workflow_plans, list_workflow_runs,
    save_calculator_blueprint, save_note_version, save_outline, save_problem_pack,
    save_project_items, save_section, save_source, save_text_source,
    save_transcript_revision, save_unit_map, save_workflow_checkpoint, update_source_markdown,
    search_sources, get_next_workflow_step,
)
from app.models import (
    CalculatorBlueprintSave, GenericItemsSave, NoteVersionSave, OutlineSave,
    ProblemPackSave, ProjectCreate, SearchRequest, SectionSave, TextSourceSave,
    TranscriptRevisionSave, UnitMapSave, WorkflowPlanCreate, WorkflowRunCreate,
    WorkflowCheckpointSave, StudyNoteSave, StudyNoteUpdate, ExamCramSave,
)
from app.modules.file_extract import extract_text
from app.modules.prgm_engine import generate_txt_files, validate_blueprint

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"

app = FastAPI(title="LectureNote Suite", version="1.8.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=False)
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
init_db()

SOURCE_TYPES = [
    ("lecture_slides", "강의 슬라이드"), ("textbook", "교재"), ("transcript", "전사본"),
    ("corrected_transcript", "보정 전사본"), ("past_exam", "시험지/기출"),
    ("exam_trend", "시험 정보/경향"), ("generated_note", "GPT 생성 정리본"),
    ("exam_cram", "시험 직전 정리"),
    ("external_note", "외부 정리본"), ("calculator_manual", "계산기 사용법/구조 해설"), ("note_example", "정리본 예시"),
]


def _is_authorized(authorization: Optional[str] = None, x_action_key: Optional[str] = None, action_key: str = "") -> bool:
    if not ACTION_API_KEY:
        return True
    return authorization == f"Bearer {ACTION_API_KEY}" or x_action_key == ACTION_API_KEY or action_key == ACTION_API_KEY


def require_auth(authorization: Optional[str] = Header(default=None), x_action_key: Optional[str] = Header(default=None)):
    if _is_authorized(authorization, x_action_key):
        return True
    raise HTTPException(status_code=401, detail="Invalid action key")


def _options(selected: str = "lecture_slides") -> str:
    return "\n".join(f'<option value="{v}" {"selected" if v == selected else ""}>{label}</option>' for v, label in SOURCE_TYPES)


def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/><title>{escape(title)}</title><style>
:root{{--bg:#f6f7fb;--card:#fff;--text:#171923;--muted:#667085;--line:#e4e7ec;--accent:#4f46e5;--accent2:#eef2ff;--danger:#d92d20;--ok:#047857}}*{{box-sizing:border-box}}body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Noto Sans KR',Arial,sans-serif;background:linear-gradient(180deg,#f8f9ff 0%,#f6f7fb 42%,#f3f4f8 100%);color:var(--text)}}.wrap{{max-width:1120px;margin:0 auto;padding:32px 20px 56px}}.top{{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:24px}}h1{{font-size:30px;line-height:1.2;margin:0 0 8px;letter-spacing:-.035em}}h2{{margin:0 0 8px;font-size:20px;letter-spacing:-.02em}}p{{margin:0;color:var(--muted);line-height:1.6}}.nav,.actions{{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}}a.btn,button,.btn{{border:0;border-radius:12px;padding:10px 14px;background:var(--accent);color:#fff;text-decoration:none;font-weight:750;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:6px}}a.btn.secondary,.btn.secondary{{background:var(--accent2);color:var(--accent)}}button.danger{{background:var(--danger)}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}}.card{{background:rgba(255,255,255,.92);border:1px solid var(--line);border-radius:22px;padding:22px;box-shadow:0 12px 34px rgba(16,24,40,.06);backdrop-filter:blur(8px)}}label{{display:block;font-weight:760;margin:16px 0 8px}}input,select{{width:100%;border:1px solid var(--line);border-radius:13px;padding:12px 13px;font-size:15px;background:white;outline:none}}input:focus,select:focus{{border-color:#818cf8;box-shadow:0 0 0 4px rgba(79,70,229,.12)}}input[type=file]{{padding:16px;border-style:dashed;background:#fbfcff}}.hint{{font-size:13px;color:var(--muted);margin-top:6px}}.keybox{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:8px}}.keybox label{{margin:0;font-weight:600;color:var(--muted);font-size:13px;display:flex;gap:6px;align-items:center}}.keybox input[type=checkbox]{{width:auto}}.key-status{{font-size:13px;color:var(--ok);font-weight:700}}table{{width:100%;border-collapse:collapse;background:white;border-radius:16px;overflow:hidden}}th,td{{border-bottom:1px solid var(--line);padding:12px;text-align:left;vertical-align:top;font-size:14px}}th{{background:#f9fafb;color:#344054;font-size:13px}}code{{background:#f2f4f7;padding:2px 6px;border-radius:6px}}.pill{{display:inline-block;padding:4px 8px;border-radius:999px;background:var(--accent2);color:var(--accent);font-size:12px;font-weight:800}}.muted{{color:var(--muted)}}.kbd{{border:1px solid var(--line);background:#fff;border-radius:8px;padding:2px 7px;font-size:12px;color:#344054}}@media(max-width:640px){{.top{{display:block}}.wrap{{padding:22px 14px}}h1{{font-size:25px}}}}</style></head><body><main class="wrap">{body}</main><script>
(function(){{
  const KEY = "lecturenote_action_key";
  const SUBJECT = "lecturenote_subject";
  function qs(sel, root=document){{ return Array.from(root.querySelectorAll(sel)); }}
  function setStatus(msg){{
    qs("[data-key-status]").forEach(el => el.textContent = msg || "");
  }}
  function fill(){{
    const savedKey = localStorage.getItem(KEY) || "";
    const savedSubject = localStorage.getItem(SUBJECT) || "";
    qs("input[name='action_key']").forEach(input => {{
      if (savedKey && !input.value) input.value = savedKey;
    }});
    qs("input[name='subject']").forEach(input => {{
      if (savedSubject && !input.value) input.value = savedSubject;
    }});
    if (savedKey) setStatus("이 브라우저에 저장된 액션 키를 자동 입력했습니다.");
  }}
  function remember(){{
    qs("input[name='action_key']").forEach(input => {{
      const v = (input.value || "").trim();
      if (v) localStorage.setItem(KEY, v);
    }});
    qs("input[name='subject']").forEach(input => {{
      const v = (input.value || "").trim();
      if (v) localStorage.setItem(SUBJECT, v);
    }});
  }}
  function clearKey(){{
    localStorage.removeItem(KEY);
    qs("input[name='action_key']").forEach(input => input.value = "");
    setStatus("저장된 액션 키를 삭제했습니다.");
  }}
  window.clearLectureNoteActionKey = clearKey;
  document.addEventListener("DOMContentLoaded", () => {{
    fill();
    qs("form").forEach(form => form.addEventListener("submit", remember));
    qs("input[name='action_key']").forEach(input => input.addEventListener("change", remember));
    qs("input[name='subject']").forEach(input => input.addEventListener("change", remember));
    qs("[data-clear-key]").forEach(btn => btn.addEventListener("click", clearKey));
  }});
}})();
</script></body></html>""")


async def _save_uploaded_file(file: UploadFile, source_type: str, subject: str, title: str = "") -> dict:
    suffix = Path(file.filename or "source.bin").suffix
    source_dir = UPLOAD_DIR / source_type
    source_dir.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    size = 0
    try:
        with open(tmp.name, "wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                out.write(chunk)
        safe_name = (file.filename or "file").replace("/", "_").replace("\\", "_")
        stored = source_dir / f"{Path(tmp.name).name}-{safe_name}"
        shutil.move(tmp.name, stored)
        text, status = extract_text(stored, safe_name, file.content_type or "")
        inferred_title = title.strip() or Path(safe_name).stem or "untitled"
        return save_source(inferred_title, source_type, safe_name, str(stored), file.content_type or "", size, text, status, subject=subject.strip())
    finally:
        Path(tmp.name).unlink(missing_ok=True)


def _upload_result(results: List[dict], subject: str = "") -> HTMLResponse:
    rows = "".join(f"<tr><td><code>{escape(r.get('source_id',''))}</code></td><td>{escape(r.get('title',''))}</td><td>{escape(r.get('subject',''))}</td><td><span class='pill'>{escape(r.get('source_type',''))}</span></td><td>{r.get('chunk_count',0)}</td><td>{escape(r.get('extract_status',''))}</td></tr>" for r in results)
    return _page("업로드 완료", f"<section class='top'><div><h1>업로드 완료</h1><p>{len(results)}개 파일을 저장했습니다.</p></div><div class='nav'><a class='btn secondary' href='/upload'>추가 업로드</a><a class='btn' href='/sources/manage?subject={escape(subject)}'>파일 관리</a></div></section><section class='card'><table><thead><tr><th>source_id</th><th>제목</th><th>과목</th><th>유형</th><th>chunks</th><th>상태</th></tr></thead><tbody>{rows}</tbody></table></section>")



def _simple_markdown_html(markdown: str) -> str:
    text = escape(markdown or "")
    text = re.sub(r"```([\s\S]*?)```", lambda m: f"<pre><code>{m.group(1)}</code></pre>", text)
    text = re.sub(r"^### (.*)$", r"<h3>\1</h3>", text, flags=re.M)
    text = re.sub(r"^## (.*)$", r"<h2>\1</h2>", text, flags=re.M)
    text = re.sub(r"^# (.*)$", r"<h1>\1</h1>", text, flags=re.M)
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r"<img alt='\1' src='\2'/>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = text.replace("&lt;mark&gt;", "<mark>").replace("&lt;/mark&gt;", "</mark>")
    blocks = []
    for block in re.split(r"\n{2,}", text):
        if re.match(r"\s*<(h\d|ul|pre|img|table|blockquote|mark)", block):
            blocks.append(block)
        else:
            blocks.append("<p>" + block.replace("\n", "<br/>") + "</p>")
    return "\n".join(blocks)


def _markdown_to_docx_bytes(title: str, markdown: str) -> BytesIO:
    from docx import Document
    from docx.shared import Inches
    from docx.enum.text import WD_COLOR_INDEX
    doc = Document()
    doc.add_heading(title or "Study Note", level=1)
    image_pattern = re.compile(r"!\[([^\]]*)\]\((data:image/[^;]+;base64,([^)]+))\)")
    for raw in (markdown or "").splitlines():
        line = raw.rstrip()
        if not line:
            doc.add_paragraph("")
            continue
        img = image_pattern.search(line)
        if img:
            try:
                bio = BytesIO(base64.b64decode(img.group(3)))
                doc.add_picture(bio, width=Inches(5.6))
            except Exception:
                doc.add_paragraph("[이미지 삽입 실패]")
            continue
        level = 0
        if line.startswith("### "):
            level, line = 3, line[4:]
        elif line.startswith("## "):
            level, line = 2, line[3:]
        elif line.startswith("# "):
            level, line = 1, line[2:]
        if level:
            doc.add_heading(line, level=level)
            continue
        style = "List Bullet" if line.startswith(('- ', '* ')) else None
        if style:
            line = line[2:]
        p = doc.add_paragraph(style=style) if style else doc.add_paragraph()
        pos = 0
        for m in re.finditer(r"<mark>(.*?)</mark>", line):
            if m.start() > pos:
                p.add_run(line[pos:m.start()])
            run = p.add_run(m.group(1))
            run.font.highlight_color = WD_COLOR_INDEX.YELLOW
            pos = m.end()
        if pos < len(line):
            p.add_run(line[pos:])
    out = BytesIO()
    doc.save(out)
    out.seek(0)
    return out

@app.get("/health")
def health():
    return {"ok": True, "service": "lecturenote-suite", "version": "1.8.0"}


@app.get("/", response_class=HTMLResponse)
def root():
    return _page("LectureNote Suite", """
<section class="top"><div><h1>LectureNote Suite</h1><p>강의자료, 교재, 전사본, 시험지, 외부 정리본을 한 곳에 올리고 GPT Actions와 연결합니다.</p><div class="nav"><a class="btn" href="/upload">자료 업로드</a><a class="btn secondary" href="/sources/manage">파일 관리</a><a class="btn secondary" href="/static/solvepad/index.html">SolvePad</a><a class="btn secondary" href="/static/casio/index.html">계산기 PRGM</a></div></div></section>
<section class="grid"><div class="card"><h2>통합 자료 업로드</h2><p>일반 자료와 외부 정리본을 자료 유형으로 구분해 한 화면에서 올립니다. 제목은 파일명으로 자동 지정됩니다.</p><div class="actions"><a class="btn" href="/upload">열기</a></div></div><div class="card"><h2>SolvePad 문제풀이</h2><p>GPT가 만든 문제팩을 iPad에서 불러오고 필기 풀이를 저장합니다.</p><div class="actions"><a class="btn" href="/static/solvepad/index.html">열기</a></div></div><div class="card"><h2>CASIO 계산기 PRGM</h2><p>GPT가 생성한 계산기 코드와 사용법/구조 해설을 확인합니다.</p><div class="actions"><a class="btn" href="/static/casio/index.html">열기</a></div></div><div class="card"><h2>관리 / 상태</h2><p>업로드 파일 삭제, 매핑 현황, API 문서를 확인합니다.</p><div class="actions"><a class="btn secondary" href="/sources/manage">파일 관리</a><a class="btn secondary" href="/mapping/status">매핑</a><a class="btn secondary" href="/docs">API</a></div></div></section>""")


@app.get("/upload", response_class=HTMLResponse)
def upload_page():
    return _page("자료 업로드", f"""
<section class="top"><div><h1>통합 자료 업로드</h1><p>강의자료, 교재, 전사본, 시험지, 외부 정리본을 자료 유형으로 골라 한 번에 업로드합니다.</p></div><div class="nav"><a class="btn secondary" href="/">홈</a><a class="btn secondary" href="/sources/manage">파일 관리</a></div></section>
<section class="card"><form action="/sources/upload-batch" method="post" enctype="multipart/form-data"><label>액션 키</label><input name="action_key" type="password" placeholder="처음 한 번만 입력하면 이 브라우저에 자동 저장" autocomplete="off"/><div class="keybox"><span class="key-status" data-key-status></span><button class="btn secondary" type="button" data-clear-key>저장된 키 지우기</button></div><div class="hint">보안 때문에 서버 전체 공개 업로드는 막아두고, 키는 이 브라우저 localStorage에만 저장합니다.</div><label>과목명</label><input name="subject" placeholder="예: CRE, 반응공학, 수학2"/><div class="hint">선택사항이지만 과목별 관리에는 입력 권장.</div><label>자료 유형</label><select name="source_type">{_options('lecture_slides')}</select><label>제목</label><input name="title" placeholder="선택사항. 비우면 각 파일명으로 자동 저장"/><label>파일</label><input type="file" name="files" multiple required/><div class="hint">여러 파일을 한 번에 선택 가능합니다.</div><div class="actions"><button type="submit">업로드</button><a class="btn secondary" href="/">홈으로</a></div></form></section>""")


@app.get("/notes/upload", response_class=HTMLResponse)
def notes_upload_page():
    return _page("외부 정리본 업로드", """
<section class="top"><div><h1>외부 정리본 업로드</h1><p>이제 외부 정리본도 통합 자료 업로드 화면의 자료 유형에서 선택합니다.</p></div><div class="nav"><a class="btn" href="/upload">통합 업로드로 이동</a><a class="btn secondary" href="/">홈</a></div></section>
<section class="card"><p>업로드 화면에서 <b>자료 유형</b>을 <code>외부 정리본</code>으로 선택하면 됩니다. 기존 링크 호환을 위해 이 페이지는 남겨둡니다.</p></section>""")


@app.post("/sources/upload")
async def upload_source(source_type: str = Form(default="lecture_slides"), title: str = Form(default=""), subject: str = Form(default=""), action_key: str = Form(default=""), file: UploadFile = File(...), authorization: Optional[str] = Header(default=None), x_action_key: Optional[str] = Header(default=None)):
    if not _is_authorized(authorization, x_action_key, action_key):
        raise HTTPException(status_code=401, detail="Invalid action key")
    return _upload_result([await _save_uploaded_file(file, source_type, subject, title)], subject.strip())


@app.post("/sources/upload-batch")
async def upload_sources_batch(source_type: str = Form(default="lecture_slides"), title: str = Form(default=""), subject: str = Form(default=""), action_key: str = Form(default=""), files: List[UploadFile] = File(...), authorization: Optional[str] = Header(default=None), x_action_key: Optional[str] = Header(default=None)):
    if not _is_authorized(authorization, x_action_key, action_key):
        raise HTTPException(status_code=401, detail="Invalid action key")
    results = []
    for i, file in enumerate(files, 1):
        item_title = f"{title.strip()} {i}" if title.strip() and len(files) > 1 else title.strip()
        results.append(await _save_uploaded_file(file, source_type, subject, item_title))
    return _upload_result(results, subject.strip())


@app.post("/sources/text", dependencies=[Depends(require_auth)])
def save_text_source_endpoint(payload: TextSourceSave):
    return save_text_source(payload.title, payload.source_type, payload.text, payload.original_name, subject=payload.subject.strip())


@app.post("/notes/text", dependencies=[Depends(require_auth)])
def save_external_note_endpoint(payload: TextSourceSave):
    source_type = payload.source_type if payload.source_type in {"external_note", "generated_note", "note_example"} else "external_note"
    return save_text_source(payload.title, source_type, payload.text, payload.original_name, subject=payload.subject.strip())


@app.get("/sources")
def sources(source_type: str = Query(default=""), subject: str = Query(default="")):
    return {"sources": list_sources(source_type, subject)}


@app.get("/sources/unmapped", dependencies=[Depends(require_auth)])
def unmapped_sources(source_type: str = Query(default=""), subject: str = Query(default="")):
    return {"unmapped_sources": list_unmapped_sources([source_type] if source_type else [], subject)}


@app.get("/external-notes")
def external_notes_endpoint(subject: str = Query(default="")):
    return {"external_notes": list_external_notes(subject)}


@app.get("/sources/manage", response_class=HTMLResponse)
def manage_sources_page(subject: str = Query(default=""), action_key: str = Query(default="")):
    rows = []
    for s in list_sources(subject=subject):
        sid = escape(s.get("id", ""))
        rows.append(f"<tr><td><span class='pill'>{escape(s.get('subject','') or '미지정')}</span></td><td>{escape(s.get('source_type',''))}</td><td>{escape(s.get('title',''))}<div class='hint'><code>{sid}</code></div></td><td>{escape(s.get('original_name',''))}</td><td>{escape(s.get('created_at',''))}</td><td><form action='/sources/{sid}/delete' method='post' onsubmit=\"return confirm('이 자료를 삭제할까요?');\"><input type='hidden' name='action_key' value='{escape(action_key)}'/><button class='danger' type='submit'>삭제</button></form></td></tr>")
    table_rows = "\n".join(rows) or "<tr><td colspan='6' class='muted'>업로드된 자료가 없습니다.</td></tr>"
    return _page("업로드 파일 관리", f"<section class='top'><div><h1>업로드 파일 관리</h1><p>업로드한 자료를 과목별로 확인하고 삭제할 수 있습니다.</p></div><div class='nav'><a class='btn secondary' href='/upload'>자료 업로드</a><a class='btn secondary' href='/'>홈</a></div></section><section class='card'><form method='get' action='/sources/manage'><label>과목 필터</label><input name='subject' value='{escape(subject)}' placeholder='예: CRE'/><label>액션 키</label><input name='action_key' type='password' value='{escape(action_key)}' placeholder='처음 한 번 입력하면 자동 저장'/><div class='keybox'><span class='key-status' data-key-status></span><button class='btn secondary' type='button' data-clear-key>저장된 키 지우기</button></div><div class='actions'><button type='submit'>적용</button><a class='btn secondary' href='/mapping/status?subject={escape(subject)}'>매핑 현황</a></div></form></section><section class='card' style='margin-top:16px;overflow:auto'><table><thead><tr><th>과목</th><th>유형</th><th>제목/source_id</th><th>파일</th><th>생성일</th><th>작업</th></tr></thead><tbody>{table_rows}</tbody></table></section>")


@app.get("/sources/{source_id}")
def source_detail(source_id: str):
    source = get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@app.get("/mapping/status", dependencies=[Depends(require_auth)])
def mapping_status_endpoint(subject: str = Query(default="")):
    return get_mapping_status(subject)


@app.delete("/sources/{source_id}", dependencies=[Depends(require_auth)])
def delete_source_endpoint(source_id: str):
    result = delete_source(source_id)
    if not result:
        raise HTTPException(status_code=404, detail="Source not found")
    return result


@app.post("/sources/{source_id}/delete")
def delete_source_form_endpoint(source_id: str, action_key: str = Form(default="")):
    if not _is_authorized(action_key=action_key):
        raise HTTPException(status_code=401, detail="Invalid action key")
    result = delete_source(source_id)
    if not result:
        raise HTTPException(status_code=404, detail="Source not found")
    return _page("삭제 완료", f"<section class='top'><div><h1>삭제 완료</h1><p>자료와 추출 chunk를 삭제했습니다.</p></div><div class='nav'><a class='btn' href='/sources/manage?action_key={escape(action_key)}'>파일 관리로 돌아가기</a></div></section><section class='card'><p><b>제목:</b> {escape(result.get('deleted_title',''))}</p><p><b>source_id:</b> <code>{escape(result.get('deleted_source_id',''))}</code></p><p><b>삭제 chunks:</b> {result.get('deleted_chunks')}</p><p><b>파일 삭제:</b> {result.get('deleted_file')}</p></section>")


@app.post("/sources/search", dependencies=[Depends(require_auth)])
def search(payload: SearchRequest):
    return {"results": search_sources(payload.query, payload.source_types, payload.limit, payload.subject)}


@app.get("/workflow/options", dependencies=[Depends(require_auth)])
def workflow_options(subject: str = Query(default="")):
    return get_workflow_options(subject)


@app.post("/workflow/plans", dependencies=[Depends(require_auth)])
def create_workflow_plan_endpoint(payload: WorkflowPlanCreate):
    return create_workflow_plan(payload.title, payload.subject, payload.selected_units, payload.selected_mode, payload.unit_map_id, payload.source_ids, payload.reference_priority, payload.notes)


@app.get("/workflow/plans", dependencies=[Depends(require_auth)])
def list_workflow_plans_endpoint():
    return {"workflow_plans": list_workflow_plans()}


@app.post("/workflow/runs", dependencies=[Depends(require_auth)])
def create_workflow_run_endpoint(payload: WorkflowRunCreate):
    return create_workflow_run(payload.title, payload.mode, payload.subject, payload.selected_units, payload.workflow_plan_id, payload.total_steps, payload.metadata)


@app.get("/workflow/runs", dependencies=[Depends(require_auth)])
def list_workflow_runs_endpoint(status: str = Query(default="")):
    return {"workflow_runs": list_workflow_runs(status)}


@app.get("/workflow/runs/{run_id}/next", dependencies=[Depends(require_auth)])
def get_next_workflow_step_endpoint(run_id: str):
    result = get_next_workflow_step(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return result


@app.post("/workflow/checkpoints", dependencies=[Depends(require_auth)])
def save_workflow_checkpoint_endpoint(payload: WorkflowCheckpointSave):
    result = save_workflow_checkpoint(payload.run_id, payload.step_index, payload.step_label, payload.status, payload.saved_refs, payload.next_action, payload.notes, payload.advance_to_next)
    if not result:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return result


@app.get("/workflow/runs/{run_id}/checkpoints", dependencies=[Depends(require_auth)])
def list_workflow_checkpoints_endpoint(run_id: str):
    return {"checkpoints": list_workflow_checkpoints(run_id)}


@app.post("/projects", dependencies=[Depends(require_auth)])
def create_project_endpoint(payload: ProjectCreate):
    return create_project(payload.title, payload.project_type, payload.source_ids, payload.metadata)


@app.post("/projects/{project_id}/outline", dependencies=[Depends(require_auth)])
def save_outline_endpoint(project_id: str, payload: OutlineSave):
    return save_outline(project_id, [section.model_dump() for section in payload.sections])


@app.get("/projects/{project_id}/next", dependencies=[Depends(require_auth)])
def next_section(project_id: str):
    return get_next_section(project_id)


@app.post("/projects/{project_id}/sections", dependencies=[Depends(require_auth)])
def save_section_endpoint(project_id: str, payload: SectionSave):
    return save_section(project_id, payload.model_dump())


@app.post("/projects/{project_id}/items/{item_type}", dependencies=[Depends(require_auth)])
def save_items_endpoint(project_id: str, item_type: str, payload: GenericItemsSave):
    return save_project_items(project_id, item_type, payload.items)


@app.get("/projects/{project_id}/final-bundle", dependencies=[Depends(require_auth)])
def final_bundle_endpoint(project_id: str):
    bundle = final_bundle(project_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Project not found")
    return bundle


@app.post("/projects/{project_id}/export-note-source", dependencies=[Depends(require_auth)])
def export_project_note_source_endpoint(project_id: str, payload: dict = None):
    result = export_project_note_as_source(project_id, (payload or {}).get("title", ""))
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")
    return result


@app.post("/notes/versions", dependencies=[Depends(require_auth)])
def save_note_version_endpoint(payload: NoteVersionSave):
    return save_note_version(payload.title, payload.content_markdown, payload.series_id, payload.source_type, payload.change_summary, payload.based_on_version, payload.subject.strip(), payload.replace_latest)


@app.get("/notes/versions", dependencies=[Depends(require_auth)])
def list_note_versions_endpoint(series_id: str = Query(default="")):
    return {"versions": list_note_versions(series_id)}


@app.get("/notes/versions/{series_id}/latest", dependencies=[Depends(require_auth)])
def latest_note_version_endpoint(series_id: str):
    latest = get_latest_note_version(series_id)
    if not latest:
        raise HTTPException(status_code=404, detail="Note series not found")
    return latest


@app.post("/transcripts/revisions", dependencies=[Depends(require_auth)])
def save_transcript_revision_endpoint(payload: TranscriptRevisionSave):
    return save_transcript_revision(payload.title, payload.corrected_text, payload.original_transcript_source_id, payload.terminology_map, payload.change_log, payload.subject.strip())


@app.post("/unit-maps", dependencies=[Depends(require_auth)])
def save_unit_map_endpoint(payload: UnitMapSave):
    return save_unit_map(payload.title, payload.source_ids, payload.map, payload.created_by)


@app.get("/unit-maps")
def list_unit_maps_endpoint():
    return {"unit_maps": list_unit_maps()}



@app.get("/study/notes", dependencies=[Depends(require_auth)])
def list_study_notes_endpoint(subject: str = Query(default=""), source_type: str = Query(default="")):
    return {"notes": list_study_notes(subject, source_type)}


@app.post("/study/notes", dependencies=[Depends(require_auth)])
def save_study_note_endpoint(payload: StudyNoteSave):
    source_type = payload.source_type if payload.source_type in {"generated_note", "external_note", "exam_cram", "calculator_manual", "note_example"} else "generated_note"
    return save_note_version(
        payload.title,
        payload.content_markdown,
        payload.series_id,
        source_type,
        payload.change_summary,
        None,
        payload.subject.strip(),
        payload.replace_latest,
    )


@app.post("/exam-cram", dependencies=[Depends(require_auth)])
def save_exam_cram_endpoint(payload: ExamCramSave):
    return save_note_version(
        payload.title,
        payload.content_markdown,
        payload.series_id,
        "exam_cram",
        payload.change_summary,
        None,
        payload.subject.strip(),
        payload.replace_latest,
    )


@app.get("/study/notes/{source_id}", dependencies=[Depends(require_auth)])
def get_study_note_endpoint(source_id: str):
    note = get_source_markdown(source_id)
    if not note:
        raise HTTPException(status_code=404, detail="Study note not found")
    return note


@app.put("/study/notes/{source_id}", dependencies=[Depends(require_auth)])
def update_study_note_endpoint(source_id: str, payload: StudyNoteUpdate):
    result = update_source_markdown(source_id, payload.content_markdown, payload.title, payload.change_summary)
    if not result:
        raise HTTPException(status_code=404, detail="Study note not found")
    return result


@app.get("/study/notes/{source_id}/download.md")
def download_study_note_md(source_id: str):
    note = get_source_markdown(source_id)
    if not note:
        raise HTTPException(status_code=404, detail="Study note not found")
    title = note["source"].get("title", source_id).replace('/', '_')
    return Response(
        note.get("markdown", ""),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{title}.md"'},
    )


@app.get("/study/notes/{source_id}/download.docx")
def download_study_note_docx(source_id: str):
    note = get_source_markdown(source_id)
    if not note:
        raise HTTPException(status_code=404, detail="Study note not found")
    title = note["source"].get("title", source_id).replace('/', '_')
    out = _markdown_to_docx_bytes(title, note.get("markdown", ""))
    return StreamingResponse(
        out,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{title}.docx"'},
    )


@app.get("/study/notes/{source_id}/print", response_class=HTMLResponse)
def print_study_note_page(source_id: str):
    note = get_source_markdown(source_id)
    if not note:
        raise HTTPException(status_code=404, detail="Study note not found")
    title = escape(note["source"].get("title", source_id))
    html = _simple_markdown_html(note.get("markdown", ""))
    return HTMLResponse(f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'/><meta name='viewport' content='width=device-width,initial-scale=1'/><title>{title}</title><script>window.MathJax={{tex:{{inlineMath:[["$","$"],["\\\\(","\\\\)"]],displayMath:[["$$","$$"],["\\\\[","\\\\]"]],processEscapes:true}},svg:{{fontCache:'global'}}}};</script><script defer src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js'></script><style>body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans KR',Arial,sans-serif;line-height:1.72;max-width:820px;margin:0 auto;padding:34px;color:#111827}}.bar{{display:flex;gap:8px;margin-bottom:20px}}button,a{{border:0;border-radius:10px;padding:9px 12px;background:#4f46e5;color:white;text-decoration:none;font-weight:800}}img{{max-width:100%;border-radius:10px}}mark{{background:#fff39a}}@media print{{.bar{{display:none}}body{{padding:0;max-width:none}}}}</style></head><body><div class='bar'><button onclick='window.print()'>PDF로 저장/인쇄</button><a href='/static/study/index.html'>Study Studio</a><a href='/'>홈</a></div><article>{html}</article></body></html>""")

@app.get("/unit-maps/{unit_map_id}", dependencies=[Depends(require_auth)])
def get_unit_map_endpoint(unit_map_id: str):
    unit_map = get_unit_map(unit_map_id)
    if not unit_map:
        raise HTTPException(status_code=404, detail="Unit map not found")
    return unit_map


@app.post("/problem-packs", dependencies=[Depends(require_auth)])
def save_problem_pack_endpoint(payload: ProblemPackSave):
    saved = save_problem_pack(payload.title, payload.pack)
    return {**saved, "import_url": f"{PUBLIC_BASE_URL}/static/solvepad/index.html?server={PUBLIC_BASE_URL}&importToken={saved['token']}"}


@app.get("/packs/{token}")
def get_pack_for_solvepad(token: str):
    pack = get_problem_pack_by_token(token)
    if not pack:
        raise HTTPException(status_code=404, detail="Problem pack not found")
    return pack


@app.get("/calculator/projects", dependencies=[Depends(require_auth)])
def list_calculator_projects_endpoint(subject: str = Query(default="")):
    return {"calculator_projects": list_calculator_blueprints(subject)}


@app.get("/calculator/projects/{project_id}", dependencies=[Depends(require_auth)])
def get_calculator_project_endpoint(project_id: str):
    project = get_calculator_blueprint(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Calculator project not found")
    return project


@app.get("/calculator/projects/{project_id}/manual", response_class=HTMLResponse)
def get_calculator_manual_page(project_id: str):
    project = get_calculator_blueprint(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Calculator project not found")
    manual = escape(project.get("manual_markdown", "") or "사용법 문서가 저장되지 않았습니다.")
    title = escape(project.get("title", project_id))
    return _page(f"계산기 사용법 - {title}", f"<section class='top'><div><h1>{title}</h1><p>CASIO PRGM 사용법 및 구조 해설</p></div><div class='nav'><a class='btn secondary' href='/static/casio/index.html'>계산기 Studio</a><a class='btn secondary' href='/'>홈</a></div></section><section class='card'><pre style='white-space:pre-wrap;line-height:1.65'>{manual}</pre></section>")


@app.delete("/calculator/projects/{project_id}", dependencies=[Depends(require_auth)])
def delete_calculator_project_endpoint(project_id: str):
    result = delete_calculator_blueprint(project_id)
    if not result:
        raise HTTPException(status_code=404, detail="Calculator project not found")
    return result



@app.get("/calculator/projects/{project_id}/download.zip", dependencies=[Depends(require_auth)])
def download_calculator_project_zip(project_id: str):
    project = get_calculator_blueprint(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Calculator project not found")
    mem = BytesIO()
    with zipfile.ZipFile(mem, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_info in (project.get("generated") or {}).get("files", []):
            archive.writestr(file_info.get("name", "PROGRAM.TXT"), file_info.get("content", ""))
        if project.get("manual_markdown"):
            archive.writestr("MANUAL.md", project.get("manual_markdown", ""))
        if project.get("analysis_markdown"):
            archive.writestr("ANALYSIS.md", project.get("analysis_markdown", ""))
    mem.seek(0)
    return StreamingResponse(mem, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{project_id}-casio.zip"'})

@app.post("/calculator/validate", dependencies=[Depends(require_auth)])
def validate_calculator(payload: CalculatorBlueprintSave):
    return validate_blueprint(payload.blueprint).as_dict()


@app.post("/calculator/generate", dependencies=[Depends(require_auth)])
def generate_calculator(payload: CalculatorBlueprintSave):
    validation = validate_blueprint(payload.blueprint).as_dict()
    generated = generate_txt_files(payload.blueprint).as_dict()
    saved = save_calculator_blueprint(
        payload.title,
        payload.blueprint,
        validation,
        generated,
        payload.metadata,
        payload.manual_markdown,
        payload.analysis_markdown,
        payload.replace_calculator_project_id,
    )
    project_id = saved["calculator_project_id"]
    return {
        **saved,
        "validation": validation,
        "generated": generated,
        "manual_url": f"{PUBLIC_BASE_URL}/calculator/projects/{project_id}/manual",
        "studio_url": f"{PUBLIC_BASE_URL}/static/casio/index.html?projectId={project_id}",
    }


@app.post("/calculator/generate.zip", dependencies=[Depends(require_auth)])
def generate_calculator_zip(payload: CalculatorBlueprintSave):
    generated = generate_txt_files(payload.blueprint).as_dict()
    mem = BytesIO()
    with zipfile.ZipFile(mem, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_info in generated.get("files", []):
            archive.writestr(file_info["name"], file_info["content"])
        if payload.manual_markdown.strip():
            archive.writestr("MANUAL.md", payload.manual_markdown)
        if payload.analysis_markdown.strip():
            archive.writestr("ANALYSIS.md", payload.analysis_markdown)
    mem.seek(0)
    return StreamingResponse(mem, media_type="application/zip", headers={"Content-Disposition": 'attachment; filename="casio-prgm-files.zip"'})
