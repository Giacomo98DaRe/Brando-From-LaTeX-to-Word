"""Exercise a packaged app with development tool discovery removed from its environment."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from PIL import Image

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
ROOT = Path(__file__).resolve().parents[1]


def main():
    executable = Path(sys.argv[1]).resolve()
    environment = {
        k: v
        for k, v in os.environ.items()
        if k not in {"PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV", "CONDA_PREFIX", "CONDA_DEFAULT_ENV"}
    }
    environment["PATH"] = (
        str(Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32")
        if os.name == "nt"
        else "/usr/bin:/bin"
    )
    with tempfile.TemporaryDirectory(prefix="brando-package-smoke-") as td:
        work = Path(td)
        package = executable.parents[2] if sys.platform == "darwin" else executable.parent
        relocated = work / "Portable Brando é" / package.name
        shutil.copytree(package, relocated, symlinks=True)
        executable = relocated / executable.relative_to(package)
        subprocess.run(
            [str(executable), "--ui-smoke"],
            cwd=work,
            env={**environment, "QT_QPA_PLATFORM": "offscreen"},
            capture_output=True,
            timeout=20,
            check=True,
        )
        # Test ZIP import through an enclosing directory without altering synthetic sources.
        archive = work / "Project with spaces é.zip"
        figure = BytesIO()
        Image.new("RGB", (120, 80), "#345678").save(figure, format="PDF")
        with ZipFile(archive, "w") as z:
            for f in (ROOT / "examples/article").rglob("*"):
                if f.is_file():
                    data = f.read_bytes()
                    if f.name == "main.tex":
                        addition = (
                            rb"\begin{figure}\includegraphics{figure.pdf}"
                            rb"\caption{Synthetic PDF figure}\end{figure}"
                            rb"\todo{Inline package review}\end{document}"
                        )
                        data = data.replace(rb"\end{document}", addition)
                    z.writestr(
                        "Enclosing/" + f.relative_to(ROOT / "examples/article").as_posix(), data
                    )
            z.writestr("Enclosing/figure.pdf", figure.getvalue())
        for comments in (False, True):
            command = [
                str(executable),
                "--convert",
                str(archive),
                "--destination",
                str(work / "out"),
            ]
            if comments:
                command.append("--comments")
            proc = subprocess.run(
                command, cwd=work, env=environment, capture_output=True, timeout=120
            )
            if proc.returncode:
                raise RuntimeError(
                    f"Packaged conversion failed ({proc.returncode}): "
                    f"{proc.stderr.decode(errors='replace')}"
                )
        outputs = sorted((work / "out").glob("*/manuscript.docx"))
        assert len(outputs) == 2
        for index, output in enumerate(outputs):
            with ZipFile(output) as z:
                doc = ET.fromstring(z.read("word/document.xml"))
                text = "".join(
                    t.text or "" for t in doc.iter() if t.tag in {f"{{{W}}}t", f"{{{M}}}t"}
                )
                text = text.replace("\u2212", "-")
                for phrase in (
                    "Avery Example",
                    "Nested file content",
                    "-0.25",
                    "+0.125",
                    "-2.50",
                    "fictional reference",
                ):
                    assert phrase in text, phrase
                assert len(list(doc.iter(f"{{{M}}}oMath"))) >= 2
                assert len(list(doc.iter(f"{{{W}}}tbl"))) == 1
                assert len(list(doc.iter(f"{{{W}}}drawing"))) >= 1
                images = [
                    name
                    for name in z.namelist()
                    if name.startswith("word/media/") and name.endswith(".png")
                ]
                assert len(images) == 1
                with Image.open(BytesIO(z.read(images[0]))) as rendered:
                    pixel = rendered.convert("RGB").getpixel(
                        (rendered.width // 2, rendered.height // 2)
                    )
                    # PDF creation uses lossy JPEG compression, so allow rounding.
                    assert all(
                        abs(actual - expected) <= 5
                        for actual, expected in zip(pixel, (52, 86, 120), strict=True)
                    )
                assert ("word/comments.xml" in z.namelist()) == bool(index)
            report = json.loads((output.parent / "conversion-report.json").read_text())
            assert not report["independent_source_observations"]["missing_numeric_tables"]
            assert report["inline_engine_comments"] == index
            assert report["body_source_comments"] >= index
            assert report["body_source_comments"] + report["appendix_source_comments"] == 3 * index
            assert len(report["source_comment_anchors"]) == 3 * index
        springer = work / "Springer folder"
        springer.mkdir()
        springer_source = (
            r"\documentclass{sn-jnl}\begin{document}\title{Adapter check}\author{Alice Example}"
            r"\equalcont{Equal contribution package sentinel.}\maketitle"
            r"\begin{tabular}{lr}Value & -0.25 \\ \botrule\end{tabular}\end{document}"
        )
        (springer / "main.tex").write_text(springer_source, encoding="utf-8")
        subprocess.run(
            [
                str(executable),
                "--convert",
                str(springer),
                "--destination",
                str(work / "springer-out"),
            ],
            cwd=work,
            env=environment,
            capture_output=True,
            timeout=120,
            check=True,
        )
        springer_output = next((work / "springer-out").glob("*/manuscript.docx"))
        with ZipFile(springer_output) as z:
            document = ET.fromstring(z.read("word/document.xml"))
            text = "".join(t.text or "" for t in document.iter(f"{{{W}}}t"))
            assert "Equal contribution package sentinel." in text
            assert r"\equalcont" not in text and r"\botrule" not in text
        springer_report = json.loads(
            (springer_output.parent / "conversion-report.json").read_text()
        )
        assert springer_report["template_adaptations"][0]["changes"] == {
            "springer_bottom_rule": 1,
            "springer_equal_contribution": 1,
        }
        failing = work / "failing-worker"
        (failing / "project").mkdir(parents=True)
        secret = work / "outside-project.tex"
        secret.write_text("Synthetic outside-project sentinel", encoding="utf-8")
        source = (
            r"\documentclass{article}\begin{document}\input{"
            + secret.as_posix()
            + r"}\end{document}"
        )
        (failing / "project/main.tex").write_text(source, encoding="utf-8")
        request = failing / "request.json"
        request.write_text(json.dumps({"main": "main.tex"}), encoding="utf-8")
        failed = subprocess.run(
            [str(executable), "--engine-worker", str(request)],
            cwd=work,
            env=environment,
            capture_output=True,
            timeout=20,
        )
        assert failed.returncode == 1
        assert "blocked" in (failing / "worker-error.txt").read_text(encoding="utf-8")
    print(
        "Relocated packaged Qt startup, PDF figure and ZIP conversion passed "
        "with comments off/on and restricted PATH."
    )
    print(
        "Worker failure returned diagnostics within the timeout. "
        "Clean-machine and rendering checks remain pending."
    )


if __name__ == "__main__":
    main()
