# v23.6 Study Note Studio Save/Image/PDF Memory Patch

Changes:
- Study Note Studio manual save uses auto_slide_images=false to preserve user edits exactly.
- Broken <br> variants are normalized before Studio render/save and server save/PDF conversion.
- Default image/slide size is 100% across Studio UI, marker fallback, CSS, and GPT instructions.
- Direct server-side Study Note PDF export has memory guards:
  - max 5 notes per direct PDF request
  - no heavy slide image rendering in direct PDF; slide placeholders are used
  - slide image LRU cache reduced from 160 to 24
- No OpenAPI Action schema change required.

Apply over v23.5.
