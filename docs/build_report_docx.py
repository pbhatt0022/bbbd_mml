"""Build docs/report_draft.docx from docs/report_draft.md.

    python docs/build_report_docx.py            # from the repo root
    python docs/build_report_docx.py --check    # rebuild to a temp file and diff

Styles, page setup and the page-number footer come from docs/report_template.docx.
The template is the formatting contract: to change fonts, margins or the footer,
edit the template, not this script.

Document structure produced here, rather than in the Markdown:

    - the front-matter block becomes a centred title page of its own;
    - a table of contents follows it, built here through Word where Word is
      available and refreshed by Word on open in any case;
    - captions are rendered where the Markdown puts them, which is above each
      table and below each figure, following the usual convention;
    - table header rows are shaded, bold and repeated across page breaks, and
      no table row is allowed to split across a page.

Markdown supported is exactly what the report uses -- no more, deliberately:

    # x          Title              | a | b |        table
    ## x         Heading 1          ![alt](p)        inline image
    ### x        Heading 2          Figure/Table N.  Caption style
    everything else                 Normal, with **bold** and `code` runs

This writes no numbers of its own: it only moves text and images that already
exist in the Markdown and in docs/report_assets/.
"""
import argparse
import pathlib
import re
import sys

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = pathlib.Path(__file__).resolve().parent.parent
MD = ROOT / "docs/report_draft.md"
TEMPLATE = ROOT / "docs/report_template.docx"
OUT = ROOT / "docs/report_draft.docx"
ASSETS = ROOT / "docs"  # image paths in the Markdown are relative to docs/

IMAGE_WIDTH = Inches(6.0)
CODE_FONT = "Consolas"
HEADER_SHADE = "D9E2F3"
TEXT_WIDTH_IN = 6.5  # 8.5in page less two 1in margins

RE_IMAGE = re.compile(r"^!\[(?P<alt>[^\]]*)\]\((?P<path>[^)]+)\)\s*$")
RE_HEADING = re.compile(r"^(?P<hashes>#{1,3})\s+(?P<text>.+?)\s*$")
RE_CAPTION = re.compile(r"^(?P<kind>Figure|Table)\s+\d+\.\s")
RE_SEPARATOR = re.compile(r"^\|[\s|:-]+\|$")
# One pass over bold and code so neither can swallow the other.
RE_INLINE = re.compile(r"\*\*(?P<bold>[^*]+)\*\*|`(?P<code>[^`]+)`")


def split_row(line):
    """'| a | b |' -> ['a', 'b']."""
    return [c.strip() for c in line.strip().strip("|").split("|")]


def plain(text):
    """Markdown inline markup removed, for width estimation."""
    return RE_INLINE.sub(lambda m: m.group("bold") or m.group("code"), text)


def add_runs(paragraph, text):
    """Write text into a paragraph, honouring **bold** and `code`."""
    pos = 0
    for m in RE_INLINE.finditer(text):
        if m.start() > pos:
            paragraph.add_run(text[pos:m.start()])
        if m.group("bold") is not None:
            paragraph.add_run(m.group("bold")).bold = True
        else:
            run = paragraph.add_run(m.group("code"))
            run.font.name = CODE_FONT
            run.font.size = Pt(9.5)
        pos = m.end()
    if pos < len(text):
        paragraph.add_run(text[pos:])


def shade(cell, colour):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), colour)
    tc_pr.append(shd)


def add_image(doc, alt, rel_path):
    path = (ASSETS / rel_path).resolve()
    if not path.is_file():
        sys.exit(f"missing image referenced by the Markdown: {rel_path}")
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.keep_with_next = True
    paragraph.add_run().add_picture(str(path), width=IMAGE_WIDTH)
    shape = doc.inline_shapes[-1]
    # Alt text, so the caption and the image description cannot drift apart.
    shape._inline.docPr.set("descr", alt)
    shape._inline.docPr.set("name", f"Picture {len(doc.inline_shapes)}")
    shape._inline.graphic.graphicData.pic.nvPicPr.cNvPr.set("name", path.name)


CHAR_IN = 0.062   # rough width of one 9.5pt Cambria character, in inches


