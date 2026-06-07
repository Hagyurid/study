from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

FILE_RE = re.compile(r"^[A-Z0-9]{1,8}$")
VAR_RE = re.compile(r"^(?:[A-Z]|r|θ|Str\s?(?:[1-9]|1[0-9]|20))$")
FINAL_VERSION_RE = re.compile(r"\d+$")

FORBIDDEN_GRAPH_TOKENS = [
    "Graph", "DrawGraph", "DrawR-Con", "DrawR-Plt", "DrawWeb",
    "DrawFTG-Con", "DrawFTG-Plt", "ViewWindow", "View Window",
    "ClrGraph", "DrawStat", "DrawDyna"
]
FORBIDDEN_DISPLAY_CHARS_IN_CODE = set("×÷≤≥≠→⇒√Σ∑ΔαβγδδεϵζηκλμνξρστφχψωΩ∞±∂∇∝∴∵")
DISPLAY_SYMBOL_MAP = [
    ("<=", "≤"), (">=", "≥"), ("<>", "≠"), ("!=", "≠"),
    ("->", "→"), ("=>", "⇒"), ("*", "×"), ("/", "÷"),
    ("DELTA", "Δ"), ("Delta", "Δ"), ("delta", "δ"),
    ("theta", "θ"), ("THETA", "θ"),
    ("alpha", "α"), ("beta", "β"), ("gamma", "γ"),
    ("epsilon", "ε"), ("eps", "ε"), ("zeta", "ζ"), ("eta", "η"),
    ("kappa", "κ"), ("lambda", "λ"), ("mu", "μ"), ("nu", "ν"),
    ("xi", "ξ"), ("rho", "ρ"), ("sigma", "σ"), ("tau", "τ"),
    ("phi", "φ"), ("chi", "χ"), ("psi", "ψ"), ("omega", "ω"), ("OMEGA", "Ω"),
    ("SUM", "Σ"), ("sum", "Σ"), ("sqrt", "√"), ("pi", "π"), ("inf", "∞"),
]
DISPLAY_ALLOWED_NON_ASCII = set("ΔδθπΣ√≤≥≠→⇒×÷αβγεϵζηκλμνξρστφχψωΩ∞±∂∇∝∴∵")

@dataclass
class ValidationMessage:
    level: str
    file: Optional[str]
    line: Optional[int]
    message: str
    detail: Optional[str] = None

@dataclass
class EngineResult:
    files: Dict[str, str] = field(default_factory=dict)
    errors: List[ValidationMessage] = field(default_factory=list)
    warnings: List[ValidationMessage] = field(default_factory=list)
    info: List[ValidationMessage] = field(default_factory=list)
    character_report: List[Dict[str, str]] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        def conv(xs: List[ValidationMessage]) -> List[Dict[str, Any]]:
            return [x.__dict__ for x in xs]
        return {
            "ok": not self.errors,
            "files": [{"name": name, "content": content} for name, content in self.files.items()],
            "errors": conv(self.errors),
            "warnings": conv(self.warnings),
            "info": conv(self.info),
            "character_report": self.character_report,
        }

