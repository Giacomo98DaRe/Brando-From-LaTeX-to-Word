"""Evaluate the application ingestion path on the ignored local corpus."""
import json
from pathlib import Path
import sys

from brando.core import Options, convert, inspect_docx
from brando.project import capture

ROOT = Path(__file__).resolve().parents[1]
H = ROOT / "overleaf_word_handoff"
OUT = ROOT / "evaluation/app"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    baseline = json.loads((H / "baseline_checks.json").read_text())
    observed = json.loads((H / "content_observations.json").read_text())
    expectations = {x["sample"]: list(x["content_presence"]) for x in observed}
    expectations["elsarticle"] = ["Abstract text.", "Example Section", "Table Caption", "Figure Caption"]
    expectations["cas-sc"] = ["This is a specimen", "J.K. Krishnan", "Han Thane", "William J. Hansen",
                              "T. Rafeeq", "Research highlights item 1", "The beauty of Munnar, Kerala"]
    expectations["IEEEtran"].append("James Kirk")
    archives = {"elsarticle": "elsarticle", "cas-sc": "els-cas-templates", "IEEEtran": "IEEEtran",
                "springer-nature": "springer-nature", "scientific-thesis": "scientific-thesis"}
    records = []
    for sample in baseline["public_samples"]:
        name = sample["name"]
        source = H / sample["source"]
        for kind, path in (("folder", source.parent), ("zip", H / "archives" / (archives[name] + ".zip"))):
            record = {"sample": name, "ingestion": kind}
            try:
                project = capture(path)
                matches = [n for n in project.files if Path(n).name == source.name]
                assert len(matches) == 1, matches
                result = convert(path, OUT / name / kind, Options(main=matches[0]), project=project)
                facts = inspect_docx(result)
                report = json.loads((result.parent / "conversion-report.json").read_text())
                record.update({"presence": {s: s in facts["text"] for s in expectations.get(name, [])},
                               "structure": report["structure"], "warnings": report["warnings"],
                               "engine_coverage": report["engine_report"]["coverage"],
                               "output": str(result.relative_to(ROOT))})
            except Exception as exc:
                record["error"] = str(exc)
            records.append(record)
            (OUT / "results.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
            print(name, kind, "ERROR: " + record["error"] if "error" in record else str(record["presence"]), flush=True)
    if any("error" in r or not all(r["presence"].values()) for r in records):
        sys.exit(1)


if __name__ == "__main__":
    main()
