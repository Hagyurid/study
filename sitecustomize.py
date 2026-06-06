"""Runtime UI enhancer for LectureNote Suite.

This file is imported automatically by Python at process startup. It replaces the
basic HTML endpoints with a cleaner interface and adds a batch upload endpoint
without requiring changes to the existing app/main.py file.
"""
from __future__ import annotations

from html import escape
from pathlib import Path
import shutil
import tempfile
from typing import List, Optional

from fastapi import File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse

try:
    from fastapi import FastAPI
except Exception:  # pragma: no cover
    FastAPI = None  # type: ignore


SOURCE_TYPES = [
    ("lecture_slides", "강의 슬라이드"),
    ("textbook", "교재"),
    ("transcript", "전사본"),
    ("corrected_transcript", "보정 전사본"),
    ("past_exam", "시험지/기출"),
    ("exam_trend", "시험 정보/경향"),
    ("generated_note", "GPT 생성 정리본"),
    ("external_note", "외부 정리본"),
    ("note_example", "정리본 예시"),
]


def _options(selected: str = "lecture_slides") -> str:
    return "\n".join(
        f'<option value="{value}" {"selected" if value == selected else ""}>{label}</option>'
        for value, label in SOURCE_TYPES
    )


def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        f"""
<!doctype html><html lang="ko"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{escape(title)}</title>
<style>
:root{{--bg:#f6f7fb;--card:#fff;--text:#171923;--muted:#667085;--line:#e4e7ec;--accent:#4f46e5;--accent2:#eef2ff;--danger:#d92d20}}
*{{box-sizing:border-box}}body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Noto Sans KR',Arial,sans-serif;background:var(--bg);color:var(--text)}}
.wrap{{max-width:1100px;margin:0 auto;padding:32px 20px 56px}}.top{{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:24px}}
h1{{font-size:30px;line-height:1.2;margin:0 0 8px;letter-spacing:-.03em}}p{{margin:0;color:var(--muted);line-height:1.6}}
.nav,.actions{{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}}a.btn,button,.btn{{border:0;border-radius:12px;padding:10px 14px;background:var(--accent);color:#fff;text-decoration:none;font-weight:700;cursor:pointer}}
a.btn.secondary,.btn.secondary{{background:var(--accent2);color:var(--accent)}}button.danger{{background:var(--danger)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}}.card{{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:22px;box-shadow:0 8px 24px rgba(16,24,40,.04)}}
label{{display:block;font-weight:700;margin:16px 0 8px}}input,select{{width:100%;border:1px solid var(--line);border-radius:12px;padding:12px 13px;font-size:15px;background:white}}
input[type=file]{{padding:14px;border-style:dashed;background:#fbfcff}}.hint{{font-size:13px;color:var(--muted);margin-top:6px}}
table{{width:100%;border-collapse:collapse;background:white;border-radius:16px;overflow:hidden}}th,td{{border-bottom:1px solid var(--line);padding:12px;text-align:left;vertical-align:top;font-size:14px}}
th{{background:#f9fafb;color:#344054;font-size:13px}}code{{background:#f2f4f7;padding:2px 6px;border-radius:6px}}.pill{{display:inline-block;padding:4px 8px;border-radius:999px;background:var(--accent2);color:var(--accent);font-size:12px;font-weight:700}}.muted{{color:var(--muted)}}
@media(max-width:640px){{.top{{display:block}}.wrap{{padding:22px 14px}}h1{{font-size:25px}}}}
</style></head><body><main class="wrap">{body}</main></body></html>
        """
    )


def _is_authorized_local(authorization: Optional[str], x_action_key: Optional[str], action_key: str) -> bool:
    from app.config import ACTION_API_KEY

    if not ACTION_API_KEY:
        return True
    return authorization == f"Bearer {ACTION_API_KEY}" or x_action_key == ACTION_API_KEY or action_key == ACTION_API_KEY


async def _save_uploaded_file(file: UploadFile, source_type: str, subject: str, title: str = "") -> dict:
    from app.config import UPLOAD_DIR
    from app.db import save_source
    from app.modules.file_extract import extract_text

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
        return save_source(
            inferred_title,
            source_type,
            safe_name,
            str(stored),
            file.content_type or "",
            size,
            text,
            status,
            subject=subject.strip(),
        )
    finally:
        Path(tmp.name).unlink(missing_ok=True)


