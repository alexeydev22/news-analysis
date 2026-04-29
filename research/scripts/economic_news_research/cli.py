import argparse
from pathlib import Path

import pandas as pd

from economic_news_research.data import load_news_dataset, split_news_dataset
from economic_news_research.eda import save_eda_artifacts
from economic_news_research.embedding import TextEmbedder, train_embedding_classifier
from economic_news_research.modeling import train_baseline_model
from economic_news_research.paths import DEFAULT_RAW_DATASET, MODELS_DIR, REPORTS_DIR
from economic_news_research.tracking import (
    log_baseline_to_mlflow,
    save_baseline_artifacts,
    save_model_artifacts,
)
from economic_news_research.transformer import (
    TinyTransformerTrainer,
    train_tiny_transformer_classifier,
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
    log_baseline_to_mlflow(result, artifact_dir=output_dir)


def run_train_embedding(
    *,
    dataset_path: Path,
    output_dir: Path,
    random_state: int,
    embedder: TextEmbedder | None = None,
) -> None:
    dataset = load_news_dataset(dataset_path)
    split = split_news_dataset(dataset, random_state=random_state)
    result = train_embedding_classifier(
        split,
        embedder=embedder,
        random_state=random_state,
    )

    save_model_artifacts(result, output_dir=output_dir)
    log_baseline_to_mlflow(result, artifact_dir=output_dir)


def run_train_transformer(
    *,
    dataset_path: Path,
    output_dir: Path,
    random_state: int,
    trainer: TinyTransformerTrainer | None = None,
) -> None:
    dataset = load_news_dataset(dataset_path)
    split = split_news_dataset(dataset, random_state=random_state)
    result = train_tiny_transformer_classifier(
        split,
        trainer=trainer,
        random_state=random_state,
    )

    save_model_artifacts(result, output_dir=output_dir)
    log_baseline_to_mlflow(result, artifact_dir=output_dir)


def run_compare_models(*, comparison_paths: list[Path], output_path: Path) -> Path:
    frames = [pd.read_csv(path) for path in comparison_paths if path.exists()]
    if not frames:
        raise FileNotFoundError("No model comparison files found")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.concat(frames, ignore_index=True).to_csv(output_path, index=False)
    return output_path


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

    if args.command == "train-embedding":
        run_train_embedding(
            dataset_path=args.dataset,
            output_dir=args.output_dir,
            random_state=args.random_state,
        )
        print(f"embedding_output_dir={args.output_dir}")
        return

    if args.command == "train-transformer":
        run_train_transformer(
            dataset_path=args.dataset,
            output_dir=args.output_dir,
            random_state=args.random_state,
        )
        print(f"transformer_output_dir={args.output_dir}")
        return

    if args.command == "compare-models":
        comparison_paths = args.comparison or _default_comparison_paths()
        try:
            output_path = run_compare_models(
                comparison_paths=comparison_paths,
                output_path=args.output_path,
            )
        except FileNotFoundError as error:
            parser.error(str(error))
        print(f"comparison_path={output_path}")
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

    embedding_parser = subparsers.add_parser("train-embedding")
    embedding_parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_RAW_DATASET,
    )
    embedding_parser.add_argument(
        "--output-dir",
        type=Path,
        default=MODELS_DIR / "embedding",
    )
    embedding_parser.add_argument(
        "--random-state",
        type=int,
        default=42,
    )

    transformer_parser = subparsers.add_parser("train-transformer")
    transformer_parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_RAW_DATASET,
    )
    transformer_parser.add_argument(
        "--output-dir",
        type=Path,
        default=MODELS_DIR / "transformer",
    )
    transformer_parser.add_argument(
        "--random-state",
        type=int,
        default=42,
    )

    compare_parser = subparsers.add_parser("compare-models")
    compare_parser.add_argument(
        "--comparison",
        action="append",
        type=Path,
        default=None,
    )
    compare_parser.add_argument(
        "--output-path",
        type=Path,
        default=MODELS_DIR / "model_comparison.csv",
    )

    return parser


def _default_comparison_paths() -> list[Path]:
    return [
        MODELS_DIR / "baseline" / "model_comparison.csv",
        MODELS_DIR / "embedding" / "model_comparison.csv",
        MODELS_DIR / "transformer" / "model_comparison.csv",
    ]


if __name__ == "__main__":
    main()
