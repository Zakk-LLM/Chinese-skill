#!/usr/bin/env python3
"""Validate the skill structure and maintained rule data."""

import argparse
import json
import os
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_json(relative):
    return json.loads((ROOT / relative).read_text())


def validate_frontmatter(errors):
    text = (ROOT / "SKILL.md").read_text()
    parts = text.split("---", 2)
    if len(parts) != 3 or parts[0].strip():
        errors.append("SKILL.md must start with YAML frontmatter")
        return
    lines = [line for line in parts[1].splitlines() if line.strip()]
    if any(not re.fullmatch(r"[a-z_]+:\s+.+", line) for line in lines):
        errors.append("SKILL.md frontmatter contains malformed YAML")
    fields = [re.fullmatch(r"([a-z_]+):\s+(.+)", line).groups()
              for line in lines if re.fullmatch(r"([a-z_]+):\s+(.+)", line)]
    names = [name for name, _ in fields]
    if names != ["name", "description"]:
        errors.append("SKILL.md frontmatter must contain only name and description")
    if not fields or fields[0][1] != "chinese-skill":
        errors.append("SKILL.md name must be chinese-skill")


def validate_agent_metadata(errors):
    path = ROOT / "agents" / "openai.yaml"
    if not path.is_file():
        errors.append("agents/openai.yaml is missing")
        return
    text = path.read_text()
    required = {
        "display_name": "Chinese Writing Control",
        "short_description": "Enforce concise Chinese and technical terminology",
        "default_prompt": "Use $chinese-skill to review Chinese wording and terminology concisely.",
    }
    for field, expected in required.items():
        match = re.search(rf"^\s{{2}}{field}:\s+[\"'](.+)[\"']\s*$", text, re.M)
        if not match or match.group(1) != expected:
            errors.append(f"agents/openai.yaml has stale {field}")


def validate_terms(errors):
    data = load_json("references/technical-terms.json")
    terms = data["terms"]
    names = [item["en"] for item in terms]
    if len(names) != len(set(names)):
        errors.append("technical term keys must be unique")
    preserve = data["preserve"]
    if len(preserve) != len(set(preserve)):
        errors.append("preserved identifiers must be unique")
    overlap = set(names).intersection(preserve)
    if overlap:
        errors.append(f"translated and preserved terms overlap: {sorted(overlap)!r}")
    preferred = {
        locale: {item[locale] for item in terms}
        for locale in ("zh-CN", "zh-TW")
    }
    for item in terms:
        if not all(item.get(field) for field in ("en", "zh-CN", "zh-TW", "domain")):
            errors.append(f"technical term is incomplete: {item!r}")
        for locale in ("zh-CN", "zh-TW"):
            rejected = item.get("reject", {}).get(locale, [])
            if item[locale] in rejected:
                errors.append(f"preferred form is rejected: {item['en']} {locale}")
            for form in rejected:
                if form in preferred[locale]:
                    errors.append(f"rejected form conflicts with a preferred term: {form}")


def validate_wording(errors):
    data = load_json("references/wording.json")
    literal = [term for group in data["literal_groups"] for term in group["terms"]]
    if len(literal) != len(set(literal)):
        errors.append("literal wording rules must be unique")
    patterns = [rule["pattern"] for rule in data["regex_rules"]]
    for key in ("attribution_patterns", "invalid_signoff_patterns",
                "routine_passing_patterns", "workflow_narration_patterns",
                "author_narration_patterns", "pr_inventory_patterns"):
        patterns.extend(data[key])
    for pattern in patterns:
        try:
            re.compile(pattern)
        except re.error as error:
            errors.append(f"invalid wording regular expression: {error}")
    if set(data["pr_body_limits"]) != {"general", "gentoo-overlay"}:
        errors.append("PR body limits must cover both profiles")
    for profile, limits in data["pr_body_limits"].items():
        if set(limits) != {"characters", "blocks", "list_items"}:
            errors.append(f"incomplete PR body limits: {profile}")
        elif any(not isinstance(value, int) or value < 1 for value in limits.values()):
            errors.append(f"invalid PR body limits: {profile}")
    for locale, terms in data["regional_exceptions"].items():
        if locale not in {"zh-CN", "zh-TW"}:
            errors.append(f"unknown regional exception locale: {locale}")
        if len(terms) != len(set(terms)):
            errors.append(f"duplicate regional exception: {locale}")


