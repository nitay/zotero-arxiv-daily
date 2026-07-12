"""Best-effort enrichment of papers with citation and author-prominence signals.

arXiv exposes no citation data of its own. To surface a sense of impact and
author standing, we query the Semantic Scholar Graph API's batch endpoint for a
paper's citation count and the maximum author h-index. For day-of-publish papers
the citation count is almost always zero, so the author h-index (a proxy for how
established the authors are) is usually the more meaningful signal.

Everything here is best-effort: any network error, rate limit, or missing record
is logged and skipped so enrichment never blocks the daily email.
"""

import re
from typing import Optional

import requests
from loguru import logger

from .protocol import Paper

S2_BATCH_URL = "https://api.semanticscholar.org/graph/v1/paper/batch"
S2_FIELDS = "citationCount,authors.hIndex"
S2_TIMEOUT = (10, 30)


def extract_arxiv_id(url: Optional[str]) -> Optional[str]:
    """Pull a bare arXiv identifier out of an abs/pdf URL or a raw id string.

    Handles new-style ids (``2401.00001``), versioned ids (``2401.00001v2``) and
    old-style category ids (``cs/9901001``). Returns ``None`` if nothing matches.
    """
    if not url:
        return None
    match = re.search(r"arxiv\.org/(?:abs|pdf)/(.+)$", url)
    if match:
        ident = match.group(1)
        ident = re.sub(r"\.pdf$", "", ident)
        ident = re.sub(r"v\d+$", "", ident)
        return ident or None
    match = re.search(r"\b(\d{4}\.\d{4,5})\b", url)
    return match.group(1) if match else None


def enrich_papers(papers: list[Paper], api_key: Optional[str] = None) -> list[Paper]:
    """Attach citation counts and author h-index to arXiv papers in place.

    Non-arXiv papers and any paper whose id cannot be resolved are left
    untouched. The paper list is always returned so callers can chain the call.
    """
    targets: list[tuple[Paper, str]] = []
    for paper in papers:
        if paper.source != "arxiv":
            continue
        arxiv_id = extract_arxiv_id(paper.url) or extract_arxiv_id(paper.pdf_url)
        if arxiv_id:
            targets.append((paper, f"ARXIV:{arxiv_id}"))

    if not targets:
        return papers

    headers = {"x-api-key": api_key} if api_key else {}
    try:
        response = requests.post(
            S2_BATCH_URL,
            params={"fields": S2_FIELDS},
            json={"ids": [ident for _, ident in targets]},
            headers=headers,
            timeout=S2_TIMEOUT,
        )
        response.raise_for_status()
        records = response.json()
    except Exception as exc:
        logger.warning(f"Semantic Scholar enrichment failed: {exc}")
        return papers

    if not isinstance(records, list) or len(records) != len(targets):
        logger.warning(
            f"Semantic Scholar returned an unexpected payload ({type(records).__name__}); "
            "skipping enrichment"
        )
        return papers

    enriched = 0
    for (paper, _), record in zip(targets, records):
        if not record:
            continue  # id not found in Semantic Scholar
        citation_count = record.get("citationCount")
        if citation_count is not None:
            paper.citation_count = citation_count
        h_indices = [
            author.get("hIndex")
            for author in (record.get("authors") or [])
            if author.get("hIndex") is not None
        ]
        if h_indices:
            paper.author_h_index = max(h_indices)
        enriched += 1

    logger.info(f"Enriched {enriched}/{len(targets)} arxiv papers with citation metrics")
    return papers
