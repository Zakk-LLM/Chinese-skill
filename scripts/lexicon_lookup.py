#!/usr/bin/env python3
"""Search the bundled terminology and lexicon snapshots with source labels."""

import argparse
import csv
import gzip
import json
import pathlib
import re
import sys
import zipfile


ROOT = pathlib.Path(__file__).resolve().parent.parent
LEXICONS = ROOT / "lexicons"
TECHNICAL = ROOT / "references" / "technical-terms.json"
CONFIG = ROOT / "references" / "lexicon-sources.json"


def matches(query, values, contains):
    return any(query in value for value in values) if contains else query in values


def technical_results(query, contains):
    data = json.loads(TECHNICAL.read_text(encoding="utf-8"))
    preserved = set(data["preserve"])
    for term in data["preserve"]:
        if matches(query, [term], contains):
            yield {"source": "technical", "authority": "project-policy",
                   "term": term, "detail": "preserve this identifier"}
    for item in data["terms"]:
        if item["en"] in preserved:
            continue
        values = [item["en"], item["zh-CN"], item["zh-TW"]]
        if matches(query, values, contains):
            yield {"source": "technical", "authority": "local-default",
                   "term": item["en"],
                   "detail": f"zh-CN={item['zh-CN']}; zh-TW={item['zh-TW']}; "
                             f"domain={item['domain']}"}


def naer_results(query, contains):
    path = LEXICONS / "naer-computing-2026-08-03.csv.gz"
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            taiwan = [form.strip() for form in re.split("[；;]", row["中文名稱"]) if form.strip()]
            mainland = [form.strip() for form in re.split("[；;]", row["中國大陸譯名"]) if form.strip()]
            if not matches(query, [row["英文名稱"], *taiwan, *mainland], contains):
                continue
            yield {"source": "naer", "authority": "official-terminology",
                   "term": row["英文名稱"],
                   "detail": f"zh-TW={'；'.join(taiwan)}; zh-CN={'；'.join(mainland)}"}


def zhconversion_results(query, contains):
    path = LEXICONS / "mediawiki-zhconversion-REL1_43.php.gz"
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        text = handle.read()
    for table, locale in (("ZH_TO_TW", "zh-TW"), ("ZH_TO_CN", "zh-CN"),
                          ("ZH_TO_HK", "zh-HK")):
        body = text.split(f"{table} = [", 1)[1].split("\n\t];", 1)[0]
        for source, target in re.findall(r"'([^']+)' => '([^']*)'", body):
            if matches(query, [source, target], contains):
                yield {"source": "zhconversion", "authority": "regional-vocabulary",
                       "term": f"{source} → {target}", "detail": f"{locale} table"}


def jieba_results(query, contains):
    path = LEXICONS / "jieba-dict-0.42.1.txt.gz"
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            fields = line.split()
            if len(fields) < 2 or not matches(query, [fields[0]], contains):
                continue
            yield {"source": "jieba", "authority": "segmentation-corpus",
                   "term": fields[0],
                   "detail": f"frequency={fields[1]}; word boundary evidence only"}


THUOCL_FILES = {
    "it": "thuocl-it-2018-11-21.txt.gz",
    "animal": "thuocl-animal-2018-11-21.txt.gz",
    "finance": "thuocl-finance-2018-11-21.txt.gz",
    "car": "thuocl-car-2018-11-21.txt.gz",
    "idiom": "thuocl-idiom-2018-11-21.txt.gz",
    "place": "thuocl-place-2018-11-21.txt.gz",
    "food": "thuocl-food-2018-11-21.txt.gz",
    "law": "thuocl-law-2018-11-21.txt.gz",
    "historical-figures": "thuocl-historical-figures-2018-11-21.txt.gz",
    "medical": "thuocl-medical-2018-11-21.txt.gz",
    "poem": "thuocl-poem-2018-11-21.txt.gz",
}


def thuocl_results(query, contains):
    for category, filename in THUOCL_FILES.items():
        with gzip.open(LEXICONS / filename, "rt", encoding="utf-8") as handle:
            for line in handle:
                fields = line.split()
                if not fields or not matches(query, [fields[0]], contains):
                    continue
                frequency = fields[1] if len(fields) > 1 else "unknown"
                yield {"source": "thuocl", "authority": "candidate-corpus",
                       "term": fields[0],
                       "detail": f"category={category}; frequency={frequency}; "
                                 "domain vocabulary evidence only"}


def rime_essay_results(query, contains):
    path = LEXICONS / "rime-essay-2026-07-13.txt.gz"
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            fields = line.split()
            if not fields or not matches(query, [fields[0]], contains):
                continue
            frequency = fields[1] if len(fields) > 1 else "unknown"
            yield {"source": "rime-essay", "authority": "candidate-corpus",
                   "term": fields[0],
                   "detail": f"frequency={frequency}; input candidate and word "
                             "boundary evidence only"}


