"""Small source-family adaptations backed by observed conversion regressions."""
from __future__ import annotations

import re

from .project import strip_comments

LITERAL = re.compile(
    r"\\begin\{(?P<environment>verbatim\*?|lstlisting|minted)\}.*?"
    r"\\end\{(?P=environment)\}"
    r"|\\verb\*?(?P<delimiter>[^A-Za-z\s]).*?(?P=delimiter)",
    re.S,
)


def adapt_source(text: str, family: str) -> tuple[str, dict[str, int]]:
    if family != "sn-jnl":
        return text, {}
    source = strip_comments(text)
    counts = {"springer_bottom_rule": 0, "springer_equal_contribution": 0}

    def adapt_segment(segment: str) -> str:
        segment, rules = re.subn(r"\\botrule\b", lambda _: r"\bottomrule", segment)
        segment, contributions = re.subn(
            r"\\equalcont\b(?=\s*\{)", lambda _: r"\par\emph", segment
        )
        counts["springer_bottom_rule"] += rules
        counts["springer_equal_contribution"] += contributions
        return segment

    chunks = []
    position = 0
    for match in LITERAL.finditer(source):
        chunks.append(adapt_segment(source[position:match.start()]))
        chunks.append(match[0])
        position = match.end()
    chunks.append(adapt_segment(source[position:]))
    return "".join(chunks), {name: count for name, count in counts.items() if count}
