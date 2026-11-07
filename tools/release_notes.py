"""Release notes for a GitHub release, taken from the Changelog section of README.md.

    python tools/release_notes.py v1.4.0 --zip NAME.zip --sha SHA256 [--all] -o notes.md

--all includes every changelog entry (used for the first release)."""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def changelog_entries():
    text = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    m = re.search(r"^## Changelog\s*$(.*?)^## ", text, re.S | re.M)
    if not m:
        sys.exit("README.md has no '## Changelog' section")
    out = []
    for block in re.split(r"^\*\*(\d+\.\d+\.\d+)\*\*", m.group(1), flags=re.M)[1:]:
        out.append(block)
    return [(out[i], out[i + 1].strip()) for i in range(0, len(out), 2)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tag")
    ap.add_argument("--zip", required=True)
    ap.add_argument("--sha", required=True)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("-o", "--output", required=True)
    a = ap.parse_args()
    version = a.tag.lstrip("v")
    entries = changelog_entries()
    if version not in [v for v, _ in entries]:
        sys.exit("README.md changelog has no entry for %s" % version)
    if not a.all:
        entries = [e for e in entries if e[0] == version]
    lines = [
        "## Download",
        "",
        "**`%s`** — Windows 64-bit, no Python needed." % a.zip,
        "",
        "1. Unpack the whole archive anywhere.",
        "2. Run `Remnant2SaveEditor\\Remnant2SaveEditor.exe` — keep it inside its folder, next to `_internal`.",
        "3. **Close Remnant 2 completely before saving.** Backups are made automatically.",
        "",
        "Распакуй архив целиком и запусти `Remnant2SaveEditor\\Remnant2SaveEditor.exe` из папки. "
        "Перед сохранением полностью закрой игру.",
        "",
        "Built by GitHub Actions from this tag (see the *Release* workflow run). "
        "Unsigned; in testing Windows Defender did not flag the folder build.",
        "",
        "SHA-256 of the zip: `%s`" % a.sha,
        "",
        "## Changes",
        "",
    ]
    for v, body in entries:
        lines += ["**%s**" % v, body, ""]
    with open(a.output, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")


if __name__ == "__main__":
    main()
