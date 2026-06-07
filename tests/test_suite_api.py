from pathlib import Path
import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_and_workflow_options():
    assert client.get("/health").status_code == 200
    options = client.get("/workflow/options")
    assert options.status_code == 200
    assert "availableModes" in options.json()


def test_external_note_unmapped_and_workflow_plan():
    note = client.post("/notes/text", json={
        "title": "External Summary",
        "source_type": "external_note",
        "text": "# External Summary\nBatch reactor and conversion notes.",
        "original_name": "external.md"
    })
    assert note.status_code == 200
    source_id = note.json()["source_id"]

    unmapped = client.get("/sources/unmapped")
    assert unmapped.status_code == 200
    assert any(s["id"] == source_id for s in unmapped.json()["unmapped_sources"])

    plan = client.post("/workflow/plans", json={
        "title": "Batch Reactor Note Plan",
        "subject": "CRE",
        "selected_units": ["Batch Reactor"],
        "selected_mode": "lecture_note",
        "source_ids": [source_id],
        "reference_priority": ["lecture_slides", "textbook"],
        "notes": "test plan"
    })
    assert plan.status_code == 200
    assert plan.json()["selected_mode"] == "lecture_note"

    plans = client.get("/workflow/plans")
    assert plans.status_code == 200
    assert len(plans.json()["workflow_plans"]) >= 1


def test_project_and_note_version_flow():
    p = client.post("/projects", json={
        "title": "Lecture Note Test",
        "project_type": "lecture_note",
        "source_ids": [],
        "metadata": {}
    })
    assert p.status_code == 200
    project_id = p.json()["project_id"]

    assert client.post(f"/projects/{project_id}/outline", json={
        "sections": [{"index": 1, "title": "Unit 1", "source_query": "intro"}]
    }).status_code == 200

    assert client.post(f"/projects/{project_id}/sections", json={
        "section_index": 1,
        "title": "Unit 1",
        "content_markdown": "# 1. Unit 1\n\nGenerated note content.",
        "study_direction": "Focus."
    }).status_code == 200

    exported = client.post(f"/projects/{project_id}/export-note-source", json={"title": "Generated Lecture Note"})
    assert exported.status_code == 200
    assert exported.json()["source_type"] == "generated_note"

    v1 = client.post("/notes/versions", json={
        "title": "Generated Lecture Note",
        "content_markdown": "# v1",
        "change_summary": "initial"
    })
    assert v1.status_code == 200
    series_id = v1.json()["series_id"]

    v2 = client.post("/notes/versions", json={
        "title": "Generated Lecture Note",
        "content_markdown": "# v2",
        "series_id": series_id,
        "change_summary": "updated",
        "based_on_version": 1
    })
    assert v2.status_code == 200
    assert v2.json()["version"] == 2

    latest = client.get(f"/notes/versions/{series_id}/latest")
    assert latest.status_code == 200
    assert latest.json()["version"] == 2


def test_unit_map_flow_and_mapped_sources():
    source = client.post("/sources/text", json={
        "title": "Textbook A",
        "source_type": "textbook",
        "text": "Batch Reactor chapter",
        "original_name": "textbook.md"
    })
    assert source.status_code == 200
    source_id = source.json()["source_id"]

    saved = client.post("/unit-maps", json={
        "title": "CRE Unit Map",
        "source_ids": [source_id],
        "unit_map": {
            "schemaVersion": "lecturenote.unitMap.v1",
            "sources": {"textbook": [source_id]},
            "units": [
                {
                    "unitId": "u001",
                    "unitTitle": "Batch Reactor",
                    "textbook": [{"sourceId": source_id, "pageRange": "p.1-10"}],
                    "confidence": "medium"
                }
            ],
            "unmapped": []
        }
    })
    assert saved.status_code == 200
    unit_map_id = saved.json()["unit_map_id"]

    fetched = client.get(f"/unit-maps/{unit_map_id}")
    assert fetched.status_code == 200
    assert fetched.json()["map"]["units"][0]["unitTitle"] == "Batch Reactor"

    unmapped = client.get("/sources/unmapped?source_type=textbook")
    assert unmapped.status_code == 200
    assert not any(s["id"] == source_id for s in unmapped.json()["unmapped_sources"])


def test_transcript_revision_flow():
    response = client.post("/transcripts/revisions", json={
        "title": "Corrected Transcript Week 1",
        "corrected_text": "Corrected terminology transcript.",
        "original_transcript_source_id": "src-original",
        "terminology_map": {"wrong": "correct"},
        "change_log": [{"from": "wrong", "to": "correct"}]
    })
    assert response.status_code == 200
    assert response.json()["source_type"] == "corrected_transcript"

    search = client.post("/sources/search", json={
        "query": "Corrected terminology",
        "source_types": ["corrected_transcript"],
        "limit": 3
    })
    assert search.status_code == 200
    assert len(search.json()["results"]) >= 1


