from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    title: str
    project_type: str = "lecture_note"
    source_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OutlineSection(BaseModel):
    index: int
    title: str
    source_query: str = ""
    slide_range: str = ""
    transcript_range: str = ""
    textbook_range: str = ""
    status: str = "pending"


class OutlineSave(BaseModel):
    sections: List[OutlineSection]


class SectionSave(BaseModel):
    section_index: int
    title: str = ""
    content_markdown: str
    study_direction: str = ""
    quality_report: Dict[str, Any] = Field(default_factory=dict)


class GenericItemsSave(BaseModel):
    items: List[Dict[str, Any]]


class ProblemPackSave(BaseModel):
    title: str = "SolvePad Problem Pack"
    pack: Dict[str, Any] = Field(default_factory=dict)
    pack_json: str = ""


class CalculatorBlueprintSave(BaseModel):
    title: str = "CASIO PRGM Project"
    blueprint: Dict[str, Any] = Field(default_factory=dict)
    blueprint_json: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    analysis_markdown: str = ""
    manual_markdown: str = ""
    replace_calculator_project_id: str = ""


class SearchRequest(BaseModel):
    query: str
    source_types: List[str] = Field(default_factory=list)
    subject: str = ""
    limit: int = 5


class TextSourceSave(BaseModel):
    title: str
    text: str
    subject: str = ""
    source_type: str = "external_note"
    original_name: str = "external_note.md"


class UnitMapSave(BaseModel):
    title: str
    source_ids: List[str] = Field(default_factory=list)
    map: Dict[str, Any]
    created_by: str = "gpt"


class NoteVersionSave(BaseModel):
    title: str
    content_markdown: str
    subject: str = ""
    series_id: str = ""
    source_type: str = "generated_note"
    change_summary: str = ""
    based_on_version: Optional[int] = None
    replace_latest: bool = False
    auto_slide_images: bool = True


class TranscriptRevisionSave(BaseModel):
    title: str
    corrected_text: str
    subject: str = ""
    original_transcript_source_id: str = ""
    terminology_map: Dict[str, Any] = Field(default_factory=dict)
    change_log: List[Dict[str, Any]] = Field(default_factory=list)


class WorkflowPlanCreate(BaseModel):
    title: str
    subject: str = ""
    selected_units: List[str] = Field(default_factory=list)
    selected_mode: str
    unit_map_id: str = ""
    source_ids: List[str] = Field(default_factory=list)
    reference_priority: List[str] = Field(default_factory=list)
    notes: str = ""



class WorkflowRunCreate(BaseModel):
    title: str
    mode: str
    subject: str = ""
    selected_units: List[str] = Field(default_factory=list)
    workflow_plan_id: str = ""
    total_steps: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowCheckpointSave(BaseModel):
    run_id: str
    step_index: int
    step_label: str = ""
    status: str = "saved"
    saved_refs: Dict[str, Any] = Field(default_factory=dict)
    next_action: str = ""
    notes: str = ""
    advance_to_next: bool = True



class StudyNoteSave(BaseModel):
    title: str
    content_markdown: str
    subject: str = ""
    source_type: str = "generated_note"
    series_id: str = ""
    change_summary: str = ""
    replace_latest: bool = True
    auto_slide_images: bool = True


class StudyNoteUpdate(BaseModel):
    title: str = ""
    content_markdown: str
    change_summary: str = "edited in Study Note Studio"
    auto_slide_images: bool = True


class ExamCramSave(BaseModel):
    title: str
    content_markdown: str
    subject: str = ""
    series_id: str = ""
    change_summary: str = "exam cram update"
    replace_latest: bool = True
    auto_slide_images: bool = True
