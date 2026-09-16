#!/usr/bin/env python3
"""Collect industry news with the Claude API and append it to data/news.json.

Designed to run unattended (GitHub Actions). One Claude request per category:
Claude searches the web (server-side web_search / web_fetch tools), reads the
candidates, and returns the new articles through a strict client tool
(`submit_articles`) so the JSON is schema-validated by the API.

Usage:
  python3 scripts/collect_news.py                 # collect all categories
  python3 scripts/collect_news.py --category rail_industry
  python3 scripts/collect_news.py --check-window  # print run=true/false (ET 06:00 / 13:00 gate)

Environment:
  ANTHROPIC_API_KEY  required for collection
  NEWS_MODEL         default claude-opus-5
  NEWS_EFFORT        optional: low | medium | high | xhigh | max
  FORCE_RUN          "true" makes --check-window always report run=true
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "news.json"
RUN_DIR = ROOT / ".run"

PT = ZoneInfo("America/Los_Angeles")   # timestamps shown on the site
ET = ZoneInfo("America/New_York")      # collection schedule (06:00 / 13:00)
RUN_HOURS_ET = (6, 13)
RETENTION_DAYS = 30

MODEL = os.environ.get("NEWS_MODEL", "claude-opus-5")
EFFORT = os.environ.get("NEWS_EFFORT", "").strip() or None

# ---------------------------------------------------------------------------
# Categories. The first three are the priority topics and get larger quotas.
# ---------------------------------------------------------------------------
CATEGORIES = [
    {
        "key": "railcar_leasing",
        "label_ja": "北米貨車リース",
        "max_new": 8,
        "search_uses": 12,
        "fetch_uses": 10,
        "brief": """North American railcar leasing (lessors and railcar builders).
Cover, with equal weight:
- Market/industry news: lease rates, fleet utilisation, railcar orders and deliveries, fleet sales/acquisitions, ABS or other financing, rating actions, tank-car and freight-car demand.
- Company disclosures (primary sources first: company IR/press-release pages, SEC 8-K/10-Q filings, earnings call coverage): GATX, Trinity Industries / TrinityRail, The Greenbrier Companies, FreightCar America, Union Tank Car (UTLX / Marmon), Wells Fargo Rail, SMBC Rail Services, Mitsui Rail Capital, First Citizens / CIT Rail, The Andersons Rail, Infinity Transportation, Procor, American Industrial Transport (AITX), Wabtec (rail equipment).
  Earnings releases, guidance, order backlog, dividend/buyback, M&A, executive appointments and departures (CEO/CFO/board), and other personnel news are all in scope.
- Regulators and rule-makers that affect railcars: FRA (tank car / equipment rules), PHMSA (hazmat tank-car rules), STB (car hire, demurrage, equipment-related dockets), AAR (interchange rules, car hire, mechanical standards), Transport Canada.
Example searches: "railcar leasing news", "railcar lease rates 2026", "GATX press release", "Trinity Industries earnings", "Greenbrier orders backlog", "FreightCar America", "Union Tank Car", "Wells Fargo Rail", "SMBC Rail", "FRA tank car rule", "PHMSA tank car", "AAR car hire".""",
    },
    {
        "key": "rail_industry",
        "label_ja": "北米鉄道業界",
        "max_new": 8,
        "search_uses": 12,
        "fetch_uses": 10,
        "brief": """The North American railroad industry as a whole.
Cover:
- Class I railroads (Union Pacific, BNSF, CSX, Norfolk Southern, CPKC, CN) and major short-line holding companies (Genesee & Wyoming, Watco, OmniTRAX, Patriot Rail): earnings, operating metrics, mergers and merger reviews, capex, network changes, labor agreements and strikes, safety incidents with industry impact, executive changes.
- Traffic and volumes: AAR weekly rail traffic reports, carloads and intermodal trends, grain/coal/chemicals/auto flows.
- Regulators and policy: Surface Transportation Board (decisions, rulemakings, merger proceedings; stb.gov "Latest News"), FRA (safety rules, crew size, inspections), Congress/DOT rail policy, Transport Canada, Canadian Transportation Agency.
- Rail suppliers and technology when it affects the industry broadly (Wabtec, Progress Rail, locomotive orders, ETCS/PTC, automation).
Example searches: "Class I railroad news", "Union Pacific Norfolk Southern merger STB", "AAR weekly rail traffic", "Surface Transportation Board decision", "FRA rule railroad", "CSX earnings", "CPKC news", "BNSF news".""",
    },
    {
        "key": "container_leasing",
        "label_ja": "海上コンテナリース",
        "max_new": 8,
        "search_uses": 12,
        "fetch_uses": 10,
        "brief": """Marine (intermodal shipping) container leasing.
