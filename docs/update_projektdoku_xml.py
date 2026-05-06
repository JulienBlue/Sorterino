from __future__ import annotations

import copy
import random
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "Projektdokumentation.docx"
ASSETS = ROOT / "docs" / "doku_assets"
EXAMPLES = ASSETS / "examples"
SNIPPETS = ASSETS / "snippets"
DIAGRAMS = ASSETS / "diagrams"

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "rels": "http://schemas.openxmlformats.org/package/2006/relationships",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
    "wp14": "http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing",
}

for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)

W = f"{{{NS['w']}}}"
R = f"{{{NS['r']}}}"
WP = f"{{{NS['wp']}}}"
A = f"{{{NS['a']}}}"
PIC = f"{{{NS['pic']}}}"
RELS = f"{{{NS['rels']}}}"
W14 = f"{{{NS['w14']}}}"
WP14 = f"{{{NS['wp14']}}}"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").rstrip()


def paragraph_text(paragraph: ET.Element) -> str:
    return "".join(t.text or "" for t in paragraph.findall(".//w:t", NS)).strip()


def paragraph_style(paragraph: ET.Element) -> str:
    style = paragraph.find("./w:pPr/w:pStyle", NS)
    return style.get(f"{W}val", "") if style is not None else ""


def is_heading(paragraph: ET.Element) -> bool:
    style = paragraph_style(paragraph)
    return style.startswith("berschrift") or style.startswith("Heading")


def body_children(body: ET.Element) -> list[ET.Element]:
    return list(body)


def find_heading_index(body: ET.Element, heading_text: str) -> int:
    for idx, child in enumerate(body_children(body)):
        if child.tag == f"{W}p" and paragraph_text(child) == heading_text:
            return idx
    raise ValueError(f"Heading not found: {heading_text}")


def find_next_heading_index(body: ET.Element, start_idx: int) -> int:
    children = body_children(body)
    for idx in range(start_idx + 1, len(children)):
        child = children[idx]
        if child.tag == f"{W}p" and is_heading(child):
            return idx
    return len(children) - 1


def replace_section(body: ET.Element, heading_text: str, new_elements: list[ET.Element]) -> None:
    start_heading_idx = find_heading_index(body, heading_text)
    children = body_children(body)
    start = start_heading_idx + 1
    end = find_next_heading_index(body, start_heading_idx)

    for elem in children[start:end]:
        body.remove(elem)

    for offset, elem in enumerate(new_elements):
        body.insert(start + offset, elem)


def make_paragraph(text: str = "", style: str | None = None) -> ET.Element:
    p = ET.Element(f"{W}p")
    p.set(f"{W14}paraId", f"{random.randrange(16**8):08X}")
    p.set(f"{W14}textId", f"{random.randrange(16**8):08X}")

    if style:
        ppr = ET.SubElement(p, f"{W}pPr")
        pstyle = ET.SubElement(ppr, f"{W}pStyle")
        pstyle.set(f"{W}val", style)

    if text:
        r = ET.SubElement(p, f"{W}r")
        t = ET.SubElement(r, f"{W}t")
        if text.startswith(" ") or text.endswith(" ") or "  " in text:
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        t.text = text

    return p


def make_code_paragraphs(content: str) -> list[ET.Element]:
    lines = content.splitlines()
    if not lines:
        return [make_paragraph("", "Coding")]
    return [make_paragraph(line, "Coding") for line in lines]


def make_text_paragraphs(*texts: str) -> list[ET.Element]:
    return [make_paragraph(text) for text in texts]


def add_relationship(rels_root: ET.Element, target: str) -> str:
    ids = []
    for rel in rels_root.findall("rels:Relationship", NS):
        rel_id = rel.get("Id", "")
        if rel_id.startswith("rId"):
            try:
                ids.append(int(rel_id[3:]))
            except ValueError:
                continue

    new_id = f"rId{max(ids) + 1 if ids else 1}"
    rel = ET.SubElement(rels_root, f"{RELS}Relationship")
    rel.set("Id", new_id)
    rel.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image")
    rel.set("Target", target)
    return new_id


