#!/usr/bin/env python3
"""Regenerate dist/index.html from data/news.json.

Usage: python3 scripts/build_site.py
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "news.json"
TEMPLATE_PATH = ROOT / "templates" / "site_template.html"
OUTPUT_PATH = ROOT / "dist" / "index.html"

RETENTION_DAYS = 30
JST = timezone(timedelta(hours=9))


def _is_recent(article, cutoff):
    """An article is recent if its published date is known and within the
    retention window; when the publish date is unknown, fall back to how
    recently it was collected."""
    published = article.get("published_at")
    if published:
        try:
            pub_dt = datetime.strptime(published, "%Y-%m-%d").replace(tzinfo=JST)
            return pub_dt >= cutoff
        except ValueError:
            pass  # unparseable published_at: fall through to collected_at
    collected = article.get("collected_at")
    if collected:
        try:
            return datetime.fromisoformat(collected) >= cutoff
        except ValueError:
            pass
    return True


def load_articles():
    articles = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    cutoff = datetime.now(JST) - timedelta(days=RETENTION_DAYS)
    kept = [a for a in articles if _is_recent(a, cutoff)]
    kept.sort(key=lambda a: a.get("published_at") or a.get("collected_at") or "", reverse=True)
    return kept


def main():
    articles = load_articles()
    # Persist pruning back to data/news.json so the source of truth stays bounded.
    DATA_PATH.write_text(
        json.dumps(articles, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    news_json = json.dumps(articles, ensure_ascii=False).replace("</", "<\\/")
    last_updated = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    output = template.replace("__RAILCAR_NEWS_JSON__", news_json).replace(
        "__RAILCAR_LAST_UPDATED__", last_updated
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(output, encoding="utf-8")
    print(f"Built {OUTPUT_PATH} with {len(articles)} articles (last_updated={last_updated})")


if __name__ == "__main__":
    sys.exit(main())
