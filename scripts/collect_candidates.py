#!/usr/bin/env python3
"""Collect dated candidate articles for Railcar Wire into data/candidates.json.

Runs on GitHub Actions (free) where outbound network access is unrestricted.
Sources: trade-press RSS feeds, Google News RSS searches (dated, `when:30d`),
SEC EDGAR 8-K feeds (press-release exhibits), and the Federal Register API.
Each candidate carries a publish date, a category hint and (when fetchable) a
plain-text excerpt so the summarising routine does not need to fetch pages.

Usage: python3 scripts/collect_candidates.py [--no-excerpts] [--max-decode N]
"""
from __future__ import annotations

import argparse
import concurrent.futures
import html
import json
import re
import sys
import time
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

warnings.filterwarnings("ignore")
import feedparser  # noqa: E402
import requests  # noqa: E402
import trafilatura  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NEWS_PATH = ROOT / "data" / "news.json"
OUT_PATH = ROOT / "data" / "candidates.json"
CACHE_PATH = ROOT / "data" / "gnews_cache.json"

WINDOW_DAYS = 30
MAX_PER_HINT = 70  # newest N candidates kept per category hint
EXCERPT_CHARS = 1000
BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
SEC_UA = "RailcarWire/1.0 (industry news aggregator) kohei.takahashi@gmail.com"

# --------------------------------------------------------------------------
# Sources
# --------------------------------------------------------------------------
CONTAINER_KW = r"container|\bbox(es)?\b|lessor|leasing|\blease|reefer|\bTEU\b|FMC|Maritime Commission|CIMC|depot|chassis|per diem|demurrage|detention|intermodal"
RAILCAR_KW = r"railcar|rail car|freight car|tank car|hopper|boxcar|gondola|lessor|leasing|\blease|GATX|Trinity|Greenbrier|FreightCar|Wabtec|UTLX|Union Tank|car hire|AAR\b|PHMSA|FRA\b"
WAGON_KW = r"wagon|lessor|leasing|\blease|locomotive|rolling stock|freight|coupl|VTG|Ermewa|Railpool|Akiem|Wascosa|Touax|Nacco|ERA\b|Agency for Railways"
RSS_FEEDS = [
    # (feed url, category hint, source label, required keyword regex on title+summary or None)
    ("https://www.freightwaves.com/news/category/news/railroad/feed", "rail_industry", "FreightWaves", None),
    ("https://www.trains.com/feed/", "rail_industry", "Trains", r"freight|railroad|Class I|STB|FRA|merger|Union Pacific|BNSF|CSX|Norfolk|CPKC|CN\b|railcar|locomotive|short line|intermodal"),
    ("https://railpace.com/feed/", "rail_industry", "Railpace", r"AAR|rail traffic|carload|freight|Class I|STB|merger"),
    ("https://www.stb.gov/feed/", "rail_industry", "Surface Transportation Board", None),
    ("https://www.worldcargonews.com/category/container-leasing/feed/", "container_leasing", "WorldCargo News", None),
    ("https://www.worldcargonews.com/feed/", "container_leasing", "WorldCargo News", CONTAINER_KW),
    ("https://container-news.com/feed/", "container_leasing", "Container News", CONTAINER_KW),
    ("https://theloadstar.com/feed/", "container_leasing", "The Loadstar", CONTAINER_KW),
    ("https://splash247.com/feed/", "container_leasing", "Splash247", CONTAINER_KW),
    ("https://www.seatrade-maritime.com/rss.xml", "container_leasing", "Seatrade Maritime", CONTAINER_KW),
    ("https://www.hellenicshippingnews.com/feed/", "container_leasing", "Hellenic Shipping News", CONTAINER_KW),
    ("https://www.fmc.gov/feed/", "container_leasing", "Federal Maritime Commission", None),
    ("https://www.railfreight.com/feed/", "eu_railcar_leasing", "RailFreight.com", WAGON_KW),
    ("https://www.railwaygazette.com/rss", "eu_railcar_leasing", "Railway Gazette", WAGON_KW),
    ("https://www.railway-technology.com/feed/", "eu_railcar_leasing", "Railway Technology", WAGON_KW),
    ("https://www.era.europa.eu/rss.xml", "eu_railcar_leasing", "European Union Agency for Railways", None),
    ("https://alternativecreditinvestor.com/feed/", "alt_investment", "Alternative Credit Investor", r"infrastructure|asset-based|asset-backed|transport|equipment|leasing|fund|close|launch"),
    ("https://www.privateequityinternational.com/feed/", "alt_investment", "Private Equity International", r"infrastructure|secondar|real asset|transport|fund close|raises"),
    ("https://www.prnewswire.com/rss/transportation-trucking-railroad-latest-news/transportation-trucking-railroad-latest-news-list.rss", "rail_industry", "PR Newswire", r"rail|locomotive|container|leasing|intermodal|freight car|tank car"),
]

