from __future__ import annotations

from typing import Any

import requests


class PubMedService:
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(
        self,
        api_key: str | None = None,
        tool_name: str = "dr_gpt",
        email: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.tool_name = tool_name
        self.email = email
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "dr_gpt/1.0 (PubMed literature search integration)"
            }
        )

    def search_articles(
        self,
        query: str,
        retmax: int = 5,
        sort: str = "relevance",
    ) -> list[dict[str, Any]]:
        query = (query or "").strip()
        if not query:
            return []

        pmids = self._esearch(query=query, retmax=retmax, sort=sort)
        if not pmids:
            return []

        summaries = self._esummary(pmids)
        results: list[dict[str, Any]] = []

        for pmid in pmids:
            s = summaries.get(str(pmid), {})

            title = (s.get("title") or "").strip() or "タイトル不明"
            pubdate = (s.get("pubdate") or "").strip()
            source = (s.get("source") or "").strip()
            authors = self._parse_authors(s.get("authors", []))
            doi = self._extract_article_id(s.get("articleids", []), "doi")

            results.append(
                {
                    "pmid": str(pmid),
                    "title": title,
                    "pubdate": pubdate,
                    "journal": source,
                    "authors": authors,
                    "doi": doi,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                }
            )

        return results

    def _base_params(self) -> dict[str, str]:
        params = {
            "tool": self.tool_name,
            "retmode": "json",
        }
        if self.email:
            params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    def _esearch(self, query: str, retmax: int, sort: str) -> list[str]:
        url = f"{self.BASE_URL}/esearch.fcgi"
        params = self._base_params()
        params.update(
            {
                "db": "pubmed",
                "term": query,
                "retmax": str(retmax),
                "sort": sort,
            }
        )

        response = self.session.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        idlist = data.get("esearchresult", {}).get("idlist", [])
        return [str(x) for x in idlist]

    def _esummary(self, pmids: list[str]) -> dict[str, Any]:
        if not pmids:
            return {}

        url = f"{self.BASE_URL}/esummary.fcgi"
        params = self._base_params()
        params.update(
            {
                "db": "pubmed",
                "id": ",".join(pmids),
                "version": "2.0",
            }
        )

        response = self.session.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        result = data.get("result", {})
        summaries: dict[str, Any] = {}
        for pmid in pmids:
            if pmid in result:
                summaries[pmid] = result[pmid]
        return summaries

    @staticmethod
    def _parse_authors(authors: list[dict[str, Any]]) -> str:
        names: list[str] = []
        for a in authors[:5]:
            name = (a.get("name") or "").strip()
            if name:
                names.append(name)

        if not names:
            return ""

        if len(authors) > 5:
            return ", ".join(names) + " et al."
        return ", ".join(names)

    @staticmethod
    def _extract_article_id(article_ids: list[dict[str, Any]], id_type: str) -> str | None:
        for item in article_ids:
            if (item.get("idtype") or "").lower() == id_type.lower():
                value = (item.get("value") or "").strip()
                if value:
                    return value
        return None
