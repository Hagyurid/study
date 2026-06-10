import json
import re
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.config import DATABASE_PATH


def now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def conn() -> sqlite3.Connection:
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    return db


def _ensure_column(db: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = [row[1] for row in db.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in columns:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db() -> None:
    with conn() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS sources (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                subject TEXT NOT NULL DEFAULT '',
                source_type TEXT NOT NULL,
                original_name TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                mime_type TEXT,
                size_bytes INTEGER NOT NULL,
                extract_status TEXT NOT NULL,
                exam_scope_status TEXT NOT NULL DEFAULT 'unknown',
                exam_usage_mode TEXT NOT NULL DEFAULT 'style_generation',
                exam_range_note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS source_chunks (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                heading TEXT DEFAULT '',
                page_hint TEXT DEFAULT '',
                text TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_sources_type ON sources(source_type);
            CREATE INDEX IF NOT EXISTS idx_sources_subject ON sources(subject);
            CREATE INDEX IF NOT EXISTS idx_chunks_source ON source_chunks(source_id);
            CREATE INDEX IF NOT EXISTS idx_chunks_source_index ON source_chunks(source_id, chunk_index);
            CREATE INDEX IF NOT EXISTS idx_chunks_text ON source_chunks(text);

            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                project_type TEXT NOT NULL,
                source_ids TEXT NOT NULL DEFAULT '[]',
                metadata TEXT NOT NULL DEFAULT '{}',
                current_section_index INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'in_progress',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS outlines (
                project_id TEXT NOT NULL,
                section_index INTEGER NOT NULL,
                title TEXT NOT NULL,
                source_query TEXT DEFAULT '',
                slide_range TEXT DEFAULT '',
                transcript_range TEXT DEFAULT '',
                textbook_range TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                PRIMARY KEY(project_id, section_index)
            );

            CREATE TABLE IF NOT EXISTS sections (
                project_id TEXT NOT NULL,
                section_index INTEGER NOT NULL,
                title TEXT DEFAULT '',
                content_markdown TEXT NOT NULL,
                study_direction TEXT DEFAULT '',
                quality_report TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                PRIMARY KEY(project_id, section_index)
            );

            CREATE TABLE IF NOT EXISTS project_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                item_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_project_items ON project_items(project_id, item_type);

            CREATE TABLE IF NOT EXISTS problem_packs (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                token TEXT NOT NULL UNIQUE,
                pack_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS problem_pack_versions (
                id TEXT PRIMARY KEY,
                pack_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                source_id TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                pack_json TEXT NOT NULL DEFAULT '{}',
                version_label TEXT NOT NULL DEFAULT '',
                change_summary TEXT NOT NULL DEFAULT '',
                render_warnings TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_problem_pack_versions_pack ON problem_pack_versions(pack_id, version);

            CREATE TABLE IF NOT EXISTS calculator_blueprints (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                blueprint_json TEXT NOT NULL,
                validation_json TEXT NOT NULL DEFAULT '{}',
                generated_json TEXT NOT NULL DEFAULT '{}',
                metadata TEXT NOT NULL DEFAULT '{}',
                manual_markdown TEXT NOT NULL DEFAULT '',
                manual_source_id TEXT NOT NULL DEFAULT '',
                analysis_markdown TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS unit_maps (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source_ids TEXT NOT NULL DEFAULT '[]',
                map_json TEXT NOT NULL,
                created_by TEXT NOT NULL DEFAULT 'gpt',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS note_versions (
                id TEXT PRIMARY KEY,
                series_id TEXT NOT NULL,
                title TEXT NOT NULL,
                version INTEGER NOT NULL,
                source_id TEXT NOT NULL,
                source_type TEXT NOT NULL DEFAULT 'generated_note',
                content_markdown TEXT NOT NULL,
                change_summary TEXT NOT NULL DEFAULT '',
                based_on_version INTEGER,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_note_versions_series ON note_versions(series_id, version);
            CREATE INDEX IF NOT EXISTS idx_note_versions_source ON note_versions(source_id);

            CREATE TABLE IF NOT EXISTS transcript_revisions (
                id TEXT PRIMARY KEY,
                original_transcript_source_id TEXT NOT NULL DEFAULT '',
                corrected_source_id TEXT NOT NULL,
                title TEXT NOT NULL,
                terminology_map TEXT NOT NULL DEFAULT '{}',
                change_log TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS workflow_plans (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                subject TEXT NOT NULL DEFAULT '',
                selected_units TEXT NOT NULL DEFAULT '[]',
                selected_mode TEXT NOT NULL,
                unit_map_id TEXT DEFAULT '',
                source_ids TEXT NOT NULL DEFAULT '[]',
                reference_priority TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'planned',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS workflow_runs (
                id TEXT PRIMARY KEY,
                workflow_plan_id TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL,
                mode TEXT NOT NULL,
                subject TEXT NOT NULL DEFAULT '',
                selected_units TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'running',
                current_step INTEGER NOT NULL DEFAULT 1,
                total_steps INTEGER NOT NULL DEFAULT 0,
                last_saved_item TEXT NOT NULL DEFAULT '',
                resume_instruction TEXT NOT NULL DEFAULT '',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS workflow_checkpoints (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                step_index INTEGER NOT NULL,
                step_label TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'saved',
                saved_refs TEXT NOT NULL DEFAULT '{}',
                next_action TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_workflow_runs_status ON workflow_runs(status);
            CREATE INDEX IF NOT EXISTS idx_workflow_checkpoints_run ON workflow_checkpoints(run_id, step_index);
            """
        )
        _ensure_column(db, "sources", "subject", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "sources", "exam_scope_status", "TEXT NOT NULL DEFAULT 'unknown'")
        _ensure_column(db, "sources", "exam_usage_mode", "TEXT NOT NULL DEFAULT 'style_generation'")
        _ensure_column(db, "sources", "exam_range_note", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "problem_packs", "source_id", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "problem_packs", "subject", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "problem_packs", "unit_number", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "problem_packs", "unit_title", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "problem_packs", "tags", "TEXT NOT NULL DEFAULT '[]'")
        _ensure_column(db, "problem_packs", "source_refs", "TEXT NOT NULL DEFAULT '[]'")
        _ensure_column(db, "problem_packs", "exam_set_id", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "problem_packs", "exam_set_title", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "problem_packs", "question_count", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(db, "problem_packs", "version", "INTEGER NOT NULL DEFAULT 1")
        _ensure_column(db, "problem_packs", "version_label", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "problem_packs", "change_summary", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "problem_packs", "render_warnings", "TEXT NOT NULL DEFAULT '[]'")
        _ensure_column(db, "calculator_blueprints", "manual_markdown", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "calculator_blueprints", "manual_source_id", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "calculator_blueprints", "analysis_markdown", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "calculator_blueprints", "source_id", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "calculator_blueprints", "program_source_ids", "TEXT NOT NULL DEFAULT '[]'")
        _ensure_column(db, "calculator_blueprints", "analysis_source_id", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "note_versions", "doc_key", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "note_versions", "unit_number", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "note_versions", "unit_title", "TEXT NOT NULL DEFAULT ''")


def make_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(4)}"


UNIT_SOURCE_FIELDS = {
    "textbook": "textbook",
    "lectureSlides": "lecture_slides",
    "transcript": "transcript",
    "correctedTranscript": "corrected_transcript",
    "pastExam": "past_exam",
    "examTrend": "exam_trend",
    "generatedNote": "generated_note",
    "externalNote": "external_note",
}


def _safe_json_loads(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except Exception:
        return fallback


def _unit_source_ids(unit: Dict[str, Any]) -> Set[str]:
    ids: Set[str] = set()
    anchor = unit.get("lectureAnchor") or {}
    if anchor.get("sourceId"):
        ids.add(str(anchor.get("sourceId")))
    for key in UNIT_SOURCE_FIELDS:
        for item in unit.get(key, []) or []:
            sid = item.get("sourceId") if isinstance(item, dict) else None
            if sid:
                ids.add(str(sid))
    return ids


def chunk_text(text: str, max_chars: int = 2600, overlap: int = 250) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        cut = text.rfind("\n", start, end)
        if cut > start + 800:
            end = cut
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


def save_source(
    title: str,
    source_type: str,
    original_name: str,
    stored_path: str,
    mime_type: str,
    size_bytes: int,
    text: str,
    status: str,
    subject: str = "",
    exam_scope_status: str = "unknown",
    exam_usage_mode: str = "style_generation",
    exam_range_note: str = "",
) -> Dict[str, Any]:
    source_id = make_id("src")
    ts = now()
    chunks = chunk_text(text)
    with conn() as db:
        db.execute(
            """
            INSERT INTO sources(id,title,subject,source_type,original_name,stored_path,mime_type,size_bytes,extract_status,exam_scope_status,exam_usage_mode,exam_range_note,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (source_id, title, subject, source_type, original_name, stored_path, mime_type, size_bytes, status, exam_scope_status, exam_usage_mode, exam_range_note, ts),
        )
        for i, chunk in enumerate(chunks, 1):
            db.execute(
                """
                INSERT INTO source_chunks(id,source_id,chunk_index,heading,page_hint,text,created_at)
                VALUES(?,?,?,?,?,?,?)
                """,
                (f"{source_id}-c{i:04d}", source_id, i, "", "", chunk, ts),
            )
    return {"source_id": source_id, "title": title, "subject": subject, "source_type": source_type, "chunk_count": len(chunks), "extract_status": status, "exam_scope_status": exam_scope_status, "exam_usage_mode": exam_usage_mode, "exam_range_note": exam_range_note}


def save_text_source(title: str, source_type: str, text: str, original_name: str = "generated.md", subject: str = "") -> Dict[str, Any]:
    title = (title or Path(original_name or "generated.md").stem or source_type).strip()
    source_id = make_id("src")
    ts = now()
    stored_path = f"text://{source_type}/{source_id}/{original_name}"
    chunks = chunk_text(text)
    with conn() as db:
        db.execute(
            """
            INSERT INTO sources(id,title,subject,source_type,original_name,stored_path,mime_type,size_bytes,extract_status,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (source_id, title, subject, source_type, original_name, stored_path, "text/markdown", len(text.encode("utf-8")), "text_saved", ts),
        )
        for i, chunk in enumerate(chunks, 1):
            db.execute(
                """
                INSERT INTO source_chunks(id,source_id,chunk_index,heading,page_hint,text,created_at)
                VALUES(?,?,?,?,?,?,?)
                """,
                (f"{source_id}-c{i:04d}", source_id, i, "", "", chunk, ts),
            )
    return {"source_id": source_id, "title": title, "subject": subject, "source_type": source_type, "chunk_count": len(chunks), "extract_status": "text_saved"}


def list_sources(source_type: str = "", subject: str = "") -> List[Dict[str, Any]]:
    where = []
    params: List[Any] = []
    if source_type:
        where.append("source_type=?")
        params.append(source_type)
    if subject:
        where.append("subject=?")
        params.append(subject)
    where_sql = "WHERE " + " AND ".join(where) if where else ""
    with conn() as db:
        rows = db.execute(f"SELECT * FROM sources {where_sql} ORDER BY created_at DESC", params).fetchall()
    return [dict(row) for row in rows]


def get_source(source_id: str) -> Optional[Dict[str, Any]]:
    with conn() as db:
        row = db.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
    return dict(row) if row else None


def update_source_names(source_id: str, title: str = "", original_name: str = "", target: str = "title") -> Dict[str, Any]:
    source = get_source(source_id)
    if not source:
        return {}
    new_title = (title or "").strip()
    new_original = (original_name or "").strip()
    target = (target or "title").strip()
    updates = []
    params: List[Any] = []
    if target in {"title", "both"} and new_title:
        updates.append("title=?")
        params.append(new_title)
    if target in {"original_name", "both"} and new_original:
        updates.append("original_name=?")
        params.append(new_original)
    if not updates:
        return {"ok": False, "source_id": source_id, "error": "no update fields"}
    params.append(source_id)
    with conn() as db:
        db.execute(f"UPDATE sources SET {', '.join(updates)} WHERE id=?", params)
    updated = get_source(source_id) or {}
    return {
        "ok": True,
        "source_id": source_id,
        "old_title": source.get("title", ""),
        "new_title": updated.get("title", ""),
        "old_original_name": source.get("original_name", ""),
        "new_original_name": updated.get("original_name", ""),
    }

def search_sources(query: str, source_types: Optional[List[str]] = None, limit: int = 5, subject: str = "") -> List[Dict[str, Any]]:
    """Return the most relevant chunks without loading the entire chunk table when a query is provided."""
    terms = [term.strip().lower() for term in (query or "").split() if term.strip()]
    source_types = source_types or []
    limit = max(1, min(int(limit or 5), 10))
    params: List[Any] = []
    where: List[str] = []
    if source_types:
        placeholders = ",".join(["?"] * len(source_types))
        where.append(f"s.source_type IN ({placeholders})")
        params.extend(source_types)
    if subject:
        where.append("s.subject=?")
        params.append(subject)
    if terms:
        like_parts = []
        for term in terms:
            like_parts.append("(LOWER(c.text) LIKE ? OR LOWER(s.title) LIKE ? OR LOWER(s.original_name) LIKE ?)")
            like = f"%{term}%"
            params.extend([like, like, like])
        where.append("(" + " OR ".join(like_parts) + ")")
    where_sql = "WHERE " + " AND ".join(where) if where else ""

    with conn() as db:
        rows = [
            dict(row)
            for row in db.execute(
                f"""
                SELECT c.*, s.title AS source_title, s.subject, s.source_type, s.original_name
                FROM source_chunks c
                JOIN sources s ON s.id = c.source_id
                {where_sql}
                ORDER BY c.created_at DESC
                LIMIT ?
                """,
                params + [max(limit * 8, 20)],
            ).fetchall()
        ]

    scored: List[Dict[str, Any]] = []
    for row in rows:
        haystack = " ".join([
            row.get("text") or "",
            row.get("source_title") or "",
            row.get("original_name") or "",
        ]).lower()
        score = sum(haystack.count(term) for term in terms) if terms else 1
        if score > 0:
            row["score"] = score
            scored.append(row)
    scored.sort(key=lambda item: (item.get("score", 0), item.get("created_at", "")), reverse=True)
    return scored[:limit]


def _mapped_source_ids_from_unit_maps() -> Set[str]:
    mapped: Set[str] = set()
    with conn() as db:
        rows = db.execute("SELECT source_ids, map_json FROM unit_maps").fetchall()
    for row in rows:
        try:
            mapped.update(json.loads(row["source_ids"] or "[]"))
        except Exception:
            pass
        try:
            mapping = json.loads(row["map_json"] or "{}")
            for ids in (mapping.get("sources") or {}).values():
                if isinstance(ids, list):
                    mapped.update(str(item) for item in ids)
            for unit in mapping.get("units", []):
                mapped.update(_unit_source_ids(unit))
        except Exception:
            pass
    return mapped


def list_unmapped_sources(source_types: Optional[List[str]] = None, subject: str = "") -> List[Dict[str, Any]]:
    mapped = _mapped_source_ids_from_unit_maps()
    source_types = source_types or []
    result = []
    for row in list_sources(subject=subject):
        if source_types and row["source_type"] not in source_types:
            continue
        if row["id"] not in mapped:
            result.append(row)
    return result


def list_unit_maps() -> List[Dict[str, Any]]:
    with conn() as db:
        rows = db.execute("SELECT id,title,source_ids,created_by,created_at,updated_at FROM unit_maps ORDER BY created_at DESC").fetchall()
    result = []
    for row in rows:
        data = dict(row)
        data["source_ids"] = json.loads(data.get("source_ids") or "[]")
        result.append(data)
    return result


def get_unit_map(map_id: str) -> Optional[Dict[str, Any]]:
    with conn() as db:
        row = db.execute("SELECT * FROM unit_maps WHERE id=?", (map_id,)).fetchone()
    if not row:
        return None
    data = dict(row)
    data["source_ids"] = json.loads(data.get("source_ids") or "[]")
    data["map"] = json.loads(data.pop("map_json"))
    return data


def _modes() -> List[Dict[str, Any]]:
    return [
        {"mode": "lecture_note", "label": "정리본", "referencePriority": ["lecture_slides", "textbook", "corrected_transcript", "transcript", "exam_trend", "past_exam"]},
        {"mode": "calculator_prgm", "label": "계산기", "referencePriority": ["generated_note", "external_note", "exam_trend", "past_exam"]},
        {"mode": "problem_pack", "label": "문제지", "referencePriority": ["generated_note", "external_note", "exam_trend", "past_exam"]},
        {"mode": "exam_cram", "label": "시험 직전 정리", "referencePriority": ["generated_note", "external_note", "exam_trend", "past_exam"]},
        {"mode": "transcript_revision", "label": "전사본 보정", "referencePriority": ["transcript", "lecture_slides", "textbook"]},
        {"mode": "unit_mapping", "label": "단원 매핑", "referencePriority": ["lecture_slides", "textbook", "corrected_transcript", "transcript", "past_exam", "generated_note", "external_note"]},
    ]


def get_workflow_options(subject: str = "") -> Dict[str, Any]:
    sources = list_sources(subject=subject)
    subject_source_ids = {source["id"] for source in sources}
    unit_maps = list_unit_maps()
    units: List[Dict[str, Any]] = []
    visible_unit_maps: List[Dict[str, Any]] = []
    for item in unit_maps:
        full = get_unit_map(item["id"])
        if not full:
            continue
        map_units = full["map"].get("units", []) or []
        visible_units = []
        for unit in map_units:
            unit_source_ids = _unit_source_ids(unit)
            if subject and unit_source_ids and not (unit_source_ids & subject_source_ids):
                continue
            visible_units.append(unit)
            units.append({
                "unitMapId": item["id"],
                "unitId": unit.get("unitId"),
                "unitNumber": unit.get("unitNumber"),
                "unitTitle": unit.get("unitTitle"),
                "lectureAnchor": unit.get("lectureAnchor", {}),
                "lectureSlideRange": unit.get("lectureSlideRange", ""),
                "keywords": unit.get("keywords", []),
                "examRelevance": unit.get("examRelevance", "check"),
                "confidence": unit.get("confidence", "low"),
            })
        if not subject or visible_units or any(sid in subject_source_ids for sid in item.get("source_ids", [])):
            visible_item = dict(item)
            visible_item["visibleUnitCount"] = len(visible_units)
            visible_unit_maps.append(visible_item)
    return {
        "subjects": sorted({source.get("subject", "") for source in sources if source.get("subject", "")}),
        "availableSourceTypes": sorted({source["source_type"] for source in sources}),
        "sources": sources,
        "unmappedSources": list_unmapped_sources(subject=subject),
        "unitMaps": visible_unit_maps,
        "units": units,
        "availableModes": _modes(),
    }



def _limit_items(items: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    return list(items or [])[: max(0, int(limit or 0))]


def get_dashboard(subject: str = "", limit: int = 5) -> Dict[str, Any]:
    """Compact dashboard for Custom GPT menu/status calls.

    This intentionally returns summaries and short lists only, so the GPT can show
    menus/status without calling several separate Actions or pulling large data.
    """
    limit = max(1, min(int(limit or 5), 10))
    sources = list_sources(subject=subject)
    subjects = sorted({source.get("subject", "") for source in list_sources() if source.get("subject", "")})

    by_type: Dict[str, Dict[str, Any]] = {}
    for source in sources:
        source_type = source.get("source_type", "unknown")
        item = by_type.setdefault(source_type, {"count": 0, "recent": []})
        item["count"] += 1
        if len(item["recent"]) < 3:
            item["recent"].append({
                "sourceId": source.get("id", ""),
                "title": source.get("title", ""),
                "createdAt": source.get("created_at", ""),
                "examScopeStatus": source.get("exam_scope_status", ""),
                "examUsageMode": source.get("exam_usage_mode", ""),
            })

    mapping = get_mapping_status(subject)
    study_notes = list_study_notes(subject)
    problem_packs = list_problem_packs(subject)
    calculator_projects = list_calculator_blueprints(subject)
    active_runs = [run for run in list_workflow_runs() if run.get("status") in {"running", "paused"}]
    if subject:
        active_runs = [run for run in active_runs if run.get("subject") == subject]

    recent_runs = list_workflow_runs()[:limit]
    if subject:
        recent_runs = [run for run in recent_runs if run.get("subject") == subject]

    return {
        "subject": subject,
        "subjects": subjects,
        "summary": {
            "sourceCount": len(sources),
            "sourceTypeCount": len(by_type),
            "mappedSourceCount": mapping.get("summary", {}).get("mappedSourceCount", 0),
            "unmappedSourceCount": mapping.get("summary", {}).get("unmappedSourceCount", 0),
            "unitMapCount": mapping.get("summary", {}).get("unitMapCount", 0),
            "unitCount": mapping.get("summary", {}).get("unitCount", 0),
            "studyNoteCount": len(study_notes),
            "problemPackCount": len(problem_packs),
            "calculatorProjectCount": len(calculator_projects),
            "activeWorkflowRunCount": len(active_runs),
            "deletedOrMissingReferenceCount": mapping.get("summary", {}).get("deletedOrMissingReferenceCount", 0),
        },
        "warnings": [
            item for item in [
                {"type": "missing_refs", "count": mapping.get("summary", {}).get("deletedOrMissingReferenceCount", 0), "message": "삭제되었거나 누락된 source 참조가 있습니다."} if mapping.get("summary", {}).get("deletedOrMissingReferenceCount", 0) else None,
                {"type": "active_workflows", "count": len(active_runs), "message": "진행 중이거나 중단된 workflow가 있습니다."} if active_runs else None,
            ] if item
        ],
        "bySourceType": by_type,
        "recentSources": _limit_items(sources, limit),
        "unmappedSources": _limit_items(mapping.get("unmappedSources", []), limit),
        "unitMaps": _limit_items(mapping.get("unitMaps", []), limit),
        "units": _limit_items(mapping.get("units", []), limit),
        "studyNotes": _limit_items(study_notes, limit),
        "problemPacks": _limit_items(problem_packs, limit),
        "calculatorProjects": _limit_items(calculator_projects, limit),
        "activeWorkflowRuns": _limit_items(active_runs, limit),
        "recentWorkflowRuns": _limit_items(recent_runs, limit),
        "quickLinks": {
            "home": "/",
            "upload": "/upload",
            "studyNoteStudio": "/static/study/index.html",
            "solvePad": "/static/solvepad/index.html",
            "calculatorStudio": "/static/casio/index.html",
            "fileManager": "/sources/manage",
        },
        "recommendedActionPolicy": {
            "menuAndStatus": "use getDashboard first",
            "uploadAndDownload": "use site UI links",
            "longWork": "use workflow run and checkpoint actions",
        },
    }

def create_workflow_plan(
    title: str,
    subject: str,
    selected_units: List[str],
    selected_mode: str,
    unit_map_id: str,
    source_ids: List[str],
    reference_priority: List[str],
    notes: str = "",
) -> Dict[str, Any]:
    plan_id = make_id("wfp")
    ts = now()
    with conn() as db:
        db.execute(
            """
            INSERT INTO workflow_plans(id,title,subject,selected_units,selected_mode,unit_map_id,source_ids,reference_priority,status,notes,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                plan_id,
                title,
                subject,
                json.dumps(selected_units, ensure_ascii=False),
                selected_mode,
                unit_map_id,
                json.dumps(source_ids, ensure_ascii=False),
                json.dumps(reference_priority, ensure_ascii=False),
                "planned",
                notes,
                ts,
                ts,
            ),
        )
    return {"workflow_plan_id": plan_id, "title": title, "selected_mode": selected_mode, "status": "planned"}


def list_workflow_plans() -> List[Dict[str, Any]]:
    with conn() as db:
        rows = db.execute("SELECT * FROM workflow_plans ORDER BY created_at DESC").fetchall()
    result = []
    for row in rows:
        data = dict(row)
        data["selected_units"] = json.loads(data.get("selected_units") or "[]")
        data["source_ids"] = json.loads(data.get("source_ids") or "[]")
        data["reference_priority"] = json.loads(data.get("reference_priority") or "[]")
        result.append(data)
    return result






def get_source_markdown(source_id: str) -> Optional[Dict[str, Any]]:
    source = get_source(source_id)
    if not source:
        return None
    with conn() as db:
        note = db.execute(
            "SELECT * FROM note_versions WHERE source_id=? ORDER BY version DESC LIMIT 1",
            (source_id,),
        ).fetchone()
        if note:
            note_data = dict(note)
            return {"source": source, "markdown": note_data.get("content_markdown", ""), "note_version": note_data}
        rows = db.execute(
            "SELECT text FROM source_chunks WHERE source_id=? ORDER BY chunk_index ASC",
            (source_id,),
        ).fetchall()
    return {"source": source, "markdown": "\n\n".join(row["text"] for row in rows), "note_version": None}


def update_source_markdown(source_id: str, content_markdown: str, title: str = "", change_summary: str = "edited", based_on_version: Optional[int] = None) -> Dict[str, Any]:
    current = get_source_markdown(source_id)
    if not current:
        return {}
    source = current["source"]
    new_title = (title or source.get("title") or "Untitled").strip()
    ts = now()
    chunks = chunk_text(content_markdown)
    new_version = None
    version_id = ""
    series_id = ""
    with conn() as db:
        db.execute("UPDATE sources SET title=?, size_bytes=?, extract_status=? WHERE id=?", (new_title, len(content_markdown.encode("utf-8")), "markdown_edited", source_id))
        db.execute("DELETE FROM source_chunks WHERE source_id=?", (source_id,))
        for i, chunk in enumerate(chunks, 1):
            db.execute(
                """
                INSERT INTO source_chunks(id,source_id,chunk_index,heading,page_hint,text,created_at)
                VALUES(?,?,?,?,?,?,?)
                """,
                (f"{source_id}-c{i:04d}", source_id, i, "", "", chunk, ts),
            )
        note = db.execute("SELECT * FROM note_versions WHERE source_id=? ORDER BY version DESC LIMIT 1", (source_id,)).fetchone()
        if note:
            series_id = note["series_id"] or source_id
            if based_on_version is None:
                based_on_version = int(note["version"] or 0)
            row = db.execute("SELECT MAX(version) AS max_version FROM note_versions WHERE series_id=?", (series_id,)).fetchone()
            new_version = int(row["max_version"] or 0) + 1
            version_id = make_id("ver")
            db.execute(
                """
                INSERT INTO note_versions(id,series_id,title,version,source_id,source_type,content_markdown,change_summary,based_on_version,created_at,doc_key,unit_number,unit_title)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    version_id,
                    series_id,
                    new_title,
                    new_version,
                    source_id,
                    source.get("source_type") or note["source_type"] or "generated_note",
                    content_markdown,
                    change_summary,
                    based_on_version,
                    ts,
                    note["doc_key"] if "doc_key" in note.keys() else "",
                    note["unit_number"] if "unit_number" in note.keys() else "",
                    note["unit_title"] if "unit_title" in note.keys() else "",
                ),
            )
    return {"ok": True, "source_id": source_id, "title": new_title, "chunk_count": len(chunks), "updated_at": ts, "note_version_id": version_id, "series_id": series_id, "version": new_version}


def list_note_source_versions(source_id: str) -> List[Dict[str, Any]]:
    with conn() as db:
        seed = db.execute("SELECT series_id FROM note_versions WHERE source_id=? ORDER BY version DESC LIMIT 1", (source_id,)).fetchone()
        if not seed:
            return []
        rows = db.execute(
            "SELECT id,series_id,title,version,source_id,source_type,change_summary,based_on_version,created_at,doc_key,unit_number,unit_title FROM note_versions WHERE series_id=? ORDER BY version DESC",
            (seed["series_id"],),
        ).fetchall()
    return [dict(row) for row in rows]


def get_note_version(version_id: str) -> Optional[Dict[str, Any]]:
    with conn() as db:
        row = db.execute("SELECT * FROM note_versions WHERE id=?", (version_id,)).fetchone()
    return dict(row) if row else None


def restore_note_source_version(source_id: str, version_id: str, change_summary: str = "restored previous version") -> Dict[str, Any]:
    target = get_note_version(version_id)
    if not target:
        return {}
    current = get_source_markdown(source_id)
    if not current:
        return {}
    latest = current.get("note_version") or {}
    if target.get("series_id") != latest.get("series_id"):
        return {}
    title = target.get("title") or (current.get("source") or {}).get("title") or "Untitled"
    summary = change_summary or f"restored from v{target.get('version')}"
    return update_source_markdown(source_id, target.get("content_markdown") or "", title, summary, int(latest.get("version") or 0) or None)


def list_study_notes(subject: str = "", source_type: str = "") -> List[Dict[str, Any]]:
    allowed = {"generated_note", "external_note", "exam_cram", "calculator_manual", "note_example"}
    if source_type:
        types = [source_type]
    else:
        types = sorted(allowed)
    result: List[Dict[str, Any]] = []
    for item_type in types:
        if item_type not in allowed:
            continue
        for source in list_sources(item_type, subject):
            normalized = dict(source)
            normalized["source_id"] = normalized.get("id", "")
            result.append(normalized)
    result.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return result



def _remove_source_ref_from_json(value: Any, source_id: str) -> tuple[Any, int]:
    """Remove a source_id from nested mapping JSON while keeping structure stable."""
    removed = 0
    if isinstance(value, dict):
        cleaned: Dict[str, Any] = {}
        for key, item in value.items():
            if key in {"sourceId", "source_id"} and str(item) == source_id:
                removed += 1
                continue
            new_item, count = _remove_source_ref_from_json(item, source_id)
            removed += count
            if key == "lectureAnchor" and isinstance(new_item, dict) and not new_item.get("sourceId"):
                # Keep the anchor shape, but mark it for review instead of silently deleting the whole unit.
                new_item["sourceId"] = ""
                new_item["basis"] = (new_item.get("basis") or "") + " CHECK SOURCE: deleted source reference removed"
            cleaned[key] = new_item
        return cleaned, removed
    if isinstance(value, list):
        cleaned_list: List[Any] = []
        for item in value:
            if isinstance(item, str) and item == source_id:
                removed += 1
                continue
            if isinstance(item, dict) and str(item.get("sourceId") or item.get("source_id") or "") == source_id:
                removed += 1
                continue
            new_item, count = _remove_source_ref_from_json(item, source_id)
            removed += count
            cleaned_list.append(new_item)
        return cleaned_list, removed
    return value, 0


def cleanup_deleted_source_refs(source_id: str) -> Dict[str, Any]:
    """Remove references to a deleted source from unit maps and workflow metadata/checkpoints."""
    source_id = str(source_id or "").strip()
    if not source_id:
        return {"removed_unit_map_refs": 0, "removed_workflow_refs": 0, "updated_unit_maps": 0, "updated_workflows": 0, "updated_checkpoints": 0}
    removed_unit_refs = 0
    removed_workflow_refs = 0
    updated_unit_maps = 0
    updated_workflows = 0
    updated_checkpoints = 0
    ts = now()
    with conn() as db:
        rows = db.execute("SELECT id,source_ids,map_json FROM unit_maps").fetchall()
        for row in rows:
            source_ids = _safe_json_loads(row["source_ids"], [])
            map_json = _safe_json_loads(row["map_json"], {})
            old_source_ids = list(source_ids) if isinstance(source_ids, list) else []
            new_source_ids = [sid for sid in old_source_ids if str(sid) != source_id]
            removed = len(old_source_ids) - len(new_source_ids)
            new_map, count = _remove_source_ref_from_json(map_json, source_id)
            removed += count
            if removed:
                removed_unit_refs += removed
                updated_unit_maps += 1
                db.execute(
                    "UPDATE unit_maps SET source_ids=?, map_json=?, updated_at=? WHERE id=?",
                    (json.dumps(new_source_ids, ensure_ascii=False), json.dumps(new_map, ensure_ascii=False), ts, row["id"]),
                )

        rows = db.execute("SELECT id,metadata FROM workflow_runs").fetchall()
        for row in rows:
            metadata = _safe_json_loads(row["metadata"], {})
            new_meta, count = _remove_source_ref_from_json(metadata, source_id)
            if count:
                removed_workflow_refs += count
                updated_workflows += 1
                db.execute("UPDATE workflow_runs SET metadata=?, updated_at=? WHERE id=?", (json.dumps(new_meta, ensure_ascii=False), ts, row["id"]))

        rows = db.execute("SELECT id,saved_refs FROM workflow_checkpoints").fetchall()
        for row in rows:
            saved_refs = _safe_json_loads(row["saved_refs"], {})
            new_refs, count = _remove_source_ref_from_json(saved_refs, source_id)
            if count:
                removed_workflow_refs += count
                updated_checkpoints += 1
                db.execute("UPDATE workflow_checkpoints SET saved_refs=? WHERE id=?", (json.dumps(new_refs, ensure_ascii=False), row["id"]))
    return {
        "removed_unit_map_refs": removed_unit_refs,
        "removed_workflow_refs": removed_workflow_refs,
        "updated_unit_maps": updated_unit_maps,
        "updated_workflows": updated_workflows,
        "updated_checkpoints": updated_checkpoints,
    }


def cleanup_missing_unit_refs() -> Dict[str, Any]:
    """Remove source references from unit maps when the source no longer exists."""
    with conn() as db:
        existing = {row["id"] for row in db.execute("SELECT id FROM sources").fetchall()}
        rows = db.execute("SELECT source_ids,map_json FROM unit_maps").fetchall()
    refs: Set[str] = set()
    for row in rows:
        for sid in _safe_json_loads(row["source_ids"], []):
            if sid:
                refs.add(str(sid))
        mapping = _safe_json_loads(row["map_json"], {})
        def walk(x: Any) -> None:
            if isinstance(x, dict):
                sid = x.get("sourceId") or x.get("source_id")
                if sid:
                    refs.add(str(sid))
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        walk(mapping)
    missing = sorted(sid for sid in refs if sid and sid not in existing)
    total_unit = total_workflow = 0
    updated_maps = updated_runs = updated_checkpoints = 0
    for sid in missing:
        result = cleanup_deleted_source_refs(sid)
        total_unit += int(result.get("removed_unit_map_refs", 0))
        total_workflow += int(result.get("removed_workflow_refs", 0))
        updated_maps += int(result.get("updated_unit_maps", 0))
        updated_runs += int(result.get("updated_workflows", 0))
        updated_checkpoints += int(result.get("updated_checkpoints", 0))
    return {
        "missing_source_ids": missing,
        "missing_ref_count": len(missing),
        "removed_unit_map_refs": total_unit,
        "removed_workflow_refs": total_workflow,
        "updated_unit_maps": updated_maps,
        "updated_workflows": updated_runs,
        "updated_checkpoints": updated_checkpoints,
    }


def _json_deep_contains(value: Any, needle: str) -> bool:
    if not needle:
        return False
    if isinstance(value, str):
        return needle in value
    if isinstance(value, dict):
        return any(_json_deep_contains(v, needle) for v in value.values())
    if isinstance(value, list):
        return any(_json_deep_contains(v, needle) for v in value)
    return False


def _loads_json_safe(raw: str, default: Any) -> Any:
    try:
        return json.loads(raw or "")
    except Exception:
        return default


def _collect_note_series_for_source(db: sqlite3.Connection, source_id: str) -> Tuple[List[str], List[str]]:
    rows = db.execute("SELECT series_id FROM note_versions WHERE source_id=?", (source_id,)).fetchall()
    series_ids = sorted({row["series_id"] for row in rows if row["series_id"]})
    if not series_ids:
        return [], []
    version_source_ids: set[str] = set()
    for sid in series_ids:
        for row in db.execute("SELECT source_id FROM note_versions WHERE series_id=?", (sid,)).fetchall():
            if row["source_id"]:
                version_source_ids.add(row["source_id"])
    return series_ids, sorted(version_source_ids)


def _collect_problem_packs_for_source(db: sqlite3.Connection, source_id: str) -> List[sqlite3.Row]:
    rows = db.execute("SELECT * FROM problem_packs").fetchall()
    linked: List[sqlite3.Row] = []
    for row in rows:
        if row["source_id"] == source_id:
            linked.append(row)
            continue
        source_refs = _loads_json_safe(row["source_refs"] if "source_refs" in row.keys() else "[]", [])
        pack_json = _loads_json_safe(row["pack_json"] if "pack_json" in row.keys() else "{}", {})
        if _json_deep_contains(source_refs, source_id) or _json_deep_contains(pack_json, source_id):
            linked.append(row)
    return linked

def delete_source(source_id: str, delete_file: bool = True, cleanup_refs: bool = True) -> Dict[str, Any]:
    source = get_source(source_id)
    if not source:
        return {}
    if source.get("source_type") == "calculator_project":
        with conn() as db:
            project = db.execute("SELECT id FROM calculator_blueprints WHERE source_id=?", (source_id,)).fetchone()
        if project:
            return delete_calculator_blueprint(project["id"])

    deleted_file = False
    file_error = ""
    if delete_file:
        stored_path = source.get("stored_path", "")
        if stored_path and not stored_path.startswith("text://") and not stored_path.startswith("generated://"):
            try:
                path = Path(stored_path)
                if path.exists() and path.is_file():
                    path.unlink()
                    deleted_file = True
            except Exception as exc:
                file_error = str(exc)

    with conn() as db:
        # Collect cascades before deleting the seed source.
        note_series_ids, note_source_ids = _collect_note_series_for_source(db, source_id)
        linked_problem_rows = _collect_problem_packs_for_source(db, source_id)
        linked_pack_ids = sorted({row["id"] for row in linked_problem_rows if row["id"]})
        linked_pack_source_ids = sorted({row["source_id"] for row in linked_problem_rows if row["source_id"]})

        # If deleting an original transcript, delete revision records and the generated corrected transcript sources too.
        revision_rows = db.execute(
            "SELECT corrected_source_id FROM transcript_revisions WHERE original_transcript_source_id=? OR corrected_source_id=?",
            (source_id, source_id),
        ).fetchall()
        transcript_generated_source_ids = sorted({row["corrected_source_id"] for row in revision_rows if row["corrected_source_id"] and row["corrected_source_id"] != source_id})

        cascade_source_ids = {source_id, *note_source_ids, *linked_pack_source_ids, *transcript_generated_source_ids}
        chunk_count = 0
        for sid in sorted(cascade_source_ids):
            row = db.execute("SELECT COUNT(*) AS n FROM source_chunks WHERE source_id=?", (sid,)).fetchone()
            chunk_count += int(row["n"] if row else 0)
            db.execute("DELETE FROM source_chunks WHERE source_id=?", (sid,))

        if note_series_ids:
            for series_id in note_series_ids:
                db.execute("DELETE FROM note_versions WHERE series_id=?", (series_id,))
        else:
            db.execute("DELETE FROM note_versions WHERE source_id=?", (source_id,))

        db.execute("DELETE FROM transcript_revisions WHERE corrected_source_id=? OR original_transcript_source_id=?", (source_id, source_id))
        for sid in transcript_generated_source_ids:
            db.execute("DELETE FROM transcript_revisions WHERE corrected_source_id=? OR original_transcript_source_id=?", (sid, sid))

        for pack_id in linked_pack_ids:
            db.execute("DELETE FROM problem_pack_versions WHERE pack_id=?", (pack_id,))
            db.execute("DELETE FROM problem_packs WHERE id=?", (pack_id,))
        db.execute("DELETE FROM problem_packs WHERE source_id=?", (source_id,))
        db.execute("DELETE FROM problem_pack_versions WHERE source_id=?", (source_id,))

        for sid in sorted(cascade_source_ids):
            db.execute("DELETE FROM sources WHERE id=?", (sid,))

    cleanup_report = cleanup_deleted_source_refs(source_id) if cleanup_refs else {}
    return {
        "ok": True,
        "deleted_source_id": source_id,
        "deleted_title": source.get("title", ""),
        "deleted_chunks": int(chunk_count or 0),
        "deleted_file": deleted_file,
        "file_error": file_error,
        "cascade_deleted_sources": sorted(s for s in cascade_source_ids if s != source_id),
        "cascade_deleted_note_series": note_series_ids,
        "cascade_deleted_problem_packs": linked_pack_ids,
        "cascade_deleted_transcript_sources": transcript_generated_source_ids,
        **cleanup_report,
    }


def _mapped_source_ids_with_details() -> Dict[str, List[Dict[str, Any]]]:
    details: Dict[str, List[Dict[str, Any]]] = {}
    with conn() as db:
        rows = db.execute("SELECT id,title,map_json FROM unit_maps ORDER BY created_at DESC").fetchall()
    for row in rows:
        try:
            mapping = json.loads(row["map_json"] or "{}")
        except Exception:
            continue
        unit_map_id = row["id"]
        unit_map_title = row["title"]
        for source_type, ids in (mapping.get("sources") or {}).items():
            if isinstance(ids, list):
                for sid in ids:
                    details.setdefault(str(sid), []).append({
                        "unitMapId": unit_map_id,
                        "unitMapTitle": unit_map_title,
                        "sourceType": source_type,
                        "unitId": "",
                        "unitNumber": "",
                        "unitTitle": "",
                        "basis": "listed in unit map sources",
                    })
        for unit in mapping.get("units", []) or []:
            unit_info = {
                "unitMapId": unit_map_id,
                "unitMapTitle": unit_map_title,
                "unitId": unit.get("unitId", ""),
                "unitNumber": unit.get("unitNumber", ""),
                "unitTitle": unit.get("unitTitle", ""),
            }
            anchor = unit.get("lectureAnchor") or {}
            sid = anchor.get("sourceId")
            if sid:
                details.setdefault(sid, []).append({
                    **unit_info,
                    "sourceType": "lecture_slides",
                    "basis": anchor.get("basis", ""),
                    "location": anchor.get("slideRange") or anchor.get("pageRange") or "",
                })
            field_map = {
                "textbook": "textbook",
                "transcript": "transcript",
                "correctedTranscript": "corrected_transcript",
                "pastExam": "past_exam",
                "examTrend": "exam_trend",
                "generatedNote": "generated_note",
                "externalNote": "external_note",
                "lectureSlides": "lecture_slides",
            }
            for key, source_type in field_map.items():
                for item in unit.get(key, []) or []:
                    sid = item.get("sourceId")
                    if sid:
                        details.setdefault(sid, []).append({
                            **unit_info,
                            "sourceType": source_type,
                            "basis": item.get("basis", ""),
                            "location": item.get("pageRange") or item.get("slideRange") or item.get("timeRange") or item.get("sectionRange") or ",".join(item.get("problemRefs", []) or []),
                        })
    return details


def get_mapping_status(subject: str = "") -> Dict[str, Any]:
    sources = list_sources(subject=subject)
    source_by_id = {source["id"]: source for source in sources}
    mapped_details = _mapped_source_ids_with_details()

    with conn() as db:
        unit_map_rows = [dict(row) for row in db.execute("SELECT * FROM unit_maps ORDER BY created_at DESC").fetchall()]

    unit_maps = []
    units = []
    extension_only = []
    unmapped_from_maps = []
    referenced_source_ids = set()

    for row in unit_map_rows:
        try:
            source_ids = json.loads(row.get("source_ids") or "[]")
            mapping = json.loads(row.get("map_json") or "{}")
        except Exception:
            source_ids = []
            mapping = {}
        if subject:
            # Keep unit map if any listed source belongs to subject or map title mentions subject.
            if not any(sid in source_by_id for sid in source_ids) and subject.lower() not in (row.get("title", "").lower()):
                continue

        unit_count = len(mapping.get("units", []) or [])
        unit_maps.append({
            "unitMapId": row["id"],
            "title": row["title"],
            "mappingBasis": mapping.get("mappingBasis", ""),
            "schemaVersion": mapping.get("schemaVersion", ""),
            "unitCount": unit_count,
            "sourceIds": source_ids,
            "createdAt": row.get("created_at", ""),
        })

        for unit in mapping.get("units", []) or []:
            unit_sources = []
            anchor = unit.get("lectureAnchor") or {}
            if anchor.get("sourceId"):
                unit_sources.append({
                    "sourceId": anchor.get("sourceId"),
                    "sourceType": "lecture_slides",
                    "location": anchor.get("slideRange") or anchor.get("pageRange") or "",
                })
                referenced_source_ids.add(anchor.get("sourceId"))
            for key, source_type in {
                "textbook": "textbook",
                "transcript": "transcript",
                "correctedTranscript": "corrected_transcript",
                "pastExam": "past_exam",
                "examTrend": "exam_trend",
                "generatedNote": "generated_note",
                "externalNote": "external_note",
                "lectureSlides": "lecture_slides",
            }.items():
                for item in unit.get(key, []) or []:
                    sid = item.get("sourceId")
                    if sid:
                        referenced_source_ids.add(sid)
                        unit_sources.append({
                            "sourceId": sid,
                            "sourceType": source_type,
                            "location": item.get("pageRange") or item.get("slideRange") or item.get("timeRange") or item.get("sectionRange") or ",".join(item.get("problemRefs", []) or []),
                        })
            units.append({
                "unitMapId": row["id"],
                "unitNumber": unit.get("unitNumber", ""),
                "unitId": unit.get("unitId", ""),
                "unitTitle": unit.get("unitTitle", ""),
                "lectureAnchor": anchor,
                "examRelevance": unit.get("examRelevance", "check"),
                "confidence": unit.get("confidence", "low"),
                "mappedSourceCount": len({s["sourceId"] for s in unit_sources}),
                "mappedSources": unit_sources,
                "checkItems": unit.get("checkItems", []),
            })
        for item in mapping.get("extensionOnly", []) or []:
            extension_only.append({"unitMapId": row["id"], **item})
            if item.get("sourceId"):
                referenced_source_ids.add(item.get("sourceId"))
        for item in mapping.get("unmapped", []) or []:
            unmapped_from_maps.append({"unitMapId": row["id"], **item})

    mapped_sources = []
    unmapped_sources = []
    deleted_or_missing_refs = sorted([sid for sid in referenced_source_ids if sid not in source_by_id])

    for source in sources:
        source_details = mapped_details.get(source["id"], [])
        if source_details:
            mapped_sources.append({
                "sourceId": source["id"],
                "title": source["title"],
                "subject": source.get("subject", ""),
                "sourceType": source["source_type"],
                "mappedCount": len(source_details),
                "mappedTo": source_details[:10],
            })
        else:
            unmapped_sources.append({
                "sourceId": source["id"],
                "title": source["title"],
                "subject": source.get("subject", ""),
                "sourceType": source["source_type"],
                "createdAt": source.get("created_at", ""),
            })

    by_type: Dict[str, Dict[str, int]] = {}
    for source in sources:
        t = source["source_type"]
        by_type.setdefault(t, {"total": 0, "mapped": 0, "unmapped": 0})
        by_type[t]["total"] += 1
    for source in mapped_sources:
        by_type.setdefault(source["sourceType"], {"total": 0, "mapped": 0, "unmapped": 0})
        by_type[source["sourceType"]]["mapped"] += 1
    for source in unmapped_sources:
        by_type.setdefault(source["sourceType"], {"total": 0, "mapped": 0, "unmapped": 0})
        by_type[source["sourceType"]]["unmapped"] += 1

    return {
        "subject": subject,
        "summary": {
            "sourceCount": len(sources),
            "mappedSourceCount": len(mapped_sources),
            "unmappedSourceCount": len(unmapped_sources),
            "unitMapCount": len(unit_maps),
            "unitCount": len(units),
            "extensionOnlyCount": len(extension_only),
            "unmappedFromMapsCount": len(unmapped_from_maps),
            "deletedOrMissingReferenceCount": len(deleted_or_missing_refs),
        },
        "bySourceType": by_type,
        "unitMaps": unit_maps,
        "units": units,
        "mappedSources": mapped_sources,
        "unmappedSources": unmapped_sources,
        "extensionOnly": extension_only,
        "unmappedFromMaps": unmapped_from_maps,
        "deletedOrMissingReferences": deleted_or_missing_refs,
    }

def list_external_notes(subject: str = "") -> List[Dict[str, Any]]:
    return list_sources(source_type="external_note", subject=subject)


def create_workflow_run(
    title: str,
    mode: str,
    subject: str = "",
    selected_units: Optional[List[str]] = None,
    workflow_plan_id: str = "",
    total_steps: int = 0,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    run_id = make_id("run")
    ts = now()
    selected_units = selected_units or []
    metadata = metadata or {}
    if not total_steps:
        total_steps = max(1, len(selected_units))
    with conn() as db:
        db.execute(
            """
            INSERT INTO workflow_runs(id,workflow_plan_id,title,mode,subject,selected_units,status,current_step,total_steps,last_saved_item,resume_instruction,metadata,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                run_id,
                workflow_plan_id,
                title,
                mode,
                subject,
                json.dumps(selected_units, ensure_ascii=False),
                "running",
                1,
                total_steps,
                "",
                "다음 단계부터 이어서 진행",
                json.dumps(metadata, ensure_ascii=False),
                ts,
                ts,
            ),
        )
    return {
        "workflow_run_id": run_id,
        "title": title,
        "mode": mode,
        "subject": subject,
        "selected_units": selected_units,
        "status": "running",
        "current_step": 1,
        "total_steps": total_steps,
    }


def get_workflow_run(run_id: str) -> Optional[Dict[str, Any]]:
    with conn() as db:
        row = db.execute("SELECT * FROM workflow_runs WHERE id=?", (run_id,)).fetchone()
    if not row:
        return None
    data = dict(row)
    data["selected_units"] = json.loads(data.get("selected_units") or "[]")
    data["metadata"] = json.loads(data.get("metadata") or "{}")
    return data


def list_workflow_runs(status: str = "") -> List[Dict[str, Any]]:
    with conn() as db:
        if status:
            rows = db.execute("SELECT * FROM workflow_runs WHERE status=? ORDER BY updated_at DESC", (status,)).fetchall()
        else:
            rows = db.execute("SELECT * FROM workflow_runs ORDER BY updated_at DESC").fetchall()
    result = []
    for row in rows:
        data = dict(row)
        data["selected_units"] = json.loads(data.get("selected_units") or "[]")
        data["metadata"] = json.loads(data.get("metadata") or "{}")
        result.append(data)
    return result


def save_workflow_checkpoint(
    run_id: str,
    step_index: int,
    step_label: str = "",
    status: str = "saved",
    saved_refs: Optional[Dict[str, Any]] = None,
    next_action: str = "",
    notes: str = "",
    advance_to_next: bool = True,
) -> Dict[str, Any]:
    checkpoint_id = make_id("ckp")
    ts = now()
    saved_refs = saved_refs or {}
    run = get_workflow_run(run_id)
    if not run:
        return {}

    total_steps = int(run.get("total_steps") or 0)
    next_step = step_index + 1 if advance_to_next else step_index
    if next_step > total_steps and status in {"saved", "done", "completed"}:
        run_status = "completed"
        next_step = total_steps or step_index
    elif status in {"paused", "timeout_safe_saved"}:
        run_status = "paused"
    elif status == "failed":
        run_status = "failed"
    else:
        run_status = "running"

    with conn() as db:
        db.execute(
            """
            INSERT INTO workflow_checkpoints(id,run_id,step_index,step_label,status,saved_refs,next_action,notes,created_at)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                checkpoint_id,
                run_id,
                step_index,
                step_label,
                status,
                json.dumps(saved_refs, ensure_ascii=False),
                next_action,
                notes,
                ts,
            ),
        )
        db.execute(
            """
            UPDATE workflow_runs
            SET current_step=?, status=?, last_saved_item=?, resume_instruction=?, updated_at=?
            WHERE id=?
            """,
            (
                next_step,
                run_status,
                json.dumps(saved_refs, ensure_ascii=False),
                next_action,
                ts,
                run_id,
            ),
        )
    return {
        "checkpoint_id": checkpoint_id,
        "workflow_run_id": run_id,
        "step_index": step_index,
        "next_step": next_step,
        "run_status": run_status,
        "resume_instruction": next_action,
    }


def list_workflow_checkpoints(run_id: str) -> List[Dict[str, Any]]:
    with conn() as db:
        rows = db.execute(
            "SELECT * FROM workflow_checkpoints WHERE run_id=? ORDER BY step_index, created_at",
            (run_id,),
        ).fetchall()
    result = []
    for row in rows:
        data = dict(row)
        data["saved_refs"] = json.loads(data.get("saved_refs") or "{}")
        result.append(data)
    return result


def get_next_workflow_step(run_id: str) -> Dict[str, Any]:
    run = get_workflow_run(run_id)
    if not run:
        return {}
    checkpoints = list_workflow_checkpoints(run_id)
    selected_units = run.get("selected_units", [])
    current_step = int(run.get("current_step") or 1)
    next_unit = None
    if 1 <= current_step <= len(selected_units):
        next_unit = selected_units[current_step - 1]
    return {
        "run": run,
        "next_step_index": current_step,
        "next_unit": next_unit,
        "recent_checkpoints": checkpoints[-3:],
        "resume_instruction": run.get("resume_instruction", ""),
    }

def create_project(title: str, project_type: str, source_ids: List[str], metadata: Dict[str, Any]) -> Dict[str, Any]:
    project_id = make_id("prj")
    ts = now()
    with conn() as db:
        db.execute(
            """
            INSERT INTO projects(id,title,project_type,source_ids,metadata,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (project_id, title, project_type, json.dumps(source_ids, ensure_ascii=False), json.dumps(metadata, ensure_ascii=False), ts, ts),
        )
    return {"project_id": project_id, "title": title, "project_type": project_type, "status": "in_progress"}


def save_outline(project_id: str, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
    with conn() as db:
        db.execute("DELETE FROM outlines WHERE project_id=?", (project_id,))
        for section in sections:
            db.execute(
                """
                INSERT INTO outlines(project_id,section_index,title,source_query,slide_range,transcript_range,textbook_range,status)
                VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    project_id,
                    section.get("index"),
                    section.get("title", ""),
                    section.get("source_query", ""),
                    section.get("slide_range", ""),
                    section.get("transcript_range", ""),
                    section.get("textbook_range", ""),
                    section.get("status", "pending"),
                ),
            )
    return {"ok": True, "section_count": len(sections)}


def get_next_section(project_id: str) -> Dict[str, Any]:
    with conn() as db:
        row = db.execute(
            "SELECT * FROM outlines WHERE project_id=? AND status!='done' ORDER BY section_index ASC LIMIT 1",
            (project_id,),
        ).fetchone()
    return {"next_section": dict(row) if row else None}


def save_section(project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    section_index = payload["section_index"]
    with conn() as db:
        db.execute(
            """
            INSERT OR REPLACE INTO sections(project_id,section_index,title,content_markdown,study_direction,quality_report,created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                project_id,
                section_index,
                payload.get("title", ""),
                payload["content_markdown"],
                payload.get("study_direction", ""),
                json.dumps(payload.get("quality_report", {}), ensure_ascii=False),
                now(),
            ),
        )
        db.execute("UPDATE outlines SET status='done' WHERE project_id=? AND section_index=?", (project_id, section_index))
    return {"ok": True, "saved_section_index": section_index}


def save_project_items(project_id: str, item_type: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    ts = now()
    with conn() as db:
        for item in items:
            db.execute(
                "INSERT INTO project_items(project_id,item_type,payload,created_at) VALUES(?,?,?,?)",
                (project_id, item_type, json.dumps(item, ensure_ascii=False), ts),
            )
    return {"ok": True, "saved_count": len(items), "item_type": item_type}


def final_bundle(project_id: str) -> Dict[str, Any]:
    with conn() as db:
        project = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if not project:
            return {}
        outline = [dict(row) for row in db.execute("SELECT * FROM outlines WHERE project_id=? ORDER BY section_index", (project_id,))]
        sections = [dict(row) for row in db.execute("SELECT * FROM sections WHERE project_id=? ORDER BY section_index", (project_id,))]
        items = [dict(row) for row in db.execute("SELECT * FROM project_items WHERE project_id=? ORDER BY id", (project_id,))]

    p = dict(project)
    p["source_ids"] = json.loads(p.get("source_ids") or "[]")
    p["metadata"] = json.loads(p.get("metadata") or "{}")
    for section in sections:
        section["quality_report"] = json.loads(section.get("quality_report") or "{}")
    for item in items:
        item["payload"] = json.loads(item["payload"])
    return {"project": p, "outline": outline, "sections": sections, "items": items}


def export_project_note_as_source(project_id: str, title: str = "") -> Dict[str, Any]:
    bundle = final_bundle(project_id)
    if not bundle:
        return {}
    project_title = title or f"{bundle['project']['title']} - generated note"
    parts = [f"# {project_title}\n"]
    for section in bundle.get("sections", []):
        parts.append(section.get("content_markdown", ""))
        parts.append("\n---\n")
    parts.append("\n# Saved item lists\n")
    for item in bundle.get("items", []):
        parts.append(f"- [{item.get('item_type')}] {item.get('payload')}\n")
    return save_text_source(project_title, "generated_note", "\n".join(parts), f"{project_id}_generated_note.md")


def _safe_note_part(value: str, fallback: str = "note") -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^0-9a-zA-Z가-힣._-]+", "-", text).strip("-._")
    return text[:80] or fallback


def make_note_doc_key(subject: str = "", unit_number: str = "", unit_title: str = "", title: str = "") -> str:
    parts = [subject, unit_number, unit_title or title]
    normalized = [_safe_note_part(part, "") for part in parts if str(part or "").strip()]
    return "-".join(part for part in normalized if part) or make_id("note")


def _note_original_name(subject: str, unit_number: str, unit_title: str, title: str, series_id: str, version: int) -> str:
    base = make_note_doc_key(subject, unit_number, unit_title, title)
    if base.startswith("note-") and series_id:
        base = _safe_note_part(series_id, "note")
    return f"{base}_v{version}.md"


def save_note_version(
    title: str,
    content_markdown: str,
    series_id: str = "",
    source_type: str = "generated_note",
    change_summary: str = "",
    based_on_version: Optional[int] = None,
    subject: str = "",
    replace_latest: bool = False,
    replace_source_id: str = "",
    doc_key: str = "",
    unit_number: str = "",
    unit_title: str = "",
) -> Dict[str, Any]:
    replace_source_id = (replace_source_id or "").strip()
    doc_key = (doc_key or "").strip()
    unit_number = str(unit_number or "").strip()
    unit_title = str(unit_title or "").strip()
    if replace_source_id:
        result = update_source_markdown(replace_source_id, content_markdown, title, change_summary or "replaced study note", based_on_version)
        if result:
            result["replace_source_id"] = replace_source_id
            result["replaced_existing_source"] = True
        return result

    series_id = (doc_key or series_id or "").strip() or make_id("note")
    # Safety rule: series_id is a grouping key, never an upsert key.
    # A study note can be replaced only through update_source_markdown() with an explicit source_id.
    with conn() as db:
        row = db.execute("SELECT MAX(version) AS max_version FROM note_versions WHERE series_id=?", (series_id,)).fetchone()
        version = int(row["max_version"] or 0) + 1
    original_name = _note_original_name(subject, unit_number, unit_title, title, series_id, version)
    source = save_text_source(f"{title} v{version}", source_type, content_markdown, original_name, subject=subject)
    version_id = make_id("ver")
    with conn() as db:
        db.execute(
            """
            INSERT INTO note_versions(id,series_id,title,version,source_id,source_type,content_markdown,change_summary,based_on_version,created_at,doc_key,unit_number,unit_title)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (version_id, series_id, title, version, source["source_id"], source_type, content_markdown, change_summary, based_on_version, now(), doc_key, unit_number, unit_title),
        )
    return {**source, "note_version_id": version_id, "series_id": series_id, "version": version, "doc_key": doc_key, "unitNumber": unit_number, "unitTitle": unit_title}


def list_note_versions(series_id: str = "") -> List[Dict[str, Any]]:
    with conn() as db:
        if series_id:
            rows = db.execute("SELECT * FROM note_versions WHERE series_id=? ORDER BY version DESC", (series_id,)).fetchall()
        else:
            rows = db.execute("SELECT * FROM note_versions ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


def get_latest_note_version(series_id: str) -> Optional[Dict[str, Any]]:
    with conn() as db:
        row = db.execute("SELECT * FROM note_versions WHERE series_id=? ORDER BY version DESC LIMIT 1", (series_id,)).fetchone()
    return dict(row) if row else None


def save_transcript_revision(
    title: str,
    corrected_text: str,
    original_transcript_source_id: str = "",
    terminology_map: Optional[Dict[str, Any]] = None,
    change_log: Optional[List[Dict[str, Any]]] = None,
    subject: str = "",
) -> Dict[str, Any]:
    source = save_text_source(title, "corrected_transcript", corrected_text, f"{title}_corrected_transcript.md", subject=subject)
    revision_id = make_id("trn")
    with conn() as db:
        db.execute(
            """
            INSERT INTO transcript_revisions(id,original_transcript_source_id,corrected_source_id,title,terminology_map,change_log,created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                revision_id,
                original_transcript_source_id,
                source["source_id"],
                title,
                json.dumps(terminology_map or {}, ensure_ascii=False),
                json.dumps(change_log or [], ensure_ascii=False),
                now(),
            ),
        )
    return {**source, "transcript_revision_id": revision_id}


def _json_text(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, indent=2)


def _artifact_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item or "").strip()]
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed if str(item or "").strip()]
        except Exception:
            return [value.strip()]
    return []


def _pack_subject(pack: Dict[str, Any], subject: str = "") -> str:
    meta = pack.get("metadata") if isinstance(pack.get("metadata"), dict) else {}
    return str(subject or pack.get("subject") or meta.get("subject") or "").strip()


def _pack_unit_number(pack: Dict[str, Any], unit_number: str = "") -> str:
    meta = pack.get("metadata") if isinstance(pack.get("metadata"), dict) else {}
    return str(unit_number or pack.get("unitNumber") or pack.get("unit_number") or meta.get("unitNumber") or meta.get("unit_number") or "").strip()


def _pack_unit_title(pack: Dict[str, Any], unit_title: str = "") -> str:
    meta = pack.get("metadata") if isinstance(pack.get("metadata"), dict) else {}
    return str(unit_title or pack.get("unitTitle") or pack.get("unit_title") or meta.get("unitTitle") or meta.get("unit_title") or "").strip()


def _pack_tags(pack: Dict[str, Any], tags: Optional[List[str]] = None) -> List[str]:
    meta = pack.get("metadata") if isinstance(pack.get("metadata"), dict) else {}
    values = tags or pack.get("tags") or meta.get("tags") or []
    if not isinstance(values, list):
        return []
    return [str(item) for item in values if str(item or "").strip()]


def _pack_source_refs(pack: Dict[str, Any], source_refs: Optional[List[str]] = None) -> List[str]:
    meta = pack.get("metadata") if isinstance(pack.get("metadata"), dict) else {}
    values = source_refs or pack.get("source_refs") or pack.get("sourceRefs") or meta.get("source_refs") or meta.get("sourceRefs") or []
    if not isinstance(values, list):
        return []
    return [str(item) for item in values if str(item or "").strip()]



LATEX_UNSUPPORTED_MACROS = [
    "\\xrightleftharpoons", "\\xleftrightarrow", "\\chemfig", "\\ce{", "\\pu{",
]


def _iter_pack_text_fields(pack: Dict[str, Any]):
    if not isinstance(pack, dict):
        return
    for field in ["description", "instructions"]:
        if isinstance(pack.get(field), str):
            yield f"pack.{field}", pack.get(field) or ""
    questions = pack.get("questions") or []
    if not isinstance(questions, list):
        return
    for qi, q in enumerate(questions, 1):
        if not isinstance(q, dict):
            continue
        prefix = f"questions[{qi}]"
        for field in ["promptMd", "title", "section"]:
            if isinstance(q.get(field), str):
                yield f"{prefix}.{field}", q.get(field) or ""
        choices = q.get("choices") or []
        if isinstance(choices, list):
            for ci, c in enumerate(choices, 1):
                if isinstance(c, dict) and isinstance(c.get("text"), str):
                    yield f"{prefix}.choices[{ci}].text", c.get("text") or ""
        solution = q.get("solution") or {}
        if isinstance(solution, dict):
            for key in ["concepts", "actualSolution", "cautions", "tips"]:
                values = solution.get(key) or []
                if isinstance(values, str):
                    yield f"{prefix}.solution.{key}", values
                elif isinstance(values, list):
                    for si, value in enumerate(values, 1):
                        if isinstance(value, str):
                            yield f"{prefix}.solution.{key}[{si}]", value
        hints = q.get("hints") or []
        if isinstance(hints, list):
            for hi, value in enumerate(hints, 1):
                if isinstance(value, str):
                    yield f"{prefix}.hints[{hi}]", value
        answer = q.get("answer") or {}
        if isinstance(answer, dict):
            if isinstance(answer.get("value"), str):
                yield f"{prefix}.answer.value", answer.get("value") or ""
        assets = q.get("assets") or []
        if isinstance(assets, list):
            for ai, a in enumerate(assets, 1):
                if isinstance(a, dict) and isinstance(a.get("description"), str):
                    yield f"{prefix}.assets[{ai}].description", a.get("description") or ""


def _has_markdown_table(text: str) -> bool:
    lines = [line.strip() for line in str(text or "").splitlines()]
    for i in range(len(lines) - 1):
        if "|" in lines[i] and re.match(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", lines[i + 1] or ""):
            return True
    return False


def validate_problem_pack_render(pack: Dict[str, Any], strict: bool = False) -> Dict[str, Any]:
    """Heuristic render-safety validation for SolvePad problem packs."""
    warnings: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    def add(code: str, field: str, message: str, severity: str = "warning") -> None:
        item = {"code": code, "field": field, "message": message, "severity": severity}
        if severity == "error":
            errors.append(item)
        else:
            warnings.append(item)

    if not isinstance(pack, dict):
        return {"ok": False, "warnings": [], "errors": [{"code": "ERR_PACK_OBJECT", "field": "pack", "message": "pack must be an object", "severity": "error"}]}
    if not pack.get("packId") and not pack.get("pack_id"):
        add("ERR_PACK_ID", "pack.packId", "packId is required.", "error")
    if not isinstance(pack.get("questions"), list) or not pack.get("questions"):
        add("ERR_QUESTIONS", "pack.questions", "questions must be a non-empty array.", "error")

    for field, text in _iter_pack_text_fields(pack):
        raw = str(text or "")
        if raw.count("$$") % 2:
            add("WARN_LATEX_DELIMITER", field, "Odd number of $$ delimiters may break block math rendering.")
        for macro in LATEX_UNSUPPORTED_MACROS:
            if macro in raw:
                add("WARN_LATEX_MACRO", field, f"Unsupported or risky LaTeX macro detected: {macro}")
        if _has_markdown_table(raw):
            add("INFO_MARKDOWN_TABLE", field, "Markdown table detected. SolvePad v23.3 renders tables; if a device still shows raw |---|, convert to LaTeX array.", "info")
        if "|---" in raw or "---|" in raw:
            add("INFO_TABLE_SEPARATOR", field, "Markdown table separator detected. Verify rendered table in SolvePad.", "info")
        for match in re.finditer(r"```[\s\S]*?```", raw):
            block = match.group(0)
            if "$" in block or "\\begin" in block:
                add("WARN_CODEBLOCK_FORMULA", field, "Formula inside code block will not render as math.")
        if "\\begin" in raw and not ("$$" in raw or "\\[" in raw):
            add("WARN_BEGIN_OUTSIDE_MATH", field, "\\begin appears outside display math delimiters.")

    questions = pack.get("questions") or []
    if isinstance(questions, list):
        for qi, q in enumerate(questions, 1):
            if not isinstance(q, dict):
                add("ERR_QUESTION_OBJECT", f"questions[{qi}]", "Each question must be an object.", "error")
                continue
            ans_fmt = q.get("answerFormat") or pack.get("answerFormat")
            if ans_fmt and isinstance(ans_fmt, dict):
                if ans_fmt.get("type") == "decimal" and ans_fmt.get("roundingMode") == "truncate":
                    sol = q.get("solution") or {}
                    actual = "\n".join(sol.get("actualSolution") or []) if isinstance(sol, dict) and isinstance(sol.get("actualSolution"), list) else ""
                    if "=" not in actual:
                        add("WARN_NO_DERIVATION", f"questions[{qi}].solution.actualSolution", "Numeric/truncate answer should include formula, substitution, and truncation steps.")
            if q.get("gradingCriterion") and not q.get("mathematicalNote"):
                add("INFO_GRADING_NOTE", f"questions[{qi}].mathematicalNote", "gradingCriterion exists. Add mathematicalNote if mathematical answer and quiz criterion differ.", "info")

    ok = not errors and (not strict or not any(w.get("severity") == "warning" for w in warnings))
    return {"ok": ok, "warning_count": len(warnings), "error_count": len(errors), "warnings": warnings, "errors": errors}


def _problem_pack_text(title: str, pack_id: str, pack: Dict[str, Any], subject: str, unit_number: str, unit_title: str, tags: List[str], source_refs: List[str]) -> str:
    question_count = len(pack.get("questions") or []) if isinstance(pack.get("questions"), list) else 0
    return "\n".join([
        f"# {title}",
        "",
        "type: problem_pack",
        f"pack_id: {pack_id}",
        f"subject: {subject}",
        f"unitNumber: {unit_number}",
        f"unitTitle: {unit_title}",
        f"question_count: {question_count}",
        "tags: " + ", ".join(tags),
        "source_refs: " + ", ".join(source_refs),
        "",
        "```json",
        _json_text(pack),
        "```",
    ])



def _pack_exam_set_id(pack: Dict[str, Any]) -> str:
    meta = pack.get("metadata", {}) if isinstance(pack, dict) else {}
    return str(pack.get("examSetId") or pack.get("exam_set_id") or meta.get("examSetId") or meta.get("exam_set_id") or "").strip()


def _pack_exam_set_title(pack: Dict[str, Any]) -> str:
    meta = pack.get("metadata", {}) if isinstance(pack, dict) else {}
    return str(pack.get("examSetTitle") or pack.get("exam_set_title") or meta.get("examSetTitle") or meta.get("exam_set_title") or "").strip()

def _next_problem_pack_version(db: sqlite3.Connection, pack_id: str) -> int:
    current = db.execute("SELECT version FROM problem_packs WHERE id=?", (pack_id,)).fetchone()
    if current:
        return int(current["version"] or 1) + 1
    latest = db.execute("SELECT MAX(version) AS v FROM problem_pack_versions WHERE pack_id=?", (pack_id,)).fetchone()
    return int((latest or {}).get("v") or 0) + 1


def _archive_problem_pack_version(db: sqlite3.Connection, row: sqlite3.Row, change_summary: str = "") -> None:
    if not row:
        return
    version = int(row["version"] if "version" in row.keys() else 1 or 1)
    db.execute(
        """
        INSERT INTO problem_pack_versions(id,pack_id,version,source_id,title,pack_json,version_label,change_summary,render_warnings,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?)
        """,
        (
            make_id("ppv"),
            row["id"],
            version,
            row["source_id"] if "source_id" in row.keys() else "",
            row["title"],
            row["pack_json"],
            row["version_label"] if "version_label" in row.keys() else "",
            change_summary or (row["change_summary"] if "change_summary" in row.keys() else "replaced"),
            row["render_warnings"] if "render_warnings" in row.keys() else "[]",
            row["created_at"],
        ),
    )


def _find_problem_pack_by_source_id(db: sqlite3.Connection, source_id: str) -> Optional[sqlite3.Row]:
    if not source_id:
        return None
    return db.execute("SELECT * FROM problem_packs WHERE source_id=?", (source_id,)).fetchone()


def save_problem_pack(
    title: str,
    pack: Dict[str, Any],
    subject: str = "",
    unit_number: str = "",
    unit_title: str = "",
    tags: Optional[List[str]] = None,
    source_refs: Optional[List[str]] = None,
    replace_source_id: str = "",
    replace_pack_id: str = "",
    version_label: str = "",
    change_summary: str = "",
    render_warnings: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    requested_pack_id = str(replace_pack_id or "").strip()
    pack_id = requested_pack_id or pack.get("packId") or pack.get("pack_id") or make_id("pack")
    pack["packId"] = pack_id
    token = secrets.token_urlsafe(16)
    subject = _pack_subject(pack, subject)
    unit_number = _pack_unit_number(pack, unit_number)
    unit_title = _pack_unit_title(pack, unit_title)
    tags = _pack_tags(pack, tags)
    source_refs = _pack_source_refs(pack, source_refs)
    exam_set_id = _pack_exam_set_id(pack)
    exam_set_title = _pack_exam_set_title(pack)
    question_count = len(pack.get("questions", [])) if isinstance(pack.get("questions"), list) else 0
    render_warnings = render_warnings or []
    render_warnings_json = json.dumps(render_warnings, ensure_ascii=False)

    old_source_id = ""
    version = 1
    with conn() as db:
        old = None
        if requested_pack_id:
            old = db.execute("SELECT * FROM problem_packs WHERE id=?", (requested_pack_id,)).fetchone()
        if not old and replace_source_id:
            old = _find_problem_pack_by_source_id(db, replace_source_id)
            if old:
                pack_id = old["id"]
                pack["packId"] = pack_id
        if not old:
            old = db.execute("SELECT * FROM problem_packs WHERE id=?", (pack_id,)).fetchone()
        if old:
            old_source_id = old["source_id"] or ""
            version = _next_problem_pack_version(db, pack_id)
            _archive_problem_pack_version(db, old, change_summary or "replaced by saveProblemPack")
        elif replace_source_id:
            old_source_id = replace_source_id
            version = 1

    if old_source_id:
        try:
            delete_source(old_source_id)
        except Exception:
            pass

    source = save_text_source(
        title,
        "problem_pack",
        _problem_pack_text(title, pack_id, pack, subject, unit_number, unit_title, tags, source_refs),
        f"{pack_id}_problem_pack.json.md",
        subject=subject,
    )
    source_id = source.get("source_id", "")
    with conn() as db:
        db.execute(
            """
            INSERT OR REPLACE INTO problem_packs(id,title,token,pack_json,created_at,source_id,subject,unit_number,unit_title,tags,source_refs,exam_set_id,exam_set_title,question_count,version,version_label,change_summary,render_warnings)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (pack_id, title, token, json.dumps(pack, ensure_ascii=False), now(), source_id, subject, unit_number, unit_title, json.dumps(tags, ensure_ascii=False), json.dumps(source_refs, ensure_ascii=False), exam_set_id, exam_set_title, question_count, version, version_label, change_summary, render_warnings_json),
        )
    return {"pack_id": pack_id, "token": token, "source_id": source_id, "source_type": "problem_pack", "subject": subject, "unitNumber": unit_number, "unitTitle": unit_title, "examSetId": exam_set_id, "examSetTitle": exam_set_title, "question_count": question_count, "version": version, "version_label": version_label, "change_summary": change_summary, "render_warnings": render_warnings}



def get_problem_pack_by_id(pack_id: str) -> Optional[Dict[str, Any]]:
    with conn() as db:
        row = db.execute("SELECT * FROM problem_packs WHERE id=?", (pack_id,)).fetchone()
    if not row:
        return None
    data = dict(row)
    pack = json.loads(data.get("pack_json") or "{}")
    return {
        "pack": pack,
        "title": data.get("title", ""),
        "pack_id": data.get("id", ""),
        "source_id": data.get("source_id", ""),
        "subject": data.get("subject", ""),
        "unitNumber": data.get("unit_number", ""),
        "unitTitle": data.get("unit_title", ""),
        "examSetId": data.get("exam_set_id", "") or _pack_exam_set_id(pack),
        "examSetTitle": data.get("exam_set_title", "") or _pack_exam_set_title(pack),
        "question_count": int(data.get("question_count") or 0),
        "created_at": data.get("created_at", ""),
        "version": int(data.get("version") or 1),
        "version_label": data.get("version_label", ""),
        "change_summary": data.get("change_summary", ""),
        "render_warnings": _artifact_list(data.get("render_warnings", "[]")),
    }

def get_problem_pack_by_token(token: str) -> Optional[Dict[str, Any]]:
    with conn() as db:
        row = db.execute("SELECT * FROM problem_packs WHERE token=?", (token,)).fetchone()
    if not row:
        return None
    data = dict(row)
    return {"pack": json.loads(data["pack_json"]), "title": data["title"], "pack_id": data["id"], "source_id": data.get("source_id", "")}


def list_problem_packs(subject: str = "") -> List[Dict[str, Any]]:
    with conn() as db:
        rows = db.execute("SELECT * FROM problem_packs ORDER BY created_at DESC").fetchall()
    result: List[Dict[str, Any]] = []
    for row in rows:
        data = dict(row)
        if subject and data.get("subject", "") != subject:
            continue
        try:
            pack = json.loads(data.get("pack_json") or "{}")
        except Exception:
            pack = {}
        questions = pack.get("questions") if isinstance(pack, dict) else []
        result.append({
            "pack_id": data.get("id", ""),
            "title": data.get("title", ""),
            "source_id": data.get("source_id", ""),
            "source_type": "problem_pack",
            "subject": data.get("subject", ""),
            "unitNumber": data.get("unit_number", ""),
            "unitTitle": data.get("unit_title", ""),
            "question_count": int(data.get("question_count") or (len(questions) if isinstance(questions, list) else 0)),
            "examSetId": data.get("exam_set_id", "") or _pack_exam_set_id(pack),
            "examSetTitle": data.get("exam_set_title", "") or _pack_exam_set_title(pack),
            "tags": _artifact_list(data.get("tags", "[]")),
            "source_refs": _artifact_list(data.get("source_refs", "[]")),
            "created_at": data.get("created_at", ""),
            "version": int(data.get("version") or 1),
            "version_label": data.get("version_label", ""),
            "change_summary": data.get("change_summary", ""),
            "render_warnings": _artifact_list(data.get("render_warnings", "[]")),
        })
    return result


def _calculator_subject(metadata: Dict[str, Any]) -> str:
    return str((metadata or {}).get("subject", "") or "").strip()


def _calculator_metadata_value(metadata: Dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = (metadata or {}).get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _calculator_project_text(title: str, project_id: str, blueprint: Dict[str, Any], validation: Dict[str, Any], generated: Dict[str, Any], metadata: Dict[str, Any], manual_markdown: str, analysis_markdown: str) -> str:
    files = generated.get("files", []) if isinstance(generated, dict) else []
    file_names = [str(item.get("name", "")) for item in files if isinstance(item, dict)]
    return "\n".join([
        f"# {title}",
        "",
        "type: calculator_project",
        f"project_id: {project_id}",
        f"subject: {_calculator_subject(metadata)}",
        f"unitNumber: {_calculator_metadata_value(metadata, 'unitNumber', 'unit_number')}",
        f"unitTitle: {_calculator_metadata_value(metadata, 'unitTitle', 'unit_title')}",
        "files: " + ", ".join(file_names),
        "",
        "## Analysis",
        analysis_markdown or "",
        "",
        "## Manual",
        manual_markdown or "",
        "",
        "## Blueprint",
        "```json",
        _json_text(blueprint),
        "```",
        "",
        "## Validation",
        "```json",
        _json_text(validation),
        "```",
    ])


def _calculator_program_text(title: str, project_id: str, file_info: Dict[str, Any], metadata: Dict[str, Any]) -> str:
    name = str(file_info.get("name") or "PROGRAM.TXT")
    content = str(file_info.get("content") or "")
    return "\n".join([
        f"# {title} / {name}",
        "",
        "type: calculator_program",
        f"project_id: {project_id}",
        f"program_name: {name}",
        f"subject: {_calculator_subject(metadata)}",
        f"unitNumber: {_calculator_metadata_value(metadata, 'unitNumber', 'unit_number')}",
        f"unitTitle: {_calculator_metadata_value(metadata, 'unitTitle', 'unit_title')}",
        "",
        "```prgm",
        content,
        "```",
    ])


def _delete_sources_quiet(source_ids: List[str]) -> None:
    seen = set()
    for source_id in source_ids:
        source_id = str(source_id or "").strip()
        if not source_id or source_id in seen:
            continue
        seen.add(source_id)
        try:
            delete_source(source_id)
        except Exception:
            pass


def save_calculator_blueprint(
    title: str,
    blueprint: Dict[str, Any],
    validation: Dict[str, Any],
    generated: Dict[str, Any],
    metadata: Dict[str, Any],
    manual_markdown: str = "",
    analysis_markdown: str = "",
    replace_project_id: str = "",
) -> Dict[str, Any]:
    blueprint_id = replace_project_id or make_id("calc")
    if replace_project_id:
        delete_calculator_blueprint(replace_project_id)

    subject = _calculator_subject(metadata)
    manual_source_id = ""
    analysis_source_id = ""
    program_source_ids: List[str] = []

    if manual_markdown.strip():
        source = save_text_source(
            f"{title} 사용법 및 구조 해설",
            "calculator_manual",
            manual_markdown,
            f"{blueprint_id}_calculator_manual.md",
            subject=subject,
        )
        manual_source_id = source.get("source_id", "")

    if analysis_markdown.strip():
        source = save_text_source(
            f"{title} 계산기화 분석",
            "calculator_analysis",
            analysis_markdown,
            f"{blueprint_id}_calculator_analysis.md",
            subject=subject,
        )
        analysis_source_id = source.get("source_id", "")

    files = generated.get("files", []) if isinstance(generated, dict) else []
    for index, file_info in enumerate(files, 1):
        if not isinstance(file_info, dict):
            continue
        name = str(file_info.get("name") or f"PROGRAM_{index}.TXT")
        source = save_text_source(
            f"{title} / {name}",
            "calculator_program",
            _calculator_program_text(title, blueprint_id, file_info, metadata),
            f"{blueprint_id}_{name}.txt.md".replace("/", "_"),
            subject=subject,
        )
        program_source_ids.append(source.get("source_id", ""))

    project_source = save_text_source(
        title,
        "calculator_project",
        _calculator_project_text(title, blueprint_id, blueprint, validation, generated, metadata, manual_markdown, analysis_markdown),
        f"{blueprint_id}_calculator_project.md",
        subject=subject,
    )
    source_id = project_source.get("source_id", "")

    with conn() as db:
        db.execute(
            """
            INSERT OR REPLACE INTO calculator_blueprints(id,title,blueprint_json,validation_json,generated_json,metadata,manual_markdown,manual_source_id,analysis_markdown,created_at,source_id,program_source_ids,analysis_source_id)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                blueprint_id,
                title,
                json.dumps(blueprint, ensure_ascii=False),
                json.dumps(validation, ensure_ascii=False),
                json.dumps(generated, ensure_ascii=False),
                json.dumps(metadata, ensure_ascii=False),
                manual_markdown,
                manual_source_id,
                analysis_markdown,
                now(),
                source_id,
                json.dumps(program_source_ids, ensure_ascii=False),
                analysis_source_id,
            ),
        )
    return {
        "calculator_project_id": blueprint_id,
        "source_id": source_id,
        "source_type": "calculator_project",
        "manual_source_id": manual_source_id,
        "analysis_source_id": analysis_source_id,
        "program_source_ids": program_source_ids,
    }


def _calculator_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    data = dict(row)
    data["blueprint"] = json.loads(data.pop("blueprint_json") or "{}")
    data["validation"] = json.loads(data.pop("validation_json") or "{}")
    data["generated"] = json.loads(data.pop("generated_json") or "{}")
    data["metadata"] = json.loads(data.pop("metadata") or "{}")
    data["program_source_ids"] = _artifact_list(data.get("program_source_ids", "[]"))
    return data


def list_calculator_blueprints(subject: str = "") -> List[Dict[str, Any]]:
    with conn() as db:
        rows = db.execute("SELECT * FROM calculator_blueprints ORDER BY created_at DESC").fetchall()
    result = []
    for row in rows:
        data = _calculator_row_to_dict(row)
        if subject and str(data.get("metadata", {}).get("subject", "")) != subject:
            continue
        generated = data.get("generated", {})
        files = generated.get("files", []) if isinstance(generated, dict) else []
        result.append({
            "calculator_project_id": data["id"],
            "title": data["title"],
            "source_id": data.get("source_id", ""),
            "source_type": "calculator_project",
            "subject": data.get("metadata", {}).get("subject", ""),
            "file_count": len(files),
            "manual_source_id": data.get("manual_source_id", ""),
            "analysis_source_id": data.get("analysis_source_id", ""),
            "program_source_ids": data.get("program_source_ids", []),
            "created_at": data.get("created_at", ""),
            "version": int(data.get("version") or 1),
            "version_label": data.get("version_label", ""),
            "change_summary": data.get("change_summary", ""),
            "render_warnings": _artifact_list(data.get("render_warnings", "[]")),
        })
    return result


def get_calculator_blueprint(project_id: str) -> Optional[Dict[str, Any]]:
    with conn() as db:
        row = db.execute("SELECT * FROM calculator_blueprints WHERE id=?", (project_id,)).fetchone()
    return _calculator_row_to_dict(row) if row else None


def delete_calculator_blueprint(project_id: str) -> Dict[str, Any]:
    project = get_calculator_blueprint(project_id)
    if not project:
        return {}
    source_ids = [
        project.get("source_id", ""),
        project.get("manual_source_id", ""),
        project.get("analysis_source_id", ""),
        *project.get("program_source_ids", []),
    ]
    with conn() as db:
        db.execute("DELETE FROM calculator_blueprints WHERE id=?", (project_id,))
    _delete_sources_quiet(source_ids)
    return {"ok": True, "deleted_calculator_project_id": project_id, "title": project.get("title", ""), "deleted_source_ids": [sid for sid in source_ids if sid]}



def cleanup_old_workflows(days: int = 30, checkpoint_keep_latest: int = 5) -> Dict[str, Any]:
    days = max(1, int(days or 30))
    checkpoint_keep_latest = max(0, int(checkpoint_keep_latest or 0))
    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat().replace("+00:00", "Z")
    deleted_runs = 0
    deleted_checkpoints = 0
    trimmed_checkpoints = 0
    with conn() as db:
        old_runs = [row["id"] for row in db.execute("SELECT id FROM workflow_runs WHERE status IN ('completed','failed') AND updated_at < ?", (cutoff,)).fetchall()]
        for run_id in old_runs:
            deleted_checkpoints += db.execute("DELETE FROM workflow_checkpoints WHERE run_id=?", (run_id,)).rowcount or 0
            deleted_runs += db.execute("DELETE FROM workflow_runs WHERE id=?", (run_id,)).rowcount or 0
        if checkpoint_keep_latest >= 0:
            runs = [row["id"] for row in db.execute("SELECT id FROM workflow_runs").fetchall()]
            for run_id in runs:
                rows = db.execute("SELECT id FROM workflow_checkpoints WHERE run_id=? ORDER BY created_at DESC", (run_id,)).fetchall()
                stale = [row["id"] for row in rows[checkpoint_keep_latest:]]
                for checkpoint_id in stale:
                    trimmed_checkpoints += db.execute("DELETE FROM workflow_checkpoints WHERE id=?", (checkpoint_id,)).rowcount or 0
    return {"deleted_workflow_runs": deleted_runs, "deleted_workflow_checkpoints": deleted_checkpoints, "trimmed_workflow_checkpoints": trimmed_checkpoints, "workflow_cutoff": cutoff}


def maintenance_cleanup(
    remove_missing_unit_refs: bool = True,
    delete_old_workflows: bool = False,
    workflow_days: int = 30,
    checkpoint_keep_latest: int = 5,
    wal_checkpoint: bool = True,
    vacuum: bool = False,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {"ok": True, "actions": []}
    if remove_missing_unit_refs:
        result["missing_refs"] = cleanup_missing_unit_refs()
        result["actions"].append("remove_missing_unit_refs")
    if delete_old_workflows:
        result["workflow_cleanup"] = cleanup_old_workflows(workflow_days, checkpoint_keep_latest)
        result["actions"].append("delete_old_workflows")
    with conn() as db:
        if wal_checkpoint:
            try:
                result["wal_checkpoint"] = [tuple(row) for row in db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchall()]
                result["actions"].append("wal_checkpoint")
            except Exception as exc:
                result["wal_checkpoint_error"] = str(exc)
        if vacuum:
            try:
                db.execute("VACUUM")
                result["vacuum"] = True
                result["actions"].append("vacuum")
            except Exception as exc:
                result["vacuum_error"] = str(exc)
    return result

def save_unit_map(title: str, source_ids: List[str], map_json: Dict[str, Any], created_by: str = "gpt") -> Dict[str, Any]:
    map_id = make_id("map")
    ts = now()
    with conn() as db:
        db.execute(
            "INSERT INTO unit_maps(id,title,source_ids,map_json,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            (map_id, title, json.dumps(source_ids, ensure_ascii=False), json.dumps(map_json, ensure_ascii=False), created_by, ts, ts),
        )
    return {"unit_map_id": map_id, "title": title, "unit_count": len(map_json.get("units", []))}
