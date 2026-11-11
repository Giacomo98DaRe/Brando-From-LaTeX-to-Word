"""Developer CLI; packaged desktop users do not need a terminal."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import TEMPLATES, Options, convert


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert a local Overleaf source ZIP or folder to Word."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument(
        "--main", help="Project-relative .tex path; required if roots are ambiguous"
    )
    parser.add_argument("--template", choices=list(TEMPLATES), default="Auto")
    parser.add_argument(
        "--comments",
        action="store_true",
        help="Export source notes as Word comments; unmatched notes use Source annotations",
    )
    parser.add_argument("--reference", type=Path, help="Reference Word DOCX for styling")
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args(argv)
    try:
        path = convert(
            args.input,
            args.destination,
            Options(args.main, args.template, args.comments, args.reference, args.timeout),
            progress=lambda msg: print(msg, flush=True),
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