def find_picture_template(body: ET.Element) -> ET.Element:
    for child in body_children(body):
        if child.tag != f"{W}p":
            continue
        if child.find(".//a:blip", NS) is not None:
            return child
    raise ValueError("No picture paragraph template found")


def make_picture_paragraph(template: ET.Element, rel_id: str, cx: int, cy: int) -> ET.Element:
    paragraph = copy.deepcopy(template)
    paragraph.set(f"{W14}paraId", f"{random.randrange(16**8):08X}")
    paragraph.set(f"{W14}textId", f"{random.randrange(16**8):08X}")

    for text_node in paragraph.findall(".//w:t", NS):
        text_node.text = ""

    for docpr in paragraph.findall(".//wp:docPr", NS):
        docpr.set("id", str(random.randrange(100000000, 1999999999)))
        docpr.set("name", "Use-Case Diagramm")

    for inline in paragraph.findall(".//wp:inline", NS):
        inline.set(f"{WP14}anchorId", f"{random.randrange(16**8):08X}")
        inline.set(f"{WP14}editId", f"{random.randrange(16**8):08X}")

    for extent in paragraph.findall(".//wp:extent", NS):
        extent.set("cx", str(cx))
        extent.set("cy", str(cy))

    for extent in paragraph.findall(".//a:ext", NS):
        extent.set("cx", str(cx))
        extent.set("cy", str(cy))

    blip = paragraph.find(".//a:blip", NS)
    if blip is None:
        raise ValueError("Picture template has no blip")
    blip.set(f"{R}embed", rel_id)

    return paragraph


def update_document() -> None:
    with zipfile.ZipFile(DOC_PATH, "r") as source_zip:
        files = {name: source_zip.read(name) for name in source_zip.namelist()}

    document_root = ET.fromstring(files["word/document.xml"])
    rels_root = ET.fromstring(files["word/_rels/document.xml.rels"])
    body = document_root.find("w:body", NS)
    if body is None:
        raise ValueError("word/document.xml has no body")

    replace_section(body, "Domain-Modell und Statusdefinition", make_code_paragraphs(read_text(SNIPPETS / "domain_model.py.txt")))
    replace_section(body, "Routing- und Pfadauflösung", make_code_paragraphs(read_text(SNIPPETS / "routing_path_builder.py.txt")))
    replace_section(body, "Orchestrierung der Verarbeitungspipeline", make_code_paragraphs(read_text(SNIPPETS / "document_pipeline.py.txt")))
    replace_section(body, "Konfigurationsdatei - config.json", make_code_paragraphs(read_text(EXAMPLES / "config.example.json")))
    replace_section(body, "Regelbasierte Klassifikationslogik - rules.json", make_code_paragraphs(read_text(EXAMPLES / "rules.example.json")))
    replace_section(body, "Vordefinierte Ordnerstruktur - structure.json", make_code_paragraphs(read_text(EXAMPLES / "structure.example.json")))
    replace_section(body, "Logging-Beispiel", make_code_paragraphs(read_text(SNIPPETS / "logging_beispiel.txt")))

    media_target = "media/use_case_diagram.svg"
    rel_id = add_relationship(rels_root, media_target)
    picture_template = find_picture_template(body)
    picture_paragraph = make_picture_paragraph(picture_template, rel_id, cx=7200000, cy=4422857)
    caption = make_paragraph("Use-Case-Diagramm der Benutzer- und Serverinteraktionen in Sorterino.")
    replace_section(body, "Use-Case Diagramm", [picture_paragraph, caption])

    files["word/document.xml"] = ET.tostring(document_root, encoding="utf-8", xml_declaration=True)
    files["word/_rels/document.xml.rels"] = ET.tostring(rels_root, encoding="utf-8", xml_declaration=True)
    files[f"word/{media_target}"] = (DIAGRAMS / "use_case_diagram.svg").read_bytes()

    tmp_path = DOC_PATH.with_suffix(".tmp.docx")
    with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as target_zip:
        for name, data in files.items():
            target_zip.writestr(name, data)

    tmp_path.replace(DOC_PATH)


if __name__ == "__main__":
    update_document()
    print(f"Projektdokumentation aktualisiert: {DOC_PATH}")
