from economic_news_research.text_normalization import normalize_news_text


def test_normalize_news_text_removes_urls_and_extra_spaces() -> None:
    text = "Revenue   rose. Read more at https://example.com/page"

    assert normalize_news_text(text) == "Revenue rose. Read more at"


def test_normalize_news_text_removes_common_nasdaq_boilerplate() -> None:
    text = (
        "Fintel reports that on December 13, 2023, analysts updated coverage. "
        "See our leaderboard of companies with the largest price target upside. "
        "Revenue rose."
    )

    assert normalize_news_text(text) == "Analysts updated coverage. Revenue rose."


def test_normalize_news_text_handles_none_conservatively() -> None:
    assert normalize_news_text(None) == ""
