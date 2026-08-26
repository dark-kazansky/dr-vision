"""
Dedicated DOCX generation module for converting parsed text with
markdown formatting into DOCX documents.

Supports per-page orientation detection: each page from the source
document gets its own DOCX section with landscape or portrait layout
based on content analysis (line lengths, table presence, column count).
"""

import re
from typing import List, Tuple

from docx import Document
from docx.shared import Pt, RGBColor, Inches, Mm
from docx.enum.section import WD_ORIENT


# Page separator pattern used by OCR agents and the parser
_PAGE_SEP_RE = re.compile(r'^--- Page \d+ ---$')

# Thresholds for landscape detection
_LONG_LINE_THRESHOLD = 100       # characters – lines longer than this hint at wide content
_LONG_LINE_RATIO = 0.30          # if ≥30 % of lines are "long", lean landscape
_TABLE_TAG_RE = re.compile(r'<table[\s>]|<tr[\s>]|<th[\s>]|<td[\s>]', re.IGNORECASE)
_PIPE_TABLE_RE = re.compile(r'^\|.*\|.*\|', re.MULTILINE)
_AVG_LINE_LANDSCAPE = 90         # average line length above this → landscape
_COLUMN_SEPARATOR_RE = re.compile(r'\t{2,}|\s{4,}')  # multiple tabs or 4+ spaces


