from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.data.load_data import load_ton_iot_dataset
from src.utils.paths import ensure_directory, resolve_project_path


CATEGORICAL_SAFE_COLUMNS = [
    "proto",
    "service",
    "conn_state",
    "dns_qtype",
    "dns_rcode",
    "ssl_version",
    "http_method",
    "http_status_code",
    "weird_name",
]

EXCLUDED_COLUMNS = [
    "ssl_subject",
    "ssl_issuer",
    "http_uri",
    "http_user_agent",
    "http_orig_mime_types",
    "http_resp_mime_types",
    "weird_addl",
    "dns_query",
]


@dataclass
class PreparedData:
    X_train: np.ndarray
    X_test: np.ndarray
    y_train: np.ndarray
    y_test: np.ndarray
    feature_names: list[str]
    preprocessor: ColumnTransformer
    class_names: list[str]
    class_distribution_before: pd.Series
    class_distribution_after: pd.Series


def normalize_binary_target(series: pd.Series) -> pd.Series:
    values = series.astype(str).str.lower().str.strip()
    mapping = {"0": 0, "1": 1, "benign": 0, "normal": 0, "malicious": 1, "attack": 1}
    return values.map(lambda value: mapping.get(value, 1 if value not in ("0", "normal", "benign") else 0)).astype(int)


def prepare_target(df: pd.DataFrame, mode: str, binary_target: str, multiclass_target: str) -> tuple[pd.Series, list[str], str]:
    if mode == "binary":
        if binary_target not in df.columns:
            raise ValueError(
                f"Binary target column '{binary_target}' was not found in the dataset. "
                f"Available columns: {list(df.columns)}"
            )
        y = normalize_binary_target(df[binary_target])
        return y, ["normal", "attack"], binary_target

    if mode == "multiclass":
        if multiclass_target not in df.columns:
            raise ValueError(
                f"Multiclass target column '{multiclass_target}' was not found in the dataset. "
                f"Available columns: {list(df.columns)}"
            )
        y_raw = df[multiclass_target].astype(str).str.strip()
        class_names = sorted(y_raw.unique().tolist())
        mapping = {label: index for index, label in enumerate(class_names)}
        return y_raw.map(mapping).astype(int), class_names, multiclass_target

    raise ValueError("classification mode must be either 'binary' or 'multiclass'.")


def build_feature_frame(df: pd.DataFrame, target_columns: list[str]) -> pd.DataFrame:
    drop_columns = [column for column in target_columns + EXCLUDED_COLUMNS if column in df.columns]
    return df.drop(columns=drop_columns)


def build_preprocessor(X: pd.DataFrame, scale_numeric: bool = True) -> tuple[ColumnTransformer, list[str], list[str]]:
    numeric_columns = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical_columns = [column for column in CATEGORICAL_SAFE_COLUMNS if column in X.columns]

    for column in X.select_dtypes(exclude=[np.number]).columns:
        if column in categorical_columns:
            continue
        if X[column].nunique(dropna=False) <= 40:
            categorical_columns.append(column)

    numeric_steps: list[tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        numeric_steps.append(("scaler", StandardScaler()))

    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", Pipeline(steps=numeric_steps), numeric_columns),
            ("cat", categorical_transformer, categorical_columns),
        ],
        remainder="drop",
    )
    return preprocessor, numeric_columns, categorical_columns


def get_feature_names(preprocessor: ColumnTransformer, numeric_columns: list[str], categorical_columns: list[str]) -> list[str]:
    feature_names = list(numeric_columns)
    if categorical_columns:
        encoder = preprocessor.named_transformers_["cat"].named_steps["onehot"]
        feature_names.extend(encoder.get_feature_names_out(categorical_columns).tolist())
    return feature_names


def prepare_dataset(
    config: dict[str, Any],
    mode: str,
    apply_smote: bool = False,
    save_processed: bool = False,
) -> PreparedData:
    dataset_path = config["dataset"]["raw_file"]
    binary_target = config["dataset"]["binary_target"]
    multiclass_target = config["dataset"]["multiclass_target"]

    df = load_ton_iot_dataset(dataset_path, required_columns=[binary_target, multiclass_target])
    y, class_names, active_target = prepare_target(df, mode, binary_target, multiclass_target)
    X = build_feature_frame(df, target_columns=[binary_target, multiclass_target])
    if X.empty:
        raise ValueError("No usable feature columns remain after dropping targets and excluded columns.")

    class_distribution_before = y.value_counts().sort_index()

    X_train_df, X_test_df, y_train, y_test = train_test_split(
        X,
        y,
        test_size=float(config["experiment"]["test_size"]),
        random_state=int(config["experiment"]["random_seed"]),
        stratify=y,
    )

    preprocessor, numeric_columns, categorical_columns = build_preprocessor(
        X_train_df,
        scale_numeric=bool(config["preprocessing"].get("scale_numeric", True)),
    )
    X_train = preprocessor.fit_transform(X_train_df)
    X_test = preprocessor.transform(X_test_df)

    if apply_smote:
        min_class_count = int(pd.Series(y_train).value_counts().min())
        if min_class_count < 2:
            raise ValueError("SMOTE requires at least two samples in every training class.")
        smote = SMOTE(
            random_state=int(config["experiment"]["random_seed"]),
            k_neighbors=min(5, min_class_count - 1),
        )
        X_train, y_train = smote.fit_resample(X_train, y_train)

    y_train_array = np.asarray(y_train)
    y_test_array = np.asarray(y_test)
    class_distribution_after = pd.Series(y_train_array).value_counts().sort_index()
    feature_names = get_feature_names(preprocessor, numeric_columns, categorical_columns)

    if save_processed:
        processed_dir = ensure_directory(resolve_project_path(config["dataset"]["processed_dir"]))
        pd.DataFrame(X_train).to_parquet(processed_dir / f"{mode}_X_train.parquet")
        pd.DataFrame(X_test).to_parquet(processed_dir / f"{mode}_X_test.parquet")
        pd.Series(y_train_array, name=active_target).to_csv(processed_dir / f"{mode}_y_train.csv", index=False)
        pd.Series(y_test_array, name=active_target).to_csv(processed_dir / f"{mode}_y_test.csv", index=False)

    return PreparedData(
        X_train=X_train,
        X_test=X_test,
        y_train=y_train_array,
        y_test=y_test_array,
        feature_names=feature_names,
        preprocessor=preprocessor,
        class_names=class_names,
        class_distribution_before=class_distribution_before,
        class_distribution_after=class_distribution_after,
    )
