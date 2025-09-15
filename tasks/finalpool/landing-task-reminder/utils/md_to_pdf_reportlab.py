#!/usr/bin/env python3
"""
Convert a simple Markdown file (headings + bullets + paragraphs) to PDF using ReportLab.
Designed for the landing_tips.md structure (Chinese-safe via STSong-Light).

Usage:
  python md_to_pdf_reportlab.py <input_md> [output_pdf]
"""
import sys
from pathlib import Path

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
except Exception as e:
    print("ERROR: ReportLab is required to run this script.")
    print("Import error:", repr(e))
    sys.exit(1)


def build_styles():
    # Register a CJK font for Chinese support (Acrobat built-in font)
    font_name = 'STSong-Light'
    try:
        pdfmetrics.registerFont(UnicodeCIDFont(font_name))
    except Exception as e:
        print("WARN: Failed to register STSong-Light:", e)
        print("The PDF may not render Chinese characters correctly.")
        font_name = 'Helvetica'

    ss = getSampleStyleSheet()
    # Clone and adjust styles to use the CJK-capable font
    styles = {
        'Title': ParagraphStyle('Title', parent=ss['Title'], fontName=font_name, fontSize=20, leading=24, spaceAfter=12),
        'Heading2': ParagraphStyle('Heading2', parent=ss['Heading2'], fontName=font_name, fontSize=14, leading=18, spaceBefore=12, spaceAfter=6),
        'BodyText': ParagraphStyle('BodyText', parent=ss['BodyText'], fontName=font_name, fontSize=11, leading=16, spaceAfter=4),
        'Bullet': ParagraphStyle('Bullet', parent=ss['BodyText'], fontName=font_name, fontSize=11, leading=16),
    }
    return styles


def parse_markdown(md_text):
    """Very lightweight parser for the specific structure we use.
    Supports:
        - # Title
        - ## Heading
        - - Bullet lines
        - Paragraph lines
        - Blank lines for spacing
    Returns a list of flowables.
    """
    styles = build_styles()
    flow = []

    lines = md_text.splitlines()
    bullet_buf = []  # accumulate bullet lines
    title_set = False

    def flush_bullets():
        nonlocal bullet_buf
        if not bullet_buf:
            return
        items = [ListItem(Paragraph(text, styles['Bullet']), leftIndent=0) for text in bullet_buf]
        flow.append(ListFlowable(items, bulletType='bullet', start=None, leftIndent=18))
        flow.append(Spacer(1, 6))
        bullet_buf = []

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            flush_bullets()
            flow.append(Spacer(1, 6))
            continue

        if line.startswith('# '):
            flush_bullets()
            # Only the first '# ' is treated as Title; others as Heading2
            text = line[2:].strip()
            if not title_set:
                flow.append(Paragraph(text, styles['Title']))
                title_set = True
            else:
                flow.append(Paragraph(text, styles['Heading2']))
            continue

        if line.startswith('## '):
            flush_bullets()
            flow.append(Paragraph(line[3:].strip(), styles['Heading2']))
            continue

        if line.lstrip().startswith('- '):
            bullet_text = line.lstrip()[2:].strip()
            bullet_buf.append(bullet_text)
            continue

        # Otherwise, paragraph line
        flush_bullets()
        flow.append(Paragraph(line, styles['BodyText']))

    flush_bullets()
    return flow


def md_to_pdf(md_path: Path, pdf_path: Path):
    content = md_path.read_text(encoding='utf-8')
    flow = parse_markdown(content)
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=50, rightMargin=50, topMargin=56, bottomMargin=56)
    doc.build(flow)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    md_path = Path(argv[1])
    if not md_path.exists():
        print(f"Input file not found: {md_path}")
        return 2
    if len(argv) >= 3:
        pdf_path = Path(argv[2])
    else:
        pdf_path = md_path.with_suffix('.pdf')

    md_to_pdf(md_path, pdf_path)
    print(f"Wrote PDF: {pdf_path}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))

