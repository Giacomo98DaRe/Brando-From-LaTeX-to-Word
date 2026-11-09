"""Word package inspection, review formatting and native source comments."""
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from .project import ConversionError

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def inspect_docx(path: Path) -> dict:
    with ZipFile(path) as z:
        if z.testzip():
            raise ConversionError("The generated DOCX archive is damaged.")
        for name in z.namelist():
            if name.endswith(".xml"):
                ET.fromstring(z.read(name))
        doc = ET.fromstring(z.read("word/document.xml"))
        comment_count = (len(ET.fromstring(z.read("word/comments.xml")))
                         if "word/comments.xml" in z.namelist() else 0)
        text = "\n".join("".join(t.text or "" for t in p.iter() if t.tag in {f"{{{W}}}t", f"{{{M}}}t"}) for p in doc.iter(f"{{{W}}}p"))
        return {"text": text, "tables": len(list(doc.iter(f"{{{W}}}tbl"))),
                "native_equations": len(list(doc.iter(f"{{{M}}}oMath"))),
                "images": len([n for n in z.namelist() if n.startswith("word/media/")]),
                "native_comments": bool(comment_count), "native_comment_count": comment_count}


def finish_docx(path: Path, review: bool, notes: list[dict], include_comments: bool) -> None:
    from docx import Document
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from docx.shared import Inches, Pt
    from lxml import etree
    doc = Document(path)
    if not include_comments:
        # The engine also creates comments for inline todo/comment/note macros.
        # Apply the checkbox to those annotations, including references in footnotes.
        for part in list(doc.part.package.parts):
            for key, relation in list(part.rels.items()):
                if relation.reltype == RT.COMMENTS:
                    del part.rels[key]
            if not (str(part.partname).startswith("/word/") and str(part.partname).endswith(".xml")):
                continue
            element = getattr(part, "_element", None)
            root = element if element is not None else etree.fromstring(part.blob)
            markers = {f"{{{W}}}commentRangeStart", f"{{{W}}}commentRangeEnd", f"{{{W}}}commentReference"}
            for marker in list(root.iter()):
                if marker.tag in markers:
                    marker.getparent().remove(marker)
            if element is None:
                part._blob = etree.tostring(root, encoding="utf-8", xml_declaration=True)
    if review:
        style = doc.styles["Normal"]
        style.font.name = "Calibri"
        style.font.size = Pt(11)
        style.paragraph_format.line_spacing = 1.15
        # Unicode bullets need a Unicode text font. Symbol and Wingdings map
        # different code points and rendered as empty squares in the Word check.
        numbering = doc.part.numbering_part.element
        for level in numbering.iter(f"{{{W}}}lvl"):
            kind = level.find(f"{{{W}}}numFmt")
            if kind is None or kind.get(f"{{{W}}}val") != "bullet":
                continue
            properties = level.find(f"{{{W}}}rPr")
            if properties is None:
                properties = etree.SubElement(level, f"{{{W}}}rPr")
            fonts = properties.find(f"{{{W}}}rFonts")
            if fonts is None:
                fonts = etree.SubElement(properties, f"{{{W}}}rFonts")
            for attribute in ("ascii", "hAnsi", "cs", "eastAsia"):
                fonts.set(f"{{{W}}}{attribute}", "Calibri")
        for sec in doc.sections:
            sec.top_margin = sec.bottom_margin = Inches(0.8)
            sec.left_margin = sec.right_margin = Inches(0.9)
            # Review layout is independent of the source class's column count.
            for cols in sec._sectPr.findall(f"{{{W}}}cols"):
                cols.set(f"{{{W}}}num", "1")
    if notes:
        doc.add_heading("Source annotations", level=1)
        doc.add_paragraph("Local source comments from all captured .tex and .bib files, including unused files. Comments are attached to source-location entries below; manuscript positions are not inferred. Overleaf Review-panel discussions are not included. No source author or date is known.")
        for note in notes:
            para = doc.add_paragraph()
            run = para.add_run(f"{note['file']}:{note['line']}")
            doc.add_comment(run, note["text"], author="Source annotation", initials="SA")
    doc.save(path)
