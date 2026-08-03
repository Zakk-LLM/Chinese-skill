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
        "short_description": "Write and revise concise professional Chinese",
        "default_prompt": "Use $chinese-skill to write or revise clear Chinese with the style and locale required by the repository.",
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
    rules = [*data["literal_groups"], *data["regex_rules"]]
    identifiers = [rule.get("id") for rule in rules]
    if (len(identifiers) != len(set(identifiers))
            or not all(isinstance(identifier, str)
                       and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identifier)
                       for identifier in identifiers)):
        errors.append("wording rule ids must be present, valid, and unique")
    literal = [term for group in data["literal_groups"] for term in group["terms"]]
    if len(literal) != len(set(literal)):
        errors.append("literal wording rules must be unique")
    grammar_rules = data.get("grammar_rules", [])
    grammar_ids = [rule.get("id") for rule in grammar_rules]
    if (not grammar_ids or len(grammar_ids) != len(set(grammar_ids))
            or not all(isinstance(identifier, str)
                       and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identifier)
                       for identifier in grammar_ids)):
        errors.append("grammar rule ids must be present, valid, and unique")
    patterns = [rule["pattern"]
                for rule in [*data["regex_rules"], *grammar_rules]]
    for key in ("emoji_patterns", "attribution_patterns", "invalid_signoff_patterns",
                "routine_passing_patterns", "workflow_narration_patterns",
                "author_narration_patterns", "pr_inventory_patterns"):
        patterns.extend(data[key])
    for pattern in patterns:
        try:
            re.compile(pattern)
        except re.error as error:
            errors.append(f"invalid wording regular expression: {error}")
    styles = data.get("style_profiles", {})
    expected_styles = {"standard", "strict", "academic", "technical", "readme", "ui"}
    expected_fields = {"emoji", "comment_language", "paragraph_characters",
                       "paragraph_sentences", "sentence_characters", "clause_markers"}
    if set(styles) != expected_styles:
        errors.append("writing style profiles are incomplete")
    for style, policy in styles.items():
        if set(policy) != expected_fields:
            errors.append(f"incomplete writing style: {style}")
            continue
        if policy["emoji"] not in {"allow", "reject"}:
            errors.append(f"invalid Emoji policy: {style}")
        if policy["comment_language"] not in {"repository", "english"}:
            errors.append(f"invalid comment language: {style}")
        limits = [policy[field] for field in expected_fields
                  if field not in {"emoji", "comment_language"}]
        if any(value is not None
               and (not isinstance(value, int) or value < 1) for value in limits):
            errors.append(f"invalid prose limit: {style}")
    repeated = data.get("repeated_sentence_characters")
    if not isinstance(repeated, int) or repeated < 1:
        errors.append("invalid repeated sentence length")
    for style, symbols in data.get("emoji_exceptions", {}).items():
        if style not in expected_styles:
            errors.append(f"Emoji exception names an unknown style: {style}")
        if (not symbols or len(symbols) != len(set(symbols))
                or not all(isinstance(symbol, str) and symbol for symbol in symbols)):
            errors.append(f"invalid Emoji exceptions: {style}")
    for rule in rules:
        if set(rule.get("styles", ())) - expected_styles:
            errors.append("wording rule names an unknown style")
    for rule in grammar_rules:
        if set(rule.get("styles", ())) - expected_styles:
            errors.append("grammar rule names an unknown style")
        if not rule.get("message"):
            errors.append("grammar rule has no message")
    consistency_groups = data.get("consistency_groups", [])
    consistency_ids = [group.get("id") for group in consistency_groups]
    if (not consistency_ids or len(consistency_ids) != len(set(consistency_ids))
            or not all(isinstance(identifier, str)
                       and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identifier)
                       for identifier in consistency_ids)):
        errors.append("consistency group ids must be present, valid, and unique")
    for group in consistency_groups:
        forms = group.get("forms", [])
        if (len(forms) < 2 or len(forms) != len(set(forms))
                or not all(isinstance(form, str) and form for form in forms)):
            errors.append(f"invalid consistency group: {group.get('id')}")
    for key in ("locale_name_exceptions", "locale_word_exceptions",
                "generic_link_labels", "comparison_markers"):
        values = data.get(key, [])
        if not values or len(values) != len(set(values)):
            errors.append(f"wording {key} must be present and unique")
        elif not all(isinstance(value, str) and value for value in values):
            errors.append(f"wording {key} contains an invalid value")
    if set(data["pr_body_limits"]) != {"standard", "strict", "gentoo-overlay"}:
        errors.append("PR body limits are incomplete")
    for profile, limits in data["pr_body_limits"].items():
        if set(limits) != {"characters", "blocks", "list_items", "headings"}:
            errors.append(f"incomplete PR body limits: {profile}")
        elif not isinstance(limits["headings"], bool):
            errors.append(f"invalid PR heading policy: {profile}")
        elif any(value is not None and (not isinstance(value, int) or value < 1)
                 for field, value in limits.items() if field != "headings"):
            errors.append(f"invalid PR body limits: {profile}")
    for locale, terms in data["regional_exceptions"].items():
        if locale not in {"zh-CN", "zh-TW"}:
            errors.append(f"unknown regional exception locale: {locale}")
        if len(terms) != len(set(terms)):
            errors.append(f"duplicate regional exception: {locale}")


