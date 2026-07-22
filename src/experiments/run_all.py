from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.data.load_data import DatasetNotFoundError, DatasetValidationError
from src.experiments import generate_result_summary, run_binary, run_extended, run_multiclass
from src.utils.paths import ensure_directory, load_config, resolve_project_path


def run() -> None:
    config = load_config()
    binary_metrics = run_binary.run()
    multiclass_metrics = run_multiclass.run()
    extended_outputs = run_extended.run()
    summary_outputs = generate_result_summary.run()

    summary_path = resolve_project_path(config["outputs"]["metrics_dir"]) / "experiment_summary.txt"
    ensure_directory(summary_path.parent)
    with summary_path.open("w", encoding="utf-8") as stream:
        stream.write("Executed experiments\n")
        stream.write(f"Binary baseline rows: {len(binary_metrics)}\n")
        stream.write(f"Multiclass baseline rows: {len(multiclass_metrics)}\n")
        stream.write(f"Binary extended rows: {len(extended_outputs['binary'])}\n")
        stream.write(f"Multiclass extended rows: {len(extended_outputs['multiclass'])}\n")
        stream.write("Generated summaries:\n")
        for name, path in summary_outputs.items():
            stream.write(f"- {name}: {path}\n")


if __name__ == "__main__":
    try:
        run()
    except (DatasetNotFoundError, DatasetValidationError) as exc:
        print(exc)
        raise SystemExit(1)
