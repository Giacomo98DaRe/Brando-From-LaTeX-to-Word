"""Build locally on the target OS. Never publishes or invokes project scripts."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from hashlib import sha256
from importlib.metadata import distribution
from pathlib import Path

from brando import __version__

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = [
    "tex2word",
    "python-docx",
    "PySide6-Essentials",
    "shiboken6",
    "lxml",
    "pylatexenc",
    "Pillow",
    "pypdfium2",
    "latex2mathml",
    "typing-extensions",
]


def notices(target: Path):
    target.mkdir(parents=True, exist_ok=True)
    versions = {}
    for name in RUNTIME:
        dist = distribution(name)
        folder = target / name
        folder.mkdir(exist_ok=True)
        versions[name] = {
            "version": dist.version,
            "license": dist.metadata.get("License-Expression") or dist.metadata.get("License"),
            "homepage": dist.metadata.get_all("Project-URL") or [],
        }
        for file in dist.files or []:
            if any(word in str(file).lower() for word in ("license", "notice", "copying")):
                source = Path(dist.locate_file(file))
                if source.is_file():
                    dest = folder / str(file).replace("../", "")
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, dest)
    # The official Python distribution includes PSF and bundled dependency notices.
    python_base = Path(sys.base_prefix)
    python_licenses = [
        python_base / "LICENSE.txt",
        python_base / "LICENSE",
        python_base / "lib/python3.12/LICENSE.txt",
        python_base / "share/doc/python3.12/LICENSE",
    ]
    python_license = next((path for path in python_licenses if path.is_file()), None)
    if python_license:
        shutil.copyfile(python_license, target / "Python-LICENSE.txt")
    else:
        raise RuntimeError(
            "Python distribution license not found; do not omit it from the package."
        )
    extra = ROOT / "resources/licenses"
    if not extra.is_dir():
        raise RuntimeError("Third-party supplemental license texts are missing.")
    shutil.copytree(extra, target / "supplemental", dirs_exist_ok=True)
    (target / "versions.json").write_text(json.dumps(versions, indent=2), encoding="utf-8")


def main():
    stage = ROOT / "build/notices"
    if stage.exists():
        if not stage.resolve().is_relative_to(ROOT / "build"):
            raise RuntimeError("Notice staging must remain inside the build directory.")
        shutil.rmtree(stage)
    notices(stage)
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--name",
        "Brando",
        "--paths",
        str(ROOT / "src"),
        "--collect-data",
        "tex2word",
        "--collect-data",
        "latex2mathml",
        "--copy-metadata",
        "tex2word",
        "--copy-metadata",
        "pylatexenc",
        "--distpath",
        str(ROOT / "dist"),
        "--workpath",
        str(ROOT / "build/pyinstaller"),
        "--specpath",
        str(ROOT / "build"),
        str(ROOT / "scripts/desktop_entry.py"),
    ]
    build_env = dict(os.environ)
    cache = (ROOT / ".tools/pyinstaller-cache").resolve()
    if not cache.is_relative_to(ROOT):
        raise RuntimeError("Build cache must remain inside the workspace.")
    build_env["PYINSTALLER_CONFIG_DIR"] = str(cache)
    if os.name == "nt":
        windows = Path(os.environ.get("SystemRoot", "C:/Windows"))
        # Prevent unrelated native libraries on the host PATH from being bundled
        # in place of Windows system libraries expected by Qt.
        build_env["PATH"] = os.pathsep.join(
            str(path)
            for path in (
                Path(sys.executable).parent,
                Path(sys.base_prefix),
                windows / "System32",
                windows,
            )
        )
    subprocess.run(command, cwd=ROOT, env=build_env, check=True)
    package = ROOT / "dist/Brando"
    # PyInstaller makes both a directory and an .app on macOS; distribute the .app.
    if sys.platform == "darwin":
        package = ROOT / "dist/Brando.app"
        data = package / "Contents/Resources"
    else:
        data = package
    shutil.copytree(stage, data / "third-party-notices", dirs_exist_ok=True)
    shutil.copytree(ROOT / "docs", data / "docs", dirs_exist_ok=True)
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md", "README.md"):
        shutil.copyfile(ROOT / name, data / name)
    shutil.copytree(ROOT / "examples/article", data / "example-project", dirs_exist_ok=True)
    manifest = {
        "app_version": __version__,
        "os": platform.platform(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "validation": "development build; clean-machine and document rendering checks are separate",
        "uv_lock_sha256": sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
        "files": {
            p.relative_to(package).as_posix(): sha256(p.read_bytes()).hexdigest()
            for p in package.rglob("*")
            if p.is_file()
        },
    }
    (data / "build-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    tag = f"Brando-{__version__}-{sys.platform}-{platform.machine()}"
    if sys.platform == "darwin":
        archive = str(ROOT / "dist" / (tag + ".zip"))
        subprocess.run(
            [
                "/usr/bin/ditto",
                "-c",
                "-k",
                "--sequesterRsrc",
                "--keepParent",
                str(package),
                archive,
            ],
            check=True,
        )
    elif sys.platform == "linux":
        archive = shutil.make_archive(
            str(ROOT / "dist" / tag), "gztar", package.parent, package.name
        )
    else:
        archive = shutil.make_archive(str(ROOT / "dist" / tag), "zip", package.parent, package.name)
    Path(archive + ".sha256").write_text(
        sha256(Path(archive).read_bytes()).hexdigest() + "  " + Path(archive).name + "\n",
        encoding="utf-8",
    )
    print(archive)


if __name__ == "__main__":
    main()
