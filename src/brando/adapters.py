"""Small source-family adaptations backed by observed conversion regressions."""

from __future__ import annotations

import posixpath
import re
from pathlib import PurePosixPath

from .project import strip_comments

LITERAL = re.compile(
    r"\\begin\{(?P<environment>verbatim\*?|lstlisting|minted)\}.*?"
    r"\\end\{(?P=environment)\}"
    r"|\\verb\*?(?P<delimiter>[^A-Za-z\s]).*?(?P=delimiter)",
    re.S,
)


def qualify_bibliographies(text: str, filename: str, files: set[str]) -> tuple[str, dict[str, int]]:
    """Keep existing root lookup, then qualify bibliography files beside an included source."""
    parent = PurePosixPath(filename).parent
    if parent == PurePosixPath("."):
        return text, {}
    count = 0

    def rewrite(match):
        nonlocal count
        targets = []
        for target in match[2].split(","):
            target = target.strip()
            extension = "" if target.endswith(".bib") else ".bib"
            candidate = posixpath.normpath(str(parent / (target + extension)))
            if (
                not any(char in target for char in "\\#{}")
                and posixpath.normpath(target + extension) not in files
                and candidate in files
            ):
                target = candidate
                count += 1
            targets.append(target)
        return match[1] + "{" + ",".join(targets) + "}"

    pattern = re.compile(r"(\\(?:bibliography|addbibresource)(?:\s*\[[^]]*\])?)\s*\{([^{}]+)\}")
    source = strip_comments(text)
    chunks = []
    position = 0
    for literal in LITERAL.finditer(source):
        chunks.append(pattern.sub(rewrite, source[position : literal.start()]))
        chunks.append(literal[0])
        position = literal.end()
    chunks.append(pattern.sub(rewrite, source[position:]))
    return ("".join(chunks), {"relative_bibliography_paths": count}) if count else (text, {})


def adapt_source(text: str, family: str) -> tuple[str, dict[str, int]]:
    if family != "sn-jnl":
        return text, {}
    source = strip_comments(text)
    counts = {"springer_bottom_rule": 0, "springer_equal_contribution": 0}

    def adapt_segment(segment: str) -> str:
        segment, rules = re.subn(r"\\botrule\b", lambda _: r"\bottomrule", segment)
        segment, contributions = re.subn(r"\\equalcont\b(?=\s*\{)", lambda _: r"\par\emph", segment)
        counts["springer_bottom_rule"] += rules
        counts["springer_equal_contribution"] += contributions
        return segment

    chunks = []
    position = 0
    for match in LITERAL.finditer(source):
        chunks.append(adapt_segment(source[position : match.start()]))
        chunks.append(match[0])
        position = match.end()
    chunks.append(adapt_segment(source[position:]))
    return "".join(chunks), {name: count for name, count in counts.items() if count}
