from io import BytesIO
from pathlib import Path
from typing import Optional
import shutil
import tempfile
import zipfile

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.config import ACTION_API_KEY, PUBLIC_BASE_URL, UPLOAD_DIR
from app.db import (
    create_project,
    create_workflow_plan,
    create_workflow_run,
    delete_source,
    export_project_note_as_source,
    final_bundle,
    get_latest_note_version,
    get_mapping_status,
    get_next_section,
    get_problem_pack_by_token,
    get_source,
    get_unit_map,
    get_workflow_options,
    init_db,
    list_external_notes,
    list_note_versions,
    list_sources,
    list_unit_maps,
    list_unmapped_sources,
    list_workflow_checkpoints,
    list_workflow_plans,
    list_workflow_runs,
    save_calculator_blueprint,
    save_note_version,
    save_outline,
    save_problem_pack,
    save_project_items,
    save_section,
    save_source,
    save_text_source,
    save_transcript_revision,
    save_unit_map,
    save_workflow_checkpoint,
    search_sources,
    get_next_workflow_step,
)
from app.models import (
    CalculatorBlueprintSave,
    GenericItemsSave,
    NoteVersionSave,
    OutlineSave,
    ProblemPackSave,
    ProjectCreate,
    SearchRequest,
    SectionSave,
    TextSourceSave,
    TranscriptRevisionSave,
    UnitMapSave,
    WorkflowPlanCreate,
    WorkflowRunCreate,
    WorkflowCheckpointSave,
)
from app.modules.file_extract import extract_text
from app.modules.prgm_engine import generate_txt_files, validate_blueprint

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"

