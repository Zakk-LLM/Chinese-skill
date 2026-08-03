#!/usr/bin/env python3
"""Regression tests for the repository check entry point."""

import contextlib
import importlib.util
import io
import pathlib
import subprocess
import sys


sys.dont_write_bytecode = True
TARGET = pathlib.Path(__file__).with_name("check_repository.py")
SPEC = importlib.util.spec_from_file_location("check_repository", TARGET)
CHECKER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECKER
SPEC.loader.exec_module(CHECKER)


def scripts_in(checks):
    return {
        pathlib.PurePath(check.command[1]).name
        for check in checks
        if len(check.command) > 1 and check.command[1].startswith("scripts/")
    }


default_checks = CHECKER.build_checks(shellcheck_available=True)
planned_scripts = scripts_in(default_checks)
expected_tests = {
    path.name for path in TARGET.parent.glob("test_*.py")
}
assert expected_tests <= planned_scripts
assert "test_check_repository.py" in planned_scripts
assert default_checks[0].command == ("bash", "-n", "install.sh")
assert default_checks[1].command == ("shellcheck", "install.sh")
assert sum(check.name == "test_chinese_lint.py (ASCII locale)"
           for check in default_checks) == 1
assert "verify_corpora.py" not in planned_scripts

validation = next(check for check in default_checks
                  if check.name == "Repository validation")
assert "--release" not in validation.command
release_checks = CHECKER.build_checks(release=True, shellcheck_available=False)
release_validation = next(check for check in release_checks
                          if check.name == "Repository validation")
assert release_validation.command[-1] == "--release"
assert not any(check.command[0] == "shellcheck" for check in release_checks)

network_checks = CHECKER.build_checks(network=True, shellcheck_available=False)
assert network_checks[-1].command[1] == "scripts/verify_corpora.py"
readme_locales = {
    check.command[-1]: check.command[check.command.index("--locale") + 1]
    for check in default_checks if check.command[-1] in {
        "README.md", "README.zh-CN.md"}
}
assert readme_locales == {"README.md": "zh-TW", "README.zh-CN.md": "zh-CN"}


def forbidden_runner(*_args, **_kwargs):
    raise AssertionError("--list executed a command")


standard_output = io.StringIO()
standard_error = io.StringIO()
with contextlib.redirect_stdout(standard_output), \
        contextlib.redirect_stderr(standard_error):
    list_status = CHECKER.main(
        ["--list", "--network"], runner=forbidden_runner,
        which=lambda _name: None)
assert list_status == 0
assert "scripts/verify_corpora.py" in standard_output.getvalue()
assert "shellcheck install.sh" not in standard_output.getvalue()
assert not standard_error.getvalue()

standard_output = io.StringIO()
standard_error = io.StringIO()
with contextlib.redirect_stdout(standard_output), \
        contextlib.redirect_stderr(standard_error):
    required_status = CHECKER.main(
        ["--require-shellcheck"], runner=forbidden_runner,
        which=lambda _name: None)
assert required_status == 1
assert "ShellCheck is required" in standard_error.getvalue()

calls = []


def failing_runner(command, **_kwargs):
    calls.append(command)
    return subprocess.CompletedProcess(
        command, 7, stdout="failure detail\n", stderr="")


standard_output = io.StringIO()
standard_error = io.StringIO()
with contextlib.redirect_stdout(standard_output), \
        contextlib.redirect_stderr(standard_error):
    failure_status = CHECKER.run_checks(default_checks[:2], runner=failing_runner)
assert failure_status == 7
assert len(calls) == 1
assert "failure detail" in standard_output.getvalue()
assert "FAIL Bash syntax: exit 7" in standard_error.getvalue()

print("repository check tests passed")
