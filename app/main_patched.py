from __future__ import annotations

from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote

from fastapi import HTTPException, Query
from fastapi.responses import Response

from app import main as _main

app = _main.app


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
