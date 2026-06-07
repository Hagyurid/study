from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_solvepad_mathjax_and_gesture_code_present():
    index = (ROOT / "static" / "solvepad" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "solvepad" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "solvepad" / "styles.css").read_text(encoding="utf-8")
    assert "MathJax" in index
    assert "tex-svg.js" in index
    assert "repairLatexBackslashes" in app
    assert "handleTouchGesture" in app
    assert "state.panX" in app and "state.panY" in app
    assert "mjx-container" in css


def test_solvepad_ipad_selection_guard_present():
    app = (ROOT / "static" / "solvepad" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "solvepad" / "styles.css").read_text(encoding="utf-8")
    index = (ROOT / "static" / "solvepad" / "index.html").read_text(encoding="utf-8")
    assert "installIOSPencilGuard" in app
    assert "clearNativeSelection" in app
    assert "selectionchange" in app
    assert "touchstart" in app and "gesturestart" in app
    assert "-webkit-touch-callout:none" in css
    assert "-webkit-user-select:none" in css
    assert "user-scalable=no" in index


def test_solvepad_modal_close_bindings_are_null_safe():
    app = (ROOT / "static" / "solvepad" / "app.js").read_text(encoding="utf-8")
    index = (ROOT / "static" / "solvepad" / "index.html").read_text(encoding="utf-8")
    assert "if($('quickImport'))$('quickImport').onclick" in app
    assert "if($('quickLibrary'))$('quickLibrary').onclick" in app
    assert "addEventListener('click',closeModals)" in app
    assert "if(e.target===m)closeModals()" in app
    assert "app.js?v=5_9" in index


def test_solvepad_main_repository_ui_present():
    app = (ROOT / "static" / "solvepad" / "app.js").read_text(encoding="utf-8")
    index = (ROOT / "static" / "solvepad" / "index.html").read_text(encoding="utf-8")
    assert "serverPackList" in index
    assert "renderServerPackList" in app
    assert "/problem-packs/" in app