def _upload_result(results: List[dict], subject: str = "") -> HTMLResponse:
    rows = "".join(
        f"""
<tr><td><code>{escape(item.get('source_id', ''))}</code></td><td>{escape(item.get('title', ''))}</td>
<td>{escape(item.get('subject', ''))}</td><td><span class="pill">{escape(item.get('source_type', ''))}</span></td>
<td>{item.get('chunk_count', 0)}</td><td>{escape(item.get('extract_status', ''))}</td></tr>
        """
        for item in results
    )
    return _page(
        "업로드 완료",
        f"""
<section class="top"><div><h1>업로드 완료</h1><p>{len(results)}개 파일을 저장했습니다.</p></div>
<div class="nav"><a class="btn secondary" href="/upload">추가 업로드</a><a class="btn" href="/sources/manage?subject={escape(subject)}">파일 관리</a></div></section>
<section class="card"><table><thead><tr><th>source_id</th><th>제목</th><th>과목</th><th>유형</th><th>chunks</th><th>상태</th></tr></thead><tbody>{rows}</tbody></table></section>
        """,
    )


def modern_root() -> HTMLResponse:
    return _page(
        "LectureNote Suite",
        """
<section class="top"><div><h1>LectureNote Suite</h1><p>강의자료, 교재, 전사본, 시험지, 정리본을 과목별로 저장하고 GPT Actions와 연결합니다.</p>
<div class="nav"><a class="btn" href="/upload">자료 업로드</a><a class="btn secondary" href="/notes/upload">외부 정리본 업로드</a><a class="btn secondary" href="/sources/manage">파일 관리</a></div></div></section>
<section class="grid"><div class="card"><h2>자료 업로드</h2><p>여러 파일을 한 번에 올리고, 제목은 파일명으로 자동 지정됩니다.</p><div class="actions"><a class="btn" href="/upload">열기</a></div></div>
<div class="card"><h2>외부 정리본</h2><p>사용자가 만든 정리본을 external_note로 저장합니다.</p><div class="actions"><a class="btn" href="/notes/upload">열기</a></div></div>
<div class="card"><h2>파일 관리</h2><p>업로드 파일을 확인하고 삭제할 수 있습니다.</p><div class="actions"><a class="btn" href="/sources/manage">열기</a></div></div>
<div class="card"><h2>상태 확인</h2><p>API 문서, 매핑 현황, SolvePad로 이동합니다.</p><div class="actions"><a class="btn secondary" href="/docs">API</a><a class="btn secondary" href="/mapping/status">매핑</a><a class="btn secondary" href="/static/solvepad/index.html">SolvePad</a></div></div></section>
        """,
    )


def modern_upload_page() -> HTMLResponse:
    return _page(
        "자료 업로드",
        f"""
<section class="top"><div><h1>자료 업로드</h1><p>제목은 비워두면 파일명으로 자동 저장됩니다. 여러 파일을 한 번에 선택할 수 있습니다.</p></div>
<div class="nav"><a class="btn secondary" href="/">홈</a><a class="btn secondary" href="/sources/manage">파일 관리</a></div></section>
<section class="card"><form action="/sources/upload-batch" method="post" enctype="multipart/form-data">
<label>액션 키</label><input name="action_key" type="password" placeholder="ACTION_API_KEY" autocomplete="off"/><div class="hint">Render 환경변수 ACTION_API_KEY와 같은 값을 입력합니다.</div>
<label>과목명</label><input name="subject" placeholder="예: CRE, 반응공학, 수학2"/><div class="hint">선택사항이지만 과목별 관리에는 입력 권장.</div>
<label>자료 유형</label><select name="source_type">{_options('lecture_slides')}</select>
<label>제목</label><input name="title" placeholder="선택사항. 비우면 각 파일명으로 자동 저장"/>
<label>파일</label><input type="file" name="files" multiple required/><div class="hint">여러 파일을 한 번에 선택 가능합니다.</div>
<div class="actions"><button type="submit">업로드</button><a class="btn secondary" href="/notes/upload">외부 정리본 업로드</a></div></form></section>
        """,
    )


def modern_notes_upload_page() -> HTMLResponse:
    return _page(
        "외부 정리본 업로드",
        """
<section class="top"><div><h1>외부 정리본 업로드</h1><p>직접 만든 정리본, 타 GPT 정리본, 기존 요약본을 external_note로 따로 저장합니다.</p></div>
<div class="nav"><a class="btn secondary" href="/">홈</a><a class="btn secondary" href="/external-notes">목록</a></div></section>
<section class="card"><form action="/sources/upload-batch" method="post" enctype="multipart/form-data"><input type="hidden" name="source_type" value="external_note"/>
<label>액션 키</label><input name="action_key" type="password" placeholder="ACTION_API_KEY"/><label>과목명</label><input name="subject" placeholder="예: CRE, 수학2"/>
<label>제목</label><input name="title" placeholder="선택사항. 비우면 각 파일명으로 자동 저장"/><label>정리본 파일</label><input type="file" name="files" multiple required/>
<div class="actions"><button type="submit">외부 정리본 업로드</button><a class="btn secondary" href="/upload">일반 자료 업로드</a></div></form></section>
        """,
    )


