import argparse

import httpx

MODELS = (
    "tfidf-logreg",
    "embedding-logreg",
    "tiny-transformer-classifier",
)


def run_smoke(*, base_url: str, timeout_seconds: float) -> None:
    url = f"{base_url.rstrip('/')}/api/v1/analyze"
    for model in MODELS:
        response = httpx.post(
            url,
            json={
                "text": "ВВП вырос быстрее ожиданий, а инфляция замедлилась.",
                "analysis_model": model,
            },
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if payload["model_name"] != model:
            raise RuntimeError(f"Unexpected model in response: {payload['model_name']}")
        if payload["impact"] not in {"positive", "neutral", "negative"}:
            raise RuntimeError(f"Unexpected impact label: {payload['impact']}")
        print(f"ok: {model} -> {payload['impact']} confidence={payload['confidence']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test trained analysis models.")
    parser.add_argument("--base-url", default="http://localhost:8001")
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    args = parser.parse_args()

    run_smoke(base_url=args.base_url, timeout_seconds=args.timeout_seconds)


if __name__ == "__main__":
    main()