def validate_readme_corpus(errors):
    data = load_json("references/readme-corpus.json")
    if data.get("schema") != 2:
        errors.append("unsupported README corpus schema")
    cutoff = data.get("cutoff", "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", cutoff):
        errors.append("README corpus has no valid cutoff")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", data.get("verified", "")):
        errors.append("README corpus has no valid verification date")
    if not data.get("selection") or not all(
            isinstance(item, str) and item for item in data["selection"]):
        errors.append("README corpus has no valid selection criteria")

    contracts = data.get("live_contracts", [])
    contract_ids = [item.get("id") for item in contracts]
    if not contracts or len(contract_ids) != len(set(contract_ids)):
        errors.append("README live contract ids must be present and unique")
    for contract in contracts:
        required = {"id", "repository", "path", "url", "checked",
                    "use_for", "avoid"}
        if set(contract) != required:
            errors.append(f"incomplete README live contract: {contract.get('id')}")
            continue
        expected_url = (f"https://github.com/{contract['repository']}/blob/master/"
                        f"{contract['path']}")
        if contract["url"] != expected_url:
            errors.append(f"invalid README live contract URL: {contract['id']}")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", contract["checked"]):
            errors.append(f"invalid README live contract check date: {contract['id']}")
        if not contract["use_for"] or not contract["avoid"]:
            errors.append(f"README live contract has empty observations: {contract['id']}")

    sources = data.get("sources", [])
    identifiers = [item.get("id") for item in sources]
    if not sources or len(identifiers) != len(set(identifiers)):
        errors.append("README corpus source ids must be present and unique")
    for source in sources:
        required = {"id", "repository", "path", "commit", "blob", "date",
                    "url", "use_for", "avoid"}
        if set(source) != required:
            errors.append(f"incomplete README corpus source: {source.get('id')}")
            continue
        if not re.fullmatch(r"[0-9a-f]{40}", source["commit"]):
            errors.append(f"README corpus source is not pinned: {source['id']}")
        if not re.fullmatch(r"[0-9a-f]{40}", source["blob"]):
            errors.append(f"README corpus source has no valid blob: {source['id']}")
        if (not re.fullmatch(r"\d{4}-\d{2}-\d{2}", source["date"])
                or source["date"] > cutoff):
            errors.append(f"README corpus source exceeds cutoff: {source['id']}")
        expected_url = (f"https://github.com/{source['repository']}/blob/"
                        f"{source['commit']}/{source['path']}")
        if source["url"] != expected_url:
            errors.append(f"README corpus URL is not reproducible: {source['id']}")
        if (not source["use_for"] or not source["avoid"]
                or not all(isinstance(value, str) and value
                           for key in ("use_for", "avoid") for value in source[key])):
            errors.append(f"README corpus source has empty observations: {source['id']}")

    for group in ("patterns", "professional_patterns"):
        patterns = data.get(group, [])
        pattern_ids = [item.get("id") for item in patterns]
        if not patterns or len(pattern_ids) != len(set(pattern_ids)):
            errors.append(f"README corpus {group} ids must be present and unique")
        for pattern in patterns:
            required_fields = {"id", "origin", "evidence", "shape", "required"}
            if set(pattern) != required_fields:
                errors.append(f"incomplete README corpus pattern: {pattern.get('id')}")
                continue
            if not pattern["shape"] or not pattern["required"]:
                errors.append(f"empty README corpus pattern: {pattern['id']}")
            if pattern["origin"] not in {"corpus", "policy"}:
                errors.append(f"invalid README corpus pattern origin: {pattern['id']}")
            evidence = pattern["evidence"]
            if len(evidence) != len(set(evidence)) or set(evidence) - set(identifiers):
                errors.append(f"invalid README corpus evidence: {pattern['id']}")
            if pattern["origin"] == "corpus" and len(evidence) < 2:
                errors.append(f"insufficient README corpus evidence: {pattern['id']}")
            if pattern["origin"] == "policy" and evidence:
                errors.append(f"policy README pattern claims source evidence: {pattern['id']}")


