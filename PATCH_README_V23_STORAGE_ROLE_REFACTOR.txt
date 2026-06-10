LectureNote Suite v23 STORAGE ROLE REFACTOR PATCH ONLY

Apply this zip over the current v22.31 tree after the previous v22.22~v22.31 patches.

Main changes:
- deleteSource reference cleanup + /maintenance/cleanup
- Dashboard/search memory-oriented compaction
- SolvePad server/local problem pack separation
- independent wrong-answer manager
- Calculator generate defaults to device/local storage; server storage is opt-in via storage_mode=server
- OpenAPI and Custom GPT v23 storage role instructions updated

Validation run in sandbox:
- python -m compileall -q app
- node --check static/solvepad/app.js
- node --check extracted static/casio script
- OpenAPI YAML parse
- pytest -q: 44 passed
