# Audit Report v22.5

## Purpose
Fix Study Note Markdown rendering issues that caused raw table syntax, raw `####` headings, and leaked `M0` placeholder artifacts to appear in rendered notes.

## Changes
- Fixed math placeholder restoration in `static/study/app.js`.
- Added Markdown table rendering and table round-trip serialization.
- Added h4-h6 heading rendering and serialization.
- Added normalization for standalone `M0`-style leaked placeholder lines to `없음`.
- Added table styling to Study Note CSS.
- Updated Study Note cache busting to `v=22_5`.
- Updated Study Note and output-quality Custom GPT contracts to require standard Markdown tables and forbid `M0` placeholder tokens.
- Updated server version to 2.2.5.

## Validation
- python compileall passed.
- node --check static/study/app.js passed.
- node --check static/solvepad/app.js passed.
- pytest passed: 25 tests.
