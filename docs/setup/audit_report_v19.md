# v19 Study Menu + UnitMap Fix

## Fixed
- Home page now exposes Study Note Studio / 정리본 보기.
- Added robust saveUnitMap endpoint compatibility for `map`, `map_json`, `mapJson`, or `mapping` payload fields.
- `source_ids` and `sourceIds` are both accepted.
- Custom GPT OpenAPI schema remains under 30 operations and uses OpenAPI 3.1.0 with `components.schemas: {}`.
- Instructions now explicitly tell GPT to use `map` field for saveUnitMap and avoid legacy Actions.

## Files to upload
- app/main.py
- app/db.py
- app/models.py
- static/study/index.html
- static/study/app.js
- static/study/styles.css
- docs/actions/openapi.yaml
- docs/custom_gpt/01_suite_instructions.txt
- docs/setup/audit_report_v19.md
