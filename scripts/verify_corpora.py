#!/usr/bin/env python3
"""Verify pinned writing files and live repository contracts against GitHub."""

import hashlib
import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIGS = (
    ROOT / "references" / "readme-corpus.json",
    ROOT / "references" / "ui-corpus.json",
    ROOT / "references" / "writing-sources.json",
)


def fetch(url):
    headers = {"User-Agent": "Chinese-skill-corpus-verifier"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def is_rate_limit(code, headers, body):
    if code == 429:
        return True
    if code != 403:
        return False
    remaining = (headers or {}).get("X-RateLimit-Remaining", "")
    return remaining == "0" or b"rate limit" in body.lower()


def git_blob(content):
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content, usedforsecurity=False).hexdigest()


def raw_url(repository, commit, file_path):
    quoted_path = urllib.parse.quote(file_path)
    return f"https://raw.githubusercontent.com/{repository}/{commit}/{quoted_path}"


def commit_date(repository, commit, cache):
    key = (repository, commit)
    if key not in cache:
        url = f"https://api.github.com/repos/{repository}/commits/{commit}"
        payload = json.loads(fetch(url))
        cache[key] = payload["commit"]["committer"]["date"][:10]
    return cache[key]


def pinned_entries(data):
    for source in data["sources"]:
        if "files" in source:
            for entry in source["files"]:
                yield source["id"], source["repository"], entry
        else:
            yield source["id"], source["repository"], source


def main():
    failed = False
    limited = False
    dates = {}
    for config_path in CONFIGS:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        for source_id, repository, entry in pinned_entries(data):
            label = f"{source_id}:{entry.get('locale', 'default')}"
            try:
                content = fetch(raw_url(repository, entry["commit"], entry["path"]))
                actual_blob = git_blob(content)
                actual_date = commit_date(repository, entry["commit"], dates)
                if actual_blob != entry["blob"]:
                    print(f"FAIL {label}: Git blob mismatch")
                    failed = True
                elif actual_date != entry["date"]:
                    print(f"FAIL {label}: commit date mismatch")
                    failed = True
                else:
                    print(f"PASS {label}")
            except urllib.error.HTTPError as error:
                body = error.read()
                if is_rate_limit(error.code, error.headers, body):
                    print(f"SKIP {label}: GitHub rate limit; set GITHUB_TOKEN")
                    limited = True
                else:
                    print(f"FAIL {label}: HTTP {error.code}")
                    failed = True
            except (OSError, KeyError, ValueError, json.JSONDecodeError) as error:
                print(f"FAIL {label}: {error}")
                failed = True

        for contract in data.get("live_contracts", []):
            label = f"{contract['id']}:live"
            try:
                content = fetch(raw_url(contract["repository"], "master",
                                        contract["path"]))
                text = content.decode("utf-8")
                missing = [value for value in contract["required_strings"]
                           if value not in text]
                passed = bool(content) and not missing
                print(f"{'PASS' if passed else 'FAIL'} {label}")
                if missing:
                    print(f"FAIL {label}: missing required strings: {missing!r}")
                failed |= not passed
            except urllib.error.HTTPError as error:
                body = error.read()
                if is_rate_limit(error.code, error.headers, body):
                    print(f"SKIP {label}: GitHub rate limit; set GITHUB_TOKEN")
                    limited = True
                else:
                    print(f"FAIL {label}: HTTP {error.code}")
                    failed = True
            except (OSError, UnicodeDecodeError) as error:
                print(f"FAIL {label}: {error}")
                failed = True
    if failed:
        return 1
    return 2 if limited else 0


if __name__ == "__main__":
    raise SystemExit(main())
