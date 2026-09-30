"""Run tests, an independent recount and a repeatability check without training."""
import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from audit_ton_iot_split import ROOT, INITIAL, OUTPUT, sha256, require


def check(csv_path, initial, output):
    started = datetime.now(timezone.utc).isoformat()
    original = {path.name: sha256(path) for path in initial.iterdir() if path.is_file()}
    manifest_path = output / "manifest.json"
    manifest_hash = sha256(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks = []

    def execute(name, command):
        result = subprocess.run([sys.executable, *command], cwd=ROOT, text=True, capture_output=True)
        require(result.returncode == 0, f"{name} failed:\n{result.stdout}\n{result.stderr}")
        checks.append({"name": name, "exit_code": result.returncode,
                       "stdout": result.stdout.strip(), "stderr": result.stderr.strip()})
        print(f"PASS: {name}", flush=True)

    execute("synthetic_and_input_validation_tests", ["scripts/test_audit_ton_iot_split.py"])
    execute("independent_tuple_recount", ["scripts/verify_ton_iot_audit.py", "--csv", str(csv_path),
            "--initial", str(initial), "--output", str(output)])
    with tempfile.TemporaryDirectory(prefix="ton-audit-repeat-") as directory:
        execute("repeat_audit", ["scripts/audit_ton_iot_split.py", "--csv", str(csv_path),
                "--initial", str(initial), "--output", directory])
        repeat = json.loads((Path(directory) / "manifest.json").read_text(encoding="utf-8"))
        for field in ("dataset", "initial_manifest_sha256", "initial_artifacts_sha256", "tasks",
                      "source_sha256", "artifacts_sha256", "packages", "split"):
            require(repeat[field] == manifest[field], f"Repeat execution differs: {field}")
    require(original == {p.name: sha256(p) for p in initial.iterdir() if p.is_file()}, "Initial delivery changed")
    require(sha256(manifest_path) == manifest_hash, "Full audit manifest changed during verification")
    result = {"started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
              "audit_manifest_sha256": manifest_hash, "validator_source_sha256": sha256(Path(__file__)),
              "checks": checks, "repeated_csv_hashes_identical": True,
              "initial_delivery_unchanged": True,
              "repeat_provenance": "Fresh temporary output directory, same interpreter and installed environment. Timestamps and output paths differ; scientific inputs and output hashes match."}
    (output / "validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("All checks passed; validation.json saved.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=ROOT / "data/raw/train_test_network.csv")
    parser.add_argument("--initial", type=Path, default=INITIAL)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    try:
        check(args.csv.resolve(), args.initial.resolve(), args.output.resolve())
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Audit checks failed: {exc}\n")
