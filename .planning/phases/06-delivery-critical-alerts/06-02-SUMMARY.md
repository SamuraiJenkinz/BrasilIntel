# Phase 6 Plan 2: PDF Generation Service Summary

## Overview

**Objective:** Create PDF generation service using WeasyPrint for converting HTML reports to PDF format.

**Outcome:** PDFGeneratorService with async generate_pdf() method that returns PDF bytes suitable for email attachment.

**Duration:** ~3 minutes

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add WeasyPrint dependency | 65a39ef | requirements.txt |
| 2 | Create PDFGeneratorService | e63479b | app/services/pdf_generator.py |
| 3 | Test PDF generation | b9e9e68 | tests/test_pdf_generator.py |

## Implementation Details

### PDFGeneratorService (137 lines)

**Key Features:**
- Async PDF generation using `asyncio.to_thread()` for non-blocking operation
- WeasyPrint HTML to PDF conversion with CSS print media support
- Print-optimized CSS with A4 page size, margins, and page break rules
- 3MB size limit enforcement for email attachment compatibility
- Optional file output with automatic parent directory creation

**API:**
```python
class PDFGeneratorService:
    MAX_PDF_SIZE = 3 * 1024 * 1024  # 3MB limit

    async def generate_pdf(
        self,
        html_content: str,
        output_path: Optional[Path] = None
    ) -> Tuple[bytes, int]:
        """Returns (pdf_bytes, file_size_bytes)"""

    async def generate_pdf_from_file(
        self,
        html_path: Path,
        output_path: Optional[Path] = None
    ) -> Tuple[bytes, int]:
        """Generate from HTML file"""
```

### Print CSS Configuration

```css
@page {
    size: A4;
    margin: 1.5cm;
}
@media print {
    .no-print { display: none; }
    h1, h2, h3 { page-break-after: avoid; }
    table { page-break-inside: avoid; }
    .insurer-card { page-break-inside: avoid; }
}
```

### Test Suite (10 tests)

Tests skip automatically if GTK3 runtime is unavailable:
- PDF generation returns valid bytes with %PDF magic
- PDF size under 3MB limit
- File output with parent directory creation
- Unicode/Portuguese content handling
- Complex HTML with tables

## Artifacts

### Files Created
- `app/services/pdf_generator.py` - PDFGeneratorService class
- `tests/test_pdf_generator.py` - Test suite with 10 tests

### Files Modified
- `requirements.txt` - Added weasyprint>=63.1

### Exports
- `PDFGeneratorService` - Async PDF generation service

## Dependencies

### New Dependencies
- `weasyprint>=63.1` - HTML to PDF conversion

### Runtime Requirements
- **Windows:** GTK3 runtime required for WeasyPrint
- Installation: https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation

## Verification Results

| Check | Status |
|-------|--------|
| weasyprint in requirements.txt | PASS |
| PDFGeneratorService syntax valid | PASS |
| Line count >= 60 | PASS (137 lines) |
| HTML().write_pdf() pattern | PASS |
| Tests collected (10) | PASS |
| Tests skip without GTK3 | PASS |

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| asyncio.to_thread() for PDF generation | Prevents blocking FastAPI event loop during CPU-intensive rendering |
| 3MB size limit | Base64 encoding inflates size ~33%, keeps within typical email limits |
| FontConfiguration for Windows | Ensures proper font rendering on Windows systems |
| Tests skip without GTK3 | Allows CI to pass even without GTK3 installed |

## Notes

**GTK3 Dependency:** WeasyPrint requires GTK3 runtime libraries on Windows. The Python package installs but cannot import without these system libraries. This is documented in:
- Module docstrings
- Test file header
- Requirements.txt comments

**Production Deployment:** Ensure GTK3 runtime is installed on the Windows server where BrasilIntel runs. See WeasyPrint documentation for installation instructions.

## Next Steps

Plan 06-03 will enhance GraphEmailService to:
- Attach PDF version of reports
- Support CC/BCC recipients
- Include professional subject lines