# Google News RSS searches: (query, category hint). `when:30d` is appended.
GNEWS_QUERIES = [
    ('"railcar leasing" OR "railcar lessor" OR "railcar lease" OR "railcar lessors"', "railcar_leasing"),
    ('GATX OR "Trinity Industries" OR TrinityRail OR "Greenbrier Companies" OR "FreightCar America"', "railcar_leasing"),
    ('"Union Tank Car" OR UTLX OR "Wells Fargo Rail" OR "SMBC Rail" OR "Mitsui Rail Capital" OR "American Industrial Transport" OR Procor OR "Andersons Rail"', "railcar_leasing"),
    ('site:railwayage.com (railcar OR lessor OR leasing OR "tank car" OR "freight car")', "railcar_leasing"),
    ('site:progressiverailroading.com (railcar OR lease OR lessor OR "tank car")', "railcar_leasing"),
    ('site:freightwaves.com (railcar OR "rail equipment")', "railcar_leasing"),
    ('"tank car" (FRA OR PHMSA OR AAR OR rule OR railcar)', "railcar_leasing"),
    ('"car hire" railroad OR "Railway Supply Institute" OR "railcar orders" OR "railcar deliveries"', "railcar_leasing"),
    ('site:railwayage.com', "rail_industry"),
    ('site:progressiverailroading.com', "rail_industry"),
    ('site:trains.com railroad', "rail_industry"),
    ('"Surface Transportation Board"', "rail_industry"),
    ('("Union Pacific" OR "Norfolk Southern" OR CSX OR BNSF OR CPKC OR "Canadian National") railroad', "rail_industry"),
    ('"Federal Railroad Administration" OR "Association of American Railroads"', "rail_industry"),
    ('"container leasing" OR "container lessor" OR "container lessors" OR "leased containers"', "container_leasing"),
    ('"Triton International" OR Textainer OR "SeaCube" OR Florens OR "Beacon Intermodal" OR "CAI International" OR "Seaco Global" OR "Touax" container', "container_leasing"),
    ('site:worldcargonews.com container', "container_leasing"),
    ('site:container-news.com (leasing OR lessor OR "container prices" OR "box")', "container_leasing"),
    ('site:theloadstar.com ("container leasing" OR lessor OR "container prices" OR "box supply" OR "empty containers")', "container_leasing"),
    ('"Federal Maritime Commission"', "container_leasing"),
    ('("container prices" OR "container production" OR "new containers") (CIMC OR "Dong Fang" OR Singamas OR lessors)', "container_leasing"),
    ('"Institute of International Container Lessors" OR IICL OR "reefer containers" leasing', "container_leasing"),
    ('(VTG OR Ermewa OR "GATX Rail Europe" OR Wascosa OR "Touax Rail" OR Nacco OR Transwaggon) wagon', "eu_railcar_leasing"),
    ('Railpool OR Akiem OR "Alpha Trains" OR "European Locomotive Leasing" OR "Beacon Rail" OR "Aves One"', "eu_railcar_leasing"),
    ('("wagon leasing" OR "wagon lessor" OR "freight wagons" OR "rail freight wagons") Europe', "eu_railcar_leasing"),
    ('"digital automatic coupling" OR "digital automatic coupler"', "eu_railcar_leasing"),
    ('"European Union Agency for Railways" OR "rail freight" Europe regulation', "eu_railcar_leasing"),
    ('site:railfreight.com (wagon OR wagons OR leasing OR lessor)', "eu_railcar_leasing"),
    ('site:railwaygazette.com (wagon OR wagons OR "rail freight" OR leasing)', "eu_railcar_leasing"),
    ('"infrastructure fund" (close OR closes OR closed OR raises OR launches OR launch)', "alt_investment"),
    ('"infrastructure debt" OR "infrastructure credit" fund', "alt_investment"),
    ('"private credit" (equipment OR leasing OR transportation OR "asset-based")', "alt_investment"),
    ('(Brookfield OR Stonepeak OR KKR OR Blackstone OR Apollo OR Macquarie OR "Global Infrastructure Partners" OR EQT OR ICG OR Ares OR Carlyle) infrastructure fund', "alt_investment"),
    ('"asset-backed" (railcar OR container OR "equipment lease" OR "equipment leasing")', "alt_investment"),
    ('site:infrastructureinvestor.com', "alt_investment"),
    ('site:alternativecreditinvestor.com (infrastructure OR "asset-based" OR transportation)', "alt_investment"),
]