Cover:
- Market news: container lease rates, new-build container prices, container factory output (CIMC, Dong Fang, Singamas), fleet utilisation, secondhand container prices, dry vs reefer vs tank container demand, and the container-shipping backdrop only where it moves leasing demand (freight rates, ordered vessel capacity, tariff-driven volume swings).
- Company disclosures (primary sources first): Triton International (Brookfield Infrastructure), Textainer (Stonepeak), SeaCube, Florens, Beacon Intermodal Leasing (Mitsubishi HC Capital), CAI / Mitsubishi HC Capital, Seaco, Touax, UES International, Blue Sky Intermodal, Global Container International, Cronos. Earnings, financing/ABS, fleet purchases, M&A, executive appointments and other personnel news are all in scope.
- Regulators and industry bodies: Federal Maritime Commission (FMC) rulings and press releases, IICL (Institute of International Container Lessors), BIC, CSC / IMO container safety rules, US customs and tariff actions specifically affecting containers or chassis.
Example searches: "container leasing news", "container lease rates", "Triton International news", "Textainer", "SeaCube Containers", "Florens container", "Beacon Intermodal", "Federal Maritime Commission press release", "IICL container", "new container prices CIMC".""",
    },
    {
        "key": "eu_railcar_leasing",
        "label_ja": "欧州貨車リース",
        "max_new": 4,
        "search_uses": 8,
        "fetch_uses": 6,
        "brief": """European rail freight wagon and locomotive leasing.
Cover:
- Wagon keepers / lessors and locomotive lessors: VTG, Ermewa, GATX Rail Europe, Wascosa, Touax Rail, Nacco, Beacon Rail, Railpool, Alpha Trains, Akiem, ELL (European Locomotive Leasing), Mitsui Rail Capital Europe, Aves One, Transwaggon. Earnings, fleet orders, financing, M&A, executive appointments and other personnel news.
- Wagon builders and market: Tatravagonka, Greenbrier Europe (Astra Rail / Wagony Swidnica), Wabtec/Knorr freight equipment, DAC (digital automatic coupling) rollout, wagon lease rates and utilisation.
- Regulators and bodies: European Union Agency for Railways (ERA), European Commission DG MOVE (rail freight policy, DAC funding), UIP (International Union of Wagon Keepers), UK ORR, national rail regulators.
Example searches: "rail wagon leasing Europe news", "VTG news", "Ermewa", "GATX Rail Europe", "Wascosa", "Railpool locomotive", "Akiem", "digital automatic coupling DAC Europe", "European Union Agency for Railways press release", "UIP wagon keepers".""",
    },
    {
        "key": "alt_investment",
        "label_ja": "オルタナ投資",
        "max_new": 4,
        "search_uses": 8,
        "fetch_uses": 6,
        "brief": """Alternative investments, with a tilt toward infrastructure and transportation real assets.
Cover: infrastructure and real-asset fund closes and launches, infrastructure debt, private credit for equipment/leasing, transportation-asset ABS, secondaries, large asset-manager moves (Brookfield, Blackstone, KKR, Apollo, Stonepeak, Macquarie, GIP/BlackRock, EQT, ICG, Ares), and institutional-investor allocation trends (pension funds, insurers, Japanese institutions investing in alternatives).
Example searches: "infrastructure fund final close", "infrastructure debt fund", "alternative investment news institutional", "transportation asset-backed securities", "private credit equipment finance".""",
    },
]
CATEGORY_KEYS = [c["key"] for c in CATEGORIES]

SYSTEM_PROMPT = """You are the automated collection agent for "Railcar Wire", an English-source industry news dashboard read by Japanese professionals in railcar and container leasing.

Your job each run: find NEW news items for one category, verify each item, write a 3-point Japanese summary, and hand the results back by calling the `submit_articles` tool exactly once at the end. Never answer in plain text; the only deliverable is the tool call (call it with an empty list if nothing qualifies).

