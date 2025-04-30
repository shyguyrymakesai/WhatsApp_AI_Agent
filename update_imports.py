#!/usr/bin/env python3
"""Batch-adjust import statements to prefix with 'src.'"""
import re
import sys
from pathlib import Path

# Patterns to rewrite top-level imports
PATTERNS = [
    (r"^(\s*from\s+)handlers\.", r"\1src.handlers."),
    (r"^(\s*import\s+)handlers\.", r"\1src.handlers."),
    (r"^(\s*from\s+)tools\.", r"\1src.tools."),
    (r"^(\s*import\s+)tools\.", r"\1src.tools."),
    (r"^(\s*from\s+)memory\.", r"\1src.memory."),
    (r"^(\s*import\s+)memory\.", r"\1src.memory."),
    (r"^(\s*from\s+)utils\.", r"\1src.utils."),
    (r"^(\s*import\s+)utils\.", r"\1src.utils."),
    (r"^(\s*from\s+)agent\.", r"\1src.agent."),
    (r"^(\s*import\s+)agent\.", r"\1src.agent."),
    (r"^(\s*from\s+)reminder_scheduler", r"\1src.reminder_scheduler"),
    (r"^(\s*import\s+)reminder_scheduler", r"\1src.reminder_scheduler"),
]


def rewrite_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    new_text = text
    for pat, repl in PATTERNS:
        new_text = re.sub(pat, repl, new_text, flags=re.MULTILINE)
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        print(f"Updated {path.relative_to(Path.cwd())}")


def main(root: Path):
    for py_file in root.rglob("*.py"):
        rewrite_file(py_file)


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    main(root)
