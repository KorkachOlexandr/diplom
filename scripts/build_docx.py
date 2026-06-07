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
TEMPLATE_DOCX = Path(__file__).resolve().parent / "template_makarenko.docx"


# ---------- low-level helpers ----------

def set_run_font(run, *, size_pt: float = 14, bold: bool = False, italic: bool = False,
                 color_hex: str = "000000"):
    """Apply Times New Roman font with explicit Eastern Asia and complex script
    fallbacks so Cyrillic and Latin characters both render in TNR. Default
    color is explicit black to override Heading style's theme accent color."""
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
    # explicit color overrides the Heading style's default theme accent color
    color = rPr.find(qn("w:color"))
    if color is None:
        color = OxmlElement("w:color")
        rPr.append(color)
    color.set(qn("w:val"), color_hex)
    # clear themeColor attribute if present
    if color.get(qn("w:themeColor")) is not None:
        del color.attrib[qn("w:themeColor")]


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


def _add_chunk_to_paragraph(p, kind, payload, *, bold: bool = False, italic: bool = False):
    """Render one (kind, payload) chunk into paragraph p."""
    if kind == "math":
        # Render LaTeX as inline OMML. Need a placeholder run to anchor
        # surrounding formatting; insert OMML element directly into the
        # paragraph after creating a non-empty run for layout stability.
        anchor = p.add_run()
        set_run_font(anchor, size_pt=14)
        add_omml_inline(anchor, payload)
        # Remove the empty anchor to avoid an extra blank run-cycle
        return

    if kind == "mono":
        # Methodics §3.1: TNR 14pt throughout. No mono fonts permitted.
        # Inline `code` markers render as normal TNR — only their lexical
        # form (the surrounding backticks were stripped by the parser)
        # distinguishes them from prose.
        run = p.add_run(payload)
        set_run_font(run, size_pt=14)
        return

    is_bold = bold or kind == "bold"
    is_italic = italic or kind == "italic"
    run = p.add_run(payload)
    set_run_font(run, size_pt=14, bold=is_bold, italic=is_italic)


def add_body_paragraph(doc, text: str, *, indent: bool = True,
                       bold: bool = False, italic: bool = False,
                       alignment=WD_ALIGN_PARAGRAPH.JUSTIFY):
    p = doc.add_paragraph()
    paragraph_setup(p, indent_first=indent, alignment=alignment)
    for kind, payload in _split_inline(text):
        _add_chunk_to_paragraph(p, kind, payload, bold=bold, italic=italic)
    return p


_INLINE_RE = re.compile(
    r"(\*\*(?P<bold>[^*]+)\*\*)|"
    r"(\*(?P<italic>[^*]+)\*)|"
    r"(`(?P<mono>[^`]+)`)|"
    r"(\$(?P<math>[^$]+)\$)"
)


def _split_inline(text: str):
    """Yield (kind, payload) tuples.

    kind ∈ {'text', 'bold', 'italic', 'mono', 'math'}
    payload is the inner text.
    """
    pos = 0
    for m in _INLINE_RE.finditer(text):
        if m.start() > pos:
            yield ("text", text[pos:m.start()])
        if m.group("bold") is not None:
            yield ("bold", m.group("bold"))
        elif m.group("italic") is not None:
            yield ("italic", m.group("italic"))
        elif m.group("mono") is not None:
            yield ("mono", m.group("mono"))
        elif m.group("math") is not None:
            yield ("math", m.group("math"))
        pos = m.end()
    if pos < len(text):
        yield ("text", text[pos:])


# ---------- LaTeX → OMML via pandoc ----------

import subprocess
import zipfile
import shutil
import tempfile

_OMML_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
_M = "{" + _OMML_NS + "}"

_math_cache: dict[str, "ET._Element"] = {}


