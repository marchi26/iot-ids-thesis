from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "thesis" / "final_thesis.md"
OUTPUT = ROOT / "thesis" / "final_thesis.docx"
THESIS_TITLE = "Sicurezza nei sistemi Internet of Things: architetture, vulnerabilità e strategie di mitigazione"
COURSE = "INGEGNERIA INFORMATICA E DELL'AUTOMAZIONE (DM 1648/23)"
STUDENT = "Samuele Marchitelli"
MATRICOLA = "001814763"
SUPERVISOR = "Prof. Oleksandr Kuznetsov"
ACADEMIC_YEAR = "2025/2026"
IMAGE_WIDTH_EMU = 5_900_000


class DocxBuildState:
    def __init__(self) -> None:
        self.images: list[tuple[str, Path]] = []

    def add_image(self, image_path: Path) -> tuple[str, int]:
        relationship_id = f"rIdImage{len(self.images) + 1}"
        self.images.append((relationship_id, image_path))
        return relationship_id, len(self.images)


def text_runs(text: str, bold: bool = False, size: int | None = None) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = text.replace("**", "")
    parts = text.split("\n")
    runs = []
    rpr_parts = ['<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>']
    if bold:
        rpr_parts.append("<w:b/>")
    if size:
        rpr_parts.append(f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>')
    rpr = "<w:rPr>" + "".join(rpr_parts) + "</w:rPr>"
    for index, part in enumerate(parts):
        if index:
            runs.append("<w:br/>")
        runs.append(f"<w:r>{rpr}<w:t xml:space=\"preserve\">{escape(part)}</w:t></w:r>")
    return "".join(runs)


def paragraph(text: str, style: str | None = None) -> str:
    style_xml = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f"<w:p>{style_xml}{text_runs(text)}</w:p>"


def caption(text: str) -> str:
    return (
        "<w:p>"
        '<w:pPr><w:jc w:val="center"/><w:spacing w:after="220"/></w:pPr>'
        f"{text_runs(text, size=20)}"
        "</w:p>"
    )


def centered(text: str, bold: bool = False, size: int | None = None, after: int = 180) -> str:
    return (
        "<w:p>"
        f'<w:pPr><w:jc w:val="center"/><w:spacing w:after="{after}"/></w:pPr>'
        f"{text_runs(text, bold=bold, size=size)}"
        "</w:p>"
    )


def page_break() -> str:
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


def spacer(lines: int = 1) -> str:
    return "".join("<w:p/>" for _ in range(lines))


def cover_page() -> str:
    return (
        spacer(2)
        + centered("UNIVERSITÀ TELEMATICA e-Campus", bold=True, size=32, after=220)
        + centered("Corso di Laurea in", size=26, after=80)
        + centered(COURSE, bold=True, size=26, after=420)
        + spacer(2)
        + centered("Tesi di Laurea", bold=True, size=30, after=260)
        + centered(THESIS_TITLE, bold=True, size=34, after=520)
        + spacer(4)
        + paragraph(f"Relatore: {SUPERVISOR}", "CoverLeft")
        + paragraph(f"Candidato: {STUDENT}", "CoverRight")
        + paragraph(f"Matricola: {MATRICOLA}", "CoverRight")
        + spacer(4)
        + centered(f"Anno Accademico {ACADEMIC_YEAR}", size=24, after=0)
        + page_break()
    )


def table_of_contents() -> str:
    items = [
        "Abstract",
        "Capitolo 1 - Introduzione",
        "Capitolo 2 - Stato dell'arte",
        "Capitolo 3 - Metodologia",
        "Capitolo 4 - Risultati sperimentali",
        "Capitolo 5 - Discussione e strategie di mitigazione",
        "Capitolo 6 - Conclusioni",
        "Bibliografia",
    ]
    body = paragraph("Indice", "Heading1")
    for item in items:
        body += paragraph(item, "TocEntry")
    return body + page_break()


def bullet(text: str) -> str:
    return (
        "<w:p>"
        '<w:pPr><w:pStyle w:val="ListParagraph"/><w:numPr>'
        '<w:ilvl w:val="0"/><w:numId w:val="1"/>'
        "</w:numPr></w:pPr>"
        f"{text_runs(text)}"
        "</w:p>"
    )


def image_element(path_text: str, alt_text: str, state: DocxBuildState) -> str:
    image_path = (ROOT / path_text).resolve()
    if not image_path.exists():
        return paragraph(f"[Figura non trovata: {path_text}]")
    relationship_id, image_id = state.add_image(image_path)
    cx = IMAGE_WIDTH_EMU
    cy = 3_300_000
    try:
        from PIL import Image

        with Image.open(image_path) as image:
            width, height = image.size
        cy = int(cx * (height / width))
    except Exception:
        pass
    name = escape(image_path.name)
    alt = escape(alt_text)
    return f"""
<w:p>
  <w:pPr><w:jc w:val="center"/><w:spacing w:before="160" w:after="80"/></w:pPr>
  <w:r>
    <w:drawing>
      <wp:inline distT="0" distB="0" distL="0" distR="0">
        <wp:extent cx="{cx}" cy="{cy}"/>
        <wp:docPr id="{image_id}" name="{name}" descr="{alt}"/>
        <wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>
        <a:graphic>
          <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
            <pic:pic>
              <pic:nvPicPr>
                <pic:cNvPr id="{image_id}" name="{name}"/>
                <pic:cNvPicPr/>
              </pic:nvPicPr>
              <pic:blipFill>
                <a:blip r:embed="{relationship_id}"/>
                <a:stretch><a:fillRect/></a:stretch>
              </pic:blipFill>
              <pic:spPr>
                <a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
                <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
              </pic:spPr>
            </pic:pic>
          </a:graphicData>
        </a:graphic>
      </wp:inline>
    </w:drawing>
  </w:r>
</w:p>
{caption(alt_text)}
"""


def table_row(cells: list[str], header: bool = False) -> str:
    cell_xml = []
    for cell in cells:
        shading = '<w:shd w:fill="D9EAF7"/>' if header else ""
        bold_start = "<w:b/>" if header else ""
        cell_xml.append(
            "<w:tc>"
            f"<w:tcPr>{shading}</w:tcPr>"
            "<w:p><w:r>"
            f"{bold_start}<w:t xml:space=\"preserve\">{escape(cell.strip())}</w:t>"
            "</w:r></w:p>"
            "</w:tc>"
        )
    return "<w:tr>" + "".join(cell_xml) + "</w:tr>"


def table(rows: list[list[str]]) -> str:
    body = [
        '<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/>'
        '<w:tblW w:w="0" w:type="auto"/>'
        '<w:tblLook w:firstRow="1" w:lastRow="0" w:firstColumn="0" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>'
        "</w:tblPr>"
    ]
    for index, row in enumerate(rows):
        body.append(table_row(row, header=index == 0))
    body.append("</w:tbl>")
    return "".join(body)


def split_table_line(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_table_separator(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and set(stripped.replace("|", "").replace(":", "").replace("-", "").strip()) == set()


def markdown_to_body(markdown: str, state: DocxBuildState) -> str:
    lines = markdown.splitlines()
    elements: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line:
            i += 1
            continue

        if line.startswith("# "):
            elements.append(paragraph(line[2:].strip(), "Title"))
            i += 1
            continue
        if line.startswith("## "):
            elements.append(paragraph(line[3:].strip(), "Heading1"))
            i += 1
            continue
        if line.startswith("### "):
            elements.append(paragraph(line[4:].strip(), "Heading2"))
            i += 1
            continue

        if line.startswith("- "):
            elements.append(bullet(line[2:].strip()))
            i += 1
            continue

        image_match = re.match(r"!\[(.*?)\]\((.*?)\)", line)
        if image_match:
            elements.append(image_element(image_match.group(2), image_match.group(1), state))
            i += 1
            continue

        if line.startswith("|") and i + 1 < len(lines) and is_table_separator(lines[i + 1]):
            rows = [split_table_line(line)]
            i += 2
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(split_table_line(lines[i]))
                i += 1
            elements.append(table(rows))
            continue

        paragraph_lines = [line]
        i += 1
        while i < len(lines):
            next_line = lines[i].rstrip()
            if (
                not next_line
                or next_line.startswith("#")
                or next_line.startswith("- ")
                or next_line.startswith("|")
            ):
                break
            paragraph_lines.append(next_line)
            i += 1
        elements.append(paragraph(" ".join(paragraph_lines)))

    return "".join(elements)


def content_types() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""


def rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""


def document_rels(state: DocxBuildState) -> str:
    image_rels = []
    for relationship_id, image_path in state.images:
        image_rels.append(
            f'<Relationship Id="{relationship_id}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
            f'Target="media/{escape(image_path.name)}"/>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(image_rels)
        + "</Relationships>"
    )


def styles() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/><w:pPr><w:jc w:val="both"/><w:spacing w:after="160" w:line="360" w:lineRule="auto"/></w:pPr><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:qFormat/><w:pPr><w:jc w:val="center"/><w:spacing w:after="360"/></w:pPr><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/><w:b/><w:sz w:val="34"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:jc w:val="left"/><w:spacing w:before="360" w:after="220"/></w:pPr><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/><w:b/><w:sz w:val="30"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:jc w:val="left"/><w:spacing w:before="240" w:after="120"/></w:pPr><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/><w:b/><w:sz w:val="26"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="ListParagraph"><w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="720"/></w:pPr></w:style>
  <w:style w:type="paragraph" w:styleId="CoverLeft"><w:name w:val="Cover Left"/><w:basedOn w:val="Normal"/><w:pPr><w:jc w:val="left"/><w:spacing w:after="120"/></w:pPr><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="24"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="CoverRight"><w:name w:val="Cover Right"/><w:basedOn w:val="Normal"/><w:pPr><w:jc w:val="right"/><w:spacing w:after="120"/></w:pPr><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="24"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="TocEntry"><w:name w:val="TOC Entry"/><w:basedOn w:val="Normal"/><w:pPr><w:jc w:val="left"/><w:spacing w:after="80"/></w:pPr><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="24"/></w:rPr></w:style>
  <w:style w:type="table" w:styleId="TableGrid"><w:name w:val="Table Grid"/><w:tblPr><w:tblBorders><w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/><w:left w:val="single" w:sz="4" w:space="0" w:color="auto"/><w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/><w:right w:val="single" w:sz="4" w:space="0" w:color="auto"/><w:insideH w:val="single" w:sz="4" w:space="0" w:color="auto"/><w:insideV w:val="single" w:sz="4" w:space="0" w:color="auto"/></w:tblBorders></w:tblPr></w:style>
</w:styles>"""


def numbering() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:abstractNum w:abstractNumId="0"><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/><w:lvlJc w:val="left"/><w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr></w:lvl></w:abstractNum>
  <w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
</w:numbering>"""


def core_props() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Sicurezza nei sistemi Internet of Things</dc:title>
  <dc:creator>Samuele Marchitelli</dc:creator>
  <cp:lastModifiedBy>Samuele Marchitelli</cp:lastModifiedBy>
</cp:coreProperties>"""


def app_props() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>Microsoft Word</Application></Properties>"""


def document(body: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document
  xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
  xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
  xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
  xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
  <w:body>
    {body}
    <w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1417" w:right="1417" w:bottom="1417" w:left="1701"/></w:sectPr>
  </w:body>
</w:document>"""


def build_docx() -> None:
    markdown = SOURCE.read_text(encoding="utf-8")
    abstract_index = markdown.find("## Abstract")
    chapter_index = markdown.find("## Capitolo 1")
    abstract_markdown = markdown[abstract_index:chapter_index] if abstract_index >= 0 and chapter_index > abstract_index else ""
    main_markdown = markdown[chapter_index:] if chapter_index >= 0 else markdown
    state = DocxBuildState()
    body = (
        cover_page()
        + markdown_to_body(abstract_markdown, state)
        + page_break()
        + table_of_contents()
        + markdown_to_body(main_markdown, state)
    )
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types())
        docx.writestr("_rels/.rels", rels())
        docx.writestr("word/_rels/document.xml.rels", document_rels(state))
        docx.writestr("word/document.xml", document(body))
        docx.writestr("word/styles.xml", styles())
        docx.writestr("word/numbering.xml", numbering())
        docx.writestr("docProps/core.xml", core_props())
        docx.writestr("docProps/app.xml", app_props())
        used_names: set[str] = set()
        for _, image_path in state.images:
            if image_path.name in used_names:
                continue
            used_names.add(image_path.name)
            docx.write(image_path, f"word/media/{image_path.name}")
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    build_docx()
