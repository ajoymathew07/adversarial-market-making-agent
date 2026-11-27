"""Repository checks run in CI and via `make checks`. Standard library only.

Subcommands:
  layout     required top-level files and directories exist
  pins       requirements files and Dockerfile base images are pinned exactly
  wordcount  SUBMISSION.md report body is within the brief's 800-word limit
  all        run every check above
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = ["README.md", "SUBMISSION.md", "Dockerfile"]
REQUIRED_DIRS = ["src", "tests"]
REQUIREMENTS_FILES = ["requirements.txt", "requirements-dev.txt"]
WORD_LIMIT = 800

PIN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*==[A-Za-z0-9][A-Za-z0-9.+!_-]*$")
# Tag must start with a full major.minor.patch version, e.g. "3.13.9" or "3.13.9-slim".
TAG_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-.+][\w.+-]*)?$")


def image_tag(image: str) -> str:
    """Return the tag of an image reference, or "" when it has none."""
    name = image.split("@", 1)[0]
    last = name.rsplit("/", 1)[-1]  # a registry host:port lives before the last slash
    return last.split(":", 1)[1] if ":" in last else ""


def check_layout() -> list[str]:
    errors = []
    for name in REQUIRED_FILES:
        if not (ROOT / name).is_file():
            errors.append(f"missing file: {name}")
    for name in REQUIRED_DIRS:
        if not (ROOT / name).is_dir():
            errors.append(f"missing directory: {name}/")
    return errors


def check_pins() -> list[str]:
    errors = []
    for name in REQUIREMENTS_FILES:
        path = ROOT / name
        if not path.is_file():
            errors.append(f"missing file: {name}")
            continue
        for lineno, raw in enumerate(path.read_text().splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if not PIN_RE.match(line):
                errors.append(f"{name}:{lineno}: not an exact 'name==version' pin: {line!r}")

    dockerfile = ROOT / "Dockerfile"
    if not dockerfile.is_file():
        errors.append("missing file: Dockerfile")
        return errors
    found_from = False
    for lineno, raw in enumerate(dockerfile.read_text().splitlines(), start=1):
        parts = raw.split()
        if not parts or parts[0].upper() != "FROM":
            continue
        found_from = True
        args = [p for p in parts[1:] if not p.startswith("--")]
        image = args[0] if args else ""
        if not TAG_VERSION_RE.match(image_tag(image)):
            errors.append(
                f"Dockerfile:{lineno}: base image needs an exact major.minor.patch tag: {image!r}"
            )
    if not found_from:
        errors.append("Dockerfile: no FROM line found")
    return errors


def count_report_words(text: str) -> int:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith("## ")), None)
    if start is None:
        return 0
    body = "\n".join(lines[start:])
    return sum(1 for token in body.split() if any(ch.isalnum() for ch in token))


def check_wordcount() -> list[str]:
    path = ROOT / "SUBMISSION.md"
    if not path.is_file():
        return ["missing file: SUBMISSION.md"]
    count = count_report_words(path.read_text())
    print(f"SUBMISSION.md report body: {count} words (limit {WORD_LIMIT})")
    if count > WORD_LIMIT:
        return [f"SUBMISSION.md report body is {count} words, over the {WORD_LIMIT}-word limit"]
    return []


CHECKS = {"layout": check_layout, "pins": check_pins, "wordcount": check_wordcount}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("check", choices=[*CHECKS, "all"])
    args = parser.parse_args()

    names = list(CHECKS) if args.check == "all" else [args.check]
    failed = False
    for name in names:
        errors = CHECKS[name]()
        if errors:
            failed = True
            print(f"[FAIL] {name}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"[ OK ] {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
