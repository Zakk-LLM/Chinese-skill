#!/usr/bin/env python3
"""Return one writing pattern or source without loading an entire corpus."""

import argparse
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parent.parent
CORPORA = {
    "readme": ROOT / "references" / "readme-corpus.json",
    "ui": ROOT / "references" / "ui-corpus.json",
    "writing": ROOT / "references" / "writing-sources.json",
}


def load_corpus(name):
    return json.loads(CORPORA[name].read_text(encoding="utf-8"))


def all_patterns(name, data):
    groups = ["patterns"]
    if name == "readme":
        groups.append("professional_patterns")
    for group in groups:
        for pattern in data[group]:
            yield group, pattern


def pattern_result(name, data, identifier, locale):
    match = next(((group, pattern) for group, pattern in all_patterns(name, data)
                  if pattern["id"] == identifier), None)
    if match is None:
        raise KeyError(identifier)
    group, pattern = match
    by_id = {source["id"]: source for source in data["sources"]}
    sources = []
    for source_id in pattern["evidence"]:
        source = by_id[source_id]
        summary = {"id": source_id, "repository": source["repository"]}
        if name in {"readme", "writing"}:
            summary["url"] = source["url"]
        else:
            files = [{"locale": entry["locale"], "url": entry["url"]}
                     for entry in source["files"]
                     if locale is None or entry["locale"] == locale]
            if not files:
                continue
            summary["files"] = files
        sources.append(summary)
    return {
        "corpus": name,
        "group": group,
        "pattern": pattern,
        "sources": sources,
    }


def source_result(name, data, identifier):
    groups = [("source", data["sources"])]
    if name == "readme":
        groups.append(("live_contract", data["live_contracts"]))
    for source_type, sources in groups:
        match = next((source for source in sources if source["id"] == identifier), None)
        if match is not None:
            return {"corpus": name, "type": source_type, "source": match}
    raise KeyError(identifier)


def list_result(name, data):
    patterns = []
    for group, pattern in all_patterns(name, data):
        item = {
            "id": pattern["id"],
            "group": group,
            "origin": pattern["origin"],
        }
        if "surface" in pattern:
            item["surface"] = pattern["surface"]
        patterns.append(item)
    return {"corpus": name, "patterns": patterns}


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="Retrieve one selected writing corpus entry.")
    parser.add_argument("corpus", choices=sorted(CORPORA))
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--list", action="store_true",
                        help="list pattern identifiers without full rules")
    action.add_argument("--pattern", help="return one writing pattern")
    action.add_argument("--source", help="return one pinned source record")
    parser.add_argument("--locale", choices=("zh-CN", "zh-TW", "zh-Hans", "zh-Hant"),
                        help="limit UI evidence files to one locale")
    args = parser.parse_args()
    if args.locale and args.corpus != "ui":
        parser.error("--locale is only valid for the UI corpus")

    data = load_corpus(args.corpus)
    try:
        if args.list:
            result = list_result(args.corpus, data)
        elif args.pattern:
            result = pattern_result(args.corpus, data, args.pattern, args.locale)
        else:
            result = source_result(args.corpus, data, args.source)
    except KeyError as error:
        parser.error(f"unknown {args.corpus} corpus entry: {error.args[0]}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
