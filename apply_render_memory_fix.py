#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
target = ROOT / "app" / "main.py"
if not target.exists():
    alt = Path.cwd() / "app" / "main.py"
    if alt.exists():
        target = alt
    else:
        raise SystemExit("app/main.py 를 찾지 못했습니다. 저장소 루트에서 실행하거나 zip 내용을 저장소 루트에 풀어주세요.")

text = target.read_text(encoding="utf-8")

def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"[FAIL] {label}: expected exactly 1 match, found {count}")
    text = text.replace(old, new, 1)

# 1) remove unused base64 import
replace_once("import base64\n", "", "remove base64 import")

# 2) replace cached renderer
old_renderer = """@lru_cache(maxsize=24)
def _render_pdf_page_png_base64(stored_path: str, mtime_ns: int, page: int, zoom: float) -> Dict[str, Any]:
    try:
        import fitz  # PyMuPDF
    except Exception:
        raise HTTPException(status_code=500, detail=\"PDF slide rendering package is not installed. Add PyMuPDF to requirements.txt and redeploy.\")
    try:
        doc = fitz.open(stored_path)
        try:
            if page > len(doc):
                raise HTTPException(status_code=400, detail=f\"Page out of range. This PDF has {len(doc)} pages.\")
            pdf_page = doc[page - 1]
            matrix = fitz.Matrix(zoom, zoom)
            pix = pdf_page.get_pixmap(matrix=matrix, alpha=False)
            png = pix.tobytes(\"png\")
            encoded = base64.b64encode(png).decode(\"ascii\")
            return {\"page_count\": len(doc), \"png_base64\": encoded, \"data_url\": \"data:image/png;base64,\" + encoded}
        finally:
            doc.close()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f\"Failed to render slide page: {exc}\")
"""
new_renderer = """@lru_cache(maxsize=6)
def _render_pdf_page_png_bytes(stored_path: str, mtime_ns: int, page: int, zoom: float) -> Dict[str, Any]:
    try:
        import fitz  # PyMuPDF
    except Exception:
        raise HTTPException(status_code=500, detail=\"PDF slide rendering package is not installed. Add PyMuPDF to requirements.txt and redeploy.\")
    try:
        doc = fitz.open(stored_path)
        try:
            if page > len(doc):
                raise HTTPException(status_code=400, detail=f\"Page out of range. This PDF has {len(doc)} pages.\")
            pdf_page = doc[page - 1]
            matrix = fitz.Matrix(zoom, zoom)
            pix = pdf_page.get_pixmap(matrix=matrix, alpha=False)
            png = pix.tobytes(\"png\")
            return {\"page_count\": len(doc), \"png_bytes\": png}
        finally:
            doc.close()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f\"Failed to render slide page: {exc}\")
"""
replace_once(old_renderer, new_renderer, "replace cached PDF renderer")

# 3) replace slide data helper
old_slide_data = """def _render_slide_data(source_id: str, page: int = 1, zoom: float = 2.0) -> dict:
    source = get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail=\"Source not found\")
    stored_path = Path(source.get(\"stored_path\") or \"\")
    if not stored_path.exists():
        raise HTTPException(status_code=404, detail=\"Stored file not found\")
    suffix = stored_path.suffix.lower()
    if suffix != \".pdf\" and \"pdf\" not in (source.get(\"mime_type\") or \"\").lower():
        raise HTTPException(status_code=400, detail=\"Slide image rendering currently supports PDF lecture slides only\")
    page = max(1, int(page or 1))
    zoom = min(4.0, max(0.5, float(zoom or 2.0)))
    stat = stored_path.stat()
    rendered = _render_pdf_page_png_base64(str(stored_path), int(stat.st_mtime_ns), page, zoom)
    label = f\"{source.get('title') or source.get('original_name') or source_id} p.{page}\"
    return {
        \"source_id\": source_id,
        \"page\": page,
        \"page_count\": rendered[\"page_count\"],
        \"label\": label,
        \"data_url\": rendered[\"data_url\"],
        \"png_base64\": rendered[\"png_base64\"],
    }
"""
new_slide_data = """def _render_slide_data(source_id: str, page: int = 1, zoom: float = 2.0) -> dict:
    source = get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail=\"Source not found\")
    stored_path = Path(source.get(\"stored_path\") or \"\")
    if not stored_path.exists():
        raise HTTPException(status_code=404, detail=\"Stored file not found\")
    suffix = stored_path.suffix.lower()
    if suffix != \".pdf\" and \"pdf\" not in (source.get(\"mime_type\") or \"\").lower():
        raise HTTPException(status_code=400, detail=\"Slide image rendering currently supports PDF lecture slides only\")
    page = max(1, int(page or 1))
    zoom = min(4.0, max(0.5, float(zoom or 2.0)))
    stat = stored_path.stat()
    rendered = _render_pdf_page_png_bytes(str(stored_path), int(stat.st_mtime_ns), page, zoom)
    label = f\"{source.get('title') or source.get('original_name') or source_id} p.{page}\"
    return {
        \"source_id\": source_id,
        \"page\": page,
        \"page_count\": rendered[\"page_count\"],
        \"label\": label,
        \"png_bytes\": rendered[\"png_bytes\"],
    }


@app.get(\"/slides/render.png\")
def render_slide_png(source_id: str = Query(...), page: int = Query(default=1), zoom: float = Query(default=2.0)):
    data = _render_slide_data(source_id, page, zoom)
    headers = {
        \"Cache-Control\": \"public, max-age=86400\",
        \"X-Slide-Source-Id\": str(data[\"source_id\"]),
        \"X-Slide-Page\": str(data[\"page\"]),
    }
    return Response(content=data[\"png_bytes\"], media_type=\"image/png\", headers=headers)
"""
replace_once(old_slide_data, new_slide_data, "replace slide data helper")

