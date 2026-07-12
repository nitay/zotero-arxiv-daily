"""Tests for zotero_arxiv_daily.enrichment: extract_arxiv_id, enrich_papers."""

from types import SimpleNamespace

import pytest

import zotero_arxiv_daily.enrichment as enrichment
from zotero_arxiv_daily.enrichment import enrich_papers, extract_arxiv_id
from tests.canned_responses import make_sample_paper


# ---------------------------------------------------------------------------
# extract_arxiv_id
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://arxiv.org/abs/2026.00001", "2026.00001"),
        ("http://arxiv.org/abs/2401.12345v3", "2401.12345"),
        ("https://arxiv.org/pdf/2401.12345", "2401.12345"),
        ("https://arxiv.org/pdf/2401.12345v2.pdf", "2401.12345"),
        ("http://arxiv.org/abs/cs/9901001v1", "cs/9901001"),
        ("2026.00001", "2026.00001"),
        (None, None),
        ("https://biorxiv.org/content/10.1101/xyz", None),
    ],
)
def test_extract_arxiv_id(url, expected):
    assert extract_arxiv_id(url) == expected


# ---------------------------------------------------------------------------
# enrich_papers
# ---------------------------------------------------------------------------


def _stub_post(payload, captured=None):
    def _post(url, params=None, json=None, headers=None, timeout=None):
        if captured is not None:
            captured.append({"url": url, "params": params, "json": json, "headers": headers})
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: payload,
        )

    return _post


def test_enrich_papers_populates_metrics(monkeypatch):
    paper = make_sample_paper(url="https://arxiv.org/abs/2026.00001")
    payload = [
        {
            "citationCount": 12,
            "authors": [{"hIndex": 30}, {"hIndex": 45}, {"hIndex": None}],
        }
    ]
    monkeypatch.setattr(enrichment.requests, "post", _stub_post(payload))

    enrich_papers([paper])

    assert paper.citation_count == 12
    assert paper.author_h_index == 45  # max h-index among authors


def test_enrich_papers_sends_arxiv_ids_and_key(monkeypatch):
    paper = make_sample_paper(url="https://arxiv.org/abs/2401.99999")
    captured = []
    monkeypatch.setattr(
        enrichment.requests, "post", _stub_post([{"citationCount": 0, "authors": []}], captured)
    )

    enrich_papers([paper], api_key="secret-key")

    assert captured[0]["json"] == {"ids": ["ARXIV:2401.99999"]}
    assert captured[0]["headers"] == {"x-api-key": "secret-key"}


def test_enrich_papers_skips_non_arxiv(monkeypatch):
    paper = make_sample_paper(source="biorxiv", url="https://biorxiv.org/content/10.1101/xyz")

    called = []

    def _tracking_post(*args, **kwargs):
        called.append((args, kwargs))
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: [])

    monkeypatch.setattr(enrichment.requests, "post", _tracking_post)

    result = enrich_papers([paper])

    assert called == [], "No HTTP call should be made when there are no arxiv papers"
    assert paper.citation_count is None
    assert result == [paper]


def test_enrich_papers_network_error_is_non_fatal(monkeypatch):
    paper = make_sample_paper(url="https://arxiv.org/abs/2026.00001")

    def _boom(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(enrichment.requests, "post", _boom)

    result = enrich_papers([paper])

    assert result == [paper]
    assert paper.citation_count is None
    assert paper.author_h_index is None


def test_enrich_papers_handles_null_record(monkeypatch):
    """Semantic Scholar returns null for ids it does not know."""
    paper = make_sample_paper(url="https://arxiv.org/abs/2026.00001")
    monkeypatch.setattr(enrichment.requests, "post", _stub_post([None]))

    enrich_papers([paper])

    assert paper.citation_count is None
    assert paper.author_h_index is None


def test_enrich_papers_handles_length_mismatch(monkeypatch):
    paper = make_sample_paper(url="https://arxiv.org/abs/2026.00001")
    # Malformed: payload length does not match number of requested ids.
    monkeypatch.setattr(enrichment.requests, "post", _stub_post([]))

    result = enrich_papers([paper])

    assert result == [paper]
    assert paper.citation_count is None


def test_enrich_papers_no_hindex_leaves_author_h_index_none(monkeypatch):
    paper = make_sample_paper(url="https://arxiv.org/abs/2026.00001")
    monkeypatch.setattr(
        enrichment.requests,
        "post",
        _stub_post([{"citationCount": 3, "authors": [{"hIndex": None}]}]),
    )

    enrich_papers([paper])

    assert paper.citation_count == 3
    assert paper.author_h_index is None
