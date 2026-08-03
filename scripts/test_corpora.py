#!/usr/bin/env python3
"""Regression tests for selective corpus retrieval."""

import json
import pathlib
import runpy
import subprocess
import sys


TARGET = pathlib.Path(__file__).with_name("corpus_lookup.py")
VERIFIER = pathlib.Path(__file__).with_name("verify_corpora.py")


def invoke(*arguments):
    return subprocess.run(
        [sys.executable, str(TARGET), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


checks = {}

verifier = runpy.run_path(str(VERIFIER), run_name="corpus_verifier_test")
checks["Git blob calculation"] = (
    verifier["git_blob"](b"test") == "30d74d258442c7c65512eafab474568dd706c430"
)
checks["GitHub rate limit classification"] = (
    verifier["is_rate_limit"](
        403, {"X-RateLimit-Remaining": "0"}, b"")
    and verifier["is_rate_limit"](
        403, {}, b'{"message":"API rate limit exceeded"}')
    and not verifier["is_rate_limit"](403, {}, b"forbidden")
    and verifier["is_rate_limit"](429, {}, b"")
    and not verifier["is_rate_limit"](404, {}, b"not found")
)

readme_list = invoke("readme", "--list")
listed = json.loads(readme_list.stdout)
checks["README pattern index"] = (
    readme_list.returncode == 0
    and len(listed["patterns"]) == 13
    and all(set(item) <= {"id", "group", "origin", "surface"}
            for item in listed["patterns"])
)

identity = invoke("readme", "--pattern", "identity")
identity_data = json.loads(identity.stdout)
checks["README pattern evidence"] = (
    identity.returncode == 0
    and identity_data["pattern"]["origin"] == "corpus"
    and {item["id"] for item in identity_data["sources"]}
    == set(identity_data["pattern"]["evidence"])
)

policy = invoke("readme", "--pattern", "claim-evidence")
policy_data = json.loads(policy.stdout)
checks["policy pattern has no false attribution"] = (
    policy.returncode == 0
    and policy_data["pattern"]["origin"] == "policy"
    and policy_data["sources"] == []
)

failure = invoke("ui", "--pattern", "failure", "--locale", "zh-TW")
failure_data = json.loads(failure.stdout)
checks["UI locale filters evidence"] = (
    failure.returncode == 0
    and failure_data["sources"]
    and all(entry["locale"] == "zh-TW"
            for source in failure_data["sources"] for entry in source["files"])
)

source = invoke("readme", "--source", "gogs-2019")
source_data = json.loads(source.stdout)
checks["pinned source details"] = (
    source.returncode == 0
    and len(source_data["source"]["commit"]) == 40
    and len(source_data["source"]["blob"]) == 40
)

contract = invoke("readme", "--source", "gentoo-zh-overlay")
contract_data = json.loads(contract.stdout)
checks["live contract details"] = (
    contract.returncode == 0
    and contract_data["type"] == "live_contract"
    and contract_data["source"]["checked"]
)

unknown = invoke("ui", "--pattern", "unknown")
checks["unknown pattern is rejected"] = (
    unknown.returncode == 2
    and "unknown ui corpus entry" in unknown.stderr
)

checks["selective output remains compact"] = (
    len(identity.stdout) < 4000 and len(failure.stdout) < 5000
)

failed = False
for name, passed in checks.items():
    print(f"{'PASS' if passed else 'FAIL'} {name}")
    failed |= not passed
raise SystemExit(1 if failed else 0)