def column_widths(rows):
    """Share the text width between columns in proportion to their content.

    Each column is also given room for the longest single word in its header,
    so a header like "Difference" is never broken across lines.
    """
    n = len(rows[0])
    longest = [max(len(plain(row[c])) for row in rows) for c in range(n)]
    # Compress the range so one long column cannot starve the others.
    weights = [w ** 0.6 for w in longest]
    total = sum(weights)
    header_word = [max((len(w) for w in plain(rows[0][c]).split()), default=1)
                   for c in range(n)]
    floors = [max(0.55, (hw + 1.5) * CHAR_IN) / TEXT_WIDTH_IN for hw in header_word]
    shares = [max(w / total, f) for w, f in zip(weights, floors)]
    scale = sum(shares)
    return [Inches(TEXT_WIDTH_IN * s / scale) for s in shares]


def add_table(doc, rows):
    header, body = rows[0], rows[1:]
    table = doc.add_table(rows=len(rows), cols=len(header))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    widths = column_widths(rows)
    for col, width in enumerate(widths):
        for cell in table.columns[col].cells:
            cell.width = width

    for col, text in enumerate(header):
        cell = table.cell(0, col)
        add_runs(cell.paragraphs[0], f"**{text}**" if text else "")
        shade(cell, HEADER_SHADE)
    for r, row in enumerate(body, start=1):
        # Tolerate neither a short nor a long row: fail loudly instead.
        if len(row) != len(header):
            sys.exit(f"table row has {len(row)} cells, header has {len(header)}: {row}")
        for c, text in enumerate(row):
            add_runs(table.cell(r, c).paragraphs[0], text)

    for r, row in enumerate(table.rows):
        tr_pr = row._tr.get_or_add_trPr()
        cant_split = OxmlElement("w:cantSplit")       # keep a row on one page
        tr_pr.append(cant_split)
        if r == 0:
            header_mark = OxmlElement("w:tblHeader")  # repeat across pages
            tr_pr.append(header_mark)

    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                paragraph.paragraph_format.space_after = Pt(2)
                paragraph.paragraph_format.space_before = Pt(2)
                for run in paragraph.runs:
                    run.font.size = Pt(9.5)
    return table


def add_title_page(doc, lines):
    """The front-matter block, centred, on a page of its own."""
    doc.add_paragraph().paragraph_format.space_after = Pt(72)
    for line in lines:
        m = RE_HEADING.match(line)
        if m:
            # Only the document title is a real heading; the rest of the cover
            # is styled text, so it does not appear in the contents.
            if len(m.group("hashes")) == 1:
                p = doc.add_paragraph(style="Title")
                add_runs(p, m.group("text"))
            else:
                p = doc.add_paragraph()
                run = p.add_run(m.group("text"))
                run.bold = True
                run.font.size = Pt(13)
        else:
            p = doc.add_paragraph()
            add_runs(p, line)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = False
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def add_contents(doc):
    """A table-of-contents field, marked so Word refreshes it on open."""
    heading = doc.add_paragraph()
    heading.paragraph_format.space_before = Pt(0)
    heading.paragraph_format.space_after = Pt(10)
    run = heading.add_run("Contents")
    run.bold = True
    run.font.size = Pt(16)

    paragraph = doc.add_paragraph()
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    begin.set(qn("w:dirty"), "true")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = r'TOC \o "1-2" \h \z \u'
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    placeholder = OxmlElement("w:t")
    placeholder.text = "Right-click and choose Update Field to build the contents."
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for node in (begin, instr, separate, placeholder, end):
        run._r.append(node)

    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def build(md_text, out_path):
    if not TEMPLATE.is_file():
        sys.exit(f"missing {TEMPLATE.relative_to(ROOT)} -- it carries the styles")
    doc = docx.Document(str(TEMPLATE))

    lines = md_text.split("\n")
    counts = {"heading": 0, "paragraph": 0, "table": 0, "image": 0, "caption": 0}

    # Front matter is everything before the first numbered section heading.
    first_section = next(i for i, l in enumerate(lines)
                         if re.match(r"^##\s+\d", l))
    add_title_page(doc, [l.rstrip() for l in lines[:first_section] if l.strip()])
    add_contents(doc)

    i = first_section
    while i < len(lines):
        line = lines[i].rstrip()

        if not line.strip():
            i += 1
            continue

        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                if not RE_SEPARATOR.match(lines[i].strip()):
                    rows.append(split_row(lines[i]))
                i += 1
            add_table(doc, rows)
            doc.add_paragraph().paragraph_format.space_after = Pt(4)
            counts["table"] += 1
            continue

        m = RE_IMAGE.match(line)
        if m:
            add_image(doc, m.group("alt"), m.group("path"))
            counts["image"] += 1
            i += 1
            continue

        m = RE_HEADING.match(line)
        if m:
            style = {1: "Title", 2: "Heading 1", 3: "Heading 2"}[len(m.group("hashes"))]
            add_runs(doc.add_paragraph(style=style), m.group("text"))
            counts["heading"] += 1
            i += 1
            continue

        if RE_CAPTION.match(line):
            add_runs(doc.add_paragraph(style="Caption"), line)
            counts["caption"] += 1
            i += 1
            continue

        add_runs(doc.add_paragraph(style="Normal"), line)
        counts["paragraph"] += 1
        i += 1

    doc.save(str(out_path))
    update_fields(out_path)
    return counts


