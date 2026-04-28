import argparse
from pathlib import Path

import mlflow

from economic_news_research.data import load_news_dataset, split_news_dataset
from economic_news_research.eda import save_eda_artifacts
from economic_news_research.modeling import train_baseline_model
from economic_news_research.paths import DEFAULT_RAW_DATASET, MODELS_DIR, REPORTS_DIR
from economic_news_research.tracking import (
    MLFLOW_EXPERIMENT_NAME,
    log_baseline_to_mlflow,
    save_baseline_artifacts,
)


def run_validate(*, dataset_path: Path) -> int:
    dataset = load_news_dataset(dataset_path)
    return len(dataset)


def run_eda(*, dataset_path: Path, output_dir: Path) -> None:
    dataset = load_news_dataset(dataset_path)
    save_eda_artifacts(dataset, output_dir=output_dir)


def run_train_baseline(
    *,
    dataset_path: Path,
    output_dir: Path,
    random_state: int,
) -> None:
    dataset = load_news_dataset(dataset_path)
    split = split_news_dataset(dataset, random_state=random_state)
    result = train_baseline_model(split, random_state=random_state)

    save_baseline_artifacts(result, output_dir=output_dir)
    _configure_mlflow_tracking(output_dir=output_dir)
    log_baseline_to_mlflow(result, artifact_dir=output_dir)


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "validate":
        row_count = run_validate(dataset_path=args.dataset)
        print(f"validated_rows={row_count}")
        return

    if args.command == "eda":
        run_eda(dataset_path=args.dataset, output_dir=args.output_dir)
        print(f"eda_output_dir={args.output_dir}")
        return

    if args.command == "train-baseline":
        run_train_baseline(
            dataset_path=args.dataset,
            output_dir=args.output_dir,
            random_state=args.random_state,
        )
        print(f"baseline_output_dir={args.output_dir}")
        return

    parser.error("unknown command")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="economic-news-research",
        description="Run economic news research pipeline commands.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_RAW_DATASET,
    )

    eda_parser = subparsers.add_parser("eda")
    eda_parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_RAW_DATASET,
    )
    eda_parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPORTS_DIR / "eda",
    )

    train_parser = subparsers.add_parser("train-baseline")
    train_parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_RAW_DATASET,
    )
    train_parser.add_argument(
        "--output-dir",
        type=Path,
        default=MODELS_DIR / "baseline",
    )
    train_parser.add_argument(
        "--random-state",
        type=int,
        default=42,
    )

    return parser


def _configure_mlflow_tracking(*, output_dir: Path) -> None:
    tracking_dir = output_dir.resolve().parent / f"{output_dir.name}-mlflow"
    tracking_dir.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(f"sqlite:///{tracking_dir / 'tracking.db'}")

    if mlflow.get_experiment_by_name(MLFLOW_EXPERIMENT_NAME) is None:
        mlflow.create_experiment(
            MLFLOW_EXPERIMENT_NAME,
            artifact_location=(tracking_dir / "artifacts").as_uri(),
        )


if __name__ == "__main__":
    main()
