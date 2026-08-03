#!/usr/bin/env python3
"""Validate declarative trigger evaluations without invoking a model."""

import json
import pathlib
import re


TARGET = pathlib.Path(__file__).parent.parent / "evals" / "trigger-evals.json"
DATA = json.loads(TARGET.read_text(encoding="utf-8"))
EXPECTED_CATEGORIES = {"direct", "indirect", "incomplete", "non-trigger"}
EXPECTED_FIELDS = {
    "id", "category", "prompt_locale", "prompt", "should_trigger",
    "expected_behavior",
}


def nonempty_string(value):
    return isinstance(value, str) and bool(value.strip())


def ascii_description(value):
    return nonempty_string(value) and value.isascii()


cases = DATA.get("cases", [])
categories = DATA.get("categories", {})
identifiers = [case.get("id") for case in cases]
prompts = [case.get("prompt") for case in cases]
counts = {
    category: sum(case.get("category") == category for case in cases)
    for category in EXPECTED_CATEGORIES
}

checks = {
    "top-level schema": set(DATA) == {
        "schema_version", "skill_name", "evaluation_type", "description",
        "categories", "cases",
    },
    "schema version": DATA.get("schema_version") == 1,
    "skill identity": (
        DATA.get("skill_name") == "chinese-skill"
        and DATA.get("evaluation_type") == "skill-triggering"
    ),
    "English dataset description": ascii_description(DATA.get("description")),
    "category coverage": (
        set(categories) == EXPECTED_CATEGORIES
        and all(ascii_description(value) for value in categories.values())
        and all(count >= 3 for count in counts.values())
    ),
    "case fields": bool(cases) and all(set(case) == EXPECTED_FIELDS for case in cases),
    "case identifiers": (
        len(identifiers) == len(set(identifiers))
        and all(
            isinstance(identifier, str)
            and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identifier)
            and identifier.startswith(f"{case.get('category')}-")
            for identifier, case in zip(identifiers, cases)
        )
    ),
    "prompt metadata": all(
        case.get("prompt_locale") in {"en", "zh-CN", "zh-TW"}
        and nonempty_string(case.get("prompt"))
        and len(case["prompt"]) <= 160
        for case in cases
    ),
    "unique prompts": len(prompts) == len(set(prompts)),
    "English expected behavior": all(
        ascii_description(case.get("expected_behavior")) for case in cases
    ),
    "boolean expectations": all(
        isinstance(case.get("should_trigger"), bool) for case in cases
    ),
    "positive and negative cases": (
        {case.get("should_trigger") for case in cases} == {True, False}
    ),
    "positive locale coverage": (
        {"en", "zh-CN", "zh-TW"} <= {
            case.get("prompt_locale") for case in cases
            if case.get("should_trigger") is True
        }
    ),
    "trigger category semantics": all(
        case.get("should_trigger") == (case.get("category") != "non-trigger")
        for case in cases
    ),
}

failed = False
for name, passed in checks.items():
    print(f"{'PASS' if passed else 'FAIL'} {name}")
    failed |= not passed
raise SystemExit(1 if failed else 0)
