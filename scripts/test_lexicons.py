#!/usr/bin/env python3
"""Regression tests for bundled lexicon lookup."""

import copy
import gzip
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile


sys.dont_write_bytecode = True
TARGET = pathlib.Path(__file__).with_name("lexicon_lookup.py")
SPEC = importlib.util.spec_from_file_location("lexicon_lookup", TARGET)
LOOKUP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LOOKUP)
SYNC_TARGET = TARGET.with_name("sync_lexicons.py")
SYNC_SPEC = importlib.util.spec_from_file_location("sync_lexicons", SYNC_TARGET)
SYNC = importlib.util.module_from_spec(SYNC_SPEC)
SYNC_SPEC.loader.exec_module(SYNC)
FIXTURES = json.loads((TARGET.parent.parent / "references" /
                       "copy-fixtures.json").read_text())["lookup"]
ROOT = TARGET.parent.parent


def has_source(query, source):
    return any(item["source"] == source
               for item in LOOKUP.lookup(query, [source], False, 8))


checks = {
    "technical terminology": has_source("kernel", "technical"),
    "OpenCC conversion": has_source(FIXTURES["opencc"], "opencc"),
    "CC-CEDICT headword": has_source(FIXTURES["cedict"], "cc-cedict"),
    "Unihan variants": has_source(FIXTURES["unihan"], "unihan"),
    "McBopomofo candidate": has_source(FIXTURES["mcbopomofo"], "mcbopomofo"),
}
ascii_environment = os.environ.copy()
ascii_environment.update({
    "LC_ALL": "C",
    "PYTHONCOERCECLOCALE": "0",
    "PYTHONUTF8": "0",
})
ascii_lookup = subprocess.run(
    [sys.executable, str(TARGET), "kernel", "--source", "technical"],
    check=False, capture_output=True, env=ascii_environment)
checks["lookup uses UTF-8 outside a UTF-8 locale"] = (
    ascii_lookup.returncode == 0
    and "核心".encode() in ascii_lookup.stdout)
terms = json.loads((ROOT / "references/technical-terms.json").read_text())
checks["preserved terms do not have translations"] = not (
    set(terms["preserve"]) & {item["en"] for item in terms["terms"]})
package_atom = LOOKUP.lookup("package atom", ["technical"], False, 8)
checks["preserved term has one result"] = (
    len(package_atom) == 1 and package_atom[0]["authority"] == "project-policy")
config = json.loads((ROOT / "references/lexicon-sources.json").read_text())
manifest = json.loads((ROOT / "lexicons/manifest.json").read_text())
moegirl = next(source for source in config["sources"] if source["id"] == "moegirl")
zhwiki = next(source for source in config["sources"] if source["id"] == "zhwiki")
checks["Moegirl is an optional source"] = moegirl.get("bundled") is False
checks["Chinese Wikipedia is an optional source"] = zhwiki.get("bundled") is False
with tempfile.TemporaryDirectory(prefix="chinese-skill-moegirl-") as raw_root:
    original_lexicons = LOOKUP.LEXICONS
    LOOKUP.LEXICONS = pathlib.Path(raw_root)
    (LOOKUP.LEXICONS / "optional" / "moegirl").mkdir(parents=True)
    with gzip.open(LOOKUP.LEXICONS / "optional" / "moegirl" /
                   moegirl["file"], "wt") as handle:
        handle.write(FIXTURES["moegirl"] + "\n")
    checks["optional Moegirl lookup"] = has_source(FIXTURES["moegirl"], "moegirl")
    (LOOKUP.LEXICONS / "optional" / "zhwiki").mkdir()
    with gzip.open(LOOKUP.LEXICONS / "optional" / "zhwiki" /
                   zhwiki["file"], "wt") as handle:
        handle.write("---\nname: test\n...\n維基百科\twei ji bai ke\n")
    checks["optional Chinese Wikipedia lookup"] = has_source("維基百科", "zhwiki")
    LOOKUP.LEXICONS = original_lexicons
