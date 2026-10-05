"""Verify exporter byte provenance without writing files or importing the exporter."""

import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
COMMIT = "5e3aaeff6facb5f8af842e8b11688fe940e02930"
SOURCE = "src/experiments/export_embedded_model.py"
MANIFEST = "research/ton_iot_audit/results/full_audit/manifest.json"
# One-based LF-only lines observed in the matching local copy on 2026-10-05.
LF_LINES = {3, 4, 12, 20, *range(184, 225), 235, 240}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def git_bytes(path):
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{COMMIT}:{path}"])


def verify(blob, expected):
    if b"\r" in blob or len(blob.splitlines(keepends=True)) != 254:
        raise ValueError("Published exporter does not match the documented LF layout")
    reconstructed = b"".join(
        line if number in LF_LINES else line.replace(b"\n", b"\r\n")
        for number, line in enumerate(blob.splitlines(keepends=True), 1)
    )
    if sha256(reconstructed) != expected:
        raise ValueError("Reconstructed bytes do not match the historical manifest")
    if reconstructed.replace(b"\r\n", b"\n") != blob:
        raise ValueError("Differences extend beyond line endings")
    return reconstructed


def main():
    blob = git_bytes(SOURCE)
    manifest = json.loads(git_bytes(MANIFEST))
    expected = manifest["source_sha256"][SOURCE]
    reconstructed = verify(blob, expected)
    local = (ROOT / SOURCE).read_bytes()
    result = {
        "delivery_commit": COMMIT,
        "source": SOURCE,
        "historical_sha256": expected,
        "git_blob_sha1": hashlib.sha1(
            b"blob " + str(len(blob)).encode("ascii") + b"\0" + blob
        ).hexdigest(),
        "git_lf_sha256": sha256(blob),
        "uniform_crlf_sha256": sha256(blob.replace(b"\n", b"\r\n")),
        "reconstructed_sha256": sha256(reconstructed),
        "reconstructed_bytes": len(reconstructed),
        "git_bytes": len(blob),
        "historical_crlf_count": reconstructed.count(b"\r\n"),
        "historical_lf_only_lines": sorted(LF_LINES),
        "normalized_bytes_identical": True,
        "local_sha256": sha256(local),
        "local_matches_historical_bytes": local == reconstructed,
        "local_normalized_matches_git": local.replace(b"\r\n", b"\n") == blob,
        "status": "PASS",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