# SEC EDGAR 8-K feeds: (CIK, company label, category hint)
EDGAR_COMPANIES = [
    ("0000040211", "GATX Corporation", "railcar_leasing"),
    ("0000099780", "Trinity Industries", "railcar_leasing"),
    ("0000923120", "The Greenbrier Companies", "railcar_leasing"),
    ("0001320854", "FreightCar America", "railcar_leasing"),
    ("0000943452", "Wabtec", "railcar_leasing"),
    ("0001660734", "Triton International", "container_leasing"),
    ("0000100885", "Union Pacific", "rail_industry"),
    ("0000277948", "CSX", "rail_industry"),
    ("0000702165", "Norfolk Southern", "rail_industry"),
]

FEDERAL_REGISTER_URL = (
    "https://www.federalregister.gov/api/v1/documents.json?"
    "conditions[agencies][]=federal-railroad-administration"
    "&conditions[agencies][]=surface-transportation-board"
    "&conditions[agencies][]=pipeline-and-hazardous-materials-safety-administration"
    "&conditions[agencies][]=federal-maritime-commission"
    "&order=newest&per_page=60"
    "&fields[]=title&fields[]=abstract&fields[]=publication_date&fields[]=html_url&fields[]=agencies&fields[]=type"
)

# Titles matching these are market-research spam or non-news pages.
NOISE_TITLE = re.compile(
    r"market (size|share|report|forecast|analysis|outlook|research|trends|to reach|growth|insights)|"
    r"\bCAGR\b|industry report|research report|company profile|stock (forecast|price target)|"
    r"gameday|volleyball|water polo|poker|football|basketball|hockey|soccer|"
    r"undervalued|fair value|should you buy|dividend analysis|insider (trading|selling|buying)|form 4\b|"
    r"worth your attention|jim cramer|price target|stocks? to (buy|watch)|top \d+ stocks|archives$|legal notice|"
    r"transit briefs|passenger|amtrak|metro|light rail|commuter",
    re.I,
)
# Stock-commentary and aggregator domains that never carry primary news.
NOISE_DOMAINS = {
    "stockstory.org", "stockinvest.us", "simplywall.st", "marketbeat.com", "tipranks.com", "seekingalpha.com",
    "fool.com", "zacks.com", "gurufocus.com", "investing.com", "benzinga.com", "insidermonkey.com", "ainvest.com",
    "stocktitan.net", "tradingview.com", "robinhood.com", "pitchbook.com", "linkedin.com", "wikipedia.org",
    "researchandmarkets.com", "globenewswire.com/news-release/2026/0/", "marketscreener.com/quote",
}
TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "source", "guccounter"}


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
    return urlunsplit(("https", host, path, urlencode(query), ""))