checks["missing optional Moegirl data is accepted"] = not has_source(
    FIXTURES["moegirl"], "moegirl")
checks["snapshot manifest complete"] = not SYNC.snapshot_failures(
    config, manifest, ROOT / "lexicons")
incomplete = copy.deepcopy(manifest)
incomplete["sources"] = incomplete["sources"][1:]
checks["missing source is rejected"] = any(
    "missing source in manifest" in failure
    for failure in SYNC.snapshot_failures(config, incomplete, ROOT / "lexicons"))
non_bundled = copy.deepcopy(manifest)
non_bundled["sources"].append({
    "id": moegirl["id"],
    "version": moegirl["version"],
    "authority": moegirl["authority"],
    "license": moegirl["license"],
    "files": [],
})
checks["non-bundled source is rejected"] = any(
    "non-bundled source in manifest" in failure
    for failure in SYNC.snapshot_failures(config, non_bundled, ROOT / "lexicons"))
with tempfile.TemporaryDirectory(prefix="chinese-skill-inventory-") as raw_root:
    inventory = pathlib.Path(raw_root)
    for path in (ROOT / "lexicons").rglob("*"):
        if path.is_file():
            target = inventory / path.relative_to(ROOT / "lexicons")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
    (inventory / "unrecorded.txt").write_text("unknown\n")
    checks["unrecorded lexicon file is rejected"] = any(
        "unrecorded lexicon file" in failure
        for failure in SYNC.snapshot_failures(config, manifest, inventory))
checks["NAER terminology"] = has_source(FIXTURES["naer"], "naer")
checks["regional conversion"] = has_source(FIXTURES["zhconversion"], "zhconversion")
checks["segmentation corpus"] = has_source(FIXTURES["jieba"], "jieba")
checks["THUOCL domain corpus"] = has_source("初始化", "thuocl")
checks["Rime essay corpus"] = has_source("一一映射", "rime-essay")
checks["every source names a license file"] = all(
    "license_file" in source
    for source in json.loads((ROOT / "references/lexicon-sources.json").read_text())["sources"])
relaxed_context = SYNC.tls_context(True)
checks["relaxed TLS keeps peer verification"] = (
    relaxed_context.check_hostname
    and relaxed_context.verify_mode == SYNC.ssl.CERT_REQUIRED
    and not relaxed_context.verify_flags & SYNC.ssl.VERIFY_X509_STRICT)
checks["default TLS uses urllib defaults"] = SYNC.tls_context(False) is None

reference = list(LOOKUP.reference_results())
checks["reference sources listed"] = (
    len(reference) == len(config["reference_only"])
    and all(item["detail"].count("http") >= 1 for item in reference))
checks["reference ids are unique"] = (
    len({item["id"] for item in config["reference_only"]}) == len(reference))
enforced = [item for item in terms["terms"] if item.get("enforce")]
checks["enforced terms differ per locale"] = all(
    item["zh-CN"] != item["zh-TW"] for item in enforced)
checks["rejected forms differ from the preferred form"] = all(
    preferred not in item.get("reject", {}).get(locale, [])
    for item in terms["terms"]
    for locale, preferred in (("zh-TW", item["zh-TW"]), ("zh-CN", item["zh-CN"])))
checks["term keys are unique"] = len({item["en"] for item in terms["terms"]}) == len(
    terms["terms"])
preferred_forms = {
    locale: {item[locale] for item in terms["terms"]}
    for locale in ("zh-CN", "zh-TW")
}
checks["rejected forms do not conflict with preferred terms"] = all(
    rejected not in preferred_forms[locale]
    for item in terms["terms"]
    for locale in ("zh-CN", "zh-TW")
    for rejected in item.get("reject", {}).get(locale, []))
term_by_name = {item["en"]: item for item in terms["terms"]}
checks["Git Traditional terminology"] = (
    term_by_name["remote repository"]["zh-TW"] == "遠端版本庫"
    and term_by_name["trailer"]["zh-TW"] == "結尾資訊")
