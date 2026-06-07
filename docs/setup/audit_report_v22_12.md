# audit_report_v22_12

- Added automatic `SLIDE_IMAGE` marker rendering in Study Note Studio.
- Added server-side conversion of `SLIDE_IMAGE` markers for Word/PDF export.
- Manual slide insertion now stores a stable marker instead of embedding a large data URL.
- Updated Custom GPT instructions/contracts to use `[[SLIDE_IMAGE source_id="..." page="..." caption="..."]]`.
- Removed runtime data from final clean package.
