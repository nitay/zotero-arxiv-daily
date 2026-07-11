import pytest

from zotero_arxiv_daily.providers import PROVIDER_BASE_URLS, resolve_base_url


class TestResolveBaseUrl:
    def test_explicit_base_url_wins_over_provider(self):
        assert resolve_base_url("anthropic", "https://custom/v1") == "https://custom/v1"

    def test_provider_lookup(self):
        assert resolve_base_url("anthropic", None) == PROVIDER_BASE_URLS["anthropic"]
        assert resolve_base_url("openai", None) == PROVIDER_BASE_URLS["openai"]

    def test_provider_lookup_is_case_insensitive_and_trimmed(self):
        assert resolve_base_url("  Anthropic ", None) == PROVIDER_BASE_URLS["anthropic"]

    def test_claude_alias_maps_to_anthropic(self):
        assert resolve_base_url("claude", None) == resolve_base_url("anthropic", None)

    def test_base_url_only(self):
        assert resolve_base_url(None, "https://api.openai.com/v1") == "https://api.openai.com/v1"

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown API provider"):
            resolve_base_url("bogus", None)

    def test_nothing_configured_raises(self):
        with pytest.raises(ValueError, match="No API endpoint configured"):
            resolve_base_url(None, None)
