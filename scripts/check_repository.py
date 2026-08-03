#!/usr/bin/env python3
"""Run the repository checks through one stable entry point."""

import argparse
import dataclasses
import os
import pathlib
import shlex
import shutil
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


@dataclasses.dataclass(frozen=True)
class Check:
    name: str
    command: tuple[str, ...]
    environment: tuple[tuple[str, str], ...] = ()


def python_check(name, script, *arguments, environment=()):
    return Check(
        name,
        (sys.executable, f"scripts/{script}", *arguments),
        tuple(environment),
    )


def test_scripts():
    discovered = {path.name for path in SCRIPTS.glob("test_*.py")}
    return sorted(discovered)


def build_checks(*, release=False, network=False, shellcheck_available=True):
    checks = [Check("Bash syntax", ("bash", "-n", "install.sh"))]
    if shellcheck_available:
        checks.append(Check("ShellCheck", ("shellcheck", "install.sh")))

    for script in test_scripts():
        checks.append(python_check(script, script))
        if script == "test_chinese_lint.py":
            checks.append(python_check(
                "test_chinese_lint.py (ASCII locale)",
                script,
                environment=(
                    ("LC_ALL", "C"),
                    ("PYTHONCOERCECLOCALE", "0"),
                    ("PYTHONUTF8", "0"),
                ),
            ))

    checks.append(python_check(
        "Bundled lexicons", "sync_lexicons.py", "--verify"))
    validation_arguments = ("--release",) if release else ()
    checks.append(python_check(
        "Repository validation", "validate_repository.py",
        *validation_arguments))
    checks.extend([
        python_check(
            "Traditional Chinese README", "chinese_lint.py",
            "--kind", "prose", "--style", "readme", "--locale", "zh-TW",
            "README.md"),
        python_check(
            "Simplified Chinese README", "chinese_lint.py",
            "--kind", "prose", "--style", "readme", "--locale", "zh-CN",
            "README.zh-CN.md"),
        python_check(
            "Repository Chinese", "chinese_lint.py",
            "--locale", "zh-TW", "--exclude", "README.zh-CN.md",
            "--exclude", "lexicons/*", "--exclude", "*/lexicons/*", "."),
    ])
    if network:
        checks.append(python_check(
            "Remote corpora", "verify_corpora.py"))
    return checks


def format_command(check):
    prefix = " ".join(
        f"{name}={shlex.quote(value)}" for name, value in check.environment)
    command = shlex.join(check.command)
    return f"{prefix} {command}" if prefix else command


def emit_child_output(result):
    if result.stdout:
        print(result.stdout.rstrip(), file=sys.stdout)
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)


def run_checks(checks, *, runner=subprocess.run):
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    for check in checks:
        child_environment = environment.copy()
        child_environment.update(check.environment)
        try:
            result = runner(
                list(check.command),
                cwd=ROOT,
                env=child_environment,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as error:
            print(f"FAIL {check.name}: {error}", file=sys.stderr)
            return 1
        if result.returncode:
            emit_child_output(result)
            print(
                f"FAIL {check.name}: exit {result.returncode}",
                file=sys.stderr,
            )
            return result.returncode if result.returncode > 0 else 1
        print(f"PASS {check.name}")
    return 0


def parse_arguments(argv=None):
    parser = argparse.ArgumentParser(
        description="Run the local checks for this repository.")
    parser.add_argument(
        "--release", action="store_true",
        help="apply checks required for a public release")
    parser.add_argument(
        "--network", action="store_true",
        help="also verify pinned corpora against their remote sources")
    parser.add_argument(
        "--require-shellcheck", action="store_true",
        help="fail when ShellCheck is not installed")
    parser.add_argument(
        "--list", action="store_true", dest="list_only",
        help="list planned commands without executing them")
    return parser.parse_args(argv)


def main(argv=None, *, runner=subprocess.run, which=shutil.which):
    arguments = parse_arguments(argv)
    shellcheck_available = which("shellcheck") is not None
    if arguments.require_shellcheck and not shellcheck_available:
        print("ERROR ShellCheck is required but not installed.", file=sys.stderr)
        return 1

    checks = build_checks(
        release=arguments.release,
        network=arguments.network,
        shellcheck_available=shellcheck_available,
    )
    if arguments.list_only:
        for check in checks:
            print(format_command(check))
        return 0
    if not shellcheck_available:
        print("SKIP ShellCheck: not installed.", file=sys.stderr)
    return run_checks(checks, runner=runner)


if __name__ == "__main__":
    raise SystemExit(main())