class DocxGenerator:
    """Generates DOCX files from parsed text with markdown formatting."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        text: str,
        filename: str,
        model_id: str,
        pages: int,
        file_type: str,
        output_path: str,
    ) -> str:
        """
        Generate a DOCX file from parsed text.

        Each source page (delimited by ``--- Page N ---``) is placed in its
        own DOCX section whose orientation (portrait / landscape) is
        estimated from the text content.

        Args:
            text: The parsed/formatted text content (may contain markdown).
            filename: Original filename used as the document title.
            model_id: The OCR model identifier (shown in metadata).
            pages: Number of pages in the source document.
            file_type: Source file type (shown in metadata).
            output_path: Destination path for the generated .docx file.

        Returns:
            The output_path where the DOCX was saved.
        """
        doc = Document()

        # --- Title / metadata section (always portrait) -----------------
        self._set_section_orientation(doc.sections[-1], landscape=False)

        doc.add_heading(filename, level=1)
        doc.add_paragraph(f"Model: {model_id}")
        doc.add_paragraph(f"Pages: {pages}")
        doc.add_paragraph(f"File Type: {file_type}")
        doc.add_paragraph("")  # spacer

        # --- Split text into per-page chunks ----------------------------
        page_chunks = self._split_pages(text)

        for idx, chunk in enumerate(page_chunks):
            landscape = self._estimate_landscape(chunk)

            # Create a new section for each page (continuous from the
            # previous one).  The first chunk reuses the existing section
            # only when there is a single page; otherwise every chunk gets
            # its own section so orientation can vary.
            if idx == 0 and len(page_chunks) == 1:
                # Single-page document – reuse the title section
                section = doc.sections[-1]
            else:
                doc.add_section()
                section = doc.sections[-1]

            self._set_section_orientation(section, landscape=landscape)

            # Add a subtle page header
            if len(page_chunks) > 1:
                hdr = doc.add_heading(f"Page {idx + 1}", level=2)
                # Muted colour for the page header
                for run in hdr.runs:
                    run.font.color.rgb = RGBColor(120, 120, 120)

            self._render_lines(doc, chunk)

        doc.save(output_path)
        return output_path

    # ------------------------------------------------------------------
    # Page splitting
    # ------------------------------------------------------------------

    @staticmethod
    def _split_pages(text: str) -> List[str]:
        """Split *text* on ``--- Page N ---`` markers.

        Returns a list of page content strings.  If no markers are found
        the entire text is returned as a single page.
        """
        if not text:
            return [""]

        chunks: List[str] = []
        current_lines: List[str] = []

        for line in text.split('\n'):
            if _PAGE_SEP_RE.match(line.strip()):
                # Flush accumulated lines as a page
                if current_lines:
                    chunks.append('\n'.join(current_lines))
                    current_lines = []
            else:
                current_lines.append(line)

        # Flush remaining
        if current_lines:
            chunks.append('\n'.join(current_lines))

        return chunks if chunks else [""]

    # ------------------------------------------------------------------
    # Orientation estimation
    # ------------------------------------------------------------------

    @staticmethod
    def _estimate_landscape(page_text: str) -> bool:
        """Heuristically decide whether *page_text* is landscape.

        Signals that push toward **landscape**:
        * High ratio of long lines (> 100 chars).
        * Presence of HTML ``<table>`` tags or pipe-delimited markdown
          tables.
        * High average line length.
        * Lines with multiple column separators (tabs / wide spaces).

        Returns ``True`` for landscape, ``False`` for portrait.
        """
        if not page_text or not page_text.strip():
            return False

        lines = [ln for ln in page_text.split('\n') if ln.strip()]
        if not lines:
            return False

        score = 0  # positive → landscape, negative → portrait

        # 1. Long-line ratio
        long_count = sum(1 for ln in lines if len(ln) > _LONG_LINE_THRESHOLD)
        long_ratio = long_count / len(lines)
        if long_ratio >= _LONG_LINE_RATIO:
            score += 2

        # 2. HTML or markdown tables
        if _TABLE_TAG_RE.search(page_text):
            score += 3
        if _PIPE_TABLE_RE.search(page_text):
            score += 2

        # 3. Average line length
        avg_len = sum(len(ln) for ln in lines) / len(lines)
        if avg_len > _AVG_LINE_LANDSCAPE:
            score += 2

        # 4. Multi-column separators
        col_lines = sum(1 for ln in lines if _COLUMN_SEPARATOR_RE.search(ln))
        if col_lines / len(lines) > 0.20:
            score += 2

        return score >= 3

    # ------------------------------------------------------------------
    # Section orientation helper
    # ------------------------------------------------------------------

    @staticmethod
    def _set_section_orientation(section, *, landscape: bool) -> None:
        """Set *section* to landscape or portrait with A4 dimensions."""
        if landscape:
            section.orientation = WD_ORIENT.LANDSCAPE
            section.page_width = Mm(297)
            section.page_height = Mm(210)
        else:
            section.orientation = WD_ORIENT.PORTRAIT
            section.page_width = Mm(210)
            section.page_height = Mm(297)

        # Comfortable margins
        section.top_margin = Mm(20)
        section.bottom_margin = Mm(20)
        section.left_margin = Mm(25)
        section.right_margin = Mm(25)

    # ------------------------------------------------------------------
    # Content rendering (unchanged logic, extracted for reuse)
    # ------------------------------------------------------------------

    def _render_lines(self, doc: Document, text: str) -> None:
        """Render *text* into *doc* with markdown formatting."""
        lines = text.split('\n') if text else []
        for line in lines:
            stripped = line.strip()

            if not stripped:
                doc.add_paragraph("")
                continue

            if stripped.startswith('# '):
                doc.add_heading(stripped[2:].strip(), level=1)
            elif stripped.startswith('## '):
                doc.add_heading(stripped[3:].strip(), level=2)
            elif stripped.startswith('### '):
                doc.add_heading(stripped[4:].strip(), level=3)
            elif stripped.startswith('#### '):
                doc.add_heading(stripped[5:].strip(), level=4)
            elif stripped.startswith('- ') or stripped.startswith('* '):
                list_text = stripped[2:].strip()
                para = doc.add_paragraph(style='List Bullet')
                para.paragraph_format.left_indent = Pt(18)
                self._add_inline_formatting(para, list_text)
            elif re.match(r'^\d+\.\s', stripped):
                text_content = re.sub(r'^\d+\.\s', '', stripped)
                para = doc.add_paragraph(style='List Number')
                para.paragraph_format.left_indent = Pt(18)
                self._add_inline_formatting(para, text_content)
            elif stripped.startswith('> '):
                quote_text = stripped[2:].strip()
                para = doc.add_paragraph()
                para.paragraph_format.left_indent = Pt(36)
                para.paragraph_format.right_indent = Pt(36)
                self._add_inline_formatting(para, quote_text)
                for run in para.runs:
                    run.font.italic = True
                    run.font.color.rgb = RGBColor(96, 96, 96)
            elif stripped.startswith('---') or stripped.startswith('***'):
                para = doc.add_paragraph()
                para.paragraph_format.space_after = Pt(12)
            else:
                para = doc.add_paragraph()
                self._add_inline_formatting(para, stripped)

    @staticmethod
    def _add_inline_formatting(para, text: str) -> None:
        """Add text with inline markdown formatting to a paragraph."""
        patterns = [
            (r'\*\*(.+?)\*\*', 'bold'),
            (r'\*(.+?)\*', 'italic'),
            (r'`(.+?)`', 'code'),
            (r'\[(.+?)\]\((.+?)\)', 'link'),
        ]

        remaining_text = text
        while remaining_text:
            earliest_match = None
            earliest_pos = len(remaining_text)
            earliest_pattern = None

            for pattern, ptype in patterns:
                match = re.search(pattern, remaining_text)
                if match and match.start() < earliest_pos:
                    earliest_match = match
                    earliest_pos = match.start()
                    earliest_pattern = ptype

            if earliest_match:
                if earliest_pos > 0:
                    run = para.add_run(remaining_text[:earliest_pos])
                    run.font.size = Pt(11)

                if earliest_pattern == 'bold':
                    run = para.add_run(earliest_match.group(1))
                    run.bold = True
                    run.font.size = Pt(11)
                elif earliest_pattern == 'italic':
                    run = para.add_run(earliest_match.group(1))
                    run.italic = True
                    run.font.size = Pt(11)
                elif earliest_pattern == 'code':
                    run = para.add_run(earliest_match.group(1))
                    run.font.name = 'Courier New'
                    run.font.size = Pt(10)
                    run.font.color.rgb = RGBColor(220, 50, 47)
                elif earliest_pattern == 'link':
                    link_text = earliest_match.group(1)
                    link_url = earliest_match.group(2)
                    run = para.add_run(f"{link_text} ({link_url})")
                    run.font.color.rgb = RGBColor(0, 102, 204)
                    run.font.size = Pt(11)

                remaining_text = remaining_text[earliest_match.end():]
            else:
                run = para.add_run(remaining_text)
                run.font.size = Pt(11)
                break
