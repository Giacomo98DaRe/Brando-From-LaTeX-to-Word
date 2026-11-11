"""Conservative, independent source observations; never a full TeX fidelity claim."""

from __future__ import annotations

import posixpath
import re
from os import PathLike
from pathlib import PurePosixPath
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from .adapters import LITERAL
from .project import Project, decode, strip_comments

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def argument(text: str, start: int) -> tuple[str, int]:
    while start < len(text) and text[start].isspace():
        start += 1
    if start >= len(text) or text[start] != "{":
        raise ValueError("Expected a static braced argument")
    depth, index = 1, start + 1
    while index < len(text):
        if text[index] == "\\":
            index += 2
            continue
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
        if depth == 0:
            return text[start + 1 : index], index + 1
        index += 1
    raise ValueError("Unbalanced argument")


def commands(text: str, name: str) -> list[str]:
    values = []
    for match in re.finditer(r"\\" + re.escape(name) + r"\b\*?(?:\s*\[[^]]*\])*\s*(?=\{)", text):
        try:
            values.append(argument(text, match.end())[0])
        except ValueError:
            continue
    return values


def source_text(
    project: Project, main: str, included: set[str] | None = None
) -> tuple[str, list[str]]:
    unresolved: list[str] = []

    def expand(name: str, stack: tuple[str, ...]) -> str:
        if name in stack or len(stack) > 40:
            unresolved.append(f"Cyclic or excessive include depth: {name}")
            return ""
        if included is not None:
            included.add(name)
        text = strip_comments(decode(project.files[name])[0])
        text = re.sub(
            r"\\begin\{(verbatim\*?|lstlisting|minted)\}.*?\\end\{\1\}", "", text, flags=re.S
        )
        if name != main and re.search(r"\\documentclass(?:\[[^]]*\])?\{subfiles\}", text):
            match = re.search(r"\\begin\{document\}(.*?)\\end\{document\}", text, re.S)
            if match:
                text = match[1]

        def include(match):
            target = match[1].strip()
            if not PurePosixPath(target).suffix:
                target += ".tex"
            for candidate in (
                posixpath.normpath(str(PurePosixPath(name).parent / target)),
                posixpath.normpath(target),
            ):
                if candidate in project.files:
                    return expand(candidate, stack + (name,))
            unresolved.append(f"Static include could not be checked: {target}")
            return ""

        return re.sub(r"\\(?:input|include|subfileinclude|subfile)\s*\{([^}]+)\}", include, text)

    text = expand(main, ())
    return text, unresolved


def numbers(text: str) -> list[str]:
    """Keep each value's sign and scientific exponent in the same token."""
    text = text.replace("\u2212", "-").replace("\u2013", "-")
    text = text.replace(r"\times", "×").replace(r"\cdot", "·")
    text = re.sub(r"\\(?:,|;|!|quad\b|qquad\b|thinspace\b)", "", text)
    text = re.sub(r"[\s{}$^_]", "", text)
    return re.findall(
        r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:(?:[eE][+-]?\d+)|(?:[×·*]10[+-]?\d+))?", text
    )


def observe(project: Project, main: str, docx: PathLike) -> dict:
    source, unresolved = source_text(project, main)
    with ZipFile(docx) as z:
        doc = ET.fromstring(z.read("word/document.xml"))
        embedded_images = sum(name.startswith("word/media/") for name in z.namelist())

    available_graphics = set()
    for target in commands(LITERAL.sub("", source), "includegraphics"):
        if any(char in target for char in "\\#{}"):
            continue
        extensions = (
            ("",)
            if PurePosixPath(target).suffix
            else (".png", ".jpg", ".jpeg", ".pdf", ".eps", ".svg")
        )
        for extension in extensions:
            for candidate in (
                target + extension,
                str(PurePosixPath(main).parent / (target + extension)),
            ):
                candidate = posixpath.normpath(candidate)
                if candidate in project.files:
                    available_graphics.add(candidate)

    def text_of(element: ET.Element) -> str:
        return "".join(
            node.text or "" for node in element.iter() if node.tag in {f"{{{W}}}t", f"{{{M}}}t"}
        )

    word_text = " ".join(text_of(doc).split())
    output_tables = [
        numbers(" | ".join(text_of(cell) for cell in table.iter(f"{{{W}}}tc")))
        for table in doc.iter(f"{{{W}}}tbl")
    ]
    checked, skipped, missing = [], [], []
    for index, match in enumerate(re.finditer(r"\\begin\{tabular\}(?:\[[^]]*\])?\s*", source), 1):
        try:
            _, start = argument(source, match.end())
            end = source.index(r"\end{tabular}", start)
            body = source[start:end]
        except ValueError:
            skipped.append(index)
            continue
        # Check the simple supported subset only; complex layouts remain explicit gaps.
        unknown = re.findall(r"\\([A-Za-z]+)", body)
        if any(
            name not in {"hline", "toprule", "midrule", "bottomrule", "botrule", "times", "cdot"}
            for name in unknown
        ):
            skipped.append(index)
            continue
        expected = numbers(body)
        if not expected:
            continue
        found = expected in output_tables
        checked.append(
            {"source_table": index, "numbers": expected, "present_in_output_table": found}
        )
        if not found:
            missing.append(index)
    expectations = []
    for name in ("title", "IEEEauthorblockN", "author"):
        if name == "author" and commands(source, "IEEEauthorblockN"):
            continue
        for value in commands(source, name):
            # Preserve transparent name wrappers; skip complex author-note macros.
            value = re.sub(r"\\(?:fnm|sur|spfx|sfx)\s*\{([^{}]+)\}", r"\1", value)
            value = value.replace("~", " ")
            if "\\" in value or "{" in value or len(value) < 3:
                continue
            value = " ".join(value.split())
            expectations.append(
                {"kind": name, "source_text": value, "present_in_word_text": value in word_text}
            )
    return {
        "method": (
            "Static include traversal; simple tabular signed/decimal/scientific token sequences; "
            "plain title/author text; static project graphics versus embedded media. "
            "Complex tables/macros/conditionals are not certified."
        ),
        "text_checks": expectations,
        "numeric_tables": checked,
        "skipped_complex_tables": skipped,
        "missing_numeric_tables": missing,
        "unresolved_static_includes": unresolved,
        "graphics": {
            "available_source_files": sorted(available_graphics),
            "embedded_images": embedded_images,
            "all_available_graphics_absent": bool(available_graphics) and embedded_images == 0,
        },
    }