# 4) replace HTML renderer to use URL instead of data URL
old_marker_html = """def _slide_marker_html(line: str, render_image: bool = True) -> Optional[str]:
    marker = _parse_slide_marker(line)
    if not marker:
        return None
    caption = marker.get(\"caption\") or f\"{marker['source_id']} p.{marker['page']}\"
    attrs = _image_figure_attrs(marker.get(\"size\", 100))
    if not render_image:
        return (
            f\"<figure class='image-card slide-card'{attrs}>\"
            f\"<div class='flow-box'>슬라이드 이미지: {escape(caption)} · source_id={escape(marker['source_id'])} · page={escape(marker['page'])}</div>\"
            f\"<figcaption>{escape(caption)}</figcaption>\"
            \"</figure>\"
        )
    try:
        data = _render_slide_data(marker[\"source_id\"], marker[\"page\"], marker[\"zoom\"])
        return (
            f\"<figure class='image-card slide-card'{attrs}>\"
            f\"<img alt='{escape(caption)}' src='{escape(data['data_url'])}'/>\"
            f\"<figcaption>{escape(caption)}</figcaption>\"
            \"</figure>\"
        )
    except Exception as exc:
        return (
            f\"<figure class='image-card slide-card slide-error'{attrs}>\"
            f\"<div class='flow-box'>슬라이드 삽입 실패: {escape(str(exc))}</div>\"
            f\"<figcaption>{escape(caption)}</figcaption>\"
            \"</figure>\"
        )
"""
new_marker_html = """def _slide_marker_html(line: str, render_image: bool = True) -> Optional[str]:
    marker = _parse_slide_marker(line)
    if not marker:
        return None
    caption = marker.get(\"caption\") or f\"{marker['source_id']} p.{marker['page']}\"
    attrs = _image_figure_attrs(marker.get(\"size\", 100))
    if not render_image:
        return (
            f\"<figure class='image-card slide-card'{attrs}>\"
            f\"<div class='flow-box'>슬라이드 이미지: {escape(caption)} · source_id={escape(marker['source_id'])} · page={escape(marker['page'])}</div>\"
            f\"<figcaption>{escape(caption)}</figcaption>\"
            \"</figure>\"
        )
    try:
        image_url = _public_url(
            f\"/slides/render.png?source_id={quote(str(marker['source_id']))}&page={int(marker['page'])}&zoom={marker['zoom']:g}\"
        )
        return (
            f\"<figure class='image-card slide-card'{attrs}>\"
            f\"<img alt='{escape(caption)}' src='{escape(image_url)}'/>\"
            f\"<figcaption>{escape(caption)}</figcaption>\"
            \"</figure>\"
        )
    except Exception as exc:
        return (
            f\"<figure class='image-card slide-card slide-error'{attrs}>\"
            f\"<div class='flow-box'>슬라이드 삽입 실패: {escape(str(exc))}</div>\"
            f\"<figcaption>{escape(caption)}</figcaption>\"
            \"</figure>\"
        )
"""
replace_once(old_marker_html, new_marker_html, "replace slide marker HTML")

backup = target.with_suffix(target.suffix + ".bak")
backup.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
target.write_text(text, encoding="utf-8")
print(f"[OK] patched: {target}")
print(f"[OK] backup : {backup}")
