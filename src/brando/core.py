"""Shared conversion orchestration. Source projects are captured, never edited."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from .project import Project, ConversionError, Cancelled, capture, checkpoint, decode, split_comment, strip_comments, relative_path
from .fidelity import observe

TEMPLATES = {
    "Auto": None, "Standard article": "article", "Elsevier elsarticle": "elsarticle",
    "Elsevier CAS": "cas-sc", "Springer Nature": "sn-jnl", "IEEEtran": "IEEEtran",
}
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"


@dataclass
class Options:
    main: str | None = None
    template: str = "Auto"
    comments: bool = False
    reference: Path | None = None
    timeout: float = 120


def detect_template(text: str) -> str:
    text = strip_comments(text)
    match = re.search(r"\\documentclass(?:\s*\[[^]]*\])?\s*\{([^}]+)\}", text)
    cls = match[1] if match else ""
    for name, value in TEMPLATES.items():
        if value == cls or (name == "Elsevier CAS" and cls == "cas-dc"):
            return name
    return f"Other ({cls or 'unknown'})"


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


def source_notes(project: Project) -> tuple[list[dict], list[str]]:
    notes, skipped = [], []
    for name, data in sorted(project.files.items()):
        if Path(name).suffix.lower() not in {".tex", ".bib"}:
            continue
        text, _ = decode(data)
        literal = False
        for line_number, line in enumerate(text.splitlines(), 1):
            if re.search(r"\\begin\{(?:verbatim\*?|lstlisting|minted)\}", line):
                literal = True
                skipped.append(f"{name}:{line_number}: literal environment comments not collected")
            if not literal:
                _, note = split_comment(line)
                if note and note.strip():
                    notes.append({"file": name, "line": line_number, "text": note.lstrip("% ")})
            if re.search(r"\\end\{(?:verbatim\*?|lstlisting|minted)\}", line):
                literal = False
    return notes, skipped


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


def convert(input_path: Path, destination: Path, options: Options | None = None,
            cancel: threading.Event | None = None, progress=lambda message: None,
            project: Project | None = None) -> Path:
    options = options or Options()
    if options.template not in TEMPLATES:
        raise ConversionError("Unknown source template selection.")
    progress("Capturing the project")
    project = project or capture(input_path, cancel)
    candidates = project.candidates()
    main = relative_path(options.main) if options.main else (candidates[0] if len(candidates) == 1 else None)
    if not main:
        raise ConversionError("Select a main document. Candidates: " + (", ".join(candidates) or "none detected"))
    if main not in project.files or not main.lower().endswith(".tex"):
        raise ConversionError("The selected main document is not a captured .tex file.")
    if re.search(r"[{}%#]", main):
        raise ConversionError("Main document paths containing braces, percent or hash characters are not supported yet.")
    destination = destination.resolve()
    if input_path.is_dir() and destination.is_relative_to(input_path.resolve()):
        raise ConversionError("Choose an output folder outside the source project.")
    destination.mkdir(parents=True, exist_ok=True)
    notes, skipped = source_notes(project) if options.comments else ([], [])
    with tempfile.TemporaryDirectory(prefix="brando-") as temporary:
        work = Path(temporary)
        sources = work / "project"
        for name, data in project.files.items():
            checkpoint(cancel)
            target = sources / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        reference = None
        if options.reference:
            reference = work / "reference.docx"
            reference.write_bytes(options.reference.read_bytes())
        request = {"main": main, "class_override": TEMPLATES[options.template],
                   "reference": str(reference) if reference else None}
        request_file = work / "request.json"
        request_file.write_text(json.dumps(request), encoding="utf-8")
        cmd = ([sys.executable, "--engine-worker"] if getattr(sys, "frozen", False)
               else [sys.executable, "-m", "brando.engine_worker"]) + [str(request_file)]
        progress("Converting text, equations, tables and references")
        (work / "tmp").mkdir()
        worker_env = {**os.environ, "TMP": str(work / "tmp"), "TEMP": str(work / "tmp"), "TMPDIR": str(work / "tmp")}
        with (work / "stdout.txt").open("wb") as stdout, (work / "stderr.txt").open("wb") as stderr:
            proc = subprocess.Popen(cmd, stdout=stdout, stderr=stderr,
                                    env=worker_env,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            start = time.monotonic()
            try:
                while proc.poll() is None:
                    checkpoint(cancel)
                    if time.monotonic() - start > options.timeout:
                        raise ConversionError(f"Conversion exceeded {options.timeout:g} seconds.")
                    time.sleep(0.1)
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
        if proc.returncode:
            detail = (work / "stderr.txt").read_text(encoding="utf-8", errors="replace")
            if (work / "worker-error.txt").is_file():
                detail += (work / "worker-error.txt").read_text(encoding="utf-8", errors="replace")
            raise ConversionError("The conversion engine failed. " + detail[-5000:])
        checkpoint(cancel)
        progress("Checking the Word file and preparing conversion notes")
        output = work / "converted.docx"
        independent = observe(project, main, output)
        if independent["missing_numeric_tables"]:
            raise ConversionError("Independent numerical table check failed for source tables "
                                  + str(independent["missing_numeric_tables"])
                                  + ". The export was not published; simplify or review these tables.")
        finish_docx(output, not reference, notes, options.comments)
        facts = inspect_docx(output)
        engine = json.loads((work / "engine-report.json").read_text(encoding="utf-8"))
        warnings = [e["message"] for e in engine["entries"] if e["severity"] != "info"]
        if engine.get("coverage", {}).get("math_raw", 0):
            warnings.append("Some equations remain raw source, not editable native equations.")
        warnings.extend(skipped)
        warnings.extend(independent["unresolved_static_includes"])
        if independent["skipped_complex_tables"]:
            warnings.append("Independent numerical checks skipped complex source tables: " + str(independent["skipped_complex_tables"]))
        for item in independent["text_checks"]:
            if not item["present_in_word_text"]:
                warnings.append("Expected source " + item["kind"] + " text was not found in Word: " + item["source_text"])
        for adaptation in engine.get("encoding_adaptations", []):
            warnings.append("Source decoded as cp1252 after UTF-8 failed; verify punctuation: " + adaptation["file"])
        report = {"app_version": "0.1.0", "engine": "tex2word 1.2.0", "main": main,
                  "source_template": detect_template(decode(project.files[main])[0]),
                  "template_override": options.template, "template_status": "experimental",
                  "layout": "reference DOCX" if reference else "review",
                  "source_comments_enabled": options.comments,
                  "source_comments_exported": facts["native_comment_count"],
                  "appendix_source_comments": len(notes),
                  "inline_engine_comments": facts["native_comment_count"] - len(notes),
                  "comment_coverage": "Percent notes from captured tex/bib files use source-location appendix anchors. Supported inline todo/comment/note macros use engine anchors. Literal environments are excluded. Overleaf Review discussions require a separate data source.",
                  "source_sha256": {name: sha256(data).hexdigest() for name, data in project.files.items()},
                  "warnings": warnings, "engine_report": engine,
                  "template_adaptations": engine.get("template_adaptations", []),
                  "independent_source_observations": independent,
                  "structure": {k: v for k, v in facts.items() if k != "text"},
                  "validation": "ZIP/XML integrity and structural observations only. Full source-content fidelity and rendering require review.",
                  "source_notes": notes}
        checkpoint(cancel)
        # A fresh directory avoids silently overwriting a reviewer's earlier export.
        folder = destination / ("brando-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f"))
        summary = ["Brando conversion notes", "", f"Main document: {main}",
                   "Template support: experimental; review the Word document before sharing.",
                   "Full content completeness and visual rendering have not been certified.",
                   f"Native source comments exported: {facts['native_comment_count']}.",
                   f"Source-location appendix comments: {len(notes)}.", "", *warnings]
        # Publish the complete export by a same-filesystem directory rename.
        # A failed write leaves no partially completed brando-* export behind.
        with tempfile.TemporaryDirectory(prefix=".brando-pending-", dir=destination) as staging:
            pending = Path(staging).resolve()
            if pending.parent != destination:
                raise ConversionError("Export staging must remain inside the destination.")
            payload = output.read_bytes()
            (pending / "manuscript.docx").write_bytes(payload)
            report["docx_sha256"] = sha256(payload).hexdigest()
            (pending / "conversion-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            (pending / "conversion-notes.txt").write_text("\n".join(summary), encoding="utf-8")
            checkpoint(cancel)
            pending.rename(folder)
        progress("Finished — review the conversion notes")
        return folder / "manuscript.docx"
