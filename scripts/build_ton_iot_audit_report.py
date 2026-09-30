"""Render the short Markdown audit report as a two-page PDF."""
import re
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "research/ton_iot_audit"


def inline(text):
    text = escape(text)
    return re.sub(r"`([^`]+)`", r'<font name="Courier" size="8">\1</font>', text)


def main():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("ReportBody", fontName="Helvetica", fontSize=9.6,
                              leading=13.1, spaceAfter=7, alignment=TA_JUSTIFY))
    styles["Title"].fontName = "Helvetica-Bold"
    styles["Title"].fontSize = 16
    styles["Title"].leading = 20
    styles["Title"].spaceAfter = 9
    styles["Heading2"].fontSize = 11
    styles["Heading2"].leading = 14
    styles["Heading2"].spaceBefore = 9
    styles["Heading2"].spaceAfter = 6
    story = []
    for block in (DIRECTORY / "report.md").read_text(encoding="utf-8").strip().split("\n\n"):
        if block == "<!-- pagebreak -->":
            story.append(PageBreak())
        elif block.startswith("# "):
            story.append(Paragraph(inline(block[2:]), styles["Title"]))
        elif block.startswith("## "):
            story.append(Paragraph(inline(block[3:]), styles["Heading2"]))
        elif block.startswith("|"):
            rows = [[cell.strip() for cell in line.strip("|").split("|")]
                    for line in block.splitlines() if not re.match(r"^\|[-:| ]+\|$", line)]
            table = Table(rows, colWidths=[75 * mm, 31 * mm, 32 * mm, 25 * mm], repeatRows=1)
            table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8edf0")),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.grey),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
            story.extend([table, Spacer(1, 8)])
        else:
            story.append(Paragraph(inline(" ".join(block.splitlines())), styles["ReportBody"]))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(22 * mm, 13 * mm, "TON_IoT - Audit delle partizioni")
        canvas.drawRightString(188 * mm, 13 * mm, str(document.page))
        canvas.restoreState()

    document = SimpleDocTemplate(str(DIRECTORY / "report.pdf"), pagesize=(210 * mm, 297 * mm),
        rightMargin=22 * mm, leftMargin=22 * mm, topMargin=17 * mm, bottomMargin=20 * mm,
        title="TON_IoT: audit dei duplicati e delle sovrapposizioni", author="Samuele Marchitelli")
    document.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    main()