Rules
- Use web_search to find candidates (several different queries per category) and web_fetch to open an article when the search snippet is not enough to confirm the date or write an accurate summary.
- Only real, dated, individual news items or official releases (press releases, earnings releases, regulator notices, SEC filings, reputable trade press). Exclude: market-research report sales pages, live rate tables or continuously updated statistics pages, job listings, stock-tip / auto-generated content, opinion pieces without new facts, and duplicates of the same story from another outlet (keep the primary source or the most detailed report).
- Only items published within the last 30 days. Confirm the publish date; if you cannot determine it, exclude the item.
- Exclude every URL in the "already collected" list, and do not resubmit the same story under a different URL.
- Prefer primary sources (company IR pages, regulator sites, SEC EDGAR) when they exist for a story.
- `summary_ja` must be exactly 3 bullet points in Japanese, each one short sentence stating a distinct fact: what was announced, the key figures (amounts, volumes, rates, dates, names), and the background or implication. Company names and product names may stay in English. No bullet may repeat another.
- `title` and `source` stay in the original English. `published_at` is YYYY-MM-DD (empty string only if genuinely unknown, which should be rare because unknown-date items are excluded).
- `kind`: earnings (financial results/guidance), personnel (appointments, departures, board changes), regulatory (a regulator's or industry body's official release, rule, or decision), news (everything else).
- Respect the requested maximum number of articles; when there are more candidates, keep the most material ones for a leasing professional (financial impact, regulatory change, large transactions, market-moving data)."""

SUBMIT_TOOL = {
    "name": "submit_articles",
    "description": "Submit the final list of new, verified articles for this category. Call exactly once at the end of the task, with an empty list if nothing qualifies.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "articles": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Original English headline"},
                        "source": {"type": "string", "description": "Publisher or organisation name"},
                        "url": {"type": "string", "description": "Canonical article URL"},
                        "published_at": {"type": "string", "description": "YYYY-MM-DD, or empty string if unknown"},
                        "kind": {"type": "string", "enum": ["news", "earnings", "personnel", "regulatory"]},
                        "summary_ja": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Exactly three Japanese bullet points",
                        },
                    },
                    "required": ["title", "source", "url", "published_at", "kind", "summary_ja"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["articles"],
        "additionalProperties": False,
    },
}

TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "source"}


def normalize_url(url: str) -> str:
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return url.strip().lower()
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in TRACKING_PARAMS]
    path = re.sub(r"/+$", "", parts.path) or "/"
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return urlunsplit(("https", host, path, urlencode(query), ""))  # scheme-insensitive dedup key


def load_articles() -> list[dict]:
    if not DATA_PATH.exists():
        return []
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def save_articles(articles: list[dict]) -> None:
    DATA_PATH.write_text(json.dumps(articles, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def within_window(now_et: datetime | None = None) -> bool:
    now_et = now_et or datetime.now(ET)
    return now_et.hour in RUN_HOURS_ET


def check_window() -> int:
    force = os.environ.get("FORCE_RUN", "").lower() == "true"
    now = datetime.now(ET)
    run = force or within_window(now)
    print(f"# now={now.isoformat()} force={force} run={run}", file=sys.stderr)
    print(f"run={'true' if run else 'false'}")
    return 0


def build_user_prompt(category: dict, existing_urls: list[str], now_pt: datetime) -> str:
    cutoff = (now_pt - timedelta(days=RETENTION_DAYS)).strftime("%Y-%m-%d")
    urls = "\n".join(f"- {u}" for u in existing_urls) or "- (none yet)"
    return f"""Category: {category['key']} ({category['label_ja']})
Today (US Pacific): {now_pt.strftime('%Y-%m-%d')}. Only include items published on or after {cutoff}.
Maximum articles to submit: {category['max_new']}.

Scope for this category:
{category['brief']}

Already collected (exclude these URLs and the stories behind them):
{urls}

