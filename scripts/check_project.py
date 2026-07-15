from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = [
    "README.md",
    "requirements.txt",
    ".gitignore",
    "config/config.yaml",
    "data",
    "data/raw",
    "data/raw/.gitkeep",
    "data/processed",
    "data/processed/.gitkeep",
    "data/README.md",
    "src",
    "src/data",
    "src/models",
    "src/experiments",
    "src/visualization",
    "src/simulation",
    "src/utils",
    "results",
    "results/metrics",
    "results/metrics/.gitkeep",
    "results/plots",
    "results/plots/.gitkeep",
    "results/models",
    "results/models/.gitkeep",
    "results/logs",
    "results/logs/.gitkeep",
    "thesis",
    "scripts",
    "docker-compose.yml",
]

THESIS_FILES = [
    "thesis/chapter_outline.md",
    "thesis/repository_audit.md",
    "thesis/methodology.md",
    "thesis/experimental_results.md",
    "thesis/discussion.md",
    "thesis/iot_simulation.md",
    "thesis/bibliography_notes.md",
]

CONFIG_KEYS = [
    "dataset:",
    "raw_dir:",
    "raw_file:",
    "processed_dir:",
    "binary_target:",
    "multiclass_target:",
    "experiment:",
    "classification_mode:",
    "test_size:",
    "random_seed:",
    "outputs:",
    "metrics_dir:",
    "plots_dir:",
    "models_dir:",
    "logs_dir:",
]

GITIGNORE_RULES = [
    ".venv/",
    "venv/",
    "**pycache**/",
    "*.pyc",
    ".ipynb_checkpoints/",
    "data/raw/*",
    "!data/raw/.gitkeep",
    "data/processed/*",
    "!data/processed/.gitkeep",
    "results/models/*",
    "!results/models/.gitkeep",
    "results/logs/*",
    "!results/logs/.gitkeep",
    "*.pkl",
    "*.joblib",
    ".env",
    ".DS_Store",
    "kaggle.json",
    ".kaggle/",
]


def check_paths() -> list[str]:
    return [path for path in REQUIRED_PATHS + THESIS_FILES if not (ROOT / path).exists()]


def check_config() -> list[str]:
    text = (ROOT / "config/config.yaml").read_text(encoding="utf-8")
    return [key for key in CONFIG_KEYS if key not in text]


def check_gitignore() -> list[str]:
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    return [rule for rule in GITIGNORE_RULES if rule not in text]


def check_generated_outputs() -> list[Path]:
    outputs: list[Path] = []
    for folder in [ROOT / "results/metrics", ROOT / "results/plots"]:
        outputs.extend(path for path in folder.iterdir() if path.is_file() and path.name != ".gitkeep")
    return outputs


def check_example_outputs() -> list[str]:
    suspicious = ["0.9903", "0.9694", "example metric", "example plot", "sample result"]
    findings: list[str] = []
    for path in list((ROOT / "thesis").glob("*.md")) + [ROOT / "README.md"]:
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for marker in suspicious:
            if marker in text:
                findings.append(f"{path.relative_to(ROOT)} contains suspicious marker: {marker}")
    return findings


def main() -> int:
    print("Static project validation")
    print("=========================")

    missing_paths = check_paths()
    missing_config = check_config()
    missing_gitignore = check_gitignore()
    generated_outputs = check_generated_outputs()
    example_findings = check_example_outputs()
    dataset = ROOT / "data/raw/train_test_network.csv"

    print(f"Dataset: {'present' if dataset.exists() else 'missing/pending'}")
    print(f"Required paths: {'OK' if not missing_paths else 'MISSING'}")
    for item in missing_paths:
        print(f" - {item}")

    print(f"Config keys: {'OK' if not missing_config else 'MISSING'}")
    for item in missing_config:
        print(f" - {item}")

    print(f".gitignore rules: {'OK' if not missing_gitignore else 'MISSING'}")
    for item in missing_gitignore:
        print(f" - {item}")

    if generated_outputs:
        print("Generated result files found:")
        for path in generated_outputs:
            print(f" - {path.relative_to(ROOT)}")
    else:
        print("Generated result files: none")

    if example_findings:
        print("Suspicious example-output markers found:")
        for finding in example_findings:
            print(f" - {finding}")
    else:
        print("Example-output markers: none")

    failed = bool(missing_paths or missing_config or missing_gitignore or example_findings)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