def latex_to_omml(latex: str, *, display: bool = False) -> "ET._Element":
    """Convert a LaTeX math expression to a Word OMML element by piping
    through pandoc and extracting the <m:oMath> node from the resulting
    docx. Cached per expression so repeated formulas only pay the cost
    once per build."""
    import lxml.etree as ET

    key = ("D" if display else "I") + latex
    if key in _math_cache:
        return _math_cache[key]

    md = ("$$" + latex + "$$") if display else ("$" + latex + "$")
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "src.md"
        dst = Path(td) / "out.docx"
        src.write_text(md, encoding="utf-8")
        # OMML is pandoc's default math output for docx; do not pass --mathml.
        subprocess.run(
            ["pandoc", "-f", "markdown", "-t", "docx",
             "-o", str(dst), str(src)],
            check=True, capture_output=True,
        )
        with zipfile.ZipFile(dst) as z:
            doc_xml = z.read("word/document.xml")
        parser = ET.XMLParser(remove_blank_text=False)
        root = ET.fromstring(doc_xml, parser=parser)
        omath = root.find(f".//{_M}oMath")
        if omath is None:
            raise RuntimeError(f"pandoc produced no <m:oMath> for: {latex!r}")
        # Make a standalone deep copy
        cloned = ET.fromstring(ET.tostring(omath))
        _math_cache[key] = cloned
        return cloned


def _attach_omml(host_element, omath_element):
    """Attach an OMML element (as lxml) into a python-docx element tree
    (which uses python-docx's own oxml). We serialize and parse with
    python-docx's parser to keep namespaces consistent."""
    from docx.oxml import parse_xml
    import lxml.etree as ET
    xml_bytes = ET.tostring(omath_element)
    parsed = parse_xml(xml_bytes)
    host_element.append(parsed)


def add_omml_inline(run, latex: str):
    """Splice an inline OMML expression into the given run's parent paragraph
    immediately after the run."""
    omath = latex_to_omml(latex, display=False)
    from docx.oxml import parse_xml
    import lxml.etree as ET
    xml_bytes = ET.tostring(omath)
    parsed = parse_xml(xml_bytes)
    # Insert after the current run
    run._element.addnext(parsed)


def add_omml_display(paragraph, latex: str):
    """Append a display-style OMML expression to a paragraph."""
    omath = latex_to_omml(latex, display=True)
    from docx.oxml import parse_xml
    import lxml.etree as ET
    # display math is wrapped in oMathPara; if pandoc gave us oMath, wrap
    if not omath.tag.endswith("}oMathPara"):
        wrapper = ET.SubElement(ET.Element(f"{_M}oMathPara"), f"{_M}oMath")
        # Simpler: build inline
        wrapper = ET.fromstring(
            f'<m:oMathPara xmlns:m="{_OMML_NS}">{ET.tostring(omath).decode()}</m:oMathPara>'
        )
        xml_bytes = ET.tostring(wrapper)
    else:
        xml_bytes = ET.tostring(omath)
    parsed = parse_xml(xml_bytes)
    paragraph._element.append(parsed)


# Methodics §3.2 + §5 (page 37):
# «За міжрядкового інтервалу 1,5, щоб отримати вертикальний відступ не
#  менш ніж два інтервали, треба додати додатковий вертикальний проміжок
#  приблизно 8 пунктів.»
# A single "інтервал" is a fixed unit ~5 mm (defined on page 36); two of
# them = ~10 mm ≈ 28 pt total. The 1.5 baseline-to-baseline already
# contributes ~7.5 mm, so the extra space_after only needs to be ~8 pt.
HEADING_GAP_TWIPS = "160"  # 8 pt in twentieths


def _set_spacing(pPr, *, before: str | None = None, after: str | None = None,
                 line: str = "360", line_rule: str = "auto"):
    spacing = pPr.find(qn("w:spacing"))
    if spacing is None:
        spacing = OxmlElement("w:spacing")
        pPr.append(spacing)
    if before is not None:
        spacing.set(qn("w:before"), before)
    if after is not None:
        spacing.set(qn("w:after"), after)
    spacing.set(qn("w:line"), line)
    spacing.set(qn("w:lineRule"), line_rule)


