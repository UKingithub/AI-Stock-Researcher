from __future__ import annotations

import os
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import httpx

from app.catalyst import NewsItem

DEFAULT_UA = os.getenv(
    "NEWS_USER_AGENT",
    "AI-Stock-Researcher research-only contact=admin@example.com",
)


class FreeNewsProvider:
    """Free/public news discovery layer.

    Sources:
    - SEC EDGAR submissions (primary source)
    - GDELT DOC 2.0 (broad news discovery)
    - Google News RSS (discovery only)

    This module stores titles/metadata/URLs, not publisher full text.
    """

    def __init__(self, timeout: float = 12.0):
        self.client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": DEFAULT_UA},
        )

    def close(self) -> None:
        self.client.close()

    def google_news(self, query: str, limit: int = 20) -> list[NewsItem]:
        encoded = urllib.parse.quote_plus(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
        response = self.client.get(url)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        items: list[NewsItem] = []
        for node in root.findall("./channel/item")[:limit]:
            title = node.findtext("title") or ""
            link = node.findtext("link") or ""
            published = node.findtext("pubDate")
            source_node = node.find("source")
            source = source_node.text if source_node is not None and source_node.text else "Google News"
            items.append(
                NewsItem(
                    source=source,
                    title=title,
                    url=link,
                    published_at=published,
                    source_type="aggregator",
                )
            )
        return items

    def gdelt(self, query: str, limit: int = 20) -> list[NewsItem]:
        params = {
            "query": query,
            "mode": "ArtList",
            "maxrecords": min(max(limit, 1), 250),
            "format": "json",
            "sort": "HybridRel",
        }
        response = self.client.get("https://api.gdeltproject.org/api/v2/doc/doc", params=params)
        response.raise_for_status()
        payload = response.json()
        items: list[NewsItem] = []
        for article in payload.get("articles", [])[:limit]:
            items.append(
                NewsItem(
                    source=article.get("domain") or "GDELT",
                    title=article.get("title") or "",
                    url=article.get("url") or "",
                    published_at=article.get("seendate"),
                    source_type="news",
                )
            )
        return items

    def _sec_ticker_map(self) -> dict[str, dict]:
        response = self.client.get("https://www.sec.gov/files/company_tickers.json")
        response.raise_for_status()
        raw = response.json()
        return {entry["ticker"].upper(): entry for entry in raw.values()}

    def sec_filings(self, ticker: str, limit: int = 20) -> list[NewsItem]:
        mapping = self._sec_ticker_map()
        company = mapping.get(ticker.upper())
        if company is None:
            return []
        cik = str(company["cik_str"]).zfill(10)
        response = self.client.get(f"https://data.sec.gov/submissions/CIK{cik}.json")
        response.raise_for_status()
        payload = response.json()
        recent = payload.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accession = recent.get("accessionNumber", [])
        filing_dates = recent.get("filingDate", [])
        primary_docs = recent.get("primaryDocument", [])
        items: list[NewsItem] = []
        for idx, form in enumerate(forms[:limit]):
            acc_no = accession[idx]
            acc_compact = acc_no.replace("-", "")
            primary_doc = primary_docs[idx]
            filing_url = (
                f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_compact}/{primary_doc}"
            )
            items.append(
                NewsItem(
                    source="SEC EDGAR",
                    title=f"{ticker.upper()} filed Form {form}",
                    url=filing_url,
                    published_at=filing_dates[idx],
                    summary=f"Official SEC filing by {company.get('title', ticker.upper())}.",
                    source_type="sec",
                )
            )
        return items

    @staticmethod
    def deduplicate(items: list[NewsItem]) -> list[NewsItem]:
        seen: set[tuple[str, str]] = set()
        unique: list[NewsItem] = []
        for item in items:
            key = (item.title.strip().lower(), item.url.strip().lower())
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    def collect(self, ticker: str, company_name: str | None = None, limit_per_source: int = 10) -> list[NewsItem]:
        query = f'"{company_name}" OR {ticker}' if company_name else ticker
        items: list[NewsItem] = []
        # Each source is allowed to fail independently so one outage does not
        # remove all catalyst intelligence.
        for loader in (
            lambda: self.sec_filings(ticker, limit_per_source),
            lambda: self.gdelt(query, limit_per_source),
            lambda: self.google_news(query, limit_per_source),
        ):
            try:
                items.extend(loader())
            except (httpx.HTTPError, ValueError, ET.ParseError):
                continue
        return self.deduplicate(items)
