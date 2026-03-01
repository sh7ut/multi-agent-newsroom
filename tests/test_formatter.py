from datetime import datetime, timezone

from agents.formatter import FormatterAgent
from services.state import Article


def make_article(source_type: str = "realtime"):
    return Article(
        headline="Headline",
        source="Reuters" if source_type == "realtime" else "Archive Times",
        source_type=source_type,
        url="https://example.com",
        published_at=datetime.now(timezone.utc),
        summary="Summary",
        evidence=[f"{source_type}:source@{datetime.now(timezone.utc).isoformat()}"],
    )


def test_formatter_requires_ten_articles():
    formatter = FormatterAgent()
    articles = [make_article() for _ in range(9)]
    try:
        formatter.format("query", articles)
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_formatter_warns_on_low_archive_coverage():
    formatter = FormatterAgent(min_archive_entries=2)
    articles = [make_article() for _ in range(8)] + [make_article("archive") for _ in range(2)]
    output = formatter.format("query", articles)
    assert "Warnings:" not in output  # 2 archive entries meets threshold

    formatter = FormatterAgent(min_archive_entries=3)
    output_with_warning = formatter.format("query", articles)
    assert "Warnings:" in output_with_warning