def cedict_results(query, contains):
    pattern = re.compile(r"^(\S+) (\S+) \[([^]]+)] /(.*)/$")
    with gzip.open(LEXICONS / "cc-cedict.txt.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            match = pattern.match(line.rstrip())
            if not match or not matches(query, match.group(1, 2), contains):
                continue
            yield {"source": "cc-cedict", "authority": "general-dictionary",
                   "term": f"{match.group(1)} / {match.group(2)}",
                   "detail": f"{match.group(3)}; {match.group(4)[:180]}"}


def opencc_results(query, contains):
    path = LEXICONS / "opencc-1.4.1-resources.zip"
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.endswith(".txt")]
        for name in names:
            for line in archive.read(name).decode().splitlines():
                values = line.split("\t")
                if matches(query, values, contains):
                    yield {"source": "opencc", "authority": "conversion",
                           "term": " → ".join(values), "detail": name}


def moegirl_results(query, contains):
    path = LEXICONS / "optional" / "moegirl" / "moegirl-titles-20260713.txt.gz"
    if not path.exists():
        return
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            title = line.rstrip("\n")
            if matches(query, [title], contains):
                yield {"source": "moegirl", "authority": "candidate-corpus",
                       "term": title, "detail": "article title; not terminology evidence"}


def zhwiki_results(query, contains):
    path = LEXICONS / "optional" / "zhwiki" / "zhwiki-20260416.dict.yaml.gz"
    if not path.exists():
        return
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("#") or "\t" not in line:
                continue
            title = line.split("\t", 1)[0]
            if matches(query, [title], contains):
                yield {"source": "zhwiki", "authority": "candidate-corpus",
                       "term": title,
                       "detail": "Wikipedia-derived entry; not terminology evidence"}


def mcbopomofo_results(query, contains):
    files = [
        ("mcbopomofo-data-3.0.txt.gz", "input candidate"),
        ("mcbopomofo-plain-3.0.txt.gz", "single-character input candidate"),
        ("mcbopomofo-associated-3.0.txt.gz", "associated phrase"),
    ]
    for filename, label in files:
        with gzip.open(LEXICONS / filename, "rt", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("#") or not matches(query, [line], True):
                    continue
                fields = line.rstrip().split()
                if not contains and query not in fields:
                    continue
                yield {"source": "mcbopomofo", "authority": "candidate-corpus",
                       "term": query, "detail": f"{label}: {line.strip()[:180]}"}


def unihan_results(query, contains):
    if contains or not query:
        return
    wanted = {f"U+{ord(character):04X}" for character in query}
    with zipfile.ZipFile(LEXICONS / "unihan-17.0.0.zip") as archive:
        with archive.open("Unihan_Variants.txt") as raw:
            for line in raw:
                text = line.decode().rstrip()
                fields = text.split("\t")
                if len(fields) == 3 and fields[0] in wanted:
                    yield {"source": "unihan", "authority": "character-data",
                           "term": fields[0], "detail": f"{fields[1]}={fields[2]}"}


SEARCHERS = {
    "technical": technical_results,
    "naer": naer_results,
    "zhconversion": zhconversion_results,
    "opencc": opencc_results,
    "cc-cedict": cedict_results,
    "unihan": unihan_results,
    "mcbopomofo": mcbopomofo_results,
    "moegirl": moegirl_results,
    "zhwiki": zhwiki_results,
    "jieba": jieba_results,
    "thuocl": thuocl_results,
    "rime-essay": rime_essay_results,
}


def reference_results():
    for item in json.loads(CONFIG.read_text(encoding="utf-8"))["reference_only"]:
        detail = f"{item['role']}; {item['url']}"
        if item.get("license"):
            detail += f"; license={item['license']}"
        if item.get("checked"):
            detail += f"; checked={item['checked']}"
        if item.get("note"):
            detail += f"; {item['note']}"
        yield {"source": item["id"], "authority": item["authority"],
               "term": item["id"], "detail": detail}


def lookup(query, sources, contains, limit):
    results = []
    for source in sources:
        count = 0
        for item in SEARCHERS[source](query, contains):
            results.append(item)
            count += 1
            if count >= limit:
                break
    return results


def positive_integer(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="Search terminology, conversion data, dictionaries, and corpora.")
    parser.add_argument("query", nargs="?",
                        help="term to search; omit with --reference")
    parser.add_argument("--source", action="append", choices=tuple(SEARCHERS),
                        help="source to search; may be repeated")
    parser.add_argument("--contains", action="store_true",
                        help="match substrings instead of exact terms")
    parser.add_argument("--limit", type=positive_integer, help="results per source")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--reference", action="store_true",
                        help="list the external terminology sources to consult manually")
    args = parser.parse_args()
    if args.reference:
        if args.query or args.source or args.contains or args.limit is not None:
            parser.error("--reference cannot be combined with a query, --source, "
                         "--contains, or --limit")
        results = list(reference_results())
    elif args.query:
        results = lookup(args.query, args.source or list(SEARCHERS),
                         args.contains, args.limit or 8)
    else:
        parser.error("a query is required without --reference")
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif not results:
        print("No lexicon evidence found")
    else:
        for item in results:
            print(f"[{item['source']}; {item['authority']}] {item['term']}")
            print(f"  {item['detail']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
