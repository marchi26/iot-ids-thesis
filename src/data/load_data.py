from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.utils.paths import resolve_project_path


class DatasetNotFoundError(FileNotFoundError):
    """Raised when the TON_IoT dataset is not available locally."""


class DatasetValidationError(ValueError):
    """Raised when the dataset exists but does not match the expected schema."""


def format_dataset_missing_message(csv_path: str | Path = "data/raw/train_test_network.csv") -> str:
    path = Path(csv_path).as_posix()
    return (
        f"Dataset not found: {path}\n"
        "Please download the TON_IoT / UNSW dataset and place train_test_network.csv inside data/raw/.\n"
        "No experiments were executed and no metrics were generated."
    )


def read_csv_robust(csv_path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(csv_path, engine="pyarrow")
    except Exception:
        return pd.read_csv(csv_path)


def validate_dataset_file(csv_path: Path, required_columns: list[str]) -> None:
    if not csv_path.exists():
        raise DatasetNotFoundError(format_dataset_missing_message("data/raw/train_test_network.csv"))
    if not csv_path.is_file():
        raise DatasetNotFoundError(
            f"Dataset path is not a file: {csv_path}\n"
            "No experiments were executed and no metrics were generated."
        )

    header = pd.read_csv(csv_path, nrows=0)
    missing_columns = [column for column in required_columns if column not in header.columns]
    if missing_columns:
        raise DatasetValidationError(
            f"Dataset file {csv_path} is missing required columns: {missing_columns}. "
            f"Available columns: {list(header.columns)}\n"
            "No experiments were executed and no metrics were generated."
        )


def load_ton_iot_dataset(
    csv_path: str | Path = "data/raw/train_test_network.csv",
    required_columns: list[str] | None = None,
) -> pd.DataFrame:
    resolved_path = resolve_project_path(csv_path)
    validate_dataset_file(resolved_path, required_columns or ["label", "type"])
    return read_csv_robust(resolved_path)