def update_fields(path):
    """Populate the contents field, using Word when it is available.

    The field is written with the dirty flag set, so Word refreshes it when the
    document is opened in any case. Doing it here as well means the saved file
    already carries a built table of contents, which matters if the reader
    never opens it in Word.
    """
    try:
        import win32com.client            # noqa: PLC0415 - optional dependency
    except ImportError:
        try:
            return _update_fields_powershell(path)
        except Exception as exc:          # noqa: BLE001 - reported, not fatal
            print(f"  note: contents field left for Word to refresh ({exc})")
            return False
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    document = word.Documents.Open(str(path), False, False)
    document.Fields.Update()
    document.Save()
    document.Close(True)
    word.Quit()
    return True


def _update_fields_powershell(path):
    import subprocess
    script = (
        "$w = New-Object -ComObject Word.Application; $w.Visible = $false; "
        f"$d = $w.Documents.Open('{path}', $false, $false); "
        "$null = $d.Fields.Update(); $d.Save(); $d.Close($true); $w.Quit()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script],
                   check=True, capture_output=True, timeout=180)
    return True


def content_signature(path):
    """The document's visible content, as a list of styled blocks.

    Byte comparison is no longer meaningful once Word has opened the file to
    build the contents field: Word rewrites several package parts each time it
    saves. What matters for staleness is whether the text, styles and tables
    still match the Markdown, so that is what this compares.
    """
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = docx.Document(str(path))
    blocks = []
    for child in document.element.body.iterchildren():
        tag = child.tag.split("}")[1]
        if tag == "p":
            paragraph = Paragraph(child, document)
            if paragraph.text.strip():
                blocks.append(f"[{paragraph.style.name}] {paragraph.text}")
        elif tag == "tbl":
            for row in Table(child, document).rows:
                blocks.append("[table] " + " | ".join(c.text for c in row.cells))
    images = len(document.inline_shapes)
    return blocks, images


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="build to a temp file and report what would change")
    args = ap.parse_args()

    md_text = MD.read_text(encoding="utf-8")
    target = OUT.with_suffix(".check.docx") if args.check else OUT
    counts = build(md_text, target)
    print(" ".join(f"{k}={v}" for k, v in counts.items()), "->", target.name)

    if args.check:
        if OUT.is_file():
            fresh, fresh_images = content_signature(target)
            saved, saved_images = content_signature(OUT)
            if fresh == saved and fresh_images == saved_images:
                print("content differs from the saved document in: nothing")
            else:
                import difflib
                diff = [l for l in difflib.unified_diff(saved, fresh, "saved",
                                                        "rebuilt", n=0, lineterm="")
                        if l[:1] in "+-" and l[:3] not in ("+++", "---")]
                print(f"content differs: {len(diff)} block(s), "
                      f"images {saved_images} -> {fresh_images}")
                for line in diff[:12]:
                    print("   ", line[:110])
        target.unlink()


if __name__ == "__main__":
    main()
