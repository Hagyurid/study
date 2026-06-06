from io import BytesIO
from pathlib import Path
from typing import List, Optional
from html import escape
import shutil
import tempfile
import zipfile

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.config import ACTION_API_KEY, PUBLIC_BASE_URL, UPLOAD_DIR
from app.db import (
    create_project, create_workflow_plan, create_workflow_run, delete_source,
    export_project_note_as_source, final_bundle, get_latest_note_version,
    get_mapping_status, get_next_section, get_problem_pack_by_token, get_source,
    get_unit_map, get_workflow_options, init_db, list_external_notes,
    list_note_versions, list_sources, list_unit_maps, list_unmapped_sources,
    list_workflow_checkpoints, list_workflow_plans, list_workflow_runs,
    save_calculator_blueprint, save_note_version, save_outline, save_problem_pack,
    save_project_items, save_section, save_source, save_text_source,
    save_transcript_revision, save_unit_map, save_workflow_checkpoint,
    search_sources, get_next_workflow_step,
)
from app.models import (
    CalculatorBlueprintSave, GenericItemsSave, NoteVersionSave, OutlineSave,
    ProblemPackSave, ProjectCreate, SearchRequest, SectionSave, TextSourceSave,
    TranscriptRevisionSave, UnitMapSave, WorkflowPlanCreate, WorkflowRunCreate,
    WorkflowCheckpointSave,
)
from app.modules.file_extract import extract_text
from app.modules.prgm_engine import generate_txt_files, validate_blueprint

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"

