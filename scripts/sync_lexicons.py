#!/usr/bin/env python3
"""Download licensed lexicon snapshots and record their provenance."""

import argparse
import datetime
import gzip
import hashlib
import json
import os
import pathlib
import shutil
import ssl
import tempfile
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = ROOT / "references" / "lexicon-sources.json"
DESTINATION = ROOT / "lexicons"
USER_AGENT = "Chinese-skill lexicon sync/1.0"
LICENSES = {
    "Apache-2.0.txt": "https://www.apache.org/licenses/LICENSE-2.0.txt",
    "CC-BY-SA-4.0.txt": "https://creativecommons.org/licenses/by-sa/4.0/legalcode.txt",
    "CC-BY-NC-SA-3.0.txt": "https://creativecommons.org/licenses/by-nc-sa/3.0/legalcode.txt",
    "GPL-2.0.txt": (
        "https://raw.githubusercontent.com/wikimedia/mediawiki/REL1_43/COPYING"
    ),
    "Jieba-MIT.txt": (
        "https://raw.githubusercontent.com/fxsjy/jieba/v0.42.1/LICENSE"
    ),
    "McBopomofo-MIT.txt": (
        "https://raw.githubusercontent.com/openvanilla/fcitx5-mcbopomofo/"
        "07dd922ddab159dd4c1865dee73f009aa3c8fdc1/LICENSE.txt"
    ),
    "OGDL-1.0.txt": None,
    "Rime-LGPL-3.0.txt": (
        "https://raw.githubusercontent.com/rime/rime-essay/"
        "e9b1a374a6ea015fca5bdd04318924b4483ac35a/LICENSE"
    ),
    "THUOCL-MIT.txt": (
        "https://raw.githubusercontent.com/thunlp/THUOCL/"
        "a30ce79d895d01ab5132a5c74c29703ff7efb4cc/LICENSE"
    ),
    "Unicode-3.0.txt": "https://www.unicode.org/license.txt",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def tls_context(relaxed):
    """Keep chain and hostname verification; drop only the RFC 5280 strict checks."""
    if not relaxed:
        return None
    context = ssl.create_default_context()
    context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return context


def fetch(url, relaxed_tls=False):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=90,
                                context=tls_context(relaxed_tls)) as response:
        return response.read()


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        handle.write(data)
        temporary = pathlib.Path(handle.name)
    os.chmod(temporary, 0o644)
    os.replace(temporary, path)


def stored_data(source_data, file_format):
    if file_format != "plain-to-gzip":
        return source_data
    return gzip.compress(source_data, compresslevel=9, mtime=0)


def existing_source_digest(path, file_format):
    data = path.read_bytes()
    if file_format == "plain-to-gzip":
        data = gzip.decompress(data)
    return digest(data)


def source_files(source):
    if "files" in source:
        return source["files"]
    return [{key: source[key]
             for key in ("url", "file", "format", "sha256", "relaxed_tls")
             if key in source}]


def required_license_names(sources):
    return {item["license_file"] for item in sources}


def bundled_sources(config):
    return [source for source in config["sources"] if source.get("bundled", True)]


def sync_file(source_id, item, refresh, destination=DESTINATION):
    path = destination / item["file"]
    expected = item.get("sha256")
    if path.exists() and not refresh:
        source_hash = existing_source_digest(path, item["format"])
        if expected and source_hash != expected:
            raise ValueError(f"{path.name}: existing source digest does not match")
        return {
            "path": path.name,
            "source_sha256": source_hash,
            "stored_sha256": digest(path.read_bytes()),
            "bytes": path.stat().st_size,
            "state": "existing",
        }

    data = fetch(item["url"], item.get("relaxed_tls", False))
    source_hash = digest(data)
    if expected and source_hash != expected:
        raise ValueError(
            f"{source_id}: expected {expected}, received {source_hash}")
    output = stored_data(data, item["format"])
    atomic_write(path, output)
    return {
        "path": path.name,
        "source_sha256": source_hash,
        "stored_sha256": digest(output),
        "bytes": len(output),
        "state": "downloaded",
    }


def sync_license(name, url, refresh, destination=DESTINATION):
    path = destination / "licenses" / name
    if url is None:
        if not path.exists():
            raise SystemExit(f"license notice must be maintained in the repository: {name}")
    elif not path.exists() or refresh:
        atomic_write(path, fetch(url))
    return {
        "path": str(path.relative_to(destination)),
        "sha256": digest(path.read_bytes()),
        "bytes": path.stat().st_size,
    }


