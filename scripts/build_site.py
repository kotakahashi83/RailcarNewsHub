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


def load_articles():
    articles = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    cutoff = datetime.now(JST) - timedelta(days=RETENTION_DAYS)
    kept = []
    for a in articles:
        collected = a.get("collected_at")
        try:
            collected_dt = datetime.fromisoformat(collected) if collected else None
        except ValueError:
            collected_dt = None
        if collected_dt is not None and collected_dt < cutoff:
            continue
        kept.append(a)
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