app = FastAPI(title="LectureNote Suite", version="1.4.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=False)
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
init_db()

SOURCE_TYPES = [
    ("lecture_slides", "강의 슬라이드"), ("textbook", "교재"), ("transcript", "전사본"),
    ("corrected_transcript", "보정 전사본"), ("past_exam", "시험지/기출"),
    ("exam_trend", "시험 정보/경향"), ("generated_note", "GPT 생성 정리본"),
    ("external_note", "외부 정리본"), ("note_example", "정리본 예시"),
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
:root{{--bg:#f6f7fb;--card:#fff;--text:#171923;--muted:#667085;--line:#e4e7ec;--accent:#4f46e5;--accent2:#eef2ff;--danger:#d92d20}}*{{box-sizing:border-box}}body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Noto Sans KR',Arial,sans-serif;background:var(--bg);color:var(--text)}}.wrap{{max-width:1100px;margin:0 auto;padding:32px 20px 56px}}.top{{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:24px}}h1{{font-size:30px;line-height:1.2;margin:0 0 8px;letter-spacing:-.03em}}p{{margin:0;color:var(--muted);line-height:1.6}}.nav,.actions{{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}}a.btn,button,.btn{{border:0;border-radius:12px;padding:10px 14px;background:var(--accent);color:#fff;text-decoration:none;font-weight:700;cursor:pointer}}a.btn.secondary,.btn.secondary{{background:var(--accent2);color:var(--accent)}}button.danger{{background:var(--danger)}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}}.card{{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:22px;box-shadow:0 8px 24px rgba(16,24,40,.04)}}label{{display:block;font-weight:700;margin:16px 0 8px}}input,select{{width:100%;border:1px solid var(--line);border-radius:12px;padding:12px 13px;font-size:15px;background:white}}input[type=file]{{padding:14px;border-style:dashed;background:#fbfcff}}.hint{{font-size:13px;color:var(--muted);margin-top:6px}}table{{width:100%;border-collapse:collapse;background:white;border-radius:16px;overflow:hidden}}th,td{{border-bottom:1px solid var(--line);padding:12px;text-align:left;vertical-align:top;font-size:14px}}th{{background:#f9fafb;color:#344054;font-size:13px}}code{{background:#f2f4f7;padding:2px 6px;border-radius:6px}}.pill{{display:inline-block;padding:4px 8px;border-radius:999px;background:var(--accent2);color:var(--accent);font-size:12px;font-weight:700}}.muted{{color:var(--muted)}}@media(max-width:640px){{.top{{display:block}}.wrap{{padding:22px 14px}}h1{{font-size:25px}}}}</style></head><body><main class="wrap">{body}</main></body></html>""")


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


@app.get("/health")
def health():
    return {"ok": True, "service": "lecturenote-suite", "version": "1.4.0"}


@app.get("/", response_class=HTMLResponse)
def root():
    return _page("LectureNote Suite", """
<section class="top"><div><h1>LectureNote Suite</h1><p>강의자료, 교재, 전사본, 시험지, 정리본을 과목별로 저장하고 GPT Actions와 연결합니다.</p><div class="nav"><a class="btn" href="/upload">자료 업로드</a><a class="btn secondary" href="/notes/upload">외부 정리본 업로드</a><a class="btn secondary" href="/sources/manage">파일 관리</a></div></div></section>
<section class="grid"><div class="card"><h2>자료 업로드</h2><p>여러 파일을 한 번에 올리고, 제목은 파일명으로 자동 지정됩니다.</p><div class="actions"><a class="btn" href="/upload">열기</a></div></div><div class="card"><h2>외부 정리본</h2><p>사용자가 만든 정리본을 external_note로 저장합니다.</p><div class="actions"><a class="btn" href="/notes/upload">열기</a></div></div><div class="card"><h2>파일 관리</h2><p>업로드 파일을 확인하고 삭제할 수 있습니다.</p><div class="actions"><a class="btn" href="/sources/manage">열기</a></div></div><div class="card"><h2>상태 확인</h2><p>API 문서, 매핑 현황, SolvePad로 이동합니다.</p><div class="actions"><a class="btn secondary" href="/docs">API</a><a class="btn secondary" href="/mapping/status">매핑</a><a class="btn secondary" href="/static/solvepad/index.html">SolvePad</a></div></div></section>""")


@app.get("/upload", response_class=HTMLResponse)
def upload_page():
    return _page("자료 업로드", f"""
<section class="top"><div><h1>자료 업로드</h1><p>제목은 비워두면 파일명으로 자동 저장됩니다. 여러 파일을 한 번에 선택할 수 있습니다.</p></div><div class="nav"><a class="btn secondary" href="/">홈</a><a class="btn secondary" href="/sources/manage">파일 관리</a></div></section>
<section class="card"><form action="/sources/upload-batch" method="post" enctype="multipart/form-data"><label>액션 키</label><input name="action_key" type="password" placeholder="ACTION_API_KEY" autocomplete="off"/><div class="hint">Render 환경변수 ACTION_API_KEY와 같은 값을 입력합니다.</div><label>과목명</label><input name="subject" placeholder="예: CRE, 반응공학, 수학2"/><div class="hint">선택사항이지만 과목별 관리에는 입력 권장.</div><label>자료 유형</label><select name="source_type">{_options('lecture_slides')}</select><label>제목</label><input name="title" placeholder="선택사항. 비우면 각 파일명으로 자동 저장"/><label>파일</label><input type="file" name="files" multiple required/><div class="hint">여러 파일을 한 번에 선택 가능합니다.</div><div class="actions"><button type="submit">업로드</button><a class="btn secondary" href="/notes/upload">외부 정리본 업로드</a></div></form></section>""")


@app.get("/notes/upload", response_class=HTMLResponse)
def notes_upload_page():
    return _page("외부 정리본 업로드", """
<section class="top"><div><h1>외부 정리본 업로드</h1><p>직접 만든 정리본, 타 GPT 정리본, 기존 요약본을 external_note로 따로 저장합니다.</p></div><div class="nav"><a class="btn secondary" href="/">홈</a><a class="btn secondary" href="/external-notes">목록</a></div></section>
<section class="card"><form action="/sources/upload-batch" method="post" enctype="multipart/form-data"><input type="hidden" name="source_type" value="external_note"/><label>액션 키</label><input name="action_key" type="password" placeholder="ACTION_API_KEY"/><label>과목명</label><input name="subject" placeholder="예: CRE, 수학2"/><label>제목</label><input name="title" placeholder="선택사항. 비우면 각 파일명으로 자동 저장"/><label>정리본 파일</label><input type="file" name="files" multiple required/><div class="actions"><button type="submit">외부 정리본 업로드</button><a class="btn secondary" href="/upload">일반 자료 업로드</a></div></form></section>""")


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
    return _page("업로드 파일 관리", f"<section class='top'><div><h1>업로드 파일 관리</h1><p>업로드한 자료를 과목별로 확인하고 삭제할 수 있습니다.</p></div><div class='nav'><a class='btn secondary' href='/upload'>자료 업로드</a><a class='btn secondary' href='/'>홈</a></div></section><section class='card'><form method='get' action='/sources/manage'><label>과목 필터</label><input name='subject' value='{escape(subject)}' placeholder='예: CRE'/><label>액션 키</label><input name='action_key' type='password' value='{escape(action_key)}' placeholder='삭제 버튼 사용 시 필요'/><div class='actions'><button type='submit'>적용</button><a class='btn secondary' href='/mapping/status?subject={escape(subject)}'>매핑 현황</a></div></form></section><section class='card' style='margin-top:16px;overflow:auto'><table><thead><tr><th>과목</th><th>유형</th><th>제목/source_id</th><th>파일</th><th>생성일</th><th>작업</th></tr></thead><tbody>{table_rows}</tbody></table></section>")


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
    return save_note_version(payload.title, payload.content_markdown, payload.series_id, payload.source_type, payload.change_summary, payload.based_on_version, payload.subject.strip())


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


@app.post("/calculator/validate", dependencies=[Depends(require_auth)])
def validate_calculator(payload: CalculatorBlueprintSave):
    return validate_blueprint(payload.blueprint).as_dict()


@app.post("/calculator/generate", dependencies=[Depends(require_auth)])
def generate_calculator(payload: CalculatorBlueprintSave):
    validation = validate_blueprint(payload.blueprint).as_dict()
    generated = generate_txt_files(payload.blueprint).as_dict()
    saved = save_calculator_blueprint(payload.title, payload.blueprint, validation, generated, payload.metadata)
    return {**saved, "validation": validation, "generated": generated}


@app.post("/calculator/generate.zip", dependencies=[Depends(require_auth)])
def generate_calculator_zip(payload: CalculatorBlueprintSave):
    generated = generate_txt_files(payload.blueprint).as_dict()
    mem = BytesIO()
    with zipfile.ZipFile(mem, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_info in generated.get("files", []):
            archive.writestr(file_info["name"], file_info["content"])
    mem.seek(0)
    return StreamingResponse(mem, media_type="application/zip", headers={"Content-Disposition": 'attachment; filename="casio-prgm-files.zip"'})
