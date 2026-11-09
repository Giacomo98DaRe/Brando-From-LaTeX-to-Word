"""Isolated engine process: local file boundary and no subprocess/network use."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys


def run(request_file: str) -> int:
    from tex2word import convert_source
    import tex2word
    from .project import decode, document_class, strip_comments
    from .adapters import adapt_source

    request_path = Path(request_file).resolve()
    request = json.loads(request_path.read_text(encoding="utf-8"))
    work = request_path.parent
    project = work / "project"
    # Runtime resources are needed for module imports, XML styles and PDFium.
    runtime_roots = [Path(sys.base_prefix).resolve(), Path(tex2word.__file__).resolve().parents[1]]
    if getattr(sys, "frozen", False):
        runtime_roots.append(Path(sys._MEIPASS).resolve())
    runtime_files = {Path(sys.executable).resolve()}

    def audit(event, args):
        if event.startswith("socket.") or event in {"subprocess.Popen", "os.system", "os.startfile"}:
            raise PermissionError("External commands and network access are disabled during conversion.")
        if event == "open" and not isinstance(args[0], int):
            target = Path(os.fsdecode(args[0])).resolve()
            if (target not in runtime_files and not target.is_relative_to(work)
                    and not any(target.is_relative_to(p) for p in runtime_roots)):
                raise PermissionError("Resource access outside the captured project was blocked.")

    sys.addaudithook(audit)
    os.environ["PATH"] = ""
    os.chdir(project)
    text, encoding = decode((project / request["main"]).read_bytes())
    if request.get("class_override"):
        text = strip_comments(text)
        text = re.sub(r"(\\documentclass(?:\s*\[[^]]*\])?\s*\{)[^}]+", lambda m: m[1] + request["class_override"], text, count=1)
    family = document_class(strip_comments(text))
    adaptations = []
    template_adaptations = []
    for file in project.rglob("*"):
        if file.suffix.lower() in {".tex", ".bib", ".sty", ".cls", ".bbl"} and file.is_file():
            content, detected = decode(file.read_bytes())
            is_main = file == project / request["main"]
            if is_main:
                content = text
            changes = {}
            if file.suffix.lower() == ".tex":
                content, changes = adapt_source(content, family)
            if detected != "utf-8" or changes or is_main:
                file.write_text(content, encoding="utf-8")
            if detected != "utf-8":
                adaptations.append({"file": file.relative_to(project).as_posix(), "from": detected, "to": "utf-8"})
            if changes:
                template_adaptations.append({"file": file.relative_to(project).as_posix(), "changes": changes})
    # Enter through an include so the engine keeps both the project root and the
    # selected main file's directory in its nested-input search paths.
    source = r"\input{" + request["main"] + "}"
    result = convert_source(source, str(project), embed_manifest=False,
                            reference_doc=request.get("reference"), math_image_fallback=False)
    (work / "converted.docx").write_bytes(result.docx)
    report = json.loads(result.report.to_json())
    report["main_encoding"] = encoding
    report["encoding_adaptations"] = adaptations
    report["template_adaptations"] = template_adaptations
    (work / "engine-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0


def main(request_file: str) -> int:
    try:
        return run(request_file)
    except Exception:
        import traceback
        # A windowed frozen executable has no Python stderr. Persist errors for
        # the parent instead of letting the bootloader display a blocking dialog.
        Path(request_file).with_name("worker-error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