def validate_ui_corpus(errors):
    data = load_json("references/ui-corpus.json")
    if data.get("schema") != 2:
        errors.append("unsupported UI corpus schema")
    cutoff = data.get("cutoff", "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", cutoff):
        errors.append("UI corpus has no valid cutoff")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", data.get("verified", "")):
        errors.append("UI corpus has no valid verification date")
    if not data.get("selection") or not all(
            isinstance(item, str) and item for item in data["selection"]):
        errors.append("UI corpus has no valid selection criteria")

    sources = data.get("sources", [])
    identifiers = [item.get("id") for item in sources]
    if not sources or len(identifiers) != len(set(identifiers)):
        errors.append("UI corpus source ids must be present and unique")
    file_urls = []
    for source in sources:
        required = {"id", "repository", "workflow", "files", "use_for", "avoid"}
        if set(source) != required:
            errors.append(f"incomplete UI corpus source: {source.get('id')}")
            continue
        if not source["files"] or not source["use_for"] or not source["avoid"]:
            errors.append(f"UI corpus source has empty observations: {source['id']}")
        for entry in source["files"]:
            required_file = {"locale", "path", "commit", "blob", "date", "url"}
            if set(entry) != required_file:
                errors.append(f"incomplete UI corpus file: {source['id']}")
                continue
            if entry["locale"] not in {"zh-CN", "zh-TW", "zh-Hans", "zh-Hant"}:
                errors.append(f"unknown UI corpus locale: {entry['locale']}")
            if not re.fullmatch(r"[0-9a-f]{40}", entry["commit"]):
                errors.append(f"UI corpus file is not pinned: {source['id']}")
            if not re.fullmatch(r"[0-9a-f]{40}", entry["blob"]):
                errors.append(f"UI corpus file has no valid blob: {source['id']}")
            if (not re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["date"])
                    or entry["date"] > cutoff):
                errors.append(f"UI corpus file exceeds cutoff: {source['id']}")
            expected_url = (f"https://github.com/{source['repository']}/blob/"
                            f"{entry['commit']}/{entry['path']}")
            if entry["url"] != expected_url:
                errors.append(f"UI corpus URL is not reproducible: {source['id']}")
            file_urls.append(entry["url"])
    if len(file_urls) != len(set(file_urls)):
        errors.append("UI corpus file URLs must be unique")

    patterns = data.get("patterns", [])
    pattern_ids = [item.get("id") for item in patterns]
    if not patterns or len(pattern_ids) != len(set(pattern_ids)):
        errors.append("UI corpus pattern ids must be present and unique")
    for pattern in patterns:
        required_fields = {"id", "origin", "evidence", "surface", "shape",
                           "required"}
        if set(pattern) != required_fields:
            errors.append(f"incomplete UI corpus pattern: {pattern.get('id')}")
            continue
        if not pattern["surface"] or not pattern["shape"] or not pattern["required"]:
            errors.append(f"empty UI corpus pattern: {pattern['id']}")
        if pattern["origin"] != "corpus":
            errors.append(f"invalid UI corpus pattern origin: {pattern['id']}")
        evidence = pattern["evidence"]
        if (len(evidence) != len(set(evidence))
                or set(evidence) - set(identifiers)):
            errors.append(f"invalid UI corpus evidence: {pattern['id']}")
        if len(evidence) < 2:
            errors.append(f"insufficient UI corpus evidence: {pattern['id']}")


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
        if not source.get("bundled", True) and not source.get("attribution"):
            errors.append(f"optional lexicon has no attribution: {source['id']}")
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
    hook = ROOT / ".pre-commit-hooks.yaml"
    if not hook.is_file():
        errors.append("pre-commit hook manifest is missing")
    else:
        hook_text = hook.read_text()
        for value in ("id: chinese-lint", "entry: scripts/chinese_lint.py",
                      "language: script", "types: [text]"):
            if value not in hook_text:
                errors.append(f"incomplete pre-commit hook: {value}")
    action = ROOT / "action.yml"
    if not action.is_file():
        errors.append("reusable action manifest is missing")
    else:
        action_text = action.read_text()
        for value in ("using: composite", "GITHUB_ACTION_PATH/scripts/chinese_lint.py",
                      '"$CHINESE_LINT_PATH"'):
            if value not in action_text:
                errors.append(f"incomplete reusable action: {value}")
    workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text()
    for command in ("shellcheck install.sh", "scripts/test_chinese_lint.py",
                    "scripts/test_install.py", "scripts/test_lexicons.py",
                    "scripts/test_corpora.py", "scripts/validate_repository.py",
                    "sync_lexicons.py --verify", "README.zh-CN.md", "uses: ./"):
        if command not in workflow:
            errors.append(f"CI does not run required check: {command}")
    if "--exclude 'test_*'" in workflow:
        errors.append("CI excludes test files from the Chinese wording check")
    readmes = {
        "README.md": "README.zh-CN.md",
        "README.zh-CN.md": "README.md",
    }
    for filename, locale_target in readmes.items():
        path = ROOT / filename
        if not path.is_file():
            errors.append(f"localized README is missing: {filename}")
            continue
        text = path.read_text()
        for required in ("Python 3.11", "scripts/corpus_lookup.py",
                         "scripts/verify_corpora.py", "scripts/test_corpora.py",
                         "--fix", "pre-commit", "Zakk-LLM/Chinese-skill@main",
                         locale_target):
            if required not in text:
                errors.append(f"incomplete localized README {filename}: {required}")
    if release and (ROOT / "lexicons" / "optional").exists():
        errors.append("optional lexicons must not be included in a release")
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
    validate_readme_corpus(errors)
    validate_ui_corpus(errors)
    validate_sources(errors)
    validate_repository(errors, args.release)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("repository validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
