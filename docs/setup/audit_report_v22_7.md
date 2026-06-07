# v22.7 export and slide insertion patch

- Fixed Study Note PDF print export to render Markdown tables as real HTML tables.
- Fixed Study Note Word export to convert Markdown tables into DOCX tables.
- Added Study Note slide insertion UI for embedding a PDF lecture slide page as an image card.
- Added authenticated `/sources/{source_id}/slide-image` endpoint using PyMuPDF for PDF page rendering.
- Added PyMuPDF dependency.
- Updated Custom GPT instructions/contracts so image-required sections use short image/slide cards instead of long insertion-location lists.
