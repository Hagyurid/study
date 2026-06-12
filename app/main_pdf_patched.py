from __future__ import annotations

from html import escape
from pathlib import Path
from typing import List, Optional, Set
import tempfile

from fastapi import Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.routing import APIRoute
from starlette.background import BackgroundTask

from app import main_patched as _patched

app = _patched.app


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


def _cleanup_file(path: str) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except Exception:
        pass


def _study_notes_pdf_tempfile(source_ids: List[str], title: str = "Study Notes") -> str:
    if len(source_ids) > 5:
        raise HTTPException(status_code=413, detail="PDF direct download is limited to 5 study notes. Split the selection or use browser print for large/image-heavy bundles.")
    try:
        import fitz  # PyMuPDF
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF export package is not installed. Add PyMuPDF to requirements.txt and redeploy: {exc}")

    doc = fitz.open()
    css = _patched._pdf_export_css()
    page = _patched._pdf_new_page(doc)
    y = 42
    exported = 0
    for index, source_id in enumerate(source_ids, 1):
        note = _patched.get_source_markdown(source_id)
        if not note:
            continue
        source = note.get("source") or {}
        if exported:
            page = _patched._pdf_new_page(doc)
            y = 42
        exported += 1
        heading = (
            f"<h1>{index}. {escape(source.get('title') or source_id)}</h1>"
            f"<div class='doc-meta'>과목: {escape(source.get('subject') or '미지정')} · "
            f"유형: {escape(_patched._source_type_label(source.get('source_type', '')))} · "
            f"source_id: {escape(source.get('id') or source_id)}</div>"
        )
        page, y = _patched._pdf_insert_block(doc, page, y, heading, css)
        blocks = _patched._markdown_to_pdf_html_blocks(note.get("markdown", ""), render_slide_images=False)
        if not blocks:
            blocks = ["<p>출력할 본문이 없습니다.</p>"]
        for block in blocks:
            page, y = _patched._pdf_insert_block(doc, page, y, block, css)
        del blocks
    if not exported:
        page, y = _patched._pdf_insert_block(doc, page, y, "<h1>출력 가능한 정리본이 없습니다</h1><p>파일 관리에서 GPT 생성 정리본 또는 문서형 자료를 선택하세요.</p>", css)
    meta = doc.metadata or {}
    meta["title"] = title or "Study Notes"
    doc.set_metadata(meta)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp_path = tmp.name
    tmp.close()
    try:
        doc.save(tmp_path, garbage=4, deflate=True)
    finally:
        doc.close()
    return tmp_path


_drop_route("/study/notes/{source_id}/download.pdf", {"GET"})


@app.get("/study/notes/{source_id}/download.pdf")
def download_study_note_pdf(source_id: str):
    note = _patched.get_source_markdown(source_id)
    if not note:
        raise HTTPException(status_code=404, detail="Study note not found")
    title = str((note.get("source") or {}).get("title") or source_id).replace("/", "_")
    temp_path = _study_notes_pdf_tempfile([source_id], title)
    return FileResponse(
        temp_path,
        media_type="application/pdf",
        headers=_patched._safe_download_headers(title, ".pdf"),
        background=BackgroundTask(_cleanup_file, temp_path),
    )


_drop_route("/sources/download-bundle.pdf", {"POST"})


@app.post("/sources/download-bundle.pdf")
def download_sources_bundle_pdf(action_key: str = Form(default=""), source_ids: Optional[List[str]] = Form(default=None)):
    if not _patched._is_authorized(action_key=action_key):
        raise HTTPException(status_code=401, detail="Invalid action key")
    ids = _patched._selected_ids(source_ids)
    if not ids:
        raise HTTPException(status_code=400, detail="No sources selected")
    ordered_ids, _order_note = _patched._order_selected_sources_for_print(ids)
    printable_ids: List[str] = []
    skipped_problem_packs: List[str] = []
    for source_id in ordered_ids:
        source = _patched.get_source(source_id) or {}
        if source.get("source_type") == "problem_pack":
            skipped_problem_packs.append(source_id)
            continue
        if source:
            printable_ids.append(source_id)
    if not printable_ids:
        raise HTTPException(status_code=400, detail="No printable Markdown documents selected. Use the problem-pack PDF buttons for problem_pack sources.")
    title = _patched._safe_pdf_bundle_title(printable_ids)
    temp_path = _study_notes_pdf_tempfile(printable_ids, title)
    headers = _patched._safe_download_headers(title, ".pdf")
    if skipped_problem_packs:
        headers["X-Skipped-Problem-Packs"] = ",".join(skipped_problem_packs[:20])
    return FileResponse(
        temp_path,
        media_type="application/pdf",
        headers=headers,
        background=BackgroundTask(_cleanup_file, temp_path),
    )
