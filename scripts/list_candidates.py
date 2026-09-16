#!/usr/bin/env python3
"""Print data/candidates.json compactly for the summarising routine.

  python3 scripts/list_candidates.py                  # all candidates, grouped by category hint
  python3 scripts/list_candidates.py --hint railcar_leasing
  python3 scripts/list_candidates.py --show <url>     # full record incl. excerpt
  python3 scripts/list_candidates.py --days 3         # only items published in the last N days
"""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "data" / "candidates.json"
ORDER = ["railcar_leasing", "rail_industry", "container_leasing", "eu_railcar_leasing", "alt_investment"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hint")
    ap.add_argument("--show")
    ap.add_argument("--days", type=int)
    args = ap.parse_args()
    data = json.loads(PATH.read_text(encoding="utf-8"))
    cands = data["candidates"]
    if args.show:
        for c in cands:
            if c["url"] == args.show or c["url"].rstrip("/") == args.show.rstrip("/"):
                print(json.dumps(c, ensure_ascii=False, indent=1))
                return
        print("not found")
        return
    if args.days:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).strftime("%Y-%m-%d")
        cands = [c for c in cands if c["published"] >= cutoff]
    print(f"generated_at={data['generated_at']} total={len(cands)} counts={data.get('counts_by_hint')}")
    for hint in ORDER:
        if args.hint and hint != args.hint:
            continue
        rows = [c for c in cands if hint in c.get("category_hints", [c.get("category_hint")])]
        print(f"\n## {hint} ({len(rows)})")
        for c in rows:
            ex = "T" if c.get("excerpt") else "-"
            print(f"{c['published']} [{ex}] {c['source'][:28]:28s} | {c['title'][:110]}\n    {c['url']}")


if __name__ == "__main__":
    main()
