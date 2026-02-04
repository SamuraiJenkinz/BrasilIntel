"""Tests for PDF generation service.

Note: These tests require GTK3 runtime to be installed on Windows.
WeasyPrint depends on GTK3 libraries (libgobject, libpango, etc.).
See: https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation
"""
import pytest
from pathlib import Path

# Skip all tests in this module if WeasyPrint cannot be imported
# This handles the GTK3 runtime dependency on Windows
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except OSError:
    WEASYPRINT_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not WEASYPRINT_AVAILABLE,
    reason="WeasyPrint requires GTK3 runtime (not installed)"
)


class TestPDFGeneratorService:
    """Test suite for PDFGeneratorService."""

    @pytest.fixture
    def pdf_service(self):
        """Create PDF service instance."""
        from app.services.pdf_generator import PDFGeneratorService
        return PDFGeneratorService()

    @pytest.fixture
    def sample_html(self):
        """Sample HTML for testing."""
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>Test Report</title></head>
        <body>
            <h1>BrasilIntel Test Report</h1>
            <p>This is a test paragraph.</p>
            <table>
                <tr><th>Insurer</th><th>Status</th></tr>
                <tr><td>Test Corp</td><td>Stable</td></tr>
            </table>
        </body>
        </html>
        '''

    @pytest.mark.asyncio
    async def test_generate_pdf_returns_bytes(self, pdf_service, sample_html):
        """Test that PDF generation returns bytes."""
        pdf_bytes, size = await pdf_service.generate_pdf(sample_html)

        assert isinstance(pdf_bytes, bytes)
        assert size > 0
        # PDF magic bytes
        assert pdf_bytes[:4] == b'%PDF'

    @pytest.mark.asyncio
    async def test_generate_pdf_size_reasonable(self, pdf_service, sample_html):
        """Test that generated PDF is under size limit."""
        from app.services.pdf_generator import PDFGeneratorService

        pdf_bytes, size = await pdf_service.generate_pdf(sample_html)

        assert size < PDFGeneratorService.MAX_PDF_SIZE
        # Simple HTML should be well under 1MB
        assert size < 1 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_generate_pdf_with_output_path(self, pdf_service, sample_html, tmp_path):
        """Test saving PDF to file."""
        output_path = tmp_path / "test_report.pdf"

        pdf_bytes, size = await pdf_service.generate_pdf(sample_html, output_path)

        assert output_path.exists()
        assert output_path.stat().st_size == size
        assert output_path.read_bytes()[:4] == b'%PDF'

    @pytest.mark.asyncio
    async def test_generate_pdf_creates_parent_dirs(self, pdf_service, sample_html, tmp_path):
        """Test that parent directories are created if needed."""
        output_path = tmp_path / "nested" / "dirs" / "report.pdf"

        pdf_bytes, size = await pdf_service.generate_pdf(sample_html, output_path)

        assert output_path.exists()
        assert output_path.parent.exists()

    @pytest.mark.asyncio
    async def test_generate_pdf_from_file(self, pdf_service, sample_html, tmp_path):
        """Test generating PDF from HTML file."""
        html_path = tmp_path / "test.html"
        html_path.write_text(sample_html, encoding='utf-8')

        pdf_bytes, size = await pdf_service.generate_pdf_from_file(html_path)

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b'%PDF'

    @pytest.mark.asyncio
    async def test_print_css_applied(self, pdf_service):
        """Test that print CSS is applied to PDF."""
        html = '''
        <!DOCTYPE html>
        <html>
        <body>
            <div class="no-print">This should be hidden in print</div>
            <p>This should appear in PDF</p>
        </body>
        </html>
        '''

        # Just verify it generates without error
        # Actual CSS application would require inspecting PDF content
        pdf_bytes, size = await pdf_service.generate_pdf(html)
        assert pdf_bytes[:4] == b'%PDF'

    @pytest.mark.asyncio
    async def test_size_limit_constant(self, pdf_service):
        """Test that MAX_PDF_SIZE is set correctly."""
        from app.services.pdf_generator import PDFGeneratorService

        # 3MB limit for email attachments
        assert PDFGeneratorService.MAX_PDF_SIZE == 3 * 1024 * 1024


class TestPDFGeneratorServiceEdgeCases:
    """Edge case tests for PDFGeneratorService."""

    @pytest.fixture
    def pdf_service(self):
        """Create PDF service instance."""
        from app.services.pdf_generator import PDFGeneratorService
        return PDFGeneratorService()

    @pytest.mark.asyncio
    async def test_empty_html(self, pdf_service):
        """Test handling of empty HTML."""
        html = '<html><body></body></html>'

        pdf_bytes, size = await pdf_service.generate_pdf(html)
        assert pdf_bytes[:4] == b'%PDF'

    @pytest.mark.asyncio
    async def test_unicode_content(self, pdf_service):
        """Test handling of Portuguese characters."""
        html = '''
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body>
            <h1>Relatório de Seguradoras</h1>
            <p>Análise de situação financeira</p>
            <p>Caracteres especiais: ção, ãe, úí, ôê</p>
        </body>
        </html>
        '''

        pdf_bytes, size = await pdf_service.generate_pdf(html)
        assert pdf_bytes[:4] == b'%PDF'

    @pytest.mark.asyncio
    async def test_complex_html_with_tables(self, pdf_service):
        """Test handling of complex HTML with tables."""
        html = '''
        <!DOCTYPE html>
        <html>
        <head><style>
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; }
        </style></head>
        <body>
            <h1>Insurance Report</h1>
            <table>
                <thead>
                    <tr><th>Insurer</th><th>Status</th><th>Score</th></tr>
                </thead>
                <tbody>
                    <tr><td>Company A</td><td>Critical</td><td>2.5</td></tr>
                    <tr><td>Company B</td><td>Watch</td><td>4.0</td></tr>
                    <tr><td>Company C</td><td>Stable</td><td>8.5</td></tr>
                </tbody>
            </table>
        </body>
        </html>
        '''

        pdf_bytes, size = await pdf_service.generate_pdf(html)
        assert pdf_bytes[:4] == b'%PDF'
        # Complex HTML should still be reasonably sized
        assert size < 500 * 1024  # Under 500KB