def add_top_level_heading(doc, text: str, *, page_break: bool = True,
                          space_after_twips: str = HEADING_GAP_TWIPS):
    """Top-level heading mirroring the Makarenko template's pattern:
    Heading 1 style + per-paragraph pageBreakBefore + center align +
    firstLine 0; run-level TNR override. The default space_after of
    42 pt satisfies §3.2 «не менше двох міжрядкових інтервалів».
    Caller can override the gap (e.g. appendices use the body gap
    so «ДОДАТОК Х» sits one line above the appendix title)."""
    p = doc.add_paragraph(style=doc.styles["Heading 1"])
    pPr = p._element.get_or_add_pPr()
    if page_break and pPr.find(qn("w:pageBreakBefore")) is None:
        pPr.append(OxmlElement("w:pageBreakBefore"))
    ind = pPr.find(qn("w:ind"))
    if ind is None:
        ind = OxmlElement("w:ind")
        pPr.append(ind)
    ind.set(qn("w:firstLine"), "0")
    jc = pPr.find(qn("w:jc"))
    if jc is None:
        jc = OxmlElement("w:jc")
        pPr.append(jc)
    jc.set(qn("w:val"), "center")
    _set_spacing(pPr, before="0", after=space_after_twips)

    text = text.strip().rstrip(".").upper()
    run = p.add_run(text)
    set_run_font(run, size_pt=14, bold=True)
    return p


def add_appendix_title(doc, text: str):
    """Appendix title — centered, sentence case, bold, sits one body
    line below «ДОДАТОК Х». §3.2: gap between two consecutive headings
    equals body line spacing; gap between heading and body ≥ 2 intervals."""
    raw = text.strip().rstrip(".")
    p = doc.add_paragraph()
    pPr = p._element.get_or_add_pPr()
    ind = pPr.find(qn("w:ind"))
    if ind is None:
        ind = OxmlElement("w:ind")
        pPr.append(ind)
    ind.set(qn("w:firstLine"), "0")
    jc = pPr.find(qn("w:jc"))
    if jc is None:
        jc = OxmlElement("w:jc")
        pPr.append(jc)
    jc.set(qn("w:val"), "center")
    _set_spacing(pPr, before="0", after=HEADING_GAP_TWIPS)
    run = p.add_run(raw)
    set_run_font(run, size_pt=14, bold=True)
    return p


def add_subsection_heading(doc, text: str):
    """Subsection heading — Heading 2 style + paragraph indent + bold + TNR.
    Per §3.2 both leading and trailing gaps must be ≥ 2 intervals."""
    p = doc.add_paragraph(style=doc.styles["Heading 2"])
    pPr = p._element.get_or_add_pPr()
    pb = pPr.find(qn("w:pageBreakBefore"))
    if pb is not None:
        pPr.remove(pb)
    ind = pPr.find(qn("w:ind"))
    if ind is None:
        ind = OxmlElement("w:ind")
        pPr.append(ind)
    ind.set(qn("w:firstLine"), "720")
    jc = pPr.find(qn("w:jc"))
    if jc is None:
        jc = OxmlElement("w:jc")
        pPr.append(jc)
    jc.set(qn("w:val"), "left")
    _set_spacing(pPr, before=HEADING_GAP_TWIPS, after=HEADING_GAP_TWIPS)

    run = p.add_run(text.strip())
    set_run_font(run, size_pt=14, bold=True)
    return p


