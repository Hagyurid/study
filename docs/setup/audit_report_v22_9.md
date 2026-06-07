# Audit Report v22.9

## Changes

- Fixed `saveUnitMap` Action schema mismatch by using `unit_map` as the GPT Action payload field.
- Kept server compatibility for legacy `map`, `mapping`, `map_json`, and `mapJson` payloads.
- Updated Custom GPT instructions and unit mapping contract so GPT uses `unit_map`, not `map`.
- Added source type filter to `/sources/manage` file management UI.
- Preserved subject filter, bulk delete, and return-to-filter behavior after deletion.
- Updated server version to `2.2.9`.

## Validation

- `python compileall app` passed.
- `pytest -q` passed: 25 tests.
- OpenAPI parsed successfully.
- Action count remains 25.
- operationId values are unique.