def test_problem_pack_flow():
    pack = {
        "packId": "test-pack",
        "title": "Test Pack",
        "questions": [
            {
                "id": "q001",
                "title": "Q1",
                "promptMd": "Solve.",
                "answer": {"value": "1"},
                "solution": {
                    "concepts": ["concept"],
                    "actualSolution": ["solution"],
                    "cautions": ["caution"],
                    "tips": ["tip"]
                }
            }
        ]
    }
    response = client.post("/problem-packs", json={"title": "Test Pack", "pack": pack})
    assert response.status_code == 200
    token = response.json()["token"]

    fetched = client.get(f"/packs/{token}")
    assert fetched.status_code == 200
    assert fetched.json()["pack"]["packId"] == "test-pack"




def test_problem_pack_json_fallback_and_open_url():
    pack = {
        "packId": "test-pack-json-fallback",
        "title": "JSON Fallback Pack",
        "questions": [{
            "id": "q001",
            "title": "Q1",
            "promptMd": "Solve.",
            "answer": {"value": "1"},
            "solution": {"concepts": [], "actualSolution": [], "cautions": [], "tips": []}
        }]
    }
    response = client.post("/problem-packs", json={"title": "JSON Fallback Pack", "pack_json": json.dumps(pack, ensure_ascii=False)})
    assert response.status_code == 200
    data = response.json()
    assert data["open_url"] == data["import_url"] == data["solvepad_url"]
    assert "/static/solvepad/index.html" in data["open_url"]
    assert "importToken=" in data["open_url"]
    assert client.get(f"/packs/{data['token']}").json()["pack"]["packId"] == "test-pack-json-fallback"


def test_calculator_validation():
    blueprint = {
        "meta": {"graphEnabled": False, "strictFinalNames": True},
        "files": [{"name": "MAIN", "lines": [{"type": "text", "value": "HELLO"}]}]
    }
    response = client.post("/calculator/validate", json={"title": "Calc", "blueprint": blueprint})
    assert response.status_code == 200
    assert "ok" in response.json()



def test_lecture_based_unit_mapping_options():
    slide = client.post("/sources/text", json={
        "title": "Lecture Slides",
        "source_type": "lecture_slides",
        "text": "Unit 1 Batch Reactor slides",
        "original_name": "slides.md"
    })
    assert slide.status_code == 200
    slide_id = slide.json()["source_id"]

    saved = client.post("/unit-maps", json={
        "title": "Lecture Based Unit Map",
        "source_ids": [slide_id],
        "map": {
            "schemaVersion": "lecturenote.unitMap.v2",
            "mappingBasis": "lecture_slides",
            "sources": {"lecture_slides": [slide_id]},
            "units": [
                {
                    "unitId": "u001",
                    "unitNumber": "1",
                    "unitTitle": "Batch Reactor",
                    "lectureAnchor": {
                        "sourceId": slide_id,
                        "slideRange": "slide 1-5",
                        "basis": "lecture title"
                    },
                    "keywords": ["batch reactor"],
                    "confidence": "high"
                }
            ],
            "unmapped": []
        }
    })
    assert saved.status_code == 200

    options = client.get("/workflow/options")
    assert options.status_code == 200
    units = options.json()["units"]
    assert any(u.get("unitNumber") == "1" and u.get("lectureAnchor", {}).get("sourceId") == slide_id for u in units)



def test_subject_based_upload_and_filtering():
    a = client.post("/sources/text", json={
        "title": "CRE Slides",
        "subject": "CRE",
        "source_type": "lecture_slides",
        "text": "CRE batch reactor content",
        "original_name": "cre-slides.md"
    })
    assert a.status_code == 200
    assert a.json()["subject"] == "CRE"

    b = client.post("/sources/text", json={
        "title": "Math Slides",
        "subject": "Math2",
        "source_type": "lecture_slides",
        "text": "Math derivative content",
        "original_name": "math-slides.md"
    })
    assert b.status_code == 200

    cre_sources = client.get("/sources?subject=CRE")
    assert cre_sources.status_code == 200
    assert all(s["subject"] == "CRE" for s in cre_sources.json()["sources"])

    search = client.post("/sources/search", json={
        "query": "batch reactor",
        "subject": "CRE",
        "source_types": ["lecture_slides"],
        "limit": 5
    })
    assert search.status_code == 200
    assert len(search.json()["results"]) >= 1
    assert all(r["source_type"] == "lecture_slides" for r in search.json()["results"])

    options = client.get("/workflow/options?subject=CRE")
    assert options.status_code == 200
    assert "CRE" in options.json()["subjects"]



