"""Local-only shared benchmark. Never include the handoff corpus in CI."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "overleaf_word_handoff"
OUT = ROOT / "evaluation" / "benchmark"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def inspect(path: Path, expected: list[str]) -> dict:
    with ZipFile(path) as z:
        doc = ET.fromstring(z.read("word/document.xml"))
        text = " ".join("".join(p.itertext()) for p in doc.iter(f"{{{W}}}p"))
        text = " ".join(text.split())
        return {
            "presence": {s: s in text for s in expected},
            "tables": len(list(doc.iter(f"{{{W}}}tbl"))),
            "native_math": len(list(doc.iter(f"{{{M}}}oMath"))),
            "media": [n for n in z.namelist() if n.startswith("word/media/")],
            "footnotes": "word/footnotes.xml" in z.namelist(),
            "text_characters": len(text),
        }


def worker(source: str, output: str) -> None:
    # Benchmark only the pure parser; prohibit optional TeX subprocess discovery.
    os.environ["PATH"] = ""
    from tex2word import convert_source

    p = Path(source)
    data = p.read_bytes()
    try:
        text = data.decode("utf-8-sig")
        encoding = "utf-8"
    except UnicodeDecodeError:
        text = data.decode("cp1252")
        encoding = "cp1252 (explicit benchmark adaptation)"
    result = convert_source(text, str(p.parent), embed_manifest=False)
    Path(output).write_bytes(result.docx)
    Path(output + ".report.json").write_text(result.report.to_json(), encoding="utf-8")
    print(encoding)


def main() -> None:
    import pypandoc
    import tex2word

    pandoc = pypandoc.get_pandoc_path()
    cases = [("probe", HANDOFF / "probe_multifile/main.tex", ["Example Author", "-0.25"])]
    baseline = json.loads((HANDOFF / "baseline_checks.json").read_text())
    checks = {
        "IEEEtran": ["Michael Shell", "Homer Simpson", "Montgomery Scott"],
        "springer-nature": ["First Author", "Second Author", "Third Author"],
        "scientific-thesis": [
            "Purpose and scope of your entire report",
            "Explicate the assumptions and state of the art",
        ],
        "elsarticle": ["Abstract text.", "Example Section", "Table Caption", "Figure Caption"],
        "cas-sc": [
            "This is a specimen",
            "J.K. Krishnan",
            "Han Thane",
            "William J. Hansen",
            "T. Rafeeq",
        ],
    }
    cases += [
        (c["name"], HANDOFF / c["source"], checks[c["name"]]) for c in baseline["public_samples"]
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    results = {
        "pandoc": str(pypandoc.get_pandoc_version()),
        "tex2word": tex2word.__version__,
        "python": sys.version,
        "platform": sys.platform,
        "method": (
            "Unmodified source copies; tex2word cp1252 decoding only when UTF-8 fails; "
            "optional TeX discovery disabled. Presence checks do not establish full fidelity."
        ),
        "runs": [],
    }
    for name, source, expected in cases:
        for engine in ("pandoc", "tex2word"):
            dest = OUT / f"{name}-{engine}.docx"
            with tempfile.TemporaryDirectory(prefix="brando-bench-", dir=OUT) as td:
                work = Path(td) / "project"
                shutil.copytree(source.parent, work)
                if engine == "pandoc":
                    cmd = [
                        pandoc,
                        source.name,
                        "-f",
                        "latex",
                        "-t",
                        "docx",
                        "-s",
                        "--citeproc",
                        "-o",
                        str(dest),
                    ]
                else:
                    cmd = [
                        sys.executable,
                        str(Path(__file__).resolve()),
                        "--worker",
                        str(work / source.name),
                        str(dest),
                    ]
                start = time.monotonic()
                try:
                    proc = subprocess.run(cmd, cwd=work, capture_output=True, timeout=90)
                    record = {
                        "sample": name,
                        "engine": engine,
                        "returncode": proc.returncode,
                        "seconds": round(time.monotonic() - start, 3),
                        "stderr": proc.stderr.decode("utf-8", errors="replace"),
                        "stdout": proc.stdout.decode("utf-8", errors="replace"),
                    }
                    if proc.returncode == 0 and dest.exists():
                        record["checks"] = inspect(dest, expected)
                except subprocess.TimeoutExpired:
                    record = {"sample": name, "engine": engine, "timeout_seconds": 90}
                results["runs"].append(record)
                (OUT / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
                print(name, engine, json.dumps(record.get("checks", record)), flush=True)


if __name__ == "__main__":
    if "--worker" in sys.argv:
        worker(sys.argv[2], sys.argv[3])
    else:
        main()