async def modern_upload_single(
    source_type: str = Form(default="lecture_slides"),
    title: str = Form(default=""),
    subject: str = Form(default=""),
    action_key: str = Form(default=""),
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
    x_action_key: Optional[str] = Header(default=None),
) -> HTMLResponse:
    if not _is_authorized_local(authorization, x_action_key, action_key):
        raise HTTPException(status_code=401, detail="Invalid action key")
    return _upload_result([await _save_uploaded_file(file, source_type, subject, title)], subject.strip())


async def modern_upload_batch(
    source_type: str = Form(default="lecture_slides"),
    title: str = Form(default=""),
    subject: str = Form(default=""),
    action_key: str = Form(default=""),
    files: List[UploadFile] = File(...),
    authorization: Optional[str] = Header(default=None),
    x_action_key: Optional[str] = Header(default=None),
) -> HTMLResponse:
    if not _is_authorized_local(authorization, x_action_key, action_key):
        raise HTTPException(status_code=401, detail="Invalid action key")
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    results = []
    for index, file in enumerate(files, 1):
        item_title = f"{title.strip()} {index}" if title.strip() and len(files) > 1 else title.strip()
        results.append(await _save_uploaded_file(file, source_type, subject, item_title))
    return _upload_result(results, subject.strip())


def modern_manage_sources_page(subject: str = Query(default=""), action_key: str = Query(default="")) -> HTMLResponse:
    from app.db import list_sources

    rows = []
    for source in list_sources(subject=subject):
        sid = escape(source.get("id", ""))
        rows.append(
            f"""
<tr><td><span class="pill">{escape(source.get('subject', '') or '미지정')}</span></td><td>{escape(source.get('source_type', ''))}</td>
<td>{escape(source.get('title', ''))}<div class="hint"><code>{sid}</code></div></td><td>{escape(source.get('original_name', ''))}</td><td>{escape(source.get('created_at', ''))}</td>
<td><form action="/sources/{sid}/delete" method="post" onsubmit="return confirm('이 자료를 삭제할까요?');"><input type="hidden" name="action_key" value="{escape(action_key)}"/><button class="danger" type="submit">삭제</button></form></td></tr>
            """
        )
    table_rows = "\n".join(rows) or "<tr><td colspan='6' class='muted'>업로드된 자료가 없습니다.</td></tr>"
    return _page(
        "업로드 파일 관리",
        f"""
<section class="top"><div><h1>업로드 파일 관리</h1><p>업로드한 자료를 과목별로 확인하고 삭제할 수 있습니다.</p></div><div class="nav"><a class="btn secondary" href="/upload">자료 업로드</a><a class="btn secondary" href="/">홈</a></div></section>
<section class="card"><form method="get" action="/sources/manage"><label>과목 필터</label><input name="subject" value="{escape(subject)}" placeholder="예: CRE"/><label>액션 키</label><input name="action_key" type="password" value="{escape(action_key)}" placeholder="삭제 버튼 사용 시 필요"/>
<div class="actions"><button type="submit">적용</button><a class="btn secondary" href="/mapping/status?subject={escape(subject)}">매핑 현황</a></div></form></section>
<section class="card" style="margin-top:16px;overflow:auto"><table><thead><tr><th>과목</th><th>유형</th><th>제목/source_id</th><th>파일</th><th>생성일</th><th>작업</th></tr></thead><tbody>{table_rows}</tbody></table></section>
        """,
    )


if FastAPI is not None:
    _original_add_api_route = FastAPI.add_api_route

    def _patched_add_api_route(self, path, endpoint, *args, **kwargs):  # type: ignore[override]
        methods = set(kwargs.get("methods") or ["GET"])
        replacement = endpoint
        if path == "/" and "GET" in methods:
            replacement = modern_root
        elif path == "/upload" and "GET" in methods:
            replacement = modern_upload_page
        elif path == "/notes/upload" and "GET" in methods:
            replacement = modern_notes_upload_page
        elif path == "/sources/manage" and "GET" in methods:
            replacement = modern_manage_sources_page
        elif path == "/sources/upload" and "POST" in methods:
            replacement = modern_upload_single
            _original_add_api_route(
                self,
                "/sources/upload-batch",
                modern_upload_batch,
                methods=["POST"],
                response_class=HTMLResponse,
            )
        return _original_add_api_route(self, path, replacement, *args, **kwargs)

    FastAPI.add_api_route = _patched_add_api_route  # type: ignore[assignment]