def test_external_notes_endpoint_and_workflow_checkpoints():
    note = client.post("/notes/text", json={
        "title": "User Uploaded Note",
        "subject": "CRE",
        "source_type": "external_note",
        "text": "External note content for CRE.",
        "original_name": "user-note.md"
    })
    assert note.status_code == 200
    assert note.json()["source_type"] == "external_note"

    notes = client.get("/external-notes?subject=CRE")
    assert notes.status_code == 200
    assert any(n["title"] == "User Uploaded Note" for n in notes.json()["external_notes"])

    run = client.post("/workflow/runs", json={
        "title": "CRE long note run",
        "mode": "lecture_note",
        "subject": "CRE",
        "selected_units": ["1", "2", "3"],
        "total_steps": 3,
        "metadata": {"purpose": "test"}
    })
    assert run.status_code == 200
    run_id = run.json()["workflow_run_id"]

    next_step = client.get(f"/workflow/runs/{run_id}/next")
    assert next_step.status_code == 200
    assert next_step.json()["next_unit"] == "1"

    checkpoint = client.post("/workflow/checkpoints", json={
        "run_id": run_id,
        "step_index": 1,
        "step_label": "unit 1",
        "status": "timeout_safe_saved",
        "saved_refs": {"note_version_id": "ver-test"},
        "next_action": "Continue with unit 2",
        "notes": "saved before timeout",
        "advance_to_next": True
    })
    assert checkpoint.status_code == 200
    assert checkpoint.json()["next_step"] == 2

    next_step2 = client.get(f"/workflow/runs/{run_id}/next")
    assert next_step2.status_code == 200
    assert next_step2.json()["next_unit"] == "2"

    checkpoints = client.get(f"/workflow/runs/{run_id}/checkpoints")
    assert checkpoints.status_code == 200
    assert len(checkpoints.json()["checkpoints"]) >= 1



def test_mapping_status_and_delete_source_flow():
    source = client.post("/sources/text", json={
        "title": "Delete Me Slides",
        "subject": "CRE",
        "source_type": "lecture_slides",
        "text": "Mapping status delete source test",
        "original_name": "delete-me.md"
    })
    assert source.status_code == 200
    source_id = source.json()["source_id"]

    status_before = client.get("/mapping/status?subject=CRE")
    assert status_before.status_code == 200
    assert any(s["sourceId"] == source_id for s in status_before.json()["unmappedSources"])

    delete_response = client.delete(f"/sources/{source_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted_source_id"] == source_id
    assert delete_response.json()["deleted_chunks"] >= 1

    status_after = client.get("/mapping/status?subject=CRE")
    assert status_after.status_code == 200
    assert not any(s["sourceId"] == source_id for s in status_after.json()["unmappedSources"])


def test_batch_upload_with_inferred_titles():
    files = [
        ("files", ("week1.txt", b"batch reactor notes", "text/plain")),
        ("files", ("week2.txt", b"cstr notes", "text/plain")),
    ]
    response = client.post(
        "/sources/upload-batch",
        data={"subject": "CRE", "source_type": "lecture_slides", "title": ""},
        files=files,
    )
    assert response.status_code == 200
    assert "업로드 완료" in response.text
    assert "week1" in response.text
    assert "week2" in response.text



def test_v15_menu_key_ui():
    upload = client.get("/upload")
    assert upload.status_code == 200
    text = upload.text
    assert "lecturenote_action_key" in text
    assert "저장된 키 지우기" in text
    assert "upload-batch" in text

    notes = client.get("/notes/upload")
    assert notes.status_code == 200
    assert "lecturenote_action_key" in notes.text

    manage = client.get("/sources/manage")
    assert manage.status_code == 200
    assert "저장된 키 지우기" in manage.text
    assert "유형 필터" in manage.text
    assert "전체 유형" in manage.text

    manage_filtered = client.get("/sources/manage?source_type=lecture_slides")
    assert manage_filtered.status_code == 200
    assert "lecture_slides" in manage_filtered.text


def test_calculator_generate_manual_and_replace_flow():
    blueprint = {
        "meta": {"graphEnabled": False, "strictFinalNames": True},
        "files": [{"name": "MAIN", "lines": [{"type": "text", "value": "HELLO"}]}]
    }
    payload = {
        "title": "Calc Manual Test",
        "blueprint": blueprint,
        "metadata": {"subject": "CRE"},
        "analysis_markdown": "# 분석\n계산 흐름 구상",
        "manual_markdown": "# 사용법\nMAIN을 실행한다."
    }
    generated = client.post("/calculator/generate", json=payload)
    assert generated.status_code == 200
    data = generated.json()
    project_id = data["calculator_project_id"]
    assert data["manual_source_id"]
    assert data["manual_url"].endswith(f"/calculator/projects/{project_id}/manual")

    listed = client.get("/calculator/projects?subject=CRE")
    assert listed.status_code == 200
    assert any(p["calculator_project_id"] == project_id for p in listed.json()["calculator_projects"])

    fetched = client.get(f"/calculator/projects/{project_id}")
    assert fetched.status_code == 200
    assert fetched.json()["manual_markdown"].startswith("# 사용법")

    replaced = client.post("/calculator/generate", json={**payload, "title": "Calc Manual Test Updated", "manual_markdown": "# 새 사용법", "replace_calculator_project_id": project_id})
    assert replaced.status_code == 200
    assert replaced.json()["calculator_project_id"] == project_id
    fetched2 = client.get(f"/calculator/projects/{project_id}")
    assert fetched2.status_code == 200
    assert fetched2.json()["manual_markdown"] == "# 새 사용법"




