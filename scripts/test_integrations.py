#!/usr/bin/env python3
"""Exercise repository integration metadata."""

import json
import pathlib
import shlex
import subprocess
import tempfile


ROOT = pathlib.Path(__file__).resolve().parent.parent
hooks = json.loads((ROOT / ".pre-commit-hooks.yaml").read_text(encoding="utf-8"))
assert len(hooks) == 1
hook = hooks[0]
assert hook == {
    "id": "chinese-lint",
    "name": "Chinese lint",
    "description": "Check Chinese wording in changed text files.",
    "entry": "scripts/chinese_lint.py",
    "language": "script",
    "types": ["text"],
}

with tempfile.TemporaryDirectory(prefix="chinese-skill-integration-") as directory:
    target = pathlib.Path(directory) / "sample.md"
    target.write_text("文件已更新。\n", encoding="utf-8")
    command = [str(ROOT / shlex.split(hook["entry"])[0]), str(target)]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr

print("integration tests passed")