def validate_sources(errors):
    data = load_json("references/lexicon-sources.json")
    if data.get("schema") != 1:
        errors.append("unsupported lexicon source schema")
    for key in ("sources", "reference_only"):
        identifiers = [item["id"] for item in data[key]]
        if len(identifiers) != len(set(identifiers)):
            errors.append(f"duplicate lexicon source id in {key}")
    all_ids = [item["id"] for key in ("sources", "reference_only")
               for item in data[key]]
    if len(all_ids) != len(set(all_ids)):
        errors.append("lexicon ids must be unique across bundled and reference sources")

    filenames = []
    allowed_formats = {"gzip", "plain-to-gzip", "zip"}
    for source in data["sources"]:
        missing = {"id", "version", "role", "authority", "license", "license_file"} \
            - set(source)
        if missing:
            errors.append(f"incomplete lexicon source {source.get('id')}: {sorted(missing)!r}")
            continue
        license_name = source["license_file"]
        if not re.fullmatch(r"[^/]+\.txt", license_name):
            errors.append(f"invalid license filename: {source['id']}")
        if (source.get("bundled", True)
                and not (ROOT / "lexicons" / "licenses" / license_name).is_file()):
            errors.append(f"missing bundled license file: {license_name}")
        files = source.get("files") or [{key: source[key]
                                         for key in ("url", "file", "format", "sha256",
                                                     "relaxed_tls") if key in source}]
        if not files or any(not {"url", "file", "format"}.issubset(item)
                            for item in files):
            errors.append(f"incomplete lexicon file declaration: {source['id']}")
            continue
        for item in files:
            filename = item["file"]
            filenames.append(filename)
            if pathlib.PurePosixPath(filename).name != filename:
                errors.append(f"lexicon file must use a basename: {filename}")
            if item["format"] not in allowed_formats:
                errors.append(f"unsupported lexicon format: {item['format']}")
            if not item["url"].startswith("https://"):
                errors.append(f"bundled lexicon URL must use HTTPS: {source['id']}")
            expected = item.get("sha256")
            if expected and not re.fullmatch(r"[0-9a-f]{64}", expected):
                errors.append(f"invalid lexicon digest: {source['id']}")
            if source["version"] != "rolling" and not expected:
                errors.append(f"fixed lexicon source has no digest: {source['id']}")
            if item.get("relaxed_tls") and not expected:
                errors.append(f"relaxed TLS source must pin a digest: {source['id']}")
    if len(filenames) != len(set(filenames)):
        errors.append("lexicon snapshot filenames must be unique")

    for item in data["reference_only"]:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", item.get("checked", "")):
            errors.append(f"reference source has no valid checked date: {item['id']}")
        if not all(item.get(field) for field in ("role", "authority", "url")):
            errors.append(f"incomplete reference source: {item['id']}")


def validate_repository(errors, release):
    if not (ROOT / "LICENSE").is_file():
        errors.append("root LICENSE is missing")
    elif "contributors\n\nPermission is hereby granted" not in (
            ROOT / "LICENSE").read_text():
        errors.append("LICENSE does not preserve the standard MIT grant")
    required_executables = [ROOT / "install.sh", *(ROOT / "scripts").glob("*.py")]
    for path in required_executables:
        if not os.access(path, os.X_OK):
            errors.append(f"script is not executable: {path.relative_to(ROOT)}")
    workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text()
    for command in ("shellcheck install.sh", "scripts/test_chinese_lint.py",
                    "scripts/test_install.py", "scripts/test_lexicons.py",
                    "scripts/validate_repository.py", "sync_lexicons.py --verify"):
        if command not in workflow:
            errors.append(f"CI does not run required check: {command}")
    if "--exclude 'test_*'" in workflow:
        errors.append("CI excludes test files from the Chinese wording check")
    if "Python 3.11" not in (ROOT / "README.md").read_text():
        errors.append("README.md does not state the minimum Python version")
    if release and (ROOT / "lexicons" / "optional").exists():
        errors.append("optional non-commercial lexicons must not be included in a release")
    for path in ROOT.rglob("*"):
        if any(part in {".git", "lexicons"} for part in path.parts):
            continue
        if path.name == "__pycache__" or path.suffix in {".pyc", ".pyo"}:
            errors.append(f"generated Python artifact: {path.relative_to(ROOT)}")
        if path.is_file():
            try:
                text = path.read_text()
            except (OSError, UnicodeDecodeError):
                continue
            if re.search(r"/home/[^/\s]+/(?:code/)?Chinese-skill", text):
                errors.append(f"hard-coded installation path: {path.relative_to(ROOT)}")


def main():
    parser = argparse.ArgumentParser(description="Validate the skill repository.")
    parser.add_argument("--release", action="store_true",
                        help="also reject local files excluded from a public release")
    args = parser.parse_args()
    errors = []
    validate_frontmatter(errors)
    validate_agent_metadata(errors)
    validate_terms(errors)
    validate_wording(errors)
    validate_sources(errors)
    validate_repository(errors, args.release)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("repository validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
