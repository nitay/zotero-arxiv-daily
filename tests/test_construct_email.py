"""Tests for zotero_arxiv_daily.construct_email: render_email, get_stars, get_block_html."""

from zotero_arxiv_daily.construct_email import render_email, get_stars, get_block_html, get_empty_html, format_metrics
from tests.canned_responses import make_sample_paper


def test_render_email_with_papers():
    papers = [make_sample_paper(score=7.5, tldr="A great paper.", affiliations=["MIT"])]
    html = render_email(papers)
    assert "Sample Paper Title" in html
    assert "A great paper." in html
    assert "MIT" in html


def test_render_email_empty_list():
    html = render_email([])
    assert "No Papers Today" in html


def test_render_email_author_truncation():
    authors = [f"Author {i}" for i in range(10)]
    paper = make_sample_paper(authors=authors, score=7.0, tldr="ok")
    html = render_email([paper])
    assert "Author 0" in html
    assert "Author 1" in html
    assert "Author 2" in html
    assert "..." in html
    assert "Author 8" in html
    assert "Author 9" in html
    # Middle authors should be truncated
    assert "Author 5" not in html


def test_render_email_affiliation_truncation():
    affiliations = [f"Uni {i}" for i in range(8)]
    paper = make_sample_paper(affiliations=affiliations, score=7.0, tldr="ok")
    html = render_email([paper])
    assert "Uni 0" in html
    assert "Uni 4" in html
    assert "..." in html
    assert "Uni 7" not in html


def test_render_email_no_affiliations():
    paper = make_sample_paper(affiliations=None, score=7.0, tldr="ok")
    html = render_email([paper])
    assert "Unknown Affiliation" in html


def test_get_stars_low_score():
    assert get_stars(5.0) == ""
    assert get_stars(6.0) == ""


def test_get_stars_high_score():
    stars = get_stars(8.0)
    assert stars.count("full-star") == 5


def test_get_stars_mid_score():
    stars = get_stars(7.0)
    assert "star" in stars
    assert stars.count("full-star") + stars.count("half-star") > 0


def test_get_block_html_contains_all_fields():
    html = get_block_html("Title", "Auth", "3.5", "Summary", "http://pdf.url", "MIT")
    assert "Title" in html
    assert "Auth" in html
    assert "3.5" in html
    assert "Summary" in html
    assert "http://pdf.url" in html
    assert "MIT" in html


def test_get_empty_html():
    html = get_empty_html()
    assert "No Papers Today" in html


# ---------------------------------------------------------------------------
# format_metrics + citation/prominence rendering
# ---------------------------------------------------------------------------


def test_format_metrics_none_when_no_data():
    paper = make_sample_paper()
    assert format_metrics(paper) == ""


def test_format_metrics_citations_and_hindex():
    paper = make_sample_paper(citation_count=12, author_h_index=45)
    metrics = format_metrics(paper)
    assert "12 citations" in metrics
    assert "h-index 45" in metrics


def test_format_metrics_singular_citation():
    paper = make_sample_paper(citation_count=1)
    assert "1 citation" in format_metrics(paper)
    assert "1 citations" not in format_metrics(paper)


def test_format_metrics_zero_citations_still_shown():
    paper = make_sample_paper(citation_count=0)
    assert "0 citations" in format_metrics(paper)


def test_render_email_includes_metrics():
    paper = make_sample_paper(score=7.0, tldr="ok", citation_count=5, author_h_index=20)
    html = render_email([paper])
    assert "Impact:" in html
    assert "5 citations" in html
    assert "h-index 20" in html


def test_render_email_omits_impact_row_without_metrics():
    paper = make_sample_paper(score=7.0, tldr="ok")
    html = render_email([paper])
    assert "Impact:" not in html
