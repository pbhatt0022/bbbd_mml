"""Build docs/report_draft.docx from docs/report_draft.md.

The Word export used to be produced by an unsaved python-docx script, so every
Markdown edit had to be carried across by hand. This rebuilds it.

    python docs/build_report_docx.py            # from the repo root
    python docs/build_report_docx.py --check    # rebuild to a temp file and diff

Styles, page setup and the page-number footer come from docs/report_template.docx,
which is the 13 November document with its body stripped. The template is the
formatting contract: to change fonts, margins or the footer, edit the template in
Word, not this script.

Markdown supported is exactly what the report uses -- no more, deliberately:

    # x          Title              | a | b |     Table Grid, bold header row
    ## x         Heading 1          ![alt](p)     inline image, 6.75in wide
    ### x        Heading 2          Figure N. x   Caption style
    everything else                 Normal, with **bold** and `code` runs

This writes no numbers of its own: it only moves text and images that already
exist in the Markdown and in docs/report_assets/.
"""
import argparse
import pathlib
import re
import sys
import zipfile

import docx
from docx.shared import Inches, Pt

ROOT = pathlib.Path(__file__).resolve().parent.parent
MD = ROOT / "docs/report_draft.md"
TEMPLATE = ROOT / "docs/report_template.docx"
OUT = ROOT / "docs/report_draft.docx"
ASSETS = ROOT / "docs"  # image paths in the Markdown are relative to docs/

IMAGE_WIDTH = Inches(6.75)  # what the 13 Nov document used
CODE_FONT = "Consolas"

RE_IMAGE = re.compile(r"^!\[(?P<alt>[^\]]*)\]\((?P<path>[^)]+)\)\s*$")
RE_HEADING = re.compile(r"^(?P<hashes>#{1,3})\s+(?P<text>.+?)\s*$")
RE_CAPTION = re.compile(r"^Figure\s+\d+\.\s")
RE_SEPARATOR = re.compile(r"^\|[\s|:-]+\|$")
# One pass over bold and code so neither can swallow the other.
RE_INLINE = re.compile(r"\*\*(?P<bold>[^*]+)\*\*|`(?P<code>[^`]+)`")


def split_row(line):
    """'| a | b |' -> ['a', 'b']."""
    return [c.strip() for c in line.strip().strip("|").split("|")]


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
            run.font.size = Pt(10)
        pos = m.end()
    if pos < len(text):
        paragraph.add_run(text[pos:])


def add_image(doc, alt, rel_path):
    path = (ASSETS / rel_path).resolve()
    if not path.is_file():
        sys.exit(f"missing image referenced by the Markdown: {rel_path}")
    doc.add_picture(str(path), width=IMAGE_WIDTH)
    shape = doc.inline_shapes[-1]
    # Alt text, so the caption and the image description cannot drift apart.
    shape._inline.docPr.set("descr", alt)
    shape._inline.docPr.set("name", f"Picture {len(doc.inline_shapes)}")
    shape._inline.graphic.graphicData.pic.nvPicPr.cNvPr.set("name", path.name)


def add_table(doc, rows):
    header, body = rows[0], rows[1:]
    table = doc.add_table(rows=len(rows), cols=len(header))
    table.style = "Table Grid"
    for col, text in enumerate(header):
        add_runs(table.cell(0, col).paragraphs[0], f"**{text}**" if text else "")
    for r, row in enumerate(body, start=1):
        # Tolerate a short or long row rather than silently dropping cells.
        if len(row) != len(header):
            sys.exit(f"table row has {len(row)} cells, header has {len(header)}: {row}")
        for c, text in enumerate(row):
            add_runs(table.cell(r, c).paragraphs[0], text)


def build(md_text, out_path):
    if not TEMPLATE.is_file():
        sys.exit(f"missing {TEMPLATE.relative_to(ROOT)} -- it carries the styles")
    doc = docx.Document(str(TEMPLATE))

    lines = md_text.split("\n")
    i = 0
    counts = {"heading": 0, "paragraph": 0, "table": 0, "image": 0, "caption": 0}
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
            doc.add_paragraph()  # the 13 Nov document spaced tables this way
            counts["table"] += 1
            continue

        m = RE_IMAGE.match(line)
        if m:
            add_image(doc, m.group("alt"), m.group("path"))
            doc.add_paragraph()
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

        style = "Caption" if RE_CAPTION.match(line) else "Normal"
        add_runs(doc.add_paragraph(style=style), line)
        counts["caption" if style == "Caption" else "paragraph"] += 1
        i += 1

    doc.save(str(out_path))
    return counts


def parts(path):
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist() if not n.endswith("/")}


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
            new, old = parts(target), parts(OUT)
            changed = sorted(k for k in new.keys() | old.keys()
                             if new.get(k) != old.get(k))
            print("differs in:", ", ".join(changed) if changed else "nothing")
        target.unlink()


if __name__ == "__main__":
    main()
