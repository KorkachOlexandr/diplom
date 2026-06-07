"""Convert thesis/diploma.md to a KNU FCSC methodics-compliant DOCX.

Rules captured from the methodics PDF (Karnaukh, Omelchuk, Stavrovskyi, 2025):
- A4 paper, margins: top/bottom 20mm, left 25mm, right 10mm
- Times New Roman, 14pt, line spacing 1.5
- Paragraph indent 1.27cm, justified
- Top-level headings (РЕФЕРАТ, ЗМІСТ, СКОРОЧЕННЯ, ВСТУП, "N CHAPTER",
  ВИСНОВКИ, ПЕРЕЛІК ДЖЕРЕЛ ПОСИЛАННЯ, ДОДАТОК A/Б/В): bold UPPERCASE,
  centered, no period at end, each on a new page
- Subsection headings (N.M): paragraph indent, bold, sentence case
- Page numbers top-right; title page is page 1 but no number printed
- Figures: caption «Рисунок N — Назва» centered below the image
- Tables: caption «Таблиця N — Назва» with paragraph indent above the table
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Cm, Mm, Pt, Emu


THESIS_MD = Path(__file__).resolve().parent.parent / "thesis" / "diploma.md"
THESIS_DOCX = Path(__file__).resolve().parent.parent / "thesis" / "diploma.docx"
FIGURES_DIR = Path(__file__).resolve().parent.parent / "thesis" / "figures"


# ---------- low-level helpers ----------

def set_run_font(run, *, size_pt: float = 14, bold: bool = False, italic: bool = False):
    """Apply Times New Roman font with explicit Eastern Asia and complex script
    fallbacks so Cyrillic and Latin characters both render in TNR."""
    run.font.name = "Times New Roman"
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rFonts.set(qn(attr), "Times New Roman")
    run.font.size = Pt(size_pt)
    run.bold = bold
    run.italic = italic


def setup_section(section, *, first_page: bool = False):
    """Margins and page number visibility."""
    section.page_height = Mm(297)
    section.page_width = Mm(210)
    section.top_margin = Mm(20)
    section.bottom_margin = Mm(20)
    section.left_margin = Mm(25)
    section.right_margin = Mm(10)
    section.header_distance = Mm(12)
    section.footer_distance = Mm(12)
    if first_page:
        section.different_first_page_header_footer = True


def add_page_number_field(paragraph):
    """Insert a {PAGE} field run into the given paragraph."""
    run = paragraph.add_run()
    set_run_font(run, size_pt=14)

    fldChar1 = OxmlElement("w:fldChar")
    fldChar1.set(qn("w:fldCharType"), "begin")
    instrText = OxmlElement("w:instrText")
    instrText.set(qn("xml:space"), "preserve")
    instrText.text = "PAGE"
    fldChar2 = OxmlElement("w:fldChar")
    fldChar2.set(qn("w:fldCharType"), "end")

    r = run._element
    r.append(fldChar1)
    r.append(instrText)
    r.append(fldChar2)


def setup_headers(section):
    """Right-aligned page-number header on every page (first-page header empty)."""
    header = section.header
    # primary header on subsequent pages
    p = header.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    add_page_number_field(p)
    # blank first-page header (title page has no number)
    first = section.first_page_header
    fp = first.paragraphs[0]
    fp.text = ""


def paragraph_setup(p, *, indent_first: bool = True, alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
                   space_before: float = 0.0, space_after: float = 0.0,
                   line_spacing: float = 1.5):
    p.paragraph_format.first_line_indent = Cm(1.27) if indent_first else Cm(0)
    p.paragraph_format.left_indent = Cm(0)
    p.paragraph_format.right_indent = Cm(0)
    p.paragraph_format.alignment = alignment
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = line_spacing
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE


def add_body_paragraph(doc, text: str, *, indent: bool = True,
                       bold: bool = False, italic: bool = False,
                       alignment=WD_ALIGN_PARAGRAPH.JUSTIFY):
    p = doc.add_paragraph()
    paragraph_setup(p, indent_first=indent, alignment=alignment)
    # parse simple inline formatting: **bold**, *italic*, `code`
    for chunk_text, chunk_bold, chunk_italic, chunk_mono in _split_inline(text):
        run = p.add_run(chunk_text)
        if chunk_mono:
            run.font.name = "Courier New"
            rPr = run._element.get_or_add_rPr()
            rFonts = rPr.find(qn("w:rFonts"))
            if rFonts is None:
                rFonts = OxmlElement("w:rFonts")
                rPr.append(rFonts)
            for attr in ("w:ascii", "w:hAnsi", "w:cs"):
                rFonts.set(qn(attr), "Courier New")
            run.font.size = Pt(12)
        else:
            set_run_font(run, size_pt=14, bold=bold or chunk_bold, italic=italic or chunk_italic)
    return p


_INLINE_RE = re.compile(
    r"(\*\*(?P<bold>[^*]+)\*\*)|"
    r"(\*(?P<italic>[^*]+)\*)|"
    r"(`(?P<mono>[^`]+)`)"
)


def _split_inline(text: str):
    """Yield (text, bold, italic, mono) tuples."""
    pos = 0
    for m in _INLINE_RE.finditer(text):
        if m.start() > pos:
            yield (text[pos:m.start()], False, False, False)
        if m.group("bold") is not None:
            yield (m.group("bold"), True, False, False)
        elif m.group("italic") is not None:
            yield (m.group("italic"), False, True, False)
        elif m.group("mono") is not None:
            yield (m.group("mono"), False, False, True)
        pos = m.end()
    if pos < len(text):
        yield (text[pos:], False, False, False)


def add_top_level_heading(doc, text: str, *, page_break: bool = True):
    """Top-level heading: bold UPPERCASE centered, no period."""
    if page_break:
        # Insert an explicit page break paragraph
        para = doc.add_paragraph()
        r = para.add_run()
        br = OxmlElement("w:br")
        br.set(qn("w:type"), "page")
        r._element.append(br)
    p = doc.add_paragraph()
    paragraph_setup(p, indent_first=False, alignment=WD_ALIGN_PARAGRAPH.CENTER,
                    space_after=24)
    text = text.strip().rstrip(".").upper()
    run = p.add_run(text)
    set_run_font(run, size_pt=14, bold=True)
    return p


def add_subsection_heading(doc, text: str):
    """Subsection heading 'N.M Title': paragraph indent, bold, sentence case."""
    p = doc.add_paragraph()
    paragraph_setup(p, indent_first=True, alignment=WD_ALIGN_PARAGRAPH.LEFT,
                    space_before=18, space_after=18)
    run = p.add_run(text.strip())
    set_run_font(run, size_pt=14, bold=True)
    return p


def add_list_item(doc, text: str, *, marker: str = "—", level: int = 0):
    """Single list item, hanging indent."""
    p = doc.add_paragraph()
    paragraph_setup(p, indent_first=True, alignment=WD_ALIGN_PARAGRAPH.JUSTIFY)
    # hanging effect: first line normal indent, continuation flush left
    p.paragraph_format.first_line_indent = Cm(1.27)
    body_text = f"{marker} {text}" if marker else text
    for chunk_text, chunk_bold, chunk_italic, chunk_mono in _split_inline(body_text):
        run = p.add_run(chunk_text)
        if chunk_mono:
            run.font.name = "Courier New"
            run.font.size = Pt(12)
        else:
            set_run_font(run, size_pt=14, bold=chunk_bold, italic=chunk_italic)
    return p


def add_image(doc, image_path: Path, caption: str):
    """Centered image, then centered caption "Рисунок N — Назва" below."""
    pp = doc.add_paragraph()
    paragraph_setup(pp, indent_first=False, alignment=WD_ALIGN_PARAGRAPH.CENTER,
                    space_before=12, space_after=6)
    run = pp.add_run()
    if image_path.exists():
        # Width fit to ~16 cm to stay within page width minus margins
        run.add_picture(str(image_path), width=Cm(16))
    else:
        set_run_font(run, size_pt=14, italic=True)
        run.text = f"[відсутнє зображення: {image_path.name}]"

    cap = doc.add_paragraph()
    paragraph_setup(cap, indent_first=False, alignment=WD_ALIGN_PARAGRAPH.CENTER,
                    space_after=12)
    crun = cap.add_run(caption)
    set_run_font(crun, size_pt=14)


def add_table(doc, header: list[str], rows: list[list[str]], *, caption: str | None = None):
    if caption:
        cp = doc.add_paragraph()
        paragraph_setup(cp, indent_first=True, alignment=WD_ALIGN_PARAGRAPH.LEFT,
                        space_before=12, space_after=6)
        crun = cp.add_run(caption)
        set_run_font(crun, size_pt=14)

    table = doc.add_table(rows=1 + len(rows), cols=len(header))
    table.style = "Table Grid"
    table.autofit = True

    # header row
    for i, h in enumerate(header):
        cell = table.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        paragraph_setup(p, indent_first=False, alignment=WD_ALIGN_PARAGRAPH.CENTER,
                        space_before=0, space_after=0, line_spacing=1.0)
        run = p.add_run(h)
        set_run_font(run, size_pt=12, bold=True)
    # data rows
    for ri, row in enumerate(rows, start=1):
        for ci, cell_text in enumerate(row):
            cell = table.rows[ri].cells[ci]
            cell.text = ""
            p = cell.paragraphs[0]
            paragraph_setup(p, indent_first=False, alignment=WD_ALIGN_PARAGRAPH.LEFT,
                            space_before=0, space_after=0, line_spacing=1.0)
            for chunk_text, chunk_bold, chunk_italic, chunk_mono in _split_inline(cell_text):
                run = p.add_run(chunk_text)
                if chunk_mono:
                    run.font.name = "Courier New"
                    run.font.size = Pt(11)
                else:
                    set_run_font(run, size_pt=12, bold=chunk_bold, italic=chunk_italic)


def add_formula(doc, body: str, number: str | None = None):
    """Centered formula on its own line; optional right-aligned number in parentheses."""
    # Single tab approach: formula centered, then tab + number aligned right.
    # We use a 1-row 2-col borderless table for reliable layout.
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    # remove all borders
    tbl = table._element
    tblPr = tbl.find(qn("w:tblPr"))
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
        tbl.insert(0, tblPr)
    tblBorders = OxmlElement("w:tblBorders")
    for border_name in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement(f"w:{border_name}")
        b.set(qn("w:val"), "nil")
        tblBorders.append(b)
    tblPr.append(tblBorders)
    # widths
    grid_cells = table.rows[0].cells
    grid_cells[0].width = Cm(14)
    grid_cells[1].width = Cm(3)
    # formula cell
    fp = grid_cells[0].paragraphs[0]
    paragraph_setup(fp, indent_first=False, alignment=WD_ALIGN_PARAGRAPH.CENTER,
                    space_before=6, space_after=6, line_spacing=1.0)
    frun = fp.add_run(body)
    set_run_font(frun, size_pt=14, italic=True)
    # number cell
    np_ = grid_cells[1].paragraphs[0]
    paragraph_setup(np_, indent_first=False, alignment=WD_ALIGN_PARAGRAPH.RIGHT,
                    space_before=6, space_after=6, line_spacing=1.0)
    if number:
        nrun = np_.add_run(f"({number})")
        set_run_font(nrun, size_pt=14)


# ---------- markdown parsing ----------

# Patterns
HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")
LIST_DASH_RE = re.compile(r"^—\s+(.*)$")  # body-style list items
LIST_LETTER_RE = re.compile(r"^([а-яґ])\)\s+(.*)$")  # «а) … б) …»
TABLE_HEADER_RE = re.compile(r"^\|(.+)\|$")
TABLE_SEP_RE = re.compile(r"^\|(\s*[-:]+\s*\|)+$")
IMAGE_RE = re.compile(r"^!\[(.*?)\]\(([^)]+)\)$")
FORMULA_BLOCK_RE = re.compile(r"^\$\$(.+?)\\tag\{([^}]+)\}\$\$$")
NEWPAGE_RE = re.compile(r"^\\newpage$")
CODE_FENCE_RE = re.compile(r"^```")


def parse_markdown(md: str):
    """Return a list of structural blocks: dicts with 'kind' and content."""
    lines = md.split("\n")
    blocks = []
    i = 0
    in_code = False
    code_buf: list[str] = []
    para_buf: list[str] = []

    def flush_para():
        nonlocal para_buf
        if para_buf:
            text = " ".join(s.strip() for s in para_buf).strip()
            if text:
                blocks.append({"kind": "para", "text": text})
            para_buf = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if CODE_FENCE_RE.match(stripped):
            flush_para()
            if in_code:
                blocks.append({"kind": "code", "lines": code_buf})
                code_buf = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue

        if NEWPAGE_RE.match(stripped):
            flush_para()
            blocks.append({"kind": "pagebreak"})
            i += 1
            continue

        if not stripped:
            flush_para()
            i += 1
            continue

        m = HEADING_RE.match(stripped)
        if m:
            flush_para()
            level = len(m.group(1))
            title = m.group(2).strip()
            blocks.append({"kind": "heading", "level": level, "text": title})
            i += 1
            continue

        m = IMAGE_RE.match(stripped)
        if m:
            flush_para()
            blocks.append({"kind": "image", "caption": m.group(1), "path": m.group(2)})
            i += 1
            continue

        m = FORMULA_BLOCK_RE.match(stripped)
        if m:
            flush_para()
            blocks.append({"kind": "formula", "body": m.group(1).strip(), "number": m.group(2)})
            i += 1
            continue

        # Table detection
        if TABLE_HEADER_RE.match(stripped) and i + 1 < len(lines) and TABLE_SEP_RE.match(lines[i + 1].strip()):
            flush_para()
            header_cells = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and TABLE_HEADER_RE.match(lines[i].strip()):
                row_cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(row_cells)
                i += 1
            # check for preceding caption — we attach it during render
            blocks.append({"kind": "table", "header": header_cells, "rows": rows})
            continue

        m = LIST_DASH_RE.match(stripped)
        if m:
            flush_para()
            blocks.append({"kind": "list_dash", "text": m.group(1)})
            i += 1
            continue

        m = LIST_LETTER_RE.match(stripped)
        if m:
            flush_para()
            blocks.append({"kind": "list_letter", "letter": m.group(1), "text": m.group(2)})
            i += 1
            continue

        para_buf.append(line)
        i += 1

    flush_para()
    return blocks


# ---------- top-level rendering ----------

# Strings recognized as top-level structural headings (h1 in markdown) that
# should be CENTERED UPPERCASE on a new page.
STRUCTURAL_HEADINGS = {
    "РЕФЕРАТ", "ЗМІСТ", "СКОРОЧЕННЯ ТА УМОВНІ ПОЗНАКИ", "ВСТУП",
    "ВИСНОВКИ", "ПЕРЕЛІК ДЖЕРЕЛ ПОСИЛАННЯ",
}

# Chapter heading pattern: "1 NAME", "2 NAME", ...
CHAPTER_RE = re.compile(r"^\d+\s+[А-ЯЇІЄҐ\s']+$")
APPENDIX_RE = re.compile(r"^ДОДАТОК [А-ЯҐЇЄ]$")


def render(blocks):
    doc = Document()
    setup_section(doc.sections[0], first_page=True)
    setup_headers(doc.sections[0])

    # default style
    style = doc.styles["Normal"]
    set_run_font_style(style)

    # state: title-page rendering flag
    in_title_page = True
    pending_table_caption: str | None = None

    i = 0
    while i < len(blocks):
        b = blocks[i]

        if b["kind"] == "heading":
            text = b["text"].strip()
            level = b["level"]

            if in_title_page and text == "Титульний аркуш":
                render_title_page(doc, blocks, i + 1)
                # skip until pagebreak
                while i < len(blocks) and blocks[i]["kind"] != "pagebreak":
                    i += 1
                in_title_page = False
                # skip the pagebreak itself
                if i < len(blocks) and blocks[i]["kind"] == "pagebreak":
                    i += 1
                continue

            text_upper = text.upper()
            if level == 1:
                # Top-level structural OR chapter OR appendix
                if text_upper in STRUCTURAL_HEADINGS or CHAPTER_RE.match(text) or APPENDIX_RE.match(text_upper):
                    add_top_level_heading(doc, text)
                else:
                    add_top_level_heading(doc, text)
            else:
                add_subsection_heading(doc, text)
            i += 1
            continue

        if b["kind"] == "pagebreak":
            # page break inserted automatically by next top-level heading; skip
            i += 1
            continue

        if b["kind"] == "para":
            text = b["text"]
            # Detect "Таблиця N — caption" preceding a table: attach as caption
            if text.startswith("Таблиця "):
                pending_table_caption = text
                i += 1
                continue
            add_body_paragraph(doc, text)
            i += 1
            continue

        if b["kind"] == "list_dash":
            add_list_item(doc, b["text"], marker="—")
            i += 1
            continue

        if b["kind"] == "list_letter":
            add_list_item(doc, b["text"], marker=f"{b['letter']})")
            i += 1
            continue

        if b["kind"] == "image":
            path = FIGURES_DIR.parent / b["path"] if not Path(b["path"]).is_absolute() else Path(b["path"])
            add_image(doc, path, b["caption"])
            i += 1
            continue

        if b["kind"] == "table":
            add_table(doc, b["header"], b["rows"], caption=pending_table_caption)
            pending_table_caption = None
            i += 1
            continue

        if b["kind"] == "formula":
            add_formula(doc, b["body"], b["number"])
            i += 1
            continue

        if b["kind"] == "code":
            for code_line in b["lines"]:
                p = doc.add_paragraph()
                paragraph_setup(p, indent_first=False, alignment=WD_ALIGN_PARAGRAPH.LEFT,
                                line_spacing=1.0)
                run = p.add_run(code_line if code_line else " ")
                run.font.name = "Courier New"
                run.font.size = Pt(11)
            i += 1
            continue

        i += 1

    return doc


def set_run_font_style(style):
    """Configure the Normal style so subsequent paragraphs inherit TNR 14."""
    style.font.name = "Times New Roman"
    style.font.size = Pt(14)
    rPr = style.element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rFonts.set(qn(attr), "Times New Roman")


def render_title_page(doc, blocks, start_idx):
    """Render the title page. Uses paragraphs taken from blocks[start_idx:].

    Methodics requires the title page to be one full page. The samples in
    Annex A use centered text without paragraph indents.
    """
    # collect paragraphs until pagebreak
    i = start_idx
    items = []
    while i < len(blocks) and blocks[i]["kind"] != "pagebreak":
        if blocks[i]["kind"] == "para":
            items.append(blocks[i]["text"])
        i += 1

    centered_lines = items  # treat each block as a centered line

    # The first paragraph in the document is empty by default — use it
    first_para = doc.paragraphs[0] if doc.paragraphs else doc.add_paragraph()

    def add_centered(text, *, bold=False, size_pt=14, space_before=0, space_after=0):
        p = first_para if not first_para.text and not centered_added else doc.add_paragraph()
        # We need to track if first_para has been used
        if not centered_added[0]:
            p = first_para
            centered_added[0] = True
        else:
            p = doc.add_paragraph()
        paragraph_setup(p, indent_first=False, alignment=WD_ALIGN_PARAGRAPH.CENTER,
                        space_before=space_before, space_after=space_after, line_spacing=1.5)
        for chunk_text, chunk_bold, chunk_italic, chunk_mono in _split_inline(text):
            run = p.add_run(chunk_text)
            set_run_font(run, size_pt=size_pt, bold=bold or chunk_bold, italic=chunk_italic)

    centered_added = [False]

    for ln in centered_lines:
        # Heuristic: ALL CAPS topic line gets bold
        is_topic = ln.startswith("**") and ln.endswith("**")
        is_uppercase_title = ln.isupper() and len(ln) > 30
        clean = ln.strip("*")
        add_centered(clean, bold=is_topic or is_uppercase_title)


def main():
    md = THESIS_MD.read_text(encoding="utf-8")
    # Unescape backslash-escaped underscores (markdown escape for emphasis)
    # so signature blanks render as solid underlines.
    md = md.replace(r"\_", "_")
    blocks = parse_markdown(md)
    doc = render(blocks)
    doc.save(str(THESIS_DOCX))
    print(f"wrote {THESIS_DOCX}")


if __name__ == "__main__":
    main()