def setup_heading_styles(doc):
    """Configure Heading 1/2 to match the methodics, so Word's TOC field
    can pick them up. Keeping the standard style names is what makes
    `TOC \\o "1-2"` populate automatically."""

    def force_tnr_font(style):
        rPr = style.element.get_or_add_rPr()
        rFonts = rPr.find(qn("w:rFonts"))
        if rFonts is None:
            rFonts = OxmlElement("w:rFonts")
            rPr.append(rFonts)
        for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rFonts.set(qn(attr), "Times New Roman")
        # explicit black color, override of "auto" theme colors
        color = rPr.find(qn("w:color"))
        if color is None:
            color = OxmlElement("w:color")
            rPr.append(color)
        color.set(qn("w:val"), "000000")

    def set_page_break_before(pf_element, enable: bool):
        # WD page_break_before via OXML to ensure persistence on style.
        pPr = pf_element
        existing = pPr.find(qn("w:pageBreakBefore"))
        if enable:
            if existing is None:
                existing = OxmlElement("w:pageBreakBefore")
                pPr.append(existing)
        else:
            if existing is not None:
                pPr.remove(existing)

    h1 = doc.styles["Heading 1"]
    h1.font.name = "Times New Roman"
    h1.font.size = Pt(14)
    h1.font.bold = True
    h1.font.italic = False
    pf1 = h1.paragraph_format
    pf1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf1.first_line_indent = Cm(0)
    pf1.left_indent = Cm(0)
    pf1.right_indent = Cm(0)
    pf1.line_spacing = 1.5
    pf1.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf1.space_before = Pt(0)
    pf1.space_after = Pt(24)
    pf1.keep_with_next = True
    # page break before via OXML
    pPr1 = h1.element.find(qn("w:pPr"))
    if pPr1 is None:
        pPr1 = OxmlElement("w:pPr")
        h1.element.insert(0, pPr1)
    set_page_break_before(pPr1, True)
    force_tnr_font(h1)

    h2 = doc.styles["Heading 2"]
    h2.font.name = "Times New Roman"
    h2.font.size = Pt(14)
    h2.font.bold = True
    h2.font.italic = False
    pf2 = h2.paragraph_format
    pf2.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf2.first_line_indent = Cm(1.27)
    pf2.left_indent = Cm(0)
    pf2.line_spacing = 1.5
    pf2.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf2.space_before = Pt(18)
    pf2.space_after = Pt(18)
    pf2.keep_with_next = True
    pPr2 = h2.element.find(qn("w:pPr"))
    if pPr2 is None:
        pPr2 = OxmlElement("w:pPr")
        h2.element.insert(0, pPr2)
    set_page_break_before(pPr2, False)
    force_tnr_font(h2)


def add_field(paragraph, instruction: str, placeholder_text: str = ""):
    """Insert a Word field into the given paragraph.

    instruction is the field code (e.g. 'TOC \\o "1-2" \\h \\z \\u'
    or 'NUMPAGES \\* MERGEFORMAT'). Returns the run that contains the
    placeholder, so the caller can apply formatting to it."""
    run = paragraph.add_run()
    set_run_font(run, size_pt=14)

    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    # Force Word to refresh the field on open by setting dirty
    fld_begin.set(qn("w:dirty"), "true")

    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " " + instruction + " "

    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")

    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = placeholder_text

    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")

    r = run._element
    r.append(fld_begin)
    r.append(instr)
    r.append(fld_sep)
    r.append(t)
    r.append(fld_end)
    return run


def insert_toc_field(doc):
    """Insert a TOC field that will populate when Word opens the doc
    (the document's updateFields setting is true, see enable_field_update)."""
    p = doc.add_paragraph()
    paragraph_setup(p, indent_first=False, alignment=WD_ALIGN_PARAGRAPH.LEFT,
                    space_before=0, space_after=0, line_spacing=1.5)
    add_field(
        p,
        # \o "1-2"  — include heading levels 1..2
        # \h         — make entries into hyperlinks
        # \z         — hide tab-leader/page numbers in web layout (ignored in print)
        # \u         — use applied outline level
        r'TOC \o "1-2" \h \z \u',
        placeholder_text="Зміст буде створено автоматично при відкритті документа в Microsoft Word "
                         "(натисніть F9 або «Оновити поле» якщо не оновився).",
    )