class PrgmEngine:
    def __init__(self, blueprint: Dict[str, Any]):
        self.blueprint = blueprint or {}
        self.meta = self.blueprint.get("meta") or {}
        self.display_width = int(self.meta.get("displayWidth") or 21)
        self.auto_wrap = bool(self.meta.get("autoWrapText", True))
        self.character_mode = self.meta.get("characterMode", "casio_display")
        self.graph_enabled = bool(self.meta.get("graphEnabled", False))
        self.strict_final_names = bool(self.meta.get("strictFinalNames", True))
        self.result = EngineResult()
        self.file_names: set[str] = set()

    def _file_name(self, file_spec: Dict[str, Any]) -> str:
        raw = str(
            file_spec.get("name")
            or file_spec.get("filename")
            or file_spec.get("fileName")
            or file_spec.get("path")
            or ""
        ).strip()
        raw = raw.replace("\\", "/").split("/")[-1]
        if raw.lower().endswith(".txt"):
            raw = raw[:-4]
        raw = re.sub(r"[^A-Za-z0-9]", "", raw).upper()
        return raw

    def _direct_file_content(self, file_spec: Dict[str, Any]) -> Optional[str]:
        for key in ("content", "program", "code", "text"):
            if key not in file_spec:
                continue
            value = file_spec.get(key)
            if isinstance(value, list):
                text = "\n".join(str(x) for x in value)
            else:
                text = str(value or "")
            if text.strip():
                return text.replace("\r\n", "\n").replace("\r", "\n").rstrip() + "\n"
        lines = file_spec.get("lines")
        if isinstance(lines, list) and lines:
            if all(not isinstance(x, dict) for x in lines):
                return "\n".join(str(x) for x in lines).replace("\r\n", "\n").replace("\r", "\n").rstrip() + "\n"
            if all(isinstance(x, dict) for x in lines):
                out: List[str] = []
                for item in lines:
                    value = item.get("content") or item.get("value") or item.get("text") or item.get("line")
                    if value is not None:
                        out.append(str(value))
                if out:
                    return "\n".join(out).replace("\r\n", "\n").replace("\r", "\n").rstrip() + "\n"
        return None

    def generate_and_validate(self) -> EngineResult:
        self._validate_top_level()
        files = self.blueprint.get("files") or []
        for f in files:
            name = self._file_name(f)
            if name:
                self.file_names.add(name)
        for f in files:
            name = self._file_name(f)
            if not name:
                continue
            content = self._emit_file(f)
            self.result.files[f"{name}.txt"] = content
            self._validate_generated_code(name, content)
        self._validate_cross_file()
        return self.result

    def validate_only(self) -> EngineResult:
        return self.generate_and_validate()

    def _msg(self, level: str, file: Optional[str], line: Optional[int], message: str, detail: Optional[str] = None):
        m = ValidationMessage(level, file, line, message, detail)
        if level == "error":
            self.result.errors.append(m)
        elif level == "warning":
            self.result.warnings.append(m)
        else:
            self.result.info.append(m)

    def _validate_top_level(self):
        if not isinstance(self.blueprint, dict):
            self._msg("error", None, None, "설계도는 JSON object여야 합니다.")
            return
        if self.meta.get("graphEnabled") is not False:
            self._msg("warning", None, None, "graphEnabled는 false 권장입니다. 현재 생성기는 그래프 명령을 금지합니다.")
        files = self.blueprint.get("files")
        if not isinstance(files, list) or not files:
            self._msg("error", None, None, "files 배열이 필요합니다.")
            return
        seen = set()
        for f in files:
            name = self._file_name(f)
            if not FILE_RE.match(name):
                raw_name = str(f.get("name") or f.get("filename") or f.get("fileName") or "").strip()
                self._msg("error", name or None, None, "파일명 규칙 위반: 1~8자, 대문자 A-Z/숫자만 허용", raw_name or name)
            if self.strict_final_names and FINAL_VERSION_RE.search(name):
                self._msg("error", name, None, "최종본 모드에서는 파일명 끝 버전 숫자를 쓰지 않습니다.")
            if name in seen:
                self._msg("error", name, None, "중복 파일명입니다.")
            seen.add(name)

    def _validate_cross_file(self):
        files = self.blueprint.get("files") or []
        for f in files:
            name = self._file_name(f)
            blocks = f.get("blocks") or []
            direct_content = self._direct_file_content(f)
            is_menu_only = any(b.get("type") == "menu" for b in blocks) and not any(b.get("type") in {"input", "calcStep", "calc", "recurrenceTable"} for b in blocks)
            if not direct_content and not f.get("referenceOnly") and not is_menu_only:
                present = {b.get("type") for b in blocks}
                required = {"screen", "symbolTable", "conditionList", "formula", "input", "output", "interpretation"}
                if "calcStep" not in present and "calc" not in present and "recurrenceTable" not in present:
                    self._msg("warning", name, None, "풀이형 프로그램 권장 block 누락: calcStep 또는 calc")
                for r in sorted(required - present):
                    self._msg("warning", name, None, f"풀이형 프로그램 권장 block 누락: {r}")
            for idx, b in enumerate(blocks):
                typ = b.get("type")
                if typ == "menu":
                    items = b.get("items") or []
                    for item in items:
                        target = item.get("target")
                        if target and target not in self.file_names:
                            self._msg("error", name, None, f"Menu target이 files 배열에 없습니다: {target}")
                if typ == "call":
                    target = b.get("target")
                    if target and target not in self.file_names:
                        self._msg("error", name, None, f"call target이 files 배열에 없습니다: {target}")

    def _emit_file(self, file_spec: Dict[str, Any]) -> str:
        name = self._file_name(file_spec)
        direct = self._direct_file_content(file_spec)
        if direct is not None:
            return direct
        out: List[str] = []
        for b in file_spec.get("blocks") or []:
            typ = b.get("type")
            try:
                lines = self._emit_block(name, b)
                out.extend(lines)
            except Exception as exc:
                self._msg("error", name, None, f"block 생성 실패: {typ}", str(exc))
        return "\n".join([x.rstrip() for x in out if x is not None]) + "\n"

    def _emit_block(self, file_name: str, b: Dict[str, Any]) -> List[str]:
        typ = b.get("type")
        if typ == "screen":
            return self._emit_display_block(b.get("title") or "INFO", b.get("lines") or [])
        if typ == "symbolTable":
            lines: List[str] = []
            for it in b.get("items") or []:
                sym = str(it.get("symbol", "")).strip()
                var = str(it.get("var", "")).strip()
                meaning = str(it.get("meaning", "")).strip()
                unit = str(it.get("unit", "")).strip()
                if var and var not in {"-", "—", "none", "None", "n/a", "N/A"}:
                    lines.append(f"{sym}={var}")
                else:
                    lines.append(sym)
                if meaning:
                    lines.append(meaning)
                if unit:
                    lines.append(f"unit {unit}")
            return self._emit_display_block(b.get("title") or "SYMBOLS", lines)
        if typ == "conditionList":
            lines = [str(x) for x in (b.get("rules") or [])]
            out = self._emit_display_block(b.get("title") or "CONDITIONS", lines)
            for check in b.get("checks") or []:
                cond = str(check.get("condition", "")).strip()
                action = str(check.get("then", "Stop")).strip() or "Stop"
                out.extend([f"If {cond}", f"Then {action}", "IfEnd"])
            return out
        if typ == "formula":
            return self._emit_display_block(b.get("title") or "FORMULA", b.get("lines") or [])
        if typ == "input":
            out: List[str] = []
            intro = b.get("intro") or []
            if intro:
                out.extend(self._emit_display_block("INPUT DATA", intro))
            for it in b.get("items") or []:
                label = self._sanitize_label(str(it.get("label", "")))
                var = str(it.get("var", "")).strip()
                meaning = str(it.get("meaning", "")).strip()
                if meaning:
                    out.extend(self._emit_display_block(label, [meaning]))
                out.append(f'"{label}"?->{var}')
            return out
        if typ == "calcStep":
            out = self._emit_display_block(b.get("title") or "STEP", b.get("explain") or [])
            op = str(b.get("operation", "")).strip()
            if op:
                out.append(op)
            result_var = str(b.get("resultVar") or self._infer_store_var(op) or b.get("resultLabel") or "").strip()
            label = str(b.get("resultLabel") or result_var).strip()
            if label:
                out.extend(self._emit_display_block("RESULT", [label]))
            if result_var and self._is_value_var(result_var):
                out.append(f"{result_var}Disps")
            return out
        if typ == "calc":
            return [str(x).strip() for x in (b.get("lines") or [])]
        if typ == "output":
            out: List[str] = []
            title = b.get("title") or "FINAL RESULT"
            out.extend(self._emit_display_block(title, []))
            for it in b.get("items") or []:
                label = str(it.get("label", "")).strip()
                val = str(it.get("value", "")).strip()
                if label:
                    out.extend(self._emit_display_block("", [label]))
                if val:
                    out.append(f"{val}Disps")
            return out
        if typ == "interpretation":
            return self._emit_display_block(b.get("title") or "INTERPRET", b.get("lines") or [])
        if typ == "if":
            cond = str(b.get("condition", "")).strip()
            then = str(b.get("then", "")).strip()
            out = [f"If {cond}", f"Then {then}"]
            if b.get("else"):
                out.append(f"Else {str(b.get('else')).strip()}")
            out.append("IfEnd")
            return out
        if typ == "for":
            var = str(b.get("var", "I")).strip()
            start = str(b.get("start", "1")).strip()
            to = str(b.get("to", "N")).strip()
            step = str(b.get("step", "")).strip()
            first = f"For {start}->{var} To {to}" + (f" Step {step}" if step else "")
            return [first] + [str(x).strip() for x in (b.get("body") or [])] + ["Next"]
        if typ == "while":
            cond = str(b.get("condition", "")).strip()
            return [f"While {cond}"] + [str(x).strip() for x in (b.get("body") or [])] + ["WhileEnd"]
        if typ == "do":
            cond = str(b.get("condition", "")).strip()
            return ["Do"] + [str(x).strip() for x in (b.get("body") or [])] + [f"LpWhile {cond}"]
        if typ == "recurrenceTable":
            initial = str(b.get("initialVar", "Y")).strip()
            end = str(b.get("endVar", "E")).strip()
            return ["an+1Type", '"_an__*_A_+_H"->an+1', f"{initial}->a0", "1->R Start", f"{end}->R End", "DispR-Tbl"]
        if typ == "menu":
            title = self._sanitize_label(str(b.get("title", "MENU")))
            items = b.get("items") or []
            out = []
            if len(items) < 2 or len(items) > 9:
                self._msg("error", file_name, None, "Menu items는 2~9개여야 합니다.")
            parts = [f'Menu "{title}"']
            for item in items:
                label = self._sanitize_label(str(item.get("label", "ITEM")))
                branch = int(item.get("branch", 0))
                parts.append(f'"{label}"')
                parts.append(str(branch))
            out.append(",".join(parts))
            for item in items:
                branch = int(item.get("branch", 0))
                target = str(item.get("target", "")).strip()
                out.extend([f"Lbl {branch}", f'Prog "{target}"', "Return"])
            return out
        if typ == "call":
            return [f'Prog "{str(b.get("target", "")).strip()}"']
        if typ == "raw":
            self._msg("warning", file_name, None, "raw block은 규칙 검사를 우회할 수 있으므로 최종본에서 최소화하십시오.")
            return [str(x).strip() for x in (b.get("lines") or [])]
        if typ == "end":
            mode = str(b.get("mode", "Return")).strip()
            if mode not in {"Return", "Stop"}:
                self._msg("error", file_name, None, "end.mode는 Return 또는 Stop만 허용됩니다.")
                mode = "Return"
            return [mode]
        self._msg("warning", file_name, None, f"알 수 없는 block type: {typ}")
        return []

    def _emit_display_block(self, title: str, lines: List[Any]) -> List[str]:
        raw_lines = []
        if title:
            raw_lines.append(str(title))
        raw_lines.extend(str(x) for x in lines if x is not None and str(x) != "")
        display_lines: List[str] = []
        for line in raw_lines:
            display_lines.extend(self._wrap_display(self._to_display_text(line)))
        if not display_lines:
            display_lines = [self._to_display_text(title or "INFO")]
        out = ["ClrText"]
        for i, line in enumerate(display_lines):
            q = self._quote(line)
            if i == len(display_lines) - 1:
                out.append(f'"{q}"Disps')
            else:
                out.append(f'"{q}"')
        return out

    def _to_display_text(self, text: str) -> str:
        s = str(text)
        if self.character_mode == "casio_display":
            before = s
            for a, b in DISPLAY_SYMBOL_MAP:
                s = s.replace(a, b)
            if before != s:
                self.result.character_report.append({"kind": "display_convert", "from": before, "to": s})
        for ch in s:
            if ord(ch) > 127 and ch not in DISPLAY_ALLOWED_NON_ASCII:
                self._msg("warning", None, None, f"CASIO 표시 변환표에 없는 비ASCII 문자: {ch}", s)
        return s

    def _wrap_display(self, text: str) -> List[str]:
        if not self.auto_wrap or len(text) <= self.display_width:
            return [text]
        chunks = []
        s = text
        breakers = ["=", "+", "-", "×", "÷", "/", "*", ")", "]", ",", " "]
        while len(s) > self.display_width:
            cut = -1
            for br in breakers:
                pos = s.rfind(br, 0, self.display_width + 1)
                if pos > cut:
                    cut = pos + (0 if br == " " else 1)
            if cut <= 0 or cut < max(8, self.display_width // 2):
                cut = self.display_width
            chunks.append(s[:cut].strip())
            s = s[cut:].strip()
        if s:
            chunks.append(s)
        return chunks

    def _quote(self, text: str) -> str:
        return text.replace('"', "'")

    def _sanitize_label(self, label: str) -> str:
        return self._quote(label.strip())[:60]

    def _infer_store_var(self, op: str) -> Optional[str]:
        if "->" in op:
            return op.split("->")[-1].strip()
        return None

    def _is_value_var(self, s: str) -> bool:
        return bool(VAR_RE.match(s)) or s in {"a0", "a1", "a2", "R Start", "R End", "F Start", "F End", "F pitch"}

    def _strip_strings(self, line: str) -> str:
        out = []
        in_str = False
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == '"':
                in_str = not in_str
                out.append(" ")
            elif not in_str:
                out.append(ch)
            else:
                out.append(" ")
            i += 1
        return "".join(out)

    def _validate_generated_code(self, file_name: str, code: str):
        lines = code.splitlines()
        counts = {"If": 0, "IfEnd": 0, "For": 0, "Next": 0, "While": 0, "WhileEnd": 0, "Do": 0, "LpWhile": 0}
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            outside = self._strip_strings(stripped)
            if stripped.startswith("'Program Mode:"):
                self._msg("error", file_name, idx, "새 생성 TXT에는 Program Mode 헤더를 넣지 않습니다.")
            if not self.graph_enabled:
                for tok in FORBIDDEN_GRAPH_TOKENS:
                    if tok in outside:
                        self._msg("error", file_name, idx, f"그래프 관련 명령 금지: {tok}")
            if re.search(r"\^\s*$", outside) or "^" in outside:
                self._msg("error", file_name, idx, "raw ^ 출력 금지. Disps를 사용하십시오.")
            if "?->" in outside and re.search(r"\?->\s*[A-Za-z],", outside):
                self._msg("error", file_name, idx, "입력문은 \"LABEL\"?->A 형식으로 작성하십시오.")
            if re.search(r"\bThen\s*$", stripped):
                self._msg("error", file_name, idx, "Then 단독 줄 금지. Then 실행문 형식 사용.")
            if re.search(r"^If\b.*\bThen\b", stripped):
                self._msg("error", file_name, idx, "한 줄 If 조건 Then 실행문 형식 금지. If 조건 / Then 실행문 / IfEnd 사용.")
            if "View Window" in outside or "Draw Graph" in outside or "If End" in outside or "While End" in outside or "Lp While" in outside:
                self._msg("error", file_name, idx, "명령어 내부 공백 오류가 있습니다.")
            if "RStart" in outside or "REnd" in outside or "R_Start" in outside or "R_End" in outside:
                self._msg("error", file_name, idx, "R Start / R End 공백을 유지하십시오.")
            if any(ch in outside for ch in FORBIDDEN_DISPLAY_CHARS_IN_CODE):
                self._msg("error", file_name, idx, "계산/명령 줄에는 표시용 기호를 넣지 마십시오. *, /, ->, <=, >=, <> 사용.", outside)
            if re.search(r"\bln\(", outside) or re.search(r"\bln[A-Z0-9]", outside) or re.search(r"\bLn\b", outside):
                self._msg("error", file_name, idx, "자연로그는 ln 뒤에 공백을 둡니다. 예: ln (A), ln A")
            # Rough implicit multiplication checks on operation-ish lines.
            if not stripped.startswith(('"', "Menu ", "Lbl ", "Prog ", "ClrText", "If ", "Then ", "Else", "IfEnd", "For ", "Next", "While", "WhileEnd", "Do", "LpWhile", "Return", "Stop", "an+1Type", "Disp")):
                if re.search(r"\d+[A-Z]", outside) or re.search(r"\d+\s*\(", outside) or re.search(r"\)[A-Z]", outside):
                    self._msg("warning", file_name, idx, "암시적 곱셈 의심. A*B, 2*A, 2*(...) 형식 권장.", outside)
            # counts
            if stripped.startswith("If "): counts["If"] += 1
            if stripped == "IfEnd": counts["IfEnd"] += 1
            if stripped.startswith("For "): counts["For"] += 1
            if stripped == "Next": counts["Next"] += 1
            if stripped.startswith("While "): counts["While"] += 1
            if stripped == "WhileEnd": counts["WhileEnd"] += 1
            if stripped == "Do": counts["Do"] += 1
            if stripped.startswith("LpWhile "): counts["LpWhile"] += 1
        pairs = [("If", "IfEnd"), ("For", "Next"), ("While", "WhileEnd"), ("Do", "LpWhile")]
        for a, b in pairs:
            if counts[a] != counts[b]:
                self._msg("error", file_name, None, f"{a}/{b} 개수가 맞지 않습니다: {counts[a]} vs {counts[b]}")


def generate_txt_files(blueprint: Dict[str, Any]) -> EngineResult:
    return PrgmEngine(blueprint).generate_and_validate()


def validate_blueprint(blueprint: Dict[str, Any]) -> EngineResult:
    return PrgmEngine(blueprint).validate_only()
