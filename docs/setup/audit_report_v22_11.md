# v22.11 audit report

## Changes

- Added bulk display-name rename in `/sources/manage`.
- Added rename target options: title only, file-name display only, or both.
- Kept batch delete and individual delete behavior.
- Changed file management source type display from internal keys to Korean labels.
- Prevented subject labels from wrapping vertically in the file management table.
- Added `update_source_names` database helper.

## Validation

- `python -m compileall app` passed.
- `pytest -q` passed: 25 tests.
