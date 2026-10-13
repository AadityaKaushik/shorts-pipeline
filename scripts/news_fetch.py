"""Fetch today's AI/tech headlines from free, keyless sources.

Sources: Hacker News (Algolia API) + TechCrunch / The Verge / Ars Technica RSS.
Every source failure is non-fatal — we return whatever we got. Stdlib only.
"""
import email.utils
import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET

UA = {"User-Agent": "Mozilla/5.0 (shorts-pipeline news fetcher)"}

RSS_FEEDS = [
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
]


def _get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read()


def _strip_html(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def fetch_hn(limit=12):
    data = json.loads(_get(
        "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=30"))
    items = []
    for hit in data.get("hits", []):
        title = hit.get("title") or ""
        if not title:
            continue
        items.append({
            "source": "Hacker News",
            "title": title,
            "summary": "",  # HN has no summary; title + points carry the signal
            "points": hit.get("points") or 0,
            "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
            "published": (hit.get("created_at") or "")[:10],
        })
    items.sort(key=lambda x: -x["points"])
    return items[:limit]


def fetch_rss(source, url, limit=8):
    root = ET.fromstring(_get(url))
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items = []
    # RSS 2.0
    for item in root.iter("item"):
        title = _strip_html(item.findtext("title"))
        desc = _strip_html(item.findtext("description"))[:400]
        link = (item.findtext("link") or "").strip()
        pub = ""
        try:
            pub = email.utils.parsedate_to_datetime(
                item.findtext("pubDate") or "").date().isoformat()
        except (TypeError, ValueError):
            pass
        if title:
            items.append({"source": source, "title": title, "summary": desc,
                          "points": 0, "url": link, "published": pub})
    # Atom
    if not items:
        for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
            title = _strip_html(entry.findtext("atom:title", namespaces=ns))
            desc = _strip_html(entry.findtext("atom:summary", namespaces=ns)
                               or entry.findtext("atom:content", namespaces=ns) or "")[:400]
            link_el = entry.find("atom:link", ns)
            link = link_el.get("href") if link_el is not None else ""
            pub = (entry.findtext("atom:published", namespaces=ns)
                   or entry.findtext("atom:updated", namespaces=ns) or "")[:10]
            if title:
                items.append({"source": source, "title": title, "summary": desc,
                              "points": 0, "url": link, "published": pub})
    return items[:limit]


def fetch_article(url, max_chars=1200):
    """Best-effort article body text for grounding the script writer."""
    try:
        page = _get(url, timeout=15).decode("utf-8", errors="ignore")
        page = re.sub(r"(?is)<(script|style|nav|header|footer)[^>]*>.*?</\1>",
                      " ", page)
        paras = re.findall(r"(?is)<p[^>]*>(.*?)</p>", page)
        text = " ".join(_strip_html(p) for p in paras)
        return text[:max_chars]
    except Exception as e:
        print(f"  [news] article fetch failed: {type(e).__name__}")
        return ""


def fetch_headlines():
    all_items = []
    try:
        all_items += fetch_hn()
    except Exception as e:
        print(f"  [news] HN failed: {type(e).__name__}")
    for source, url in RSS_FEEDS:
        try:
            all_items += fetch_rss(source, url)
        except Exception as e:
            print(f"  [news] {source} failed: {type(e).__name__}")
    # de-dup near-identical titles across sources
    seen, out = set(), []
    for it in all_items:
        key = re.sub(r"\W+", "", it["title"].lower())[:60]
        if key not in seen:
            seen.add(key)
            it["id"] = len(out)
            out.append(it)
    return out


if __name__ == "__main__":
    for it in fetch_headlines():
        print(f"[{it['id']:2}] ({it['source']}) {it['title'][:90]}")
