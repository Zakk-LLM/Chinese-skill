#!/usr/bin/env python3
"""Regression tests for release commit validation."""

import importlib.util
import pathlib
import subprocess
import sys
import tempfile


sys.dont_write_bytecode = True
TARGET = pathlib.Path(__file__).with_name("validate_repository.py")
SPEC = importlib.util.spec_from_file_location("validate_repository", TARGET)
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def git(root, *arguments):
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def new_repository(parent):
    root = parent / "repository"
    root.mkdir()
    git(root, "init", "--quiet")
    git(root, "config", "user.name", "Release Test")
    git(root, "config", "user.email", "release@example.invalid")
    (root / "VERSION").write_text("1.3.0\n", encoding="utf-8")
    git(root, "add", "VERSION")
    git(root, "commit", "--quiet", "-m", "Initial release")
    return root


with tempfile.TemporaryDirectory(prefix="chinese-skill-release-git-") as raw:
    root = new_repository(pathlib.Path(raw))
    errors = []
    VALIDATOR.validate_release_git(errors, "1.3.0", root)
    assert errors == []

    (root / "VERSION").write_text("1.4.0\n", encoding="utf-8")
    errors = []
    VALIDATOR.validate_release_git(errors, "1.4.0", root)
    assert "release worktree contains tracked or untracked changes" in errors
    assert any("release commit VERSION is '1.3.0'" in error for error in errors)

with tempfile.TemporaryDirectory(prefix="chinese-skill-release-git-") as raw:
    root = new_repository(pathlib.Path(raw))
    (root / "untracked.txt").write_text("not released\n", encoding="utf-8")
    errors = []
    VALIDATOR.validate_release_git(errors, "1.3.0", root)
    assert errors == ["release worktree contains tracked or untracked changes"]

with tempfile.TemporaryDirectory(prefix="chinese-skill-release-git-") as raw:
    errors = []
    VALIDATOR.validate_release_git(errors, "1.3.0", pathlib.Path(raw))
    assert len(errors) == 1
    assert errors[0].startswith("cannot inspect release worktree:")

print("release commit validation tests passed")