def snapshot_failures(config, manifest, destination, ignored_directories=()):
    failures = []
    if manifest.get("schema") != 1:
        failures.append("unsupported manifest schema")
    configured = {source["id"]: source for source in config["sources"]}
    manifest_sources = manifest.get("sources", [])
    manifest_ids = [source.get("id") for source in manifest_sources
                    if isinstance(source, dict)]
    duplicate_ids = {item for item in manifest_ids if manifest_ids.count(item) > 1}
    for source_id in sorted(duplicate_ids):
        failures.append(f"duplicate source in manifest: {source_id}")
    required_ids = {source["id"] for source in bundled_sources(config)}
    missing_ids = required_ids - set(manifest_ids)
    extra_ids = set(manifest_ids) - set(configured)
    non_bundled_ids = (set(manifest_ids) & set(configured)) - required_ids
    failures.extend(f"missing source in manifest: {item}" for item in sorted(missing_ids))
    failures.extend(f"unknown source in manifest: {item}" for item in sorted(extra_ids))
    failures.extend(f"non-bundled source in manifest: {item}"
                    for item in sorted(non_bundled_ids))

    all_recorded_paths = set()
    for manifest_source in manifest_sources:
        if not isinstance(manifest_source, dict) or "id" not in manifest_source:
            failures.append("malformed source in manifest")
            continue
        source = configured.get(manifest_source["id"])
        if not source:
            continue
        for field in ("version", "authority", "license"):
            if manifest_source.get(field) != source.get(field):
                failures.append(f"{source['id']}: manifest {field} does not match config")
        expected_items = {item["file"]: item for item in source_files(source)}
        recorded_items = manifest_source.get("files", [])
        recorded_paths = [item.get("path") for item in recorded_items
                          if isinstance(item, dict)]
        all_recorded_paths.update(path for path in recorded_paths if path)
        duplicate_paths = {item for item in recorded_paths if recorded_paths.count(item) > 1}
        for item in sorted(duplicate_paths):
            failures.append(f"duplicate file in manifest: {item}")
        missing_paths = set(expected_items) - set(recorded_paths)
        extra_paths = set(recorded_paths) - set(expected_items)
        failures.extend(f"missing file in manifest: {item}" for item in sorted(missing_paths))
        failures.extend(f"unknown file in manifest: {item}" for item in sorted(extra_paths))
        recorded = {item.get("path"): item for item in recorded_items
                    if isinstance(item, dict)}
        for filename, item in expected_items.items():
            path = destination / filename
            if not path.exists():
                failures.append(f"missing {path.name}")
                continue
            stored_hash = digest(path.read_bytes())
            source_hash = existing_source_digest(path, item["format"])
            entry = recorded.get(path.name, {})
            if entry.get("stored_sha256") != stored_hash:
                failures.append(f"stored digest changed: {path.name}")
            if entry.get("source_sha256") != source_hash:
                failures.append(f"source digest changed: {path.name}")
            if entry.get("bytes") != path.stat().st_size:
                failures.append(f"stored size changed: {path.name}")
            if item.get("sha256") and item["sha256"] != source_hash:
                failures.append(f"pinned digest changed: {path.name}")

    license_items = manifest.get("licenses", [])
    license_paths = [item.get("path") for item in license_items if isinstance(item, dict)]
    duplicate_licenses = {item for item in license_paths if license_paths.count(item) > 1}
    failures.extend(f"duplicate license in manifest: {item}"
                    for item in sorted(duplicate_licenses))
    present_sources = [configured[source_id] for source_id in manifest_ids
                       if source_id in configured]
    expected_licenses = {
        f"licenses/{name}" for name in required_license_names(present_sources)
    }
    failures.extend(f"missing license in manifest: {item}"
                    for item in sorted(expected_licenses - set(license_paths)))
    failures.extend(f"unknown license in manifest: {item}"
                    for item in sorted(set(license_paths) - expected_licenses))
    for item in license_items:
        if not isinstance(item, dict) or not item.get("path"):
            failures.append("malformed license in manifest")
            continue
        path = destination / item["path"]
        if not path.exists():
            failures.append(f"missing license: {item['path']}")
            continue
        if digest(path.read_bytes()) != item.get("sha256"):
            failures.append(f"license changed: {item['path']}")
        if path.stat().st_size != item.get("bytes"):
            failures.append(f"license size changed: {item['path']}")

    recorded_files = {"ATTRIBUTION.md", "manifest.json", *all_recorded_paths,
                      *license_paths}
    actual_files = set()
    for path in destination.rglob("*"):
        relative = path.relative_to(destination)
        if path.is_file() and (not relative.parts
                               or relative.parts[0] not in ignored_directories):
            actual_files.add(str(relative))
    failures.extend(f"missing lexicon metadata file: {item}"
                    for item in sorted({"ATTRIBUTION.md", "manifest.json"}
                                       - actual_files))
    failures.extend(f"unrecorded lexicon file: {item}"
                    for item in sorted(actual_files - recorded_files))
    return failures


