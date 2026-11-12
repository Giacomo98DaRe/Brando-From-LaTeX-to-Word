"""Build locally on the target OS. Never publishes or invokes project scripts."""

from __future__ import annotations

import ast
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


def linux_system_dependencies(package: Path):
    """Use the target distribution's libraries instead of copying host system binaries."""
    analysis = ast.literal_eval((ROOT / "build/pyinstaller/Brando/Analysis-00.toc").read_text())
    sources = set()

    def visit(value):
        if not isinstance(value, (tuple, list)):
            return
        if len(value) == 3 and value[2] == "BINARY" and isinstance(value[1], str):
            source = Path(value[1])
            if source.is_relative_to("/lib") or source.is_relative_to("/usr/lib"):
                sources.add(source)
            return
        for item in value:
            visit(item)

    visit(analysis)
    system_hashes = {sha256(path.read_bytes()).hexdigest() for path in sources}
    # Resolve all candidates before unlinking, including duplicate symlinks.
    excluded = [
        path
        for path in package.rglob("*")
        if path.is_file() and sha256(path.read_bytes()).hexdigest() in system_hashes
    ]
    packages = set()
    for source in sorted(sources):
        # Ubuntu's /lib -> /usr/lib merge can differ from the package database spelling.
        canonical = source.resolve()
        candidates = (
            source,
            canonical,
            Path(str(canonical).replace("/usr/lib/", "/lib/", 1)),
        )
        for candidate in candidates:
            ownership = subprocess.run(
                ["dpkg-query", "-S", str(candidate)], capture_output=True, text=True
            )
            if ownership.returncode == 0:
                break
        ownership.check_returncode()
        packages.update(line.split(": ", 1)[0] for line in ownership.stdout.splitlines())
    for path in excluded:
        path.unlink()
    (package / "linux-system-dependencies.txt").write_text(
        "\n".join(sorted(packages)) + "\n", encoding="utf-8"
    )
    print(f"Using {len(sources)} system libraries from {len(packages)} Ubuntu packages.")


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
        "--collect-data",
        "brando",
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
    ]
    if sys.platform in {"win32", "darwin"}:
        extension = "ico" if sys.platform == "win32" else "png"
        icon = ROOT / "src/brando/resources" / f"brando.{extension}"
        command.extend(["--icon", str(icon)])
    command.append(str(ROOT / "scripts/desktop_entry.py"))
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
    if sys.platform == "linux":
        linux_system_dependencies(package)
    if sys.platform == "win32":
        # Qt Widgets uses raster painting here, not the optional Mesa OpenGL fallback.
        # Use Microsoft's separately installed runtime rather than redistributing its DLLs.
        for path in package.rglob("*.dll"):
            name = path.name.lower()
            if name == "opengl32sw.dll" or name.startswith(("msvcp140", "vcruntime140")):
                path.unlink()
    shutil.copytree(stage, data / "third-party-notices", dirs_exist_ok=True)
    shutil.copytree(ROOT / "docs", data / "docs", dirs_exist_ok=True)
    for name in ("LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md"):
        shutil.copyfile(ROOT / name, data / name)
    # The packaged README uses the existing frozen resource instead of the source tree.
    resource_prefix = "" if sys.platform == "darwin" else "_internal/"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme = readme.replace(
        'src="src/brando/resources/brando.png"',
        f'src="{resource_prefix}brando/resources/brando.png"',
    )
    (data / "README.md").write_text(readme, encoding="utf-8")
    shutil.copytree(ROOT / "examples/article", data / "example-project", dirs_exist_ok=True)
    # Final macOS signing rewrites the main executable and signature envelopes.
    # Their integrity is covered by codesign and the complete archive checksum.
    signing_outputs = set()
    if sys.platform == "darwin":
        signing_outputs = {package / "Contents/MacOS/Brando"}
        signing_outputs.update(p for p in package.rglob("*") if "_CodeSignature" in p.parts)
    manifest = {
        "app_version": __version__,
        "os": platform.platform(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "validation": "Native package and document checks are recorded in docs/VALIDATION.md",
        "uv_lock_sha256": sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
        "files": {
            p.relative_to(package).as_posix(): sha256(p.read_bytes()).hexdigest()
            for p in package.rglob("*")
            if p.is_file() and p not in signing_outputs
        },
    }
    if sys.platform == "darwin":
        manifest["signing"] = "ad-hoc; no Developer ID signature or Apple notarization"
        manifest["signing_outputs_excluded"] = [
            "Contents/MacOS/Brando",
            "**/_CodeSignature/**",
        ]
    (data / "build-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    tag = f"Brando-{__version__}-{sys.platform}-{platform.machine()}"
    if sys.platform == "darwin":
        # PyInstaller signs before the documentation/notices above are added. Seal the
        # complete bundle again, preserving the already signed nested libraries.
        subprocess.run(
            ["/usr/bin/codesign", "--force", "--sign", "-", "--timestamp=none", str(package)],
            check=True,
        )
        subprocess.run(
            ["/usr/bin/codesign", "--verify", "--deep", "--strict", str(package)], check=True
        )
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
