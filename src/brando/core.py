"""Shared conversion orchestration. Source projects are captured, never edited."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

from . import __version__
from .fidelity import observe
from .project import (
    ConversionError,
    Project,
    capture,
    checkpoint,
    decode,
    document_class,
    relative_path,
    source_notes,
    strip_comments,
)

# Keep the existing core imports available to developer scripts and callers.
from .word import M as M
from .word import W as W
from .word import finish_docx, inspect_docx

TEMPLATES = {
    "Auto": None,
    "Standard article": "article",
    "Elsevier elsarticle": "elsarticle",
    "Elsevier CAS": "cas-sc",
    "Springer Nature": "sn-jnl",
    "IEEEtran": "IEEEtran",
}


@dataclass
class Options:
    main: str | None = None
    template: str = "Auto"
    comments: bool = False
    reference: Path | None = None
    timeout: float = 120


def detect_template(text: str) -> str:
    text = strip_comments(text)
    cls = document_class(text)
    for name, value in TEMPLATES.items():
        if value == cls or (name == "Elsevier CAS" and cls == "cas-dc"):
            return name
    return f"Other ({cls or 'unknown'})"


def _run_engine(work: Path, request: dict, timeout: float, cancel: threading.Event | None) -> None:
    """Run the isolated worker and always reap it on cancellation or failure."""
    request_file = work / "request.json"
    request_file.write_text(json.dumps(request), encoding="utf-8")
    cmd = (
        [sys.executable, "--engine-worker"]
        if getattr(sys, "frozen", False)
        else [sys.executable, "-m", "brando.engine_worker"]
    ) + [str(request_file)]
    (work / "tmp").mkdir()
    worker_env = {
        **os.environ,
        "TMP": str(work / "tmp"),
        "TEMP": str(work / "tmp"),
        "TMPDIR": str(work / "tmp"),
    }
    with (work / "stderr.txt").open("wb") as stderr:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=stderr,
            env=worker_env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        start = time.monotonic()
        try:
            while proc.poll() is None:
                checkpoint(cancel)
                if time.monotonic() - start > timeout:
                    raise ConversionError(f"Conversion exceeded {timeout:g} seconds.")
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


def convert(
    input_path: Path,
    destination: Path,
    options: Options | None = None,
    cancel: threading.Event | None = None,
    progress=lambda message: None,
    project: Project | None = None,
) -> Path:
    """Convert a captured snapshot and publish its document and reports atomically."""
    options = options or Options()
    if options.template not in TEMPLATES:
        raise ConversionError("Unknown source template selection.")
    progress("Capturing the project")
    project = project or capture(input_path, cancel)
    candidates = project.candidates()
    main = (
        relative_path(options.main)
        if options.main
        else (candidates[0] if len(candidates) == 1 else None)
    )
    if not main:
        raise ConversionError(
            "Select a main document. Candidates: " + (", ".join(candidates) or "none detected")
        )
    if main not in project.files or not main.lower().endswith(".tex"):
        raise ConversionError("The selected main document is not a captured .tex file.")
    if re.search(r"[{}%#]", main):
        raise ConversionError(
            "Main document paths containing braces, percent or hash characters "
            "are not supported yet."
        )
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
        request = {
            "main": main,
            "class_override": TEMPLATES[options.template],
            "reference": str(reference) if reference else None,
        }
        progress("Converting text, equations, tables and references")
        _run_engine(work, request, options.timeout, cancel)
        checkpoint(cancel)
        progress("Checking the Word file and preparing conversion notes")
        output = work / "converted.docx"
        independent = observe(project, main, output)
        if independent["missing_numeric_tables"]:
            raise ConversionError(
                "Independent numerical table check failed for source tables "
                + str(independent["missing_numeric_tables"])
                + ". The export was not published; simplify or review these tables."
            )
        anchors = finish_docx(output, not reference, notes, options.comments, project, main)
        body_notes = sum(anchor["anchor"] == "body" for anchor in anchors)
        appendix_notes = len(anchors) - body_notes
        facts = inspect_docx(output)
        engine = json.loads((work / "engine-report.json").read_text(encoding="utf-8"))
        warnings = [e["message"] for e in engine["entries"] if e["severity"] != "info"]
        if engine.get("coverage", {}).get("math_raw", 0):
            warnings.append("Some equations remain raw source, not editable native equations.")
        warnings.extend(skipped)
        warnings.extend(independent["unresolved_static_includes"])
        if independent["graphics"]["all_available_graphics_absent"]:
            warnings.append(
                "Source references available project graphics, but Word contains no embedded "
                "images. Review figures and conditional image macros."
            )
        if independent["skipped_complex_tables"]:
            warnings.append(
                "Independent numerical checks skipped complex source tables: "
                + str(independent["skipped_complex_tables"])
            )
        for item in independent["text_checks"]:
            if not item["present_in_word_text"]:
                warnings.append(
                    "Expected source "
                    + item["kind"]
                    + " text was not found in Word: "
                    + item["source_text"]
                )
        for adaptation in engine.get("encoding_adaptations", []):
            warnings.append(
                "Source decoded as cp1252 after UTF-8 failed; verify punctuation: "
                + adaptation["file"]
            )
        report = {
            "app_version": __version__,
            "engine": f"tex2word {version('tex2word')}",
            "main": main,
            "source_template": detect_template(decode(project.files[main])[0]),
            "template_override": options.template,
            "template_status": "experimental",
            "layout": "reference DOCX" if reference else "review",
            "source_comments_enabled": options.comments,
            "source_comments_exported": facts["native_comment_count"],
            "body_source_comments": body_notes,
            "appendix_source_comments": appendix_notes,
            "inline_engine_comments": facts["native_comment_count"] - len(notes),
            "comment_coverage": (
                "Percent notes use unique nearby source-text matches in the manuscript. "
                "Unmatched or unused-file notes use source-location appendix anchors. "
                "Supported inline todo/comment/note macros use engine anchors. "
                "Literal environments are excluded. Overleaf Review discussions "
                "require a separate data source."
            ),
            "source_sha256": {
                name: sha256(data).hexdigest() for name, data in project.files.items()
            },
            "warnings": warnings,
            "engine_report": engine,
            "template_adaptations": engine.get("template_adaptations", []),
            "independent_source_observations": independent,
            "structure": {k: v for k, v in facts.items() if k != "text"},
            "validation": (
                "ZIP/XML integrity and structural observations only. "
                "Full source-content fidelity and rendering require review."
            ),
            "source_notes": notes,
            "source_comment_anchors": anchors,
        }
        checkpoint(cancel)
        # A fresh directory avoids silently overwriting a reviewer's earlier export.
        folder = destination / ("brando-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f"))
        summary = [
            "Brando conversion notes",
            "",
            f"Main document: {main}",
            "Template support: experimental; review the Word document before sharing.",
            "Full content completeness and visual rendering have not been certified.",
            f"Native source comments exported: {facts['native_comment_count']}.",
            f"Source comments beside manuscript text: {body_notes}.",
            f"Source-location appendix comments: {appendix_notes}.",
            "",
            *warnings,
        ]
        # Publish the complete export by a same-filesystem directory rename.
        # A failed write leaves no partially completed brando-* export behind.
        with tempfile.TemporaryDirectory(prefix=".brando-pending-", dir=destination) as staging:
            pending = Path(staging).resolve()
            if pending.parent != destination:
                raise ConversionError("Export staging must remain inside the destination.")
            payload = output.read_bytes()
            (pending / "manuscript.docx").write_bytes(payload)
            report["docx_sha256"] = sha256(payload).hexdigest()
            (pending / "conversion-report.json").write_text(
                json.dumps(report, indent=2), encoding="utf-8"
            )
            (pending / "conversion-notes.txt").write_text("\n".join(summary), encoding="utf-8")
            checkpoint(cancel)
            pending.rename(folder)
        progress("Finished — review the conversion notes")
        return folder / "manuscript.docx"