def enable_field_update_on_open(doc):
    """Set <w:updateFields w:val="true"/> in settings so Word refreshes
    all fields (TOC, NUMPAGES) when the document is opened."""
    settings = doc.settings.element
    existing = settings.find(qn("w:updateFields"))
    if existing is None:
        existing = OxmlElement("w:updateFields")
        settings.append(existing)
    existing.set(qn("w:val"), "true")


def add_referat_volume_paragraph(doc, prefix: str, suffix: str):
    """Render the «Обсяг роботи — N сторінок ... » paragraph with N as a
    NUMPAGES field, so the page count is always live."""
    p = doc.add_paragraph()
    paragraph_setup(p, indent_first=True, alignment=WD_ALIGN_PARAGRAPH.JUSTIFY)

    r1 = p.add_run(prefix)
    set_run_font(r1, size_pt=14)

    add_field(p, "NUMPAGES \\* MERGEFORMAT", placeholder_text="56")

    r2 = p.add_run(suffix)
    set_run_font(r2, size_pt=14)
    return p


def add_list_item(doc, text: str, *, marker: str = "—", level: int = 0):
    """Single list item, hanging indent."""
    p = doc.add_paragraph()
    paragraph_setup(p, indent_first=True, alignment=WD_ALIGN_PARAGRAPH.JUSTIFY)
    p.paragraph_format.first_line_indent = Cm(1.27)
    body_text = f"{marker} {text}" if marker else text
    for kind, payload in _split_inline(body_text):
        _add_chunk_to_paragraph(p, kind, payload)
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
        set_run_font(run, size_pt=14, bold=True)
    # data rows
    for ri, row in enumerate(rows, start=1):
        for ci, cell_text in enumerate(row):
            cell = table.rows[ri].cells[ci]
            cell.text = ""
            p = cell.paragraphs[0]
            paragraph_setup(p, indent_first=False, alignment=WD_ALIGN_PARAGRAPH.LEFT,
                            space_before=0, space_after=0, line_spacing=1.0)
            for kind, payload in _split_inline(cell_text):
                if kind == "math":
                    anchor = p.add_run()
                    set_run_font(anchor, size_pt=14)
                    add_omml_inline(anchor, payload)
                else:
                    run = p.add_run(payload)
                    set_run_font(run, size_pt=14,
                                 bold=(kind == "bold"),
                                 italic=(kind == "italic"))


def add_formula(doc, body: str, number: str | None = None):
    """Centered OMML formula on its own line; right-aligned number in
    parentheses. Uses a 1×2 borderless table for layout."""
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
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
    grid_cells = table.rows[0].cells
    grid_cells[0].width = Cm(14)
    grid_cells[1].width = Cm(3)

    # formula cell: render the LaTeX as OMML
    fp = grid_cells[0].paragraphs[0]
    paragraph_setup(fp, indent_first=False, alignment=WD_ALIGN_PARAGRAPH.CENTER,
                    space_before=6, space_after=6, line_spacing=1.5)
    add_omml_display(fp, body)

    # number cell
    np_ = grid_cells[1].paragraphs[0]
    paragraph_setup(np_, indent_first=False, alignment=WD_ALIGN_PARAGRAPH.RIGHT,
                    space_before=6, space_after=6, line_spacing=1.5)
    if number:
        nrun = np_.add_run(f"({number})")
        set_run_font(nrun, size_pt=14)


# ---------- markdown parsing ----------

# Patterns
HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")
LIST_DASH_RE = re.compile(r"^—\s+(.*)$")  # «— …» body-style list items
LIST_HYPHEN_RE = re.compile(r"^-\s+(.+)$")  # «- …» plain markdown bullets
LIST_LETTER_RE = re.compile(r"^([а-яґ])\)\s+(.*)$")  # «а) … б) …»
TABLE_HEADER_RE = re.compile(r"^\|(.+)\|$")
TABLE_SEP_RE = re.compile(r"^\|(\s*[-:]+\s*\|)+$")
IMAGE_RE = re.compile(r"^!\[(.*?)\]\(([^)]+)\)$")
FORMULA_BLOCK_TAGGED_RE = re.compile(r"^\$\$(.+?)\\tag\{([^}]+)\}\$\$$")
FORMULA_BLOCK_PLAIN_RE = re.compile(r"^\$\$(.+?)\$\$$")
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

        m = FORMULA_BLOCK_TAGGED_RE.match(stripped)
        if m:
            flush_para()
            blocks.append({"kind": "formula", "body": m.group(1).strip(), "number": m.group(2)})
            i += 1
            continue
        m = FORMULA_BLOCK_PLAIN_RE.match(stripped)
        if m:
            flush_para()
            blocks.append({"kind": "formula", "body": m.group(1).strip(), "number": None})
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

        m = LIST_HYPHEN_RE.match(stripped)
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


