"""`fastbase init` — generate the canonical project skeleton.

Rules:
  - Files with the marker `# fastbase: generated` may be overwritten only
    with --force; otherwise they are skipped.
  - Files without the marker are user code and are never touched.
  - `.env.fastbase` and `pyproject.toml` live in the current working
    directory (project root). `pyproject.toml` is never overwritten.
  - `docs/*.md` are generated once and never overwritten (they become
    the project's own documentation).
"""

import shutil
from pathlib import Path

GENERATED_MARKER = "# fastbase: generated"
TEMPLATES_DIR = Path(__file__).parent / "templates"

# (template filename, relative path inside the target package directory)
PACKAGE_STRUCTURE: list[tuple[str, str]] = [
    ("main.py.tmpl", "main.py"),
    ("core__config.py.tmpl", "core/config.py"),
    ("core__exceptions.py.tmpl", "core/exceptions.py"),
    ("core__env.py.tmpl", "core/env.py"),
    ("api__v1__routes__health.py.tmpl", "api/v1/routes/health.py"),
    ("api__v1__dependencies.py.tmpl", "api/v1/dependencies.py"),
    ("api__handlers.py.tmpl", "api/handlers.py"),
    ("schemas__example.py.tmpl", "schemas/example.py"),
]

ROOT_FILES: list[tuple[str, str]] = [
    ("env.fastbase.tmpl", ".env.fastbase"),
]

# (template filename, relative path inside the docs/ directory)
DOCS_FILES: list[tuple[str, str]] = [
    ("event-infra.md.tmpl", "event-infra.md"),
    ("core-package.md.tmpl", "core-package.md"),
    ("fastbase.md.tmpl", "fastbase.md"),
    ("full-stack.md.tmpl", "full-stack.md"),
]


def _has_marker(path: Path) -> bool:
    try:
        head = path.read_text(encoding="utf-8-sig").splitlines()[:5]
    except OSError:
        return False
    return any(line.startswith(GENERATED_MARKER) for line in head)


def _write_file(src: Path, dst: Path, *, force: bool) -> str:
    """Copy a template file, respecting the marker/force rules.

    Returns one of: "created", "overwrite", "skip", "skip (user code)".
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        shutil.copyfile(src, dst)
        return "created"
    if not _has_marker(dst):
        return "skip (user code)"
    if not force:
        return "skip"
    shutil.copyfile(src, dst)
    return "overwrite"


def _write_docs(src: Path, dst: Path) -> str:
    """Docs are generated once and never overwritten.

    Returns "created" or "skip".
    """
    if dst.exists():
        return "skip"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return "created"


def _write_pyproject(src: Path, dst: Path) -> str:
    """pyproject.toml is never overwritten. Returns status string."""
    if dst.exists():
        return "skip"
    shutil.copyfile(src, dst)
    return "created"


def _display_path(p: Path, base: Path) -> str:
    try:
        return str(p.relative_to(base))
    except ValueError:
        return str(p)


def _print_tree(root: Path, base: Path) -> None:
    print(f"{_display_path(root, base)}/")
    _print_children(root, prefix="")


def _print_children(directory: Path, *, prefix: str) -> None:
    try:
        entries = sorted(
            directory.iterdir(), key=lambda p: (p.is_file(), p.name)
        )
    except OSError:
        return
    for i, entry in enumerate(entries):
        last = i == len(entries) - 1
        branch = "└── " if last else "├── "
        print(f"{prefix}{branch}{entry.name}")
        if entry.is_dir():
            ext = "    " if last else "│   "
            _print_children(entry, prefix=prefix + ext)


def main_init(*, path: str = "app", force: bool = False) -> int:
    cwd = Path.cwd()
    target = (cwd / path).resolve()

    if target.exists() and not target.is_dir():
        print(f"error: --path '{path}' exists and is not a directory")
        return 1

    rows: list[tuple[str, str]] = []

    try:
        for tmpl_name, rel in PACKAGE_STRUCTURE:
            src = TEMPLATES_DIR / tmpl_name
            dst = target / rel
            status = _write_file(src, dst, force=force)
            rows.append((status, _display_path(dst, cwd)))
    except OSError as e:
        print(f"error: {e}")
        return 1

    try:
        for tmpl_name, rel in ROOT_FILES:
            src = TEMPLATES_DIR / tmpl_name
            dst = cwd / rel
            status = _write_file(src, dst, force=force)
            rows.append((status, rel))

        pyproject_status = _write_pyproject(
            TEMPLATES_DIR / "pyproject.toml.tmpl", cwd / "pyproject.toml"
        )
        rows.append((pyproject_status, "pyproject.toml"))

        docs_dir = cwd / "docs"
        docs_template_dir = TEMPLATES_DIR / "docs"
        for tmpl_name, rel in DOCS_FILES:
            src = docs_template_dir / tmpl_name
            dst = docs_dir / rel
            status = _write_docs(src, dst)
            rows.append((status, f"docs/{rel}"))
    except OSError as e:
        print(f"error: {e}")
        return 1

    for status, p in rows:
        print(f"{status}: {p}")
    print()
    _print_tree(target, cwd)
    print()
    print("Next steps:")
    print("  1. pip install -r requirements.txt")
    print("  2. Edit .env.fastbase")
    print("  3. python -m app.main")
    print()
    print("Связка с core-package и event-infra — см. docs/full-stack.md")
    return 0