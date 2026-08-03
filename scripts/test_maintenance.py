#!/usr/bin/env python3
"""Regression tests for the machine-readable maintenance report."""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile


sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGET = pathlib.Path(__file__).with_name("maintenance_report.py")
CORPORA = {
    "readme": ROOT / "references" / "readme-corpus.json",
    "release": ROOT / "references" / "release-corpus.json",
    "ui": ROOT / "references" / "ui-corpus.json",
    "writing": ROOT / "references" / "writing-sources.json",
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def expected_report():
    wording = load_json(ROOT / "references" / "wording.json")
    terms = load_json(ROOT / "references" / "technical-terms.json")
    writing_evals = load_json(ROOT / "evals" / "evals.json")["evals"]
    trigger_cases = load_json(ROOT / "evals" / "trigger-evals.json")["cases"]
    trigger_categories = load_json(
        ROOT / "evals" / "trigger-evals.json")["categories"]
    category_counts = {
        category: sum(case["category"] == category for case in trigger_cases)
        for category in trigger_categories
    }
    positive_locales = sorted({
        case["prompt_locale"] for case in trigger_cases if case["should_trigger"]
    })
    lexicon_config = load_json(ROOT / "references" / "lexicon-sources.json")
    lexicon_catalog = lexicon_config["sources"]
    manifest_sources = load_json(ROOT / "lexicons" / "manifest.json")["sources"]
    rule_counts = {
        "consistency_groups": len(wording["consistency_groups"]),
        "grammar": len(wording["grammar_rules"]),
        "literal_groups": len(wording["literal_groups"]),
        "literal_terms": sum(
            len(group["terms"]) for group in wording["literal_groups"]),
        "regex": len(wording["regex_rules"]),
    }
    rule_counts["total"] = sum(
        rule_counts[key]
        for key in ("consistency_groups", "grammar", "literal_groups", "regex")
    )
    return {
        "corpora": {
            name: {
                "sources": len(load_json(path)["sources"]),
                "verified": load_json(path)["verified"],
            }
            for name, path in CORPORA.items()
        },
        "evaluations": {
            "writing": len(writing_evals),
            "trigger": {
                "categories": dict(sorted(category_counts.items())),
                "positive_prompt_locales": positive_locales,
                "total": len(trigger_cases),
            },
        },
        "lexicons": {
            "bundled_catalog_sources": sum(
                source.get("bundled", True) for source in lexicon_catalog),
            "catalog_sources": len(lexicon_catalog),
            "manifest_sources": len(manifest_sources),
            "optional_catalog_sources": sum(
                source.get("bundled", True) is False for source in lexicon_catalog),
            "reference_only_sources": len(lexicon_config["reference_only"]),
        },
        "rules": rule_counts,
        "schema_version": 1,
        "skill": {"lines": len((ROOT / "SKILL.md").read_text(
            encoding="utf-8").splitlines())},
        "technical_terms": {
            "entries": len(terms["terms"]),
            "preserved_identifiers": len(terms["preserve"]),
        },
        "test_scripts": len(list((ROOT / "scripts").glob("test_*.py"))),
        "version": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
    }


def invoke(*arguments, environment=None):
    return subprocess.run(
        [sys.executable, str(TARGET), *arguments],
        check=False,
        capture_output=True,
        env=environment,
    )


def expected_text(report):
    rules = report["rules"]
    terms = report["technical_terms"]
    evaluations = report["evaluations"]
    trigger = evaluations["trigger"]
    lexicons = report["lexicons"]
    lines = [
        "Chinese Skill maintenance report",
        f"Version: {report['version']}",
        f"SKILL.md lines: {report['skill']['lines']}",
        (f"Structured rule groups: {rules['total']} "
         f"(literal groups {rules['literal_groups']}, regex {rules['regex']}, "
         f"grammar {rules['grammar']}, consistency groups "
         f"{rules['consistency_groups']}; literal terms {rules['literal_terms']})"),
        (f"Technical terms: {terms['entries']} "
         f"(preserved identifiers {terms['preserved_identifiers']})"),
        f"Writing evaluations: {evaluations['writing']}",
        f"Trigger evaluations: {trigger['total']}",
        "Trigger categories: " + ", ".join(
            f"{name}={count}" for name, count in trigger["categories"].items()),
        "Positive prompt locales: " + ", ".join(trigger["positive_prompt_locales"]),
        "Corpora:",
    ]
    lines.extend(
        f"  {name}: {data['sources']} sources; verified {data['verified']}"
        for name, data in report["corpora"].items()
    )
    lines.extend([
        (f"Lexicon catalog: {lexicons['catalog_sources']} sources "
         f"({lexicons['bundled_catalog_sources']} bundled, "
         f"{lexicons['optional_catalog_sources']} optional)"),
        f"Lexicon manifest sources: {lexicons['manifest_sources']}",
        f"Reference-only lexicon sources: {lexicons['reference_only_sources']}",
        f"Test scripts: {report['test_scripts']}",
    ])
    return ("\n".join(lines) + "\n").encode("ascii")


expected = expected_report()
checks = {}

utf8_environment = os.environ.copy()
utf8_environment.update({
    "LC_ALL": "C.UTF-8",
    "PYTHONCOERCECLOCALE": "0",
    "PYTHONUTF8": "0",
})
utf8_text = invoke(environment=utf8_environment)
checks["text report in a UTF-8 locale"] = (
    utf8_text.returncode == 0
    and utf8_text.stdout == expected_text(expected)
    and utf8_text.stderr == b""
)

ascii_environment = os.environ.copy()
ascii_environment.update({
    "LC_ALL": "C",
    "PYTHONCOERCECLOCALE": "0",
    "PYTHONUTF8": "0",
})
ascii_text = invoke(environment=ascii_environment)
checks["text report in an ASCII locale"] = (
    ascii_text.returncode == 0
    and ascii_text.stdout == expected_text(expected)
    and ascii_text.stderr == b""
)

utf8_json = invoke("--json", environment=utf8_environment)
ascii_json = invoke("--json", environment=ascii_environment)
checks["JSON report in UTF-8 and ASCII locales"] = (
    utf8_json.returncode == 0
    and ascii_json.returncode == 0
    and utf8_json.stderr == b""
    and ascii_json.stderr == b""
    and json.loads(utf8_json.stdout.decode("utf-8")) == expected
    and json.loads(ascii_json.stdout.decode("utf-8")) == expected
)
second_json = invoke("--json", environment=utf8_environment)
checks["JSON output is stable"] = (
    second_json.returncode == 0
    and second_json.stdout == utf8_json.stdout
    and utf8_json.stdout.endswith(b"\n")
)

with tempfile.TemporaryDirectory() as temporary:
    temporary_root = pathlib.Path(temporary)
    for directory in ("references", "evals", "lexicons", "scripts"):
        (temporary_root / directory).mkdir()
    for relative in (
            "VERSION", "SKILL.md", "references/wording.json",
            "references/technical-terms.json", "references/readme-corpus.json",
            "references/release-corpus.json", "references/ui-corpus.json",
            "references/writing-sources.json", "references/lexicon-sources.json",
            "evals/evals.json", "evals/trigger-evals.json",
            "lexicons/manifest.json"):
        shutil.copy2(ROOT / relative, temporary_root / relative)
    for test_script in (ROOT / "scripts").glob("test_*.py"):
        shutil.copy2(test_script, temporary_root / "scripts" / test_script.name)
    invalid_path = temporary_root / "references" / "writing-sources.json"
    invalid = load_json(invalid_path)
    invalid["verified"] = "not-a-date"
    invalid_path.write_text(json.dumps(invalid), encoding="utf-8")
    invalid_result = invoke("--root", str(temporary_root), "--json")
checks["invalid maintained data returns nonzero"] = (
    invalid_result.returncode != 0
    and invalid_result.stdout == b""
    and b"is not an ISO date" in invalid_result.stderr
)

failed = False
for name, passed in checks.items():
    print(f"{'PASS' if passed else 'FAIL'} {name}")
    failed |= not passed
raise SystemExit(1 if failed else 0)
