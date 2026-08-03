#!/usr/bin/env python3
"""Report maintained repository counts without assessing writing quality."""

import argparse
import datetime
import json
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parent.parent
CORPORA = {
    "readme": "references/readme-corpus.json",
    "release": "references/release-corpus.json",
    "ui": "references/ui-corpus.json",
    "writing": "references/writing-sources.json",
}


class DataError(ValueError):
    """Raised when a maintained source cannot provide a report value."""


def read_text(root, relative):
    path = root / relative
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise DataError(f"cannot read {relative}: {error}") from error


def load_json(root, relative):
    try:
        data = json.loads(read_text(root, relative))
    except json.JSONDecodeError as error:
        raise DataError(f"invalid JSON in {relative}: {error}") from error
    if not isinstance(data, dict):
        raise DataError(f"{relative} must contain a JSON object")
    return data


def require_list(data, key, relative):
    value = data.get(key)
    if not isinstance(value, list):
        raise DataError(f"{relative} field {key!r} must be a list")
    return value


def require_object(data, key, relative):
    value = data.get(key)
    if not isinstance(value, dict):
        raise DataError(f"{relative} field {key!r} must be an object")
    return value


def require_string(data, key, relative):
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise DataError(f"{relative} field {key!r} must be a non-empty string")
    return value


def require_date(data, key, relative):
    value = require_string(data, key, relative)
    try:
        parsed = datetime.date.fromisoformat(value)
    except ValueError as error:
        raise DataError(f"{relative} field {key!r} is not an ISO date") from error
    if parsed.isoformat() != value:
        raise DataError(f"{relative} field {key!r} is not an ISO date")
    return value


def require_unique_ids(items, relative, label):
    if not items:
        raise DataError(f"{relative} {label} entries must not be empty")
    identifiers = []
    for item in items:
        if not isinstance(item, dict):
            raise DataError(f"{relative} {label} entries must be objects")
        identifier = item.get("id")
        if not isinstance(identifier, str) or not identifier:
            raise DataError(f"{relative} {label} entries need non-empty ids")
        identifiers.append(identifier)
    if len(identifiers) != len(set(identifiers)):
        raise DataError(f"{relative} {label} ids must be unique")
    return identifiers


def rule_report(root):
    relative = "references/wording.json"
    data = load_json(root, relative)
    fields = {
        "literal_groups": "literal_groups",
        "regex": "regex_rules",
        "grammar": "grammar_rules",
        "consistency_groups": "consistency_groups",
    }
    result = {}
    for output_name, source_name in fields.items():
        records = require_list(data, source_name, relative)
        require_unique_ids(records, relative, source_name)
        result[output_name] = len(records)
    result["total"] = sum(result.values())
    literal_terms = []
    for group in data["literal_groups"]:
        terms = group.get("terms")
        if (not isinstance(terms, list) or not terms
                or any(not isinstance(term, str) or not term for term in terms)):
            raise DataError(f"{relative} literal group terms must be non-empty strings")
        literal_terms.extend(terms)
    if len(literal_terms) != len(set(literal_terms)):
        raise DataError(f"{relative} literal terms must be unique")
    result["literal_terms"] = len(literal_terms)
    return result


def terminology_report(root):
    relative = "references/technical-terms.json"
    data = load_json(root, relative)
    terms = require_list(data, "terms", relative)
    if (not terms
            or any(not isinstance(item, dict)
                   or not isinstance(item.get("en"), str) or not item["en"]
                   for item in terms)):
        raise DataError(f"{relative} term entries need non-empty English keys")
    term_keys = [item["en"] for item in terms]
    if len(term_keys) != len(set(term_keys)):
        raise DataError(f"{relative} term keys must be unique")
    preserved = require_list(data, "preserve", relative)
    if (any(not isinstance(value, str) or not value for value in preserved)
            or len(preserved) != len(set(preserved))):
        raise DataError(f"{relative} preserved identifiers must be non-empty and unique")
    return {"entries": len(terms), "preserved_identifiers": len(preserved)}


