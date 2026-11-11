"""Conservative source-note placement in Word, with explicit unmatched-note fallback."""

from __future__ import annotations

import re
import unicodedata

from .fidelity import commands, source_text
from .project import Project, decode, split_comment


def _words(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", text).casefold()))


def _context(lines: list[str], line_number: int) -> str:
    code, _ = split_comment(lines[line_number - 1])
    if code.strip():
        return code
    following = []
    for line in lines[line_number : line_number + 8]:
        code, _ = split_comment(line)
        if not code.strip():
            if following:
                break
            continue
        following.append(code)
    context = "\n".join(following)
    if context.lstrip().startswith(
        (
            r"\section",
            r"\subsection",
            r"\subsubsection",
            r"\title",
            r"\caption",
            r"\begin{figure}",
            r"\begin{table}",
        )
    ):
        match = re.search(r"\\(section|subsection|subsubsection|title|caption)\b", context)
        if match:
            values = commands(context[match.start() :], match[1])
            if values:
                return values[0]
    return context


def add_source_comments(
    doc, notes: list[dict], project: Project | None, main: str | None
) -> list[dict]:
    """Anchor unique nearby source text, keeping ambiguous/unused notes in an appendix."""
    from docx.oxml.ns import qn
    from docx.text.paragraph import Paragraph
    from pylatexenc.latex2text import LatexNodes2Text

    active: set[str] = set()
    if project is not None and main is not None:
        source_text(project, main, included=active)
    source_lines = {
        name: decode(project.files[name])[0].splitlines()
        for name in active
        if name.lower().endswith(".tex")
    }
    # Snapshot body/table paragraphs before adding any fallback entries or comments.
    paragraphs = [Paragraph(element, doc._body) for element in doc.element.body.iter(qn("w:p"))]
    paragraph_words = []
    for paragraph in paragraphs:
        text = paragraph.text
        if paragraph.style.name.lower().startswith(("heading", "caption", "title")):
            text = re.sub(r"^(?:(?:figure|table)\s*)?\d+[\d.\s:–-]*", "", text, flags=re.I)
        paragraph_words.append(_words(text))
    converter = LatexNodes2Text(math_mode="remove")
    anchors, unmatched = [], []
    for note in notes:
        record = {"file": note["file"], "line": note["line"]}
        lines = source_lines.get(note["file"])
        matches = []
        reason = "Source file is outside the statically included manuscript."
        if lines:
            reason = "No unique nearby source-text match in the Word document."
            context = _context(lines, note["line"])
            # Literal examples are not interpreted as manuscript context.
            if not re.search(r"\\begin\{(?:verbatim\*?|lstlisting|minted)\}", context):
                try:
                    words = _words(converter.latex_to_text(context))
                except Exception:
                    words = ()
                if len(" ".join(words)) >= 12:
                    for index, output in enumerate(paragraph_words):
                        exact = words == output
                        # A long, consecutive phrase tolerates citation/style differences
                        # elsewhere in the paragraph. Repeated matches remain ambiguous.
                        phrase = words[:8]
                        occurrences = (
                            sum(
                                output[start : start + len(phrase)] == phrase
                                for start in range(len(output) - len(phrase) + 1)
                            )
                            if len(phrase) >= 6
                            else 0
                        )
                        if (exact or occurrences) and any(
                            run.text for run in paragraphs[index].runs
                        ):
                            # Engines can merge source paragraphs. Repeated context in
                            # one Word paragraph is just as ambiguous as two paragraphs.
                            matches.extend([index] * max(1, occurrences))
        if len(matches) == 1:
            index = matches[0]
            paragraph = paragraphs[index]
            runs = [run for run in paragraph.runs if run.text]
            comment = doc.add_comment(
                runs,
                f"{note['file']}:{note['line']}\n\n{note['text']}",
                author="Source annotation",
                initials="SA",
            )
            record.update(
                anchor="body",
                paragraph=index + 1,
                word_text=paragraph.text,
                comment_id=comment.comment_id,
                method="Unique normalized nearby source text",
            )
        else:
            record.update(anchor="appendix", reason=reason)
            unmatched.append((note, record))
        anchors.append(record)
    if unmatched:
        doc.add_heading("Source annotations", level=1)
        doc.add_paragraph(
            "These source notes have no unique nearby text match in the converted manuscript. "
            "They include notes from unused files. Each Word comment is attached to its "
            "source location below. Other source notes are attached beside manuscript paragraphs."
        )
        for note, record in unmatched:
            run = doc.add_paragraph().add_run(f"{note['file']}:{note['line']}")
            comment = doc.add_comment(run, note["text"], author="Source annotation", initials="SA")
            record["comment_id"] = comment.comment_id
    return anchors