app = FastAPI(title="LectureNote Suite", version="1.3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=False)
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

init_db()


def _is_authorized(authorization: Optional[str] = None, x_action_key: Optional[str] = None, action_key: str = "") -> bool:
    if not ACTION_API_KEY:
        return True
    return authorization == f"Bearer {ACTION_API_KEY}" or x_action_key == ACTION_API_KEY or action_key == ACTION_API_KEY


def require_auth(authorization: Optional[str] = Header(default=None), x_action_key: Optional[str] = Header(default=None)):
    if _is_authorized(authorization, x_action_key):
        return True
    raise HTTPException(status_code=401, detail="Invalid action key")


@app.get("/health")
def health():
    return {"ok": True, "service": "lecturenote-suite", "version": "1.3.0"}


@app.get("/", response_class=HTMLResponse)
def root():
    return HTMLResponse(
        """
        <h1>LectureNote Suite</h1>
        <ul>
          <li><a href="/upload">Upload Sources</a></li>
          <li><a href="/notes/upload">Upload External Notes</a></li>
          <li><a href="/workflow/runs">Workflow Runs JSON</a></li>
          <li><a href="/workflow/options">Workflow Options JSON</a></li>
          <li><a href="/sources">Source List JSON</a></li>
          <li><a href="/sources/manage">Manage Uploaded Files</a></li>
          <li><a href="/mapping/status">Mapping Status JSON</a></li>
          <li><a href="/sources/unmapped">Unmapped Sources JSON</a></li>
          <li><a href="/unit-maps">Unit Maps JSON</a></li>
          <li><a href="/static/solvepad/index.html">SolvePad</a></li>
          <li><a href="/static/casio/index.html">CASIO PRGM Tool</a></li>
          <li><a href="/docs">API Docs</a></li>
        </ul>
        """
    )


@app.get("/upload", response_class=HTMLResponse)
def upload_page():
    return HTMLResponse(
        """
        <h1>Upload LectureNote Source</h1>
        <p>If ACTION_API_KEY is set, paste the same key below.</p>
        <form action="/sources/upload" method="post" enctype="multipart/form-data">
          <label>Action key</label><br/>
          <input name="action_key" type="password" style="width:360px"/><br/><br/>
          <label>Subject / 과목명</label><br/>
          <input name="subject" style="width:360px" placeholder="예: CRE, 반응공학, 수학2"/><br/><br/>
          <label>Source type</label><br/>
          <select name="source_type">
            <option value="lecture_slides">lecture_slides</option>
            <option value="transcript">transcript</option>
            <option value="corrected_transcript">corrected_transcript</option>
            <option value="textbook">textbook</option>
            <option value="past_exam">past_exam</option>
            <option value="exam_trend">exam_trend</option>
            <option value="generated_note">generated_note</option>
            <option value="external_note">external_note</option>
            <option value="note_example">note_example</option>
          </select><br/><br/>
          <label>Title</label><br/>
          <input name="title" style="width:360px" required/><br/><br/>
          <input type="file" name="file" required/><br/><br/>
          <button type="submit">Upload</button>
        </form>
        """
    )



@app.get("/notes/upload", response_class=HTMLResponse)
def notes_upload_page():
    return HTMLResponse(
        """
        <h1>Upload External Lecture Note</h1>
        <p>This page stores user-provided notes separately as <code>external_note</code>.</p>
        <form action="/sources/upload" method="post" enctype="multipart/form-data">
          <input type="hidden" name="source_type" value="external_note"/>
          <label>Action key</label><br/>
          <input name="action_key" type="password" style="width:360px"/><br/><br/>
          <label>Subject / 과목명</label><br/>
          <input name="subject" style="width:360px" placeholder="예: CRE, 수학2"/><br/><br/>
          <label>Note title</label><br/>
          <input name="title" style="width:360px" required/><br/><br/>
          <input type="file" name="file" required/><br/><br/>
          <button type="submit">Upload External Note</button>
        </form>
        """
    )


@app.post("/sources/upload")
async def upload_source(
    source_type: str = Form(...),
    title: str = Form(...),
    subject: str = Form(default=""),
    action_key: str = Form(default=""),
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
    x_action_key: Optional[str] = Header(default=None),
):
    if not _is_authorized(authorization, x_action_key, action_key):
        raise HTTPException(status_code=401, detail="Invalid action key")

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
        return save_source(title, source_type, safe_name, str(stored), file.content_type or "", size, text, status, subject=subject.strip())
    finally:
        Path(tmp.name).unlink(missing_ok=True)


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
    source_types = [source_type] if source_type else []
    return {"unmapped_sources": list_unmapped_sources(source_types, subject)}



@app.get("/external-notes")
def external_notes_endpoint(subject: str = Query(default="")):
    return {"external_notes": list_external_notes(subject)}



@app.get("/sources/manage", response_class=HTMLResponse)
def manage_sources_page(subject: str = Query(default=""), action_key: str = Query(default="")):
    sources_list = list_sources(subject=subject)
    rows = []
    for source in sources_list:
        rows.append(
            f"""
            <tr>
              <td>{source.get('subject','')}</td>
              <td>{source.get('source_type','')}</td>
              <td>{source.get('title','')}</td>
              <td>{source.get('original_name','')}</td>
              <td>{source.get('created_at','')}</td>
              <td>
                <form action="/sources/{source.get('id')}/delete" method="post" onsubmit="return confirm('Delete this file/source?');">
                  <input type="hidden" name="action_key" value="{action_key}"/>
                  <button type="submit">Delete</button>
                </form>
              </td>
            </tr>
            """
        )
    table_rows = "\n".join(rows) or "<tr><td colspan='6'>No uploaded sources.</td></tr>"
    return HTMLResponse(
        f"""
        <h1>Manage Uploaded Files</h1>
        <form method="get" action="/sources/manage">
          <label>Subject filter</label>
          <input name="subject" value="{subject}" placeholder="CRE"/>
          <label>Action key</label>
          <input name="action_key" type="password" value="{action_key}"/>
          <button type="submit">Apply</button>
        </form>
        <p>Delete removes the source record, extracted chunks, and local uploaded file when available.</p>
        <table border="1" cellpadding="6" cellspacing="0">
          <thead>
            <tr><th>Subject</th><th>Type</th><th>Title</th><th>File</th><th>Created</th><th>Action</th></tr>
          </thead>
          <tbody>{table_rows}</tbody>
        </table>
        """
    )


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
    return HTMLResponse(
        f"""
        <h1>Deleted</h1>
        <p>Deleted source: {result.get('deleted_title')} ({result.get('deleted_source_id')})</p>
        <p>Deleted chunks: {result.get('deleted_chunks')}</p>
        <p>Deleted file: {result.get('deleted_file')}</p>
        <p><a href="/sources/manage?action_key={action_key}">Back to Manage Uploaded Files</a></p>
        """
    )


@app.post("/sources/search", dependencies=[Depends(require_auth)])
def search(payload: SearchRequest):
    return {"results": search_sources(payload.query, payload.source_types, payload.limit, payload.subject)}


@app.get("/workflow/options", dependencies=[Depends(require_auth)])
def workflow_options(subject: str = Query(default="")):
    return get_workflow_options(subject)


@app.post("/workflow/plans", dependencies=[Depends(require_auth)])
def create_workflow_plan_endpoint(payload: WorkflowPlanCreate):
    return create_workflow_plan(
        payload.title,
        payload.subject,
        payload.selected_units,
        payload.selected_mode,
        payload.unit_map_id,
        payload.source_ids,
        payload.reference_priority,
        payload.notes,
    )


@app.get("/workflow/plans", dependencies=[Depends(require_auth)])
def list_workflow_plans_endpoint():
    return {"workflow_plans": list_workflow_plans()}



@app.post("/workflow/runs", dependencies=[Depends(require_auth)])
def create_workflow_run_endpoint(payload: WorkflowRunCreate):
    return create_workflow_run(
        payload.title,
        payload.mode,
        payload.subject,
        payload.selected_units,
        payload.workflow_plan_id,
        payload.total_steps,
        payload.metadata,
    )


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
    result = save_workflow_checkpoint(
        payload.run_id,
        payload.step_index,
        payload.step_label,
        payload.status,
        payload.saved_refs,
        payload.next_action,
        payload.notes,
        payload.advance_to_next,
    )
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
    payload = payload or {}
    result = export_project_note_as_source(project_id, payload.get("title", ""))
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")
    return result


@app.post("/notes/versions", dependencies=[Depends(require_auth)])
def save_note_version_endpoint(payload: NoteVersionSave):
    return save_note_version(
        payload.title,
        payload.content_markdown,
        payload.series_id,
        payload.source_type,
        payload.change_summary,
        payload.based_on_version,
        payload.subject.strip(),
    )


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
    return save_transcript_revision(
        payload.title,
        payload.corrected_text,
        payload.original_transcript_source_id,
        payload.terminology_map,
        payload.change_log,
        payload.subject.strip(),
    )


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