def verify_snapshots(config):
    manifest_path = DESTINATION / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures = snapshot_failures(config, manifest, DESTINATION, {"optional"})
    if failures:
        raise SystemExit("\n".join(failures))
    count = sum(len(source.get("files", [])) for source in manifest["sources"])
    print(f"verified {count} lexicon snapshots")


def clone_file(source, destination):
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def stage_snapshots(destination=None):
    destination = destination or DESTINATION
    destination.parent.mkdir(parents=True, exist_ok=True)
    staged = pathlib.Path(tempfile.mkdtemp(
        prefix=f".{destination.name}-stage-", dir=destination.parent))
    if destination.exists():
        shutil.copytree(destination, staged, dirs_exist_ok=True,
                        copy_function=clone_file, symlinks=True)
    return staged


def replace_snapshots(staged, destination=None):
    destination = destination or DESTINATION
    backup = None
    try:
        if destination.exists():
            backup = pathlib.Path(tempfile.mkdtemp(
                prefix=f".{destination.name}-old-", dir=destination.parent))
            backup.rmdir()
            os.replace(destination, backup)
        os.replace(staged, destination)
    except BaseException:
        if backup is not None and backup.exists() and not destination.exists():
            os.replace(backup, destination)
        raise
    if backup is not None:
        shutil.rmtree(backup)


def optional_config(source):
    item = dict(source)
    item["bundled"] = True
    return {"schema": 1, "sources": [item]}