def test_calculator_blueprint_json_fallback_and_open_url():
    blueprint = {
        "meta": {"graphEnabled": False, "strictFinalNames": True},
        "files": [{"name": "MAIN", "lines": [{"type": "text", "value": "HELLO"}]}]
    }
    response = client.post("/calculator/generate", json={
        "title": "Calc JSON Fallback",
        "blueprint_json": json.dumps(blueprint, ensure_ascii=False),
        "metadata": {"subject": "CRE"}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["open_url"] == data["studio_url"] == data["casio_url"]
    assert "/static/casio/index.html?projectId=" in data["open_url"]
    assert data["download_url"].endswith("/download.zip")
    fetched = client.get(f"/calculator/projects/{data['calculator_project_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["blueprint"]["files"][0]["name"] == "MAIN"


def test_note_version_replace_latest_without_source_id_is_safe_append():
    v1 = client.post("/notes/versions", json={"title": "Replace Note", "content_markdown": "# old", "subject": "CRE"})
    assert v1.status_code == 200
    series_id = v1.json()["series_id"]
    first_source_id = v1.json()["source_id"]
    v2 = client.post("/notes/versions", json={"title": "Replace Note", "content_markdown": "# new", "subject": "CRE", "series_id": series_id, "replace_latest": True})
    assert v2.status_code == 200
    assert v2.json()["version"] == 2
    assert v2.json()["source_id"] != first_source_id
    assert v2.json()["replace_latest_ignored"] is True
    latest = client.get(f"/notes/versions/{series_id}/latest")
    assert latest.status_code == 200
    assert latest.json()["content_markdown"] == "# new"
    first = client.get(f"/study/notes/{first_source_id}")
    assert first.status_code == 200
    assert "# old" in first.json()["markdown"]



def test_v17_search_and_workflow_subject_filtering():
    cre = client.post("/sources/text", json={
        "title": "CRE Reactor Slides",
        "subject": "CRE",
        "source_type": "lecture_slides",
        "text": "Batch reactor conversion and residence time.",
        "original_name": "cre-reactor.md"
    })
    assert cre.status_code == 200
    cre_id = cre.json()["source_id"]

    math = client.post("/sources/text", json={
        "title": "Math Limit Slides",
        "subject": "Math2",
        "source_type": "lecture_slides",
        "text": "Limit derivative integral sequence.",
        "original_name": "math-limit.md"
    })
    assert math.status_code == 200
    math_id = math.json()["source_id"]

    saved = client.post("/unit-maps", json={
        "title": "Mixed Unit Map",
        "source_ids": [cre_id, math_id],
        "map": {
            "schemaVersion": "lecturenote.unitMap.v2",
            "mappingBasis": "lecture_slides",
            "units": [
                {"unitId": "u001", "unitNumber": "1", "unitTitle": "Batch Reactor", "lectureAnchor": {"sourceId": cre_id}, "confidence": "high"},
                {"unitId": "u002", "unitNumber": "2", "unitTitle": "Limits", "lectureAnchor": {"sourceId": math_id}, "confidence": "high"}
            ],
            "unmapped": []
        }
    })
    assert saved.status_code == 200

    search = client.post("/sources/search", json={
        "query": "reactor conversion",
        "subject": "CRE",
        "source_types": ["lecture_slides"],
        "limit": 5
    })
    assert search.status_code == 200
    results = search.json()["results"]
    assert results
    assert all(r.get("subject") == "CRE" for r in results)

    options = client.get("/workflow/options?subject=CRE")
    assert options.status_code == 200
    unit_titles = [u.get("unitTitle") for u in options.json()["units"]]
    assert "Batch Reactor" in unit_titles
    assert "Limits" not in unit_titles



def test_study_note_editor_and_exam_cram_flow():
    created = client.post("/study/notes", json={
        "title": "CRE Unit 1 Note",
        "subject": "CRE",
        "source_type": "generated_note",
        "content_markdown": "# Unit 1\n\n수식 $\\frac{1}{2}$ and <mark>important</mark>",
        "replace_latest": False
    })
    assert created.status_code == 200
    source_id = created.json()["source_id"]

    listed = client.get("/study/notes?subject=CRE&source_type=generated_note")
    assert listed.status_code == 200
    assert any(n["source_id"] == source_id for n in listed.json()["notes"])

    fetched = client.get(f"/study/notes/{source_id}")
    assert fetched.status_code == 200
    assert "\\frac" in fetched.json()["markdown"]

    updated = client.put(f"/study/notes/{source_id}", json={
        "title": "CRE Unit 1 Note Edited",
        "content_markdown": "# Edited\n\nUpdated $$x^2$$",
        "change_summary": "test edit"
    })
    assert updated.status_code == 200
    assert updated.json()["chunk_count"] >= 1

    versions = client.get(f"/study/notes/{source_id}/versions")
    assert versions.status_code == 200
    assert len(versions.json()["versions"]) >= 2
    initial = [v for v in versions.json()["versions"] if v["version"] == 1][0]
    restored = client.post(f"/study/notes/{source_id}/restore", json={"version_id": initial["id"], "change_summary": "restore test"})
    assert restored.status_code == 200
    assert "Unit 1" in restored.json()["content_markdown"]
    assert restored.json()["version"] >= 3

    md = client.get(f"/study/notes/{source_id}/download.md")
    assert md.status_code == 200
    assert b"Unit 1" in md.content

    docx = client.get(f"/study/notes/{source_id}/download.docx")
    assert docx.status_code == 200
    assert docx.headers["content-type"].startswith("application/vnd.openxmlformats")

    printed = client.get(f"/study/notes/{source_id}/print")
    assert printed.status_code == 200
    assert "MathJax" in printed.text

    cram = client.post("/exam-cram", json={
        "title": "CRE 시험 직전 정리",
        "subject": "CRE",
        "content_markdown": "# CRE 시험 직전 정리\n\n## 1. 직전 암기\n- test",
        "replace_latest": False
    })
    assert cram.status_code == 200
    assert cram.json()["source_type"] == "exam_cram"


def test_static_study_app_exists():
    assert client.get("/static/study/index.html").status_code == 200

def test_home_contains_study_note_studio_link():
    response = client.get("/")
    assert response.status_code == 200
    text = response.text
    assert "/static/study/index.html" in text
    assert "정리본" in text or "Study Note" in text


def test_save_unit_map_accepts_mapping_alias():
    response = client.post("/unit-maps", json={
        "title": "Alias Unit Map",
        "sourceIds": [],
        "mapping": {
            "schemaVersion": "lecturenote.unitMap.v2",
            "mappingBasis": "lecture_slides",
            "units": [],
            "unmapped": []
        },
        "createdBy": "gpt"
    })
    assert response.status_code == 200
    assert response.json()["title"] == "Alias Unit Map"


def test_study_note_docx_download_korean_filename_and_wysiwyg_static():
    created = client.post('/study/notes', json={
        'title': 'CRE 정리본 한글',
        'subject': 'CRE',
        'source_type': 'generated_note',
        'content_markdown': '# 제목\n\n본문 <mark>강조</mark>\n\n![샘플](data:image/png;base64,iVBORw0KGgo=)',
        'replace_latest': False
    })
    assert created.status_code == 200
    source_id = created.json()['source_id']
    docx = client.get(f'/study/notes/{source_id}/download.docx')
    assert docx.status_code == 200
    assert docx.headers['content-type'].startswith('application/vnd.openxmlformats')
    assert 'filename*=' in docx.headers.get('content-disposition', '')

    html = Path('static/study/index.html').read_text(encoding='utf-8')
    js = Path('static/study/app.js').read_text(encoding='utf-8')
    assert 'contenteditable="true"' in html
    assert 'documentToMarkdown' in js
    assert 'image-card' in js



def test_v21_past_exam_upload_metadata_and_wysiwyg_source_hidden():
    files = [("files", ("final_exam.txt", b"problem 1 reactor", "text/plain"))]
    response = client.post(
        "/sources/upload-batch",
        data={
            "subject": "CRE",
            "source_type": "past_exam",
            "title": "CRE Final Past Exam",
            "exam_scope_status": "in_scope",
            "exam_usage_mode": "both",
            "exam_range_note": "1-3 units only",
        },
        files=files,
    )
    assert response.status_code == 200
    assert "현재 시험범위 해당" in response.text
    sources = client.get("/sources?subject=CRE&source_type=past_exam")
    assert sources.status_code == 200
    assert any(s.get("exam_scope_status") == "in_scope" and s.get("exam_usage_mode") == "both" for s in sources.json()["sources"])
    search = client.post("/sources/search", json={"query": "시험범위", "subject": "CRE", "source_types": ["past_exam"], "limit": 5})
    assert search.status_code == 200
    assert search.json()["results"]

    html = Path("static/study/index.html").read_text(encoding="utf-8")
    js = Path("static/study/app.js").read_text(encoding="utf-8")
    assert "sourceDialog" in html
    assert "<textarea id=\"markdown\"" in html
    assert "data-md-src" in js
    assert "sourcePanel" not in html


def test_v22_dashboard_and_openapi_contract():
    created = client.post('/sources/text', json={
        'title': 'CRE Dashboard Note',
        'subject': 'CRE',
        'source_type': 'generated_note',
        'text': '# Dashboard Note\ncontent',
        'original_name': 'dashboard.md'
    })
    assert created.status_code == 200

    dashboard = client.get('/dashboard?subject=CRE&limit=5')
    assert dashboard.status_code == 200
    data = dashboard.json()
    assert data['subject'] == 'CRE'
    assert 'summary' in data
    assert 'quickLinks' in data
    assert data['quickLinks']['studyNoteStudio'] == '/static/study/index.html'

    schema_text = Path('docs/actions/openapi.yaml').read_text(encoding='utf-8')
    assert 'openapi: 3.1.0' in schema_text
    assert 'schemas: {}' in schema_text
    assert 'operationId: getDashboard' in schema_text
    assert schema_text.count('operationId:') <= 30


def _make_test_pdf(path: Path, pages: int = 3) -> None:
    import fitz
    doc = fitz.open()
    try:
        for idx in range(pages):
            page = doc.new_page()
            page.insert_text((72, 72), f"Slide {idx + 1}")
        doc.save(str(path))
    finally:
        doc.close()


def test_auto_slide_placeholder_conversion_and_rendering(tmp_path):
    from app.db import save_source

    pdf_path = tmp_path / "auto-slides.pdf"
    _make_test_pdf(pdf_path, pages=3)
    slide = save_source(
        "Auto Slides",
        "lecture_slides",
        "auto-slides.pdf",
        str(pdf_path),
        "application/pdf",
        pdf_path.stat().st_size,
        "Auto slide deck text",
        "pdf_extracted",
        subject="AUTO_SLIDE",
    )
    response = client.post("/study/notes", json={
        "title": "Auto Slide Note",
        "subject": "AUTO_SLIDE",
        "source_type": "generated_note",
        "content_markdown": "# Auto Slide Note\n\n[슬라이드 2]\n\n본문",
        "replace_latest": False,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["auto_slide_markers_inserted"] == 1
    assert f'source_id="{slide["source_id"]}"' in data["content_markdown"]
    assert 'page="2"' in data["content_markdown"]

    rendered = client.get(f'/sources/{slide["source_id"]}/slide-image?page=2')
    assert rendered.status_code == 200
    assert rendered.json()["data_url"].startswith("data:image/png;base64,")


def test_unit_map_heading_auto_slide_insertion(tmp_path):
    from app.db import save_source

    pdf_path = tmp_path / "unit-slides.pdf"
    _make_test_pdf(pdf_path, pages=4)
    slide = save_source(
        "Unit Slides",
        "lecture_slides",
        "unit-slides.pdf",
        str(pdf_path),
        "application/pdf",
        pdf_path.stat().st_size,
        "Unit slide deck text",
        "pdf_extracted",
        subject="UNIT_AUTO",
    )
    saved_map = client.post("/unit-maps", json={
        "title": "Unit Auto Map",
        "source_ids": [slide["source_id"]],
        "map": {
            "schemaVersion": "lecturenote.unitMap.v2",
            "mappingBasis": "lecture_slides",
            "units": [{
                "unitId": "u001",
                "unitNumber": "1",
                "unitTitle": "Batch Reactor",
                "lectureAnchor": {"sourceId": slide["source_id"], "slideRange": "slide 2-4"},
                "confidence": "high",
            }],
            "unmapped": [],
        },
    })
    assert saved_map.status_code == 200

    response = client.post("/study/notes", json={
        "title": "Batch Reactor Note",
        "subject": "UNIT_AUTO",
        "source_type": "generated_note",
        "content_markdown": "# Batch Reactor\n\n반응기 설명",
        "replace_latest": False,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["auto_slide_markers_inserted"] == 1
    assert f'source_id="{slide["source_id"]}"' in data["content_markdown"]
    assert 'page="2"' in data["content_markdown"]


def test_problem_pack_is_registered_as_searchable_source():
    pack = {
        "packId": "indexed-pack",
        "title": "Indexed Pack",
        "subject": "CRE",
        "unitNumber": "1",
        "unitTitle": "Batch Reactor",
        "tags": ["conversion", "reactor"],
        "questions": [{
            "id": "q001",
            "title": "Indexed Question",
            "promptMd": "Find reactor conversion.",
            "answer": {"value": "X"},
            "solution": {"concepts": [], "actualSolution": [], "cautions": [], "tips": []}
        }]
    }
    response = client.post("/problem-packs", json={"title": "Indexed Pack", "pack": pack})
    assert response.status_code == 200
    data = response.json()
    assert data["source_type"] == "problem_pack"
    assert data["source_id"]

    listed = client.get("/problem-packs?subject=CRE")
    assert listed.status_code == 200
    assert any(p["pack_id"] == "indexed-pack" and p["source_id"] == data["source_id"] for p in listed.json()["problem_packs"])

    search = client.post("/sources/search", json={"query": "reactor conversion", "subject": "CRE", "source_types": ["problem_pack"], "limit": 5})
    assert search.status_code == 200
    assert any(r["source_id"] == data["source_id"] for r in search.json()["results"])

    dashboard = client.get("/dashboard?subject=CRE")
    assert dashboard.status_code == 200
    assert dashboard.json()["summary"]["problemPackCount"] >= 1
    assert "problem_pack" in dashboard.json()["bySourceType"]


def test_calculator_project_program_and_analysis_are_searchable_sources():
    blueprint = {
        "meta": {"graphEnabled": False, "strictFinalNames": True},
        "files": [{"name": "MAIN", "lines": [{"type": "text", "value": "REACTOR"}]}]
    }
    response = client.post("/calculator/generate", json={
        "title": "Indexed Calculator",
        "blueprint": blueprint,
        "metadata": {"subject": "CRE", "unitNumber": "1", "unitTitle": "Batch Reactor"},
        "analysis_markdown": "# Analysis\nreactor conversion calculation",
        "manual_markdown": "# Manual\nRun MAIN for reactor conversion."
    })
    assert response.status_code == 200
    data = response.json()
    assert data["source_type"] == "calculator_project"
    assert data["source_id"]
    assert data["program_source_ids"]
    assert data["manual_source_id"]
    assert data["analysis_source_id"]

    for source_type in ["calculator_project", "calculator_program", "calculator_manual", "calculator_analysis"]:
        search = client.post("/sources/search", json={"query": "reactor conversion", "subject": "CRE", "source_types": [source_type], "limit": 5})
        assert search.status_code == 200
        assert search.json()["results"], source_type

    dashboard = client.get("/dashboard?subject=CRE")
    assert dashboard.status_code == 200
    by_type = dashboard.json()["bySourceType"]
    assert "calculator_project" in by_type
    assert "calculator_program" in by_type
    assert "calculator_analysis" in by_type


def test_print_and_docx_image_output_rules_are_left_aligned_sixty_percent():
    css = Path("static/study/styles.css").read_text(encoding="utf-8")
    assert ".doc .image-card{width:60%;margin:18px 0;padding:10px" in css
    assert "position:relative;text-align:left}" in css
    assert ".doc .image-card figcaption{text-align:left}" in css

    created = client.post('/study/notes', json={
        'title': 'Image Size Note',
        'subject': 'CRE',
        'source_type': 'generated_note',
        'content_markdown': '# 이미지\n\n![샘플](data:image/png;base64,iVBORw0KGgo=)',
        'replace_latest': False
    })
    assert created.status_code == 200
    printed = client.get(f"/study/notes/{created.json()['source_id']}/print")
    assert printed.status_code == 200
    assert "figure.image-card{width:60%;margin:18px 0;text-align:left}" in printed.text


def test_study_note_image_scale_markdown_print_and_docx():
    created = client.post('/study/notes', json={
        'title': 'Image Scale Note',
        'subject': 'CRE',
        'source_type': 'generated_note',
        'content_markdown': '# 이미지\n\n![샘플](data:image/png;base64,iVBORw0KGgo=){width=80%}',
        'replace_latest': False
    })
    assert created.status_code == 200
    printed = client.get(f"/study/notes/{created.json()['source_id']}/print")
    assert printed.status_code == 200
    assert "style='width:80%;'" in printed.text
    docx = client.get(f"/study/notes/{created.json()['source_id']}/download.docx")
    assert docx.status_code == 200



def test_study_note_image_scale_controls_support_ten_percent_steps():
    html = Path("static/study/index.html").read_text(encoding="utf-8")
    js = Path("static/study/app.js").read_text(encoding="utf-8")
    for value in range(10, 101, 10):
        assert f'<option value="{value}"' in html
    assert "Math.round(n / 10) * 10" in js

    created = client.post('/study/notes', json={
        'title': 'Small Image Scale Note',
        'subject': 'CRE',
        'source_type': 'generated_note',
        'content_markdown': '# 이미지\n\n![샘플](data:image/png;base64,iVBORw0KGgo=){width=10%}',
        'replace_latest': False
    })
    assert created.status_code == 200
    printed = client.get(f"/study/notes/{created.json()['source_id']}/print")
    assert printed.status_code == 200
    assert "style='width:10%;'" in printed.text
    docx = client.get(f"/study/notes/{created.json()['source_id']}/download.docx")
    assert docx.status_code == 200

def test_artifact_storage_creates_source_rows_not_only_private_tables():
    pack = {
        "packId": "storage-mode-pack",
        "title": "Storage Mode Pack",
        "subject": "STORE",
        "unitNumber": "2",
        "unitTitle": "Indexed Artifacts",
        "questions": [{
            "id": "q001",
            "title": "Stored Problem",
            "promptMd": "storage source row check",
            "answer": {"value": "ok"},
            "solution": {"concepts": [], "actualSolution": [], "cautions": [], "tips": []}
        }]
    }
    saved_pack = client.post("/problem-packs", json={"title": "Storage Mode Pack", "pack": pack})
    assert saved_pack.status_code == 200
    pack_source_id = saved_pack.json()["source_id"]
    sources = client.get("/sources?subject=STORE&source_type=problem_pack")
    assert sources.status_code == 200
    assert any(s["id"] == pack_source_id for s in sources.json()["sources"])

    blueprint = {
        "meta": {"graphEnabled": False, "strictFinalNames": True},
        "files": [{"name": "MAIN", "lines": [{"type": "text", "value": "STORE"}]}]
    }
    saved_calc = client.post("/calculator/generate", json={
        "title": "Storage Mode Calculator",
        "blueprint": blueprint,
        "metadata": {"subject": "STORE", "unitNumber": "2", "unitTitle": "Indexed Artifacts"},
        "analysis_markdown": "storage analysis source row check",
        "manual_markdown": "storage manual source row check"
    })
    assert saved_calc.status_code == 200
    calc_data = saved_calc.json()
    assert calc_data["source_id"]
    assert calc_data["program_source_ids"]
    for source_type in ["calculator_project", "calculator_program", "calculator_manual", "calculator_analysis"]:
        res = client.get(f"/sources?subject=STORE&source_type={source_type}")
        assert res.status_code == 200
        assert res.json()["sources"], source_type


def test_study_note_same_series_does_not_replace_without_replace_source_id():
    first = client.post("/study/notes", json={
        "title": "전재설 9-1 정리본",
        "subject": "전재설",
        "source_type": "generated_note",
        "series_id": "전재설-final-notes-2026-rechecked",
        "content_markdown": "# 9-1\n\nold",
    })
    assert first.status_code == 200
    first_id = first.json()["source_id"]

    second = client.post("/study/notes", json={
        "title": "전재설 10-1 정리본",
        "subject": "전재설",
        "source_type": "generated_note",
        "series_id": "전재설-final-notes-2026-rechecked",
        "content_markdown": "# 10-1\n\nnew",
        "replace_latest": True,
    })
    assert second.status_code == 200
    assert second.json()["source_id"] != first_id
    assert second.json()["replace_latest_ignored"] is True

    fetched = client.get(f"/study/notes/{first_id}")
    assert fetched.status_code == 200
    assert "9-1" in fetched.json()["markdown"]


def test_study_note_replace_source_id_updates_existing_note():
    created = client.post("/study/notes", json={
        "title": "Replace Target",
        "subject": "SAFE",
        "source_type": "generated_note",
        "content_markdown": "# before",
    })
    assert created.status_code == 200
    source_id = created.json()["source_id"]

    replaced = client.post("/study/notes", json={
        "title": "Replace Target Updated",
        "subject": "SAFE",
        "source_type": "generated_note",
        "content_markdown": "# after",
        "replace_latest": True,
        "replace_source_id": source_id,
    })
    assert replaced.status_code == 200
    assert replaced.json()["source_id"] == source_id
    assert replaced.json()["replaced_existing_source"] is True

    fetched = client.get(f"/study/notes/{source_id}")
    assert fetched.status_code == 200
    assert "after" in fetched.json()["markdown"]


def test_study_note_unit_number_creates_unit_specific_series_id():
    first = client.post("/study/notes", json={
        "title": "전재설 Photolithography 정리본",
        "subject": "전재설",
        "source_type": "generated_note",
        "series_id": "전재설-final-notes-2026-rechecked",
        "unitNumber": "11-1/12-2",
        "unitTitle": "Photolithography",
        "content_markdown": "# Photo",
    })
    second = client.post("/study/notes", json={
        "title": "전재설 Film Deposition 정리본",
        "subject": "전재설",
        "source_type": "generated_note",
        "series_id": "전재설-final-notes-2026-rechecked",
        "unitNumber": "13-1",
        "unitTitle": "Film Deposition",
        "content_markdown": "# Film",
    })
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["series_id"] != second.json()["series_id"]
    assert "11-1" in first.json()["series_id"]
    assert "13-1" in second.json()["series_id"]