def evaluation_report(root):
    writing_relative = "evals/evals.json"
    writing = load_json(root, writing_relative)
    writing_evals = require_list(writing, "evals", writing_relative)
    if (not writing_evals
            or any(not isinstance(item, dict)
                   or not isinstance(item.get("id"), int)
                   or isinstance(item["id"], bool) for item in writing_evals)):
        raise DataError(f"{writing_relative} eval ids must be integers")
    writing_ids = [item["id"] for item in writing_evals]
    if len(writing_ids) != len(set(writing_ids)):
        raise DataError(f"{writing_relative} eval ids must be unique")

    trigger_relative = "evals/trigger-evals.json"
    trigger = load_json(root, trigger_relative)
    categories = require_object(trigger, "categories", trigger_relative)
    if (not categories
            or any(not isinstance(key, str) or not key
                   or not isinstance(value, str) or not value.strip()
                   for key, value in categories.items())):
        raise DataError(f"{trigger_relative} categories must be non-empty strings")
    cases = require_list(trigger, "cases", trigger_relative)
    require_unique_ids(cases, trigger_relative, "cases")
    category_counts = {category: 0 for category in categories}
    positive_locales = set()
    for case in cases:
        category = case.get("category")
        if category not in categories:
            raise DataError(f"{trigger_relative} case has an unknown category")
        category_counts[category] += 1
        should_trigger = case.get("should_trigger")
        if not isinstance(should_trigger, bool):
            raise DataError(f"{trigger_relative} should_trigger values must be boolean")
        locale = case.get("prompt_locale")
        if not isinstance(locale, str) or not locale:
            raise DataError(f"{trigger_relative} prompt locales must be non-empty strings")
        if should_trigger:
            positive_locales.add(locale)
    if not all(category_counts.values()):
        raise DataError(f"{trigger_relative} must include every declared category")
    return {
        "writing": len(writing_evals),
        "trigger": {
            "categories": dict(sorted(category_counts.items())),
            "positive_prompt_locales": sorted(positive_locales),
            "total": len(cases),
        },
    }


def corpus_report(root):
    result = {}
    for name, relative in CORPORA.items():
        data = load_json(root, relative)
        sources = require_list(data, "sources", relative)
        require_unique_ids(sources, relative, "sources")
        result[name] = {
            "sources": len(sources),
            "verified": require_date(data, "verified", relative),
        }
    return result


def lexicon_report(root):
    config_relative = "references/lexicon-sources.json"
    config = load_json(root, config_relative)
    catalog = require_list(config, "sources", config_relative)
    reference_only = require_list(config, "reference_only", config_relative)
    catalog_ids = require_unique_ids(catalog, config_relative, "sources")
    reference_ids = require_unique_ids(reference_only, config_relative, "reference_only")
    if set(catalog_ids).intersection(reference_ids):
        raise DataError(f"{config_relative} source ids must be unique across groups")
    optional = sum(source.get("bundled", True) is False for source in catalog)
    if any(not isinstance(source.get("bundled", True), bool) for source in catalog):
        raise DataError(f"{config_relative} bundled flags must be boolean")

    manifest_relative = "lexicons/manifest.json"
    manifest = load_json(root, manifest_relative)
    manifest_sources = require_list(manifest, "sources", manifest_relative)
    manifest_ids = require_unique_ids(manifest_sources, manifest_relative, "sources")
    bundled_ids = {
        source["id"] for source in catalog if source.get("bundled", True)
    }
    if set(manifest_ids) != bundled_ids:
        raise DataError("lexicon manifest sources do not match bundled catalog sources")
    return {
        "bundled_catalog_sources": len(bundled_ids),
        "catalog_sources": len(catalog),
        "manifest_sources": len(manifest_sources),
        "optional_catalog_sources": optional,
        "reference_only_sources": len(reference_only),
    }


def build_report(root):
    version = read_text(root, "VERSION").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise DataError("VERSION must contain a semantic version")
    skill_text = read_text(root, "SKILL.md")
    skill_lines = len(skill_text.splitlines())
    if not skill_lines:
        raise DataError("SKILL.md must not be empty")
    test_scripts = sorted((root / "scripts").glob("test_*.py"))
    if not test_scripts:
        raise DataError("scripts must contain at least one test_*.py file")
    return {
        "corpora": corpus_report(root),
        "evaluations": evaluation_report(root),
        "lexicons": lexicon_report(root),
        "rules": rule_report(root),
        "schema_version": 1,
        "skill": {"lines": skill_lines},
        "technical_terms": terminology_report(root),
        "test_scripts": len(test_scripts),
        "version": version,
    }


def text_report(report):
    rules = report["rules"]
    evaluations = report["evaluations"]
    trigger = evaluations["trigger"]
    terms = report["technical_terms"]
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
    return "\n".join(lines)


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="Report maintained Chinese Skill repository counts.")
    parser.add_argument("--json", action="store_true",
                        help="write stable JSON instead of compact text")
    parser.add_argument("--root", type=pathlib.Path, default=ROOT,
                        help="read another Chinese Skill checkout")
    args = parser.parse_args()
    try:
        report = build_report(args.root.resolve())
    except DataError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(text_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
