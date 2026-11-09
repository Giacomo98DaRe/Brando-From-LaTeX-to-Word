"""Bounded, read-only project capture and main-document discovery."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re
import stat
import threading
from zipfile import ZipFile

MAX_BYTES = 200 * 1024 * 1024
MAX_FILES = 10000
SKIP = {".git", "__MACOSX", ".venv", "node_modules"}


class ConversionError(ValueError):
    """An actionable input or conversion error."""


class Cancelled(ConversionError):
    pass


def checkpoint(cancel: threading.Event | None) -> None:
    if cancel and cancel.is_set():
        raise Cancelled("Conversion cancelled.")


def relative_path(name: str) -> str:
    name = name.replace("\\", "/")
    p = PurePosixPath(name)
    reserved = re.compile(r"^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)
    if (not p.parts or p.is_absolute() or any(x == ".." for x in p.parts) or ":" in name
            or "\x00" in name or any(reserved.match(x) or x.endswith((".", " "))
                                     or re.search(r'[<>"|?*]', x) for x in p.parts)):
        raise ConversionError(f"Project path is not allowed: {name}")
    return p.as_posix()


@dataclass
class Project:
    files: dict[str, bytes]
    enclosing_directory: str = ""

    def candidates(self) -> list[str]:
        candidates = []
        for name, data in self.files.items():
            if not name.lower().endswith(".tex"):
                continue
            text = strip_comments(decode(data)[0])
            cls = re.search(r"\\documentclass(?:\s*\[[^]]*\])?\s*\{([^}]+)\}", text)
            if cls and cls[1] != "subfiles" and re.search(r"\\begin\s*\{document\}", text):
                candidates.append(name)
        return sorted(candidates)


def decode(data: bytes) -> tuple[str, str]:
    try:
        return data.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("cp1252"), "cp1252"


def split_comment(line: str) -> tuple[str, str | None]:
    i = 0
    while i < len(line):
        verb = re.match(r"\\verb\*?([^A-Za-z\s])", line[i:])
        if verb:
            end = line.find(verb[1], i + verb.end())
            if end < 0:
                return line, None
            i = end + 1
        elif line[i] == "\\":
            i += 2
        elif line[i] == "%":
            return line[:i], line[i + 1:].rstrip("\r\n")
        else:
            i += 1
    return line, None


def strip_comments(text: str) -> str:
    # Preserve literal environments; percent characters there are content.
    parts = re.split(r"(\\begin\{(?:verbatim\*?|lstlisting|minted)\}.*?\\end\{(?:verbatim\*?|lstlisting|minted)\})", text, flags=re.S)
    return "".join(p if i % 2 else "".join(split_comment(line)[0].rstrip("\r\n") + "\n" for line in p.splitlines(keepends=True)) for i, p in enumerate(parts))


def capture(path: Path, cancel: threading.Event | None = None) -> Project:
    path = path.resolve()
    files: dict[str, bytes] = {}
    total = 0
    names: set[str] = set()

    def add(name: str, size: int, reader) -> None:
        nonlocal total
        checkpoint(cancel)
        name = relative_path(name)
        if any(p in SKIP for p in PurePosixPath(name).parts):
            return
        folded = name.casefold()
        if folded in names:
            raise ConversionError(f"Duplicate or case-colliding project path: {name}")
        names.add(folded)
        total += size
        if total > MAX_BYTES or len(names) > MAX_FILES:
            raise ConversionError("Project exceeds the 200 MiB / 10,000 file import limit.")
        files[name] = reader()

    if path.is_dir():
        for f in sorted(path.rglob("*")):
            checkpoint(cancel)
            if any(p in SKIP for p in f.relative_to(path).parts):
                continue
            if f.is_symlink() or f.is_junction():
                raise ConversionError(f"Links are not accepted in projects: {f.name}")
            if f.is_file():
                add(f.relative_to(path).as_posix(), f.stat().st_size, f.read_bytes)
    elif path.is_file() and path.suffix.lower() == ".zip":
        with ZipFile(path) as archive:
            if len(archive.infolist()) > MAX_FILES:
                raise ConversionError("Archive contains too many entries.")
            for info in archive.infolist():
                relative_path(info.filename)
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise ConversionError("Archive contains a symbolic link.")
                if info.is_dir():
                    continue
                add(info.filename, info.file_size, lambda i=info: archive.read(i))
    else:
        raise ConversionError("Select a project folder or an Overleaf source ZIP.")
    enclosing = []
    while files and all("/" in n for n in files) and len({n.split("/")[0] for n in files}) == 1:
        enclosing.append(next(iter(files)).split("/")[0])
        files = {n.split("/", 1)[1]: data for n, data in files.items()}
    if not any(n.lower().endswith(".tex") for n in files):
        raise ConversionError("No LaTeX source files were found.")
    return Project(files, "/".join(enclosing))
