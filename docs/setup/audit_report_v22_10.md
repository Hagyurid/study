# v22.10 UnitMap JSON String Hotfix

## Purpose
- Fix Custom GPT Actions object-field transmission issue for `saveUnitMap`.
- Replace free-form `unit_map` object input with stable `unit_map_json` string input in OpenAPI and GPT instructions.
- Server remains backward compatible with `unit_map`, `unitMap`, `map`, `mapping`, and now parses JSON text from `unit_map_json`.

## Checks
- python compileall: pass
- OpenAPI 3.1.0 parse: pass
- operationId duplicate check: pass