Search broadly (at least 4 distinct queries, mixing general market news, company/IR sources, and regulator sources), verify dates, then call submit_articles once with the new items."""


def collect_category(client, category: dict, existing_urls: list[str], now_pt: datetime) -> list[dict]:
    """One Claude conversation: server-side web research, then a strict tool call with the results."""
    tools = [
        {"type": "web_search_20260209", "name": "web_search", "max_uses": category["search_uses"]},
        {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": category["fetch_uses"]},
        SUBMIT_TOOL,
    ]
    messages = [{"role": "user", "content": build_user_prompt(category, existing_urls, now_pt)}]
    request = dict(
        model=MODEL,
        max_tokens=32000,
        system=SYSTEM_PROMPT,
        tools=tools,
        messages=messages,
    )
    if EFFORT:
        request["output_config"] = {"effort": EFFORT}

    nudges = 0
    for turn in range(8):
        with client.messages.stream(**request) as stream:
            response = stream.get_final_message()
        usage = response.usage
        print(f"  [{category['key']}] turn {turn + 1}: stop={response.stop_reason} in={usage.input_tokens} out={usage.output_tokens}", file=sys.stderr)

        if response.stop_reason == "refusal":
            print(f"  [{category['key']}] request refused; skipping category", file=sys.stderr)
            return []

        submit = next((b for b in response.content if b.type == "tool_use" and b.name == "submit_articles"), None)
        if submit is not None:
            payload = submit.input if isinstance(submit.input, dict) else json.loads(submit.input)
            return list(payload.get("articles", []))

        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason == "pause_turn":
            continue  # server-side tool loop hit its iteration cap; resume
        if response.stop_reason == "max_tokens":
            print(f"  [{category['key']}] hit max_tokens before submitting", file=sys.stderr)
        nudges += 1
        if nudges > 2:
            break
        messages.append({"role": "user", "content": "Finish now: call submit_articles exactly once with the verified new articles (or an empty list)."})
    print(f"  [{category['key']}] no submit_articles call received; treating as empty", file=sys.stderr)
    return []


def clean_articles(raw: list[dict], category_key: str, existing_norm: set[str], now_pt: datetime) -> list[dict]:
    cutoff = (now_pt - timedelta(days=RETENTION_DAYS)).strftime("%Y-%m-%d")
    seen = set()
    out = []
    for a in raw:
        url = (a.get("url") or "").strip()
        if not url.startswith("http"):
            continue
        norm = normalize_url(url)
        if norm in existing_norm or norm in seen:
            continue
        published = (a.get("published_at") or "").strip() or None
        if published:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", published):
                published = None
            elif published < cutoff:
                continue
        bullets = [str(b).strip() for b in (a.get("summary_ja") or []) if str(b).strip()]
        if len(bullets) < 2:
            continue
        bullets = bullets[:3]
        kind = a.get("kind") if a.get("kind") in ("news", "earnings", "personnel", "regulatory") else "news"
        seen.add(norm)
        out.append({
            "category": category_key,
            "kind": kind,
            "title": (a.get("title") or "").strip() or url,
            "source": (a.get("source") or "").strip(),
            "url": url,
            "published_at": published,
            "summary_ja": bullets,
            "collected_at": now_pt.isoformat(timespec="seconds"),
        })
    return out


def write_run_outputs(new_articles: list[dict], counts: dict[str, int], now_pt: datetime) -> None:
    RUN_DIR.mkdir(exist_ok=True)
    label = {c["key"]: c["label_ja"] for c in CATEGORIES}
    summary = ", ".join(f"{label.get(k, k)} {v}" for k, v in counts.items())
    (RUN_DIR / "summary.txt").write_text(f"新規 {len(new_articles)} 件（{summary}）\n", encoding="utf-8")
    (RUN_DIR / "new_articles.json").write_text(json.dumps(new_articles, ensure_ascii=False, indent=2), encoding="utf-8")

    def esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    parts = [f"<p>Railcar Wire {now_pt.strftime('%Y-%m-%d %H:%M %Z')} 更新。新規 {len(new_articles)} 件。</p>"]
    for key in CATEGORY_KEYS:
        items = [a for a in new_articles if a["category"] == key]
        if not items:
            continue
        parts.append(f"<h3>{esc(label[key])}</h3>")
        for a in items:
            bullets = "".join(f"<li>{esc(b)}</li>" for b in a["summary_ja"])
            parts.append(
                f'<p><a href="{esc(a["url"])}">{esc(a["title"])}</a><br>'
                f'<small>{esc(a["source"])} · {a["published_at"] or "日付不明"}</small></p><ul>{bullets}</ul>'
            )
    (RUN_DIR / "digest.html").write_text("\n".join(parts), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-window", action="store_true", help="print run=true/false for the ET 06:00/13:00 schedule gate")
    parser.add_argument("--category", action="append", choices=CATEGORY_KEYS, help="limit to one or more categories")
    args = parser.parse_args()

    if args.check_window:
        return check_window()

    import anthropic  # imported late so --check-window works without the SDK

    client = anthropic.Anthropic(max_retries=3, timeout=900.0)
    now_pt = datetime.now(PT)
    articles = load_articles()
    existing_norm = {normalize_url(a["url"]) for a in articles if a.get("url")}
    existing_urls = [a["url"] for a in articles if a.get("url")]

    selected = [c for c in CATEGORIES if not args.category or c["key"] in args.category]
    new_articles: list[dict] = []
    counts: dict[str, int] = {}
    for category in selected:
        print(f"== {category['key']} ({category['label_ja']}) model={MODEL}", file=sys.stderr)
        try:
            raw = collect_category(client, category, existing_urls, now_pt)
        except anthropic.RateLimitError as e:
            print(f"  rate limited ({e.status_code}); skipping {category['key']}", file=sys.stderr)
            continue
        except anthropic.APIStatusError as e:
            print(f"  API error {e.status_code} on {category['key']}: {e.message}", file=sys.stderr)
            continue
        except anthropic.APIConnectionError as e:
            print(f"  connection error on {category['key']}: {e}", file=sys.stderr)
            continue
        cleaned = clean_articles(raw, category["key"], existing_norm, now_pt)[: category["max_new"]]
        for a in cleaned:
            existing_norm.add(normalize_url(a["url"]))
            existing_urls.append(a["url"])
        counts[category["key"]] = len(cleaned)
        new_articles.extend(cleaned)
        print(f"  {category['key']}: {len(raw)} returned, {len(cleaned)} new", file=sys.stderr)

    if new_articles:
        save_articles(articles + new_articles)
    write_run_outputs(new_articles, counts, now_pt)
    print((RUN_DIR / "summary.txt").read_text(encoding="utf-8").strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
