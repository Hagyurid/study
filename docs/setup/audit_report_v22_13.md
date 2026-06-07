# v22.13 audit report

## Scope
- Ensure GPT-generated SolvePad problem packs can be imported directly without manual JSON upload.
- Ensure GPT-generated CASIO calculator projects can be opened/downloaded directly without manual TXT upload.
- Update Custom GPT instructions and contracts accordingly.

## Server changes
- `/problem-packs` now returns `import_url`, `open_url`, and a short message.
- `/calculator/generate` now returns `studio_url`, `manual_url`, `download_url`, and a short message.
- Service version updated to `2.2.13`.

## Custom GPT changes
- Instructions require `saveProblemPack` result URL to be provided by default.
- Instructions require `generateCalculatorProgram` result URLs to be provided by default.
- SolvePad contract updated with direct-import rule.
- CASIO contract updated with direct-open/direct-download rule.

## Validation
- python compileall app: pass
- node --check static/study/app.js: pass
- node --check static/solvepad/app.js: pass
- pytest: 25 passed