def synchronize_optional(source, refresh):
    destination = DESTINATION / "optional" / source["id"]
    synchronized_at = datetime.datetime.now(datetime.UTC).isoformat()
    staged = stage_snapshots(destination)
    try:
        previous_path = staged / "manifest.json"
        previous = (json.loads(previous_path.read_text(encoding="utf-8"))
                    if previous_path.exists() else {})
        files = [sync_file(source["id"], item, refresh, staged)
                 for item in source_files(source)]
        entry = {
            "id": source["id"],
            "version": source["version"],
            "authority": source["authority"],
            "license": source["license"],
            "source_url": source["url"],
            "files": files,
            "verified_at": synchronized_at,
        }
        if any(item["state"] == "downloaded" for item in files):
            entry["retrieved_at"] = synchronized_at
        else:
            previous_entries = previous.get("sources") or [{}]
            if previous_entries[0].get("retrieved_at"):
                entry["retrieved_at"] = previous_entries[0]["retrieved_at"]
        manifest = {
            "schema": 1,
            "generated_at": synchronized_at,
            "sources": [entry],
            "licenses": [],
        }
        for name in sorted(required_license_names([source])):
            manifest["licenses"].append(
                sync_license(name, LICENSES[name], refresh, staged))
        attribution = (
            "# Optional lexicon attribution\n\n"
            f"{source['attribution']}\n\n"
            "The downloaded text is recompressed without changing its contents. "
            "The source URL and digests are recorded in `manifest.json`.\n"
        )
        atomic_write(staged / "ATTRIBUTION.md", attribution.encode())
        atomic_write(staged / "manifest.json",
                     (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode())
        failures = snapshot_failures(optional_config(source), manifest, staged)
        if failures:
            raise SystemExit("optional snapshot validation failed:\n" +
                             "\n".join(failures))
        replace_snapshots(staged, destination)
    finally:
        if staged.exists():
            shutil.rmtree(staged)
    print(f"{source['id']}: {', '.join(item['state'] for item in files)}")
    print(f"manifest: {destination / 'manifest.json'}")


def verify_optional(config):
    destination = DESTINATION / "optional"
    if not destination.exists():
        print("optional lexicons are not installed")
        return
    sources = {source["id"]: source for source in config["sources"]
               if not source.get("bundled", True)}
    failures = []
    installed = []
    for path in sorted(destination.iterdir()):
        if not path.is_dir() or path.name not in sources:
            failures.append(f"unknown optional lexicon path: {path.name}")
            continue
        manifest_path = path / "manifest.json"
        if not manifest_path.is_file():
            failures.append(f"missing optional manifest: {path.name}")
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_ids = [item["id"] for item in manifest.get("sources", [])]
        if manifest_ids != [path.name]:
            failures.append(f"optional manifest does not match directory: {path.name}")
            continue
        failures.extend(snapshot_failures(
            optional_config(sources[path.name]), manifest, path))
        installed.append(path.name)
    if failures:
        raise SystemExit("\n".join(failures))
    if installed:
        print(f"verified {len(installed)} optional lexicon snapshots: "
              f"{', '.join(installed)}")
    else:
        print("optional lexicons are not installed")


def main():
    parser = argparse.ArgumentParser(
        description="Synchronize the lexicons declared in lexicon-sources.json.")
    parser.add_argument("--source", action="append", default=[],
                        help="source id to synchronize; may be repeated")
    parser.add_argument("--refresh", action="store_true",
                        help="download sources even when a snapshot exists")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--list", action="store_true", help="list configured sources")
    action.add_argument("--verify", action="store_true",
                        help="verify snapshots without downloading or writing")
    action.add_argument("--verify-optional", action="store_true",
                        help="verify an installed optional snapshot")
    args = parser.parse_args()

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    sources = config["sources"]
    if (args.list or args.verify or args.verify_optional) and (args.source or args.refresh):
        parser.error("listing and verification cannot be combined with synchronization options")
    if args.list:
        for source in sources:
            state = "bundled" if source.get("bundled", True) else "optional"
            print(f"{source['id']}\t{source['version']}\t{source['license']}\t{state}")
        return 0
    if args.verify:
        verify_snapshots(config)
        return 0
    if args.verify_optional:
        verify_optional(config)
        return 0

    selected = set(args.source)
    known = {source["id"] for source in sources}
    unknown = selected - known
    if unknown:
        parser.error(f"unknown source: {', '.join(sorted(unknown))}")
    optional = {source["id"]: source for source in sources
                if not source.get("bundled", True)}
    selected_optional = selected.intersection(optional)
    if selected_optional:
        if selected != selected_optional or len(selected_optional) != 1:
            parser.error("synchronize one optional source separately")
        synchronize_optional(optional[selected_optional.pop()], args.refresh)
        return 0

    required_ids = {source["id"] for source in bundled_sources(config)}
    targets = selected or required_ids
    partial = bool(selected and not required_ids.issubset(selected))
    previous_path = DESTINATION / "manifest.json"
    previous = (json.loads(previous_path.read_text(encoding="utf-8"))
                if previous_path.exists() else {})
    if partial:
        if not previous:
            parser.error("--source requires an existing complete snapshot manifest")
        failures = snapshot_failures(config, previous, DESTINATION, {"optional"})
        if failures:
            raise SystemExit(
                "cannot perform a partial synchronization:\n" + "\n".join(failures))

    synchronized_at = datetime.datetime.now(datetime.UTC).isoformat()
    manifest = {
        "schema": 1,
        "generated_at": synchronized_at,
        "sources": [],
        "licenses": [],
    }
    previous_sources = {item["id"]: item for item in previous.get("sources", [])}
    staged = stage_snapshots()
    try:
        for source in sources:
            if source["id"] not in targets:
                if source["id"] in previous_sources:
                    entry = dict(previous_sources[source["id"]])
                    entry["verified_at"] = synchronized_at
                    manifest["sources"].append(entry)
                continue
            files = [sync_file(source["id"], item, args.refresh, staged)
                     for item in source_files(source)]
            entry = {
                "id": source["id"],
                "version": source["version"],
                "authority": source["authority"],
                "license": source["license"],
                "files": files,
                "verified_at": synchronized_at,
            }
            if any(item["state"] == "downloaded" for item in files):
                entry["retrieved_at"] = synchronized_at
            elif previous_sources.get(source["id"], {}).get("retrieved_at"):
                entry["retrieved_at"] = previous_sources[source["id"]]["retrieved_at"]
            manifest["sources"].append(entry)
            print(f"{source['id']}: {', '.join(item['state'] for item in files)}")

        refreshed_sources = [source for source in sources if source["id"] in targets]
        refreshed_licenses = required_license_names(refreshed_sources)
        source_by_id = {source["id"]: source for source in sources}
        present_sources = [source_by_id[item["id"]] for item in manifest["sources"]]
        for name in sorted(required_license_names(present_sources)):
            refresh_license = args.refresh and name in refreshed_licenses
            manifest["licenses"].append(
                sync_license(name, LICENSES[name], refresh_license, staged))

        atomic_write(staged / "manifest.json",
                     (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode())
        failures = snapshot_failures(config, manifest, staged, {"optional"})
        if failures:
            raise SystemExit("staged snapshot validation failed:\n" + "\n".join(failures))
        replace_snapshots(staged)
    finally:
        if staged.exists():
            shutil.rmtree(staged)
    print(f"manifest: {DESTINATION / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
