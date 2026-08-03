#!/usr/bin/env python3
"""Test install.sh without changing user configuration."""

import os
import pathlib
import subprocess
import tempfile


ROOT = pathlib.Path(__file__).resolve().parent.parent
INSTALLER = ROOT / "install.sh"


def invoke(arguments, environment, expected=0):
    result = subprocess.run(
        [str(INSTALLER), *arguments], env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode != expected:
        print(result.stdout, end="")
        raise AssertionError(
            f"{arguments!r} returned {result.returncode}, expected {expected}")
    return result


with tempfile.TemporaryDirectory(prefix="chinese-skill-install-") as raw_root:
    root = pathlib.Path(raw_root)
    environment = os.environ.copy()
    environment.update({
        "CLAUDE_HOME": str(root / "claude"),
        "CODEX_HOME": str(root / "codex"),
        "XDG_CONFIG_HOME": str(root / "xdg"),
    })

    instruction_files = [
        root / "claude/CLAUDE.md",
        root / "codex/AGENTS.md",
        root / "xdg/opencode/AGENTS.md",
    ]
    central_instructions = root / "shared-claude.md"
    central_instructions.write_text("Existing instructions.\n\n")
    instruction_files[0].parent.mkdir(parents=True)
    instruction_files[0].symlink_to(central_instructions)
    instruction_files[1].parent.mkdir(parents=True)
    instruction_files[1].write_text("Codex instructions without final newline.")
    instruction_files[2].parent.mkdir(parents=True)
    instruction_files[2].write_text("OpenCode instructions.\n")
    original_instruction_text = [path.read_text() for path in instruction_files]
    invoke([], environment)
    assert instruction_files[0].is_symlink()
    first_instruction_text = [path.read_text() for path in instruction_files]
    status = invoke(["--status"], environment)
    assert "link, current" in status.stdout
    complete_reminder = instruction_files[1].read_text()
    instruction_files[1].write_text(
        complete_reminder.replace("<!-- chinese-skill:end -->", ""))
    incomplete = invoke(["codex", "--status"], environment, expected=1)
    assert "reminder absent" in incomplete.stdout
    instruction_files[1].write_text(complete_reminder)
    invoke(["--copy"], environment)
    status = invoke(["--status"], environment)
    assert "copy, current" in status.stdout
    assert all(path.read_text().count("<!-- chinese-skill:begin -->") == 1
               for path in instruction_files)
    assert [path.read_text() for path in instruction_files] == first_instruction_text
    copied_skills = [
        root / "claude/skills/chinese-skill",
        root / "codex/skills/chinese-skill",
        root / "xdg/opencode/skills/chinese-skill",
    ]
    assert not any(list(path.rglob("*.pyc")) for path in copied_skills)
    assert not any(list(path.rglob("__pycache__")) for path in copied_skills)
    assert not any((path / ".github").exists() for path in copied_skills)
    assert not any((path / ".git").exists() for path in copied_skills)
    assert all("source=" not in (path / ".chinese-skill-install").read_text()
               for path in copied_skills)
    (copied_skills[0] / "SKILL.md").write_text("stale\n")
    stale = invoke(["--status"], environment, expected=1)
    assert "copy, stale" in stale.stdout
    invoke(["--copy"], environment)

    invoke(["--uninstall"], environment)
    skill_paths = copied_skills
    assert not any(path.exists() or path.is_symlink() for path in skill_paths)
    assert all("chinese-skill:begin" not in path.read_text()
               for path in instruction_files)
    assert [path.read_text() for path in instruction_files] == original_instruction_text
    assert instruction_files[0].is_symlink()

    unowned = root / "claude/skills/chinese-skill"
    unowned.mkdir(parents=True)
    sentinel = unowned / "keep.txt"
    sentinel.write_text("keep\n")
    invoke(["claude"], environment, expected=1)
    assert sentinel.read_text() == "keep\n"
    (unowned / ".chinese-skill-install").write_text("source=/tmp/unrelated\n")
    invoke(["claude", "--uninstall"], environment, expected=1)
    assert sentinel.read_text() == "keep\n"

    invoke(["--copy", "--link"], environment, expected=2)
    invoke(["--status", "--uninstall"], environment, expected=2)

with tempfile.TemporaryDirectory(prefix="chinese-skill-empty-") as raw_root:
    root = pathlib.Path(raw_root)
    environment = os.environ.copy()
    environment["CODEX_HOME"] = str(root / "codex")
    invoke(["codex", "--uninstall"], environment)
    assert not (root / "codex").exists()

with tempfile.TemporaryDirectory(prefix="chinese-skill-ascii-") as raw_root:
    root = pathlib.Path(raw_root)
    environment = os.environ.copy()
    environment.update({
        "CODEX_HOME": str(root / "codex"),
        "LC_ALL": "C",
        "PYTHONCOERCECLOCALE": "0",
        "PYTHONUTF8": "0",
    })
    invoke(["codex", "--copy"], environment)
    assert (root / "codex/skills/chinese-skill/SKILL.md").is_file()
    invoke(["codex", "--uninstall"], environment)

print("installer tests passed")
