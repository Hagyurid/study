# v22.1 hotfix

## Fix
- Fixed Python SyntaxError in `app/main.py` upload-result table rendering.
- Removed backslash-containing HTML string from inside an f-string expression.

## Validation
- `python -m compileall -q app` passed.
- `node --check static/study/app.js` passed.
- `node --check static/solvepad/app.js` passed.
- `pytest -q` passed: 25 tests.
