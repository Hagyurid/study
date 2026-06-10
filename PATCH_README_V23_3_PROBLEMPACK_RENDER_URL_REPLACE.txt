# v23.3 ProblemPack Render / URL / Replace Stability Patch

Base: v23.0 storage-role-refactor patch.

Apply this patch on top of v23.0. Do not delete the whole repository.

## Included changes
- Normalize all public Action shortcut URLs to `https://study-xqe8.onrender.com`; guards historical typo `study-xge8`.
- Add `validateProblemPackRender` Action: `/problem-packs/validate-render`.
- Add `replace_source_id`, `replace_pack_id`, `version_label`, `change_summary`, `validate_render` to `saveProblemPack`.
- Add problem-pack version archiving table.
- SolvePad renderer now renders Markdown tables and applies math rendering to prompt, choices, solution arrays, hints, answer, and asset descriptions.
- Add answerFormat / gradingCriterion / mathematicalNote / sourceRefs / questionSource support as pass-through metadata in problem-pack JSON.
- Update OpenAPI to v23.3.

## Required GPT Builder update
Replace Actions schema with `docs/actions/openapi.yaml`. Add the Custom GPT v23.3 patch text from the companion GPT zip or paste the provided block into Instructions.

## Quick checks
```bash
python -m compileall -q app
node --check static/solvepad/app.js
pytest -q
```