def to_date(struct_or_str) -> str | None:
    """Return YYYY-MM-DD from a feedparser time struct or an ISO/RFC string."""
    if not struct_or_str:
        return None
    if isinstance(struct_or_str, str):
        m = re.search(r"(\d{4}-\d{2}-\d{2})", struct_or_str)
        if m:
            return m.group(1)
        try:
            return datetime.strptime(struct_or_str[:25].strip(), "%a, %d %b %Y %H:%M:%S").strftime("%Y-%m-%d")
        except ValueError:
            return None
    try:
        return time.strftime("%Y-%m-%d", struct_or_str)
    except (TypeError, ValueError):
        return None


def get(url: str, ua: str = BROWSER_UA, timeout: int = 25) -> requests.Response | None:
    try:
        r = requests.get(url, headers={"User-Agent": ua, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.8"}, timeout=timeout, allow_redirects=True)
        if r.status_code == 200:
            return r
        print(f"  ! HTTP {r.status_code} {url[:90]}", file=sys.stderr)
    except requests.RequestException as e:
        print(f"  ! {type(e).__name__} {url[:90]}", file=sys.stderr)
    return None


def source_from_url(url: str) -> str:
    host = urlsplit(url).netloc.lower().removeprefix("www.")
    return host


# --------------------------------------------------------------------------
# Collectors. Each yields dicts with title/url/source/published/category_hint/feed.
# --------------------------------------------------------------------------
def collect_rss():
    for url, hint, label, kw in RSS_FEEDS:
        r = get(url)
        if not r:
            continue
        feed = feedparser.parse(r.content)
        n = 0
        for e in feed.entries:
            link = e.get("link") or ""
            published = to_date(e.get("published_parsed") or e.get("updated_parsed")) or to_date(e.get("published") or e.get("updated"))
            if not link or not published:
                continue
            title = html.unescape(e.get("title", "")).strip()
            snippet = re.sub(r"<[^>]+>", " ", html.unescape(e.get("summary", "")))[:400].strip()
            if kw and not re.search(kw, f"{title} {snippet}", re.I):
                continue
            n += 1
            yield {"title": title, "url": link, "source": label, "published": published,
                   "category_hint": hint, "feed": f"rss:{source_from_url(url)}", "snippet": snippet}
        print(f"rss {label:32s} {n} items", file=sys.stderr)


def collect_gnews(cache: dict, max_decode: int):
    try:
        from googlenewsdecoder import gnewsdecoder
    except ImportError:
        gnewsdecoder = None
    decoded = 0
    for query, hint in GNEWS_QUERIES:
        q = quote(f"{query} when:{WINDOW_DAYS}d")
        r = get(f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en")
        if not r:
            continue
        feed = feedparser.parse(r.content)
        n = 0
        for e in feed.entries[:20]:
            glink = e.get("link") or ""
            title = html.unescape(e.get("title", "")).strip()
            source = ""
            if " - " in title:
                title, source = title.rsplit(" - ", 1)
            published = to_date(e.get("published_parsed")) or to_date(e.get("published"))
            if not glink or not published or NOISE_TITLE.search(title):
                continue
            key = glink.split("/articles/")[-1].split("?")[0]
            real = cache.get(key)
            if real is None and gnewsdecoder is not None and decoded < max_decode:
                try:
                    res = gnewsdecoder(glink, interval=1)
                    real = res.get("decoded_url") if res.get("status") else ""
                except Exception as ex:  # noqa: BLE001
                    real = ""
                    print(f"  ! decode failed: {ex}", file=sys.stderr)
                decoded += 1
                cache[key] = real or ""
            if not real:
                real = glink  # decoding failed or budget exhausted: keep the Google redirect link (opens the article in a browser)
            n += 1
            yield {"title": title, "url": real, "source": source or source_from_url(real), "published": published,
                   "category_hint": hint, "feed": "gnews", "snippet": ""}
        print(f"gnews [{hint}] {query[:50]!r}: {n} items (decoded so far {decoded})", file=sys.stderr)


def edgar_exhibit(index_url: str) -> tuple[str, str, str]:
    """Return (exhibit_url, headline, text) for an 8-K filing index page."""
    r = get(index_url, ua=SEC_UA)
    if not r:
        return "", "", ""
    docs = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", r.text, flags=re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.S)
        if len(cells) >= 4:
            m = re.search(r'href="([^"]+)"', cells[2])
            typ = re.sub(r"<[^>]+>", "", cells[3]).strip().upper()
            if m and m.group(1).endswith(".htm"):
                docs.append((typ, m.group(1)))
    target = next((d for d in docs if d[0].startswith("EX-99")), None) or next((d for d in docs if d[0] == "8-K"), None)
    if not target:
        return "", "", ""
    doc_url = "https://www.sec.gov" + target[1].replace("/ix?doc=", "")
    rd = get(doc_url, ua=SEC_UA)
    if not rd:
        return doc_url, "", ""
    text = trafilatura.extract(rd.text, include_comments=False, include_tables=False) or re.sub(r"<[^>]+>", "\n", rd.text)
    text = html.unescape(text)
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln and not re.match(r"^(EX-99|Exhibit 99|News Release|Earnings Release|For release|Contact|Ph:|www\.)", ln, re.I)]
    headline = next((ln for ln in lines if 25 <= len(ln) <= 180 and re.search(r"\b(Reports|Announces|Declares|Appoints|Names|Completes|Prices|Increases|Raises|Enters|Signs|Acquires|Sells|Elects|Provides|Updates|Receives|Awarded)\b", ln)), "")
    body = " ".join(lines)
    time.sleep(0.4)  # SEC fair-access guidance (<10 req/s)
    return doc_url, headline, body


def collect_edgar(cutoff: str):
    for cik, company, hint in EDGAR_COMPANIES:
        url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=8-K&dateb=&owner=include&count=10&output=atom"
        r = get(url, ua=SEC_UA)
        if not r:
            continue
        feed = feedparser.parse(r.content)
        n = 0
        for e in feed.entries:
            published = to_date(e.get("updated_parsed")) or to_date(e.get("updated"))
            if not published or published < cutoff:
                continue
            index_url = e.get("link") or ""
            doc_url, headline, body = edgar_exhibit(index_url)
            if not doc_url:
                continue
            n += 1
            yield {"title": headline or f"{company}: Form 8-K filed {published}", "url": doc_url, "source": f"SEC EDGAR ({company})",
                   "published": published, "category_hint": hint, "feed": "edgar", "snippet": "", "excerpt": body[:EXCERPT_CHARS]}
        print(f"edgar {company:28s} {n} recent 8-K", file=sys.stderr)


def collect_federal_register(cutoff: str):
    r = get(FEDERAL_REGISTER_URL)
    if not r:
        return
    n = 0
    for d in r.json().get("results", []):
        published = d.get("publication_date")
        if not published or published < cutoff:
            continue
        agencies = ", ".join(a.get("name", "") for a in d.get("agencies", []) if isinstance(a, dict))
        title = d.get("title", "")
        text = f"{title}. {agencies}. {d.get('type', '')}. {d.get('abstract') or ''}"
        if "Maritime" in agencies:
            hint = "container_leasing"
        elif re.search(r"tank car|freight car|railcar|rail car|car hire|demurrage|hazardous", title + (d.get("abstract") or ""), re.I):
            hint = "railcar_leasing"
        else:
            hint = "rail_industry"
        n += 1
        yield {"title": title, "url": d.get("html_url", ""), "source": f"Federal Register ({agencies})", "published": published,
               "category_hint": hint, "feed": "federalregister", "snippet": (d.get("abstract") or "")[:400], "excerpt": text[:EXCERPT_CHARS]}
    print(f"federalregister {n} documents", file=sys.stderr)


# --------------------------------------------------------------------------
def fetch_excerpt(url: str) -> str:
    r = get(url, timeout=20)
    if not r or "html" not in r.headers.get("content-type", ""):
        return ""
    text = trafilatura.extract(r.text, include_comments=False, include_tables=False) or ""
    return re.sub(r"\s+", " ", text).strip()[:EXCERPT_CHARS]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-excerpts", action="store_true")
    ap.add_argument("--max-decode", type=int, default=900, help="max Google News links to decode this run")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%d")
    previous = {"candidates": [], "gnews_cache": {}}
    if OUT_PATH.exists():
        try:
            previous = json.loads(OUT_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else previous.get("gnews_cache", {})
    known = {normalize_url(a["url"]): a for a in previous.get("candidates", []) if a.get("url")}
    published_urls = {normalize_url(a["url"]) for a in json.loads(NEWS_PATH.read_text(encoding="utf-8")) if a.get("url")} if NEWS_PATH.exists() else set()

    merged: dict[str, dict] = {}
    for item in list(collect_rss()) + list(collect_gnews(cache, args.max_decode)) + list(collect_edgar(cutoff)) + list(collect_federal_register(cutoff)):
        if not item.get("url", "").startswith("http") or not item.get("title"):
            continue
        if item["published"] < cutoff or NOISE_TITLE.search(item["title"]):
            continue
        key = normalize_url(item["url"])
        host = urlsplit(item["url"]).netloc.lower().removeprefix("www.")
        if key in published_urls or any(host == d or host.endswith("." + d) or d in item["url"] for d in NOISE_DOMAINS):
            continue
        if key in merged:
            hints = merged[key].setdefault("category_hints", [merged[key]["category_hint"]])
            if item["category_hint"] not in hints:
                hints.append(item["category_hint"])
            continue
        item["category_hints"] = [item["category_hint"]]
        old = known.get(key)
        if old:
            item["excerpt"] = item.get("excerpt") or old.get("excerpt", "")
            item["first_seen"] = old.get("first_seen", now.strftime("%Y-%m-%d"))
        else:
            item["first_seen"] = now.strftime("%Y-%m-%d")
        merged[key] = item

    # Keep the newest MAX_PER_HINT items per category hint (an item can belong to several hints).
    keep: set[str] = set()
    for hint in {"railcar_leasing", "rail_industry", "container_leasing", "eu_railcar_leasing", "alt_investment"}:
        rows = sorted((c for c in merged.values() if hint in c["category_hints"]), key=lambda a: a["published"], reverse=True)
        keep.update(normalize_url(c["url"]) for c in rows[:MAX_PER_HINT])
    candidates = sorted((c for k, c in merged.items() if k in keep), key=lambda a: a["published"], reverse=True)

    if not args.no_excerpts:
        todo = [c for c in candidates if not c.get("excerpt")]
        print(f"fetching excerpts for {len(todo)} new candidates", file=sys.stderr)
        with concurrent.futures.ThreadPoolExecutor(8) as ex:
            for c, text in zip(todo, ex.map(lambda c: fetch_excerpt(c["url"]), todo)):
                c["excerpt"] = text

    counts: dict[str, int] = {}
    for c in candidates:
        if c.get("excerpt") and "snippet" in c:
            del c["snippet"]
        for h in c["category_hints"]:
            counts[h] = counts.get(h, 0) + 1
    out = {
        "generated_at": now.isoformat(timespec="seconds"),
        "window_days": WINDOW_DAYS,
        "counts_by_hint": counts,
        "candidates": candidates,
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    CACHE_PATH.write_text(json.dumps({k: v for k, v in cache.items() if v}, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT_PATH.name}: {len(candidates)} candidates, hints={counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