def clear_body(doc):
    """Remove every paragraph and table from the template's body so the
    resulting document inherits ONLY styles, section properties, headers
    and footers — but starts with an empty content area."""
    body = doc.element.body
    sectPr = body.find(qn("w:sectPr"))
    # Remove every child of body except the final sectPr (which holds
    # margins / page size / header references).
    for child in list(body):
        if child is sectPr:
            continue
        body.remove(child)


def render(blocks):
    # Open the Makarenko template — inherit all styles, margins, headers,
    # footers, theme. We only clear the body content.
    doc = Document(str(TEMPLATE_DOCX))
    clear_body(doc)
    enable_field_update_on_open(doc)

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
                # Appendix: "ДОДАТОК Х" must sit on the same page as the
                # appendix title (next H1) per methodics §3.16. Render the
                # appendix header (with page break), then immediately the
                # appendix title as a centered subtitle WITHOUT page break,
                # consuming the next heading block.
                if APPENDIX_RE.match(text_upper):
                    # «ДОДАТОК Х» followed by the appendix title — two
                    # consecutive headings, gap = body line spacing (§3.2).
                    j = i + 1
                    while j < len(blocks) and blocks[j]["kind"] == "pagebreak":
                        j += 1
                    has_title = (j < len(blocks) and blocks[j]["kind"] == "heading"
                                 and blocks[j]["level"] == 1)
                    add_top_level_heading(
                        doc, text,
                        space_after_twips="0" if has_title else HEADING_GAP_TWIPS,
                    )
                    if has_title:
                        add_appendix_title(doc, blocks[j]["text"])
                        i = j + 1
                        continue
                    i += 1
                    continue

                # Top-level structural OR chapter heading
                add_top_level_heading(doc, text)

                # Special handling for ЗМІСТ: emit a TOC field and skip the
                # static body of section entries until the next H1 / pagebreak.
                if text_upper == "ЗМІСТ":
                    insert_toc_field(doc)
                    i += 1
                    while i < len(blocks):
                        nb = blocks[i]
                        if nb["kind"] == "heading" and nb["level"] == 1:
                            break
                        if nb["kind"] == "pagebreak":
                            # consume the page break that terminates the static TOC
                            i += 1
                            break
                        i += 1
                    continue
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
            # Intercept the referat volume sentence and substitute a live
            # NUMPAGES field for the hardcoded page count.
            m = re.match(r"^(Обсяг роботи\s+—\s+)(\d+)(\s+сторінок.*)$", text)
            if m:
                add_referat_volume_paragraph(doc, m.group(1), m.group(3))
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
            # Methodics §3.1: TNR 14pt, line spacing 1.5 throughout.
            # Code blocks render in the same font as body text. Visual
            # distinction is achieved through layout (no first-line indent,
            # left alignment, preserved line breaks), not font family.
            for code_line in b["lines"]:
                p = doc.add_paragraph()
                paragraph_setup(p, indent_first=False, alignment=WD_ALIGN_PARAGRAPH.LEFT)
                run = p.add_run(code_line if code_line else " ")
                set_run_font(run, size_pt=14)
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
        for kind, payload in _split_inline(text):
            run = p.add_run(payload)
            set_run_font(run, size_pt=size_pt,
                         bold=bold or kind == "bold",
                         italic=kind == "italic")

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