checks["reference metadata listed"] = all(
    "checked=" in item["detail"] for item in reference)
for value in ("0", "-1"):
    result = subprocess.run(
        [sys.executable, str(TARGET), "軟體", "--limit", value],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    checks[f"limit {value} is rejected"] = result.returncode == 2
incompatible_reference = subprocess.run(
    [sys.executable, str(TARGET), "term", "--reference"],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
checks["reference arguments are exclusive"] = incompatible_reference.returncode == 2

original_root = SYNC.ROOT
original_destination = SYNC.DESTINATION
with tempfile.TemporaryDirectory(prefix="chinese-skill-sync-") as raw_root:
    temporary_root = pathlib.Path(raw_root)
    SYNC.ROOT = temporary_root
    SYNC.DESTINATION = temporary_root / "lexicons"
    SYNC.DESTINATION.mkdir()
    (SYNC.DESTINATION / "sample.txt").write_text("old\n")
    staged = SYNC.stage_snapshots()
    SYNC.atomic_write(staged / "sample.txt", b"new\n")
    checks["staging does not mutate active snapshots"] = (
        (SYNC.DESTINATION / "sample.txt").read_text() == "old\n")
    SYNC.replace_snapshots(staged)
    checks["staged snapshots replace the complete directory"] = (
        (SYNC.DESTINATION / "sample.txt").read_text() == "new\n")

    staged = SYNC.stage_snapshots()
    SYNC.atomic_write(staged / "sample.txt", b"broken\n")
    real_replace = SYNC.os.replace
    calls = 0

    def fail_new_tree(source, destination):
        global calls
        calls += 1
        if calls == 2:
            raise OSError("injected replacement failure")
        return real_replace(source, destination)

    SYNC.os.replace = fail_new_tree
    try:
        try:
            SYNC.replace_snapshots(staged)
        except OSError:
            pass
        checks["failed replacement restores active snapshots"] = (
            (SYNC.DESTINATION / "sample.txt").read_text() == "new\n")
    finally:
        SYNC.os.replace = real_replace

    optional_source = copy.deepcopy(moegirl)
    optional_data = (FIXTURES["moegirl"] + "\n").encode()
    optional_source["sha256"] = SYNC.digest(optional_data)
    wiki_source = copy.deepcopy(zhwiki)
    wiki_data = b'---\nname: test\n...\nWikipedia\twei ji bai ke\n'
    wiki_source["sha256"] = SYNC.digest(wiki_data)
    real_fetch = SYNC.fetch

    def optional_fetch(url, relaxed_tls=False):
        if url == optional_source["url"]:
            return optional_data
        if url == wiki_source["url"]:
            return wiki_data
        return b"test license\n"

    SYNC.fetch = optional_fetch
    try:
        SYNC.synchronize_optional(optional_source, True)
        optional_destination = SYNC.DESTINATION / "optional" / "moegirl"
        optional_manifest = json.loads(
            (optional_destination / "manifest.json").read_text())
        checks["optional synchronization is isolated"] = (
            (optional_destination / optional_source["file"]).is_file()
            and not SYNC.snapshot_failures(
                SYNC.optional_config(optional_source), optional_manifest,
                optional_destination))
        SYNC.synchronize_optional(wiki_source, True)
        wiki_destination = SYNC.DESTINATION / "optional" / "zhwiki"
        checks["optional sources coexist"] = (
            optional_destination.is_dir()
            and (wiki_destination / wiki_source["file"]).is_file())
        SYNC.verify_optional({"sources": [optional_source, wiki_source]})
    finally:
        SYNC.fetch = real_fetch
SYNC.ROOT = original_root
SYNC.DESTINATION = original_destination
for name, passed in checks.items():
    print(f"{'PASS' if passed else 'FAIL'} {name}")
raise SystemExit(0 if all(checks.values()) else 1)
