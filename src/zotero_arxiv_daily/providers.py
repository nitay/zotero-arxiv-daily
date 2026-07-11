"""Resolution of API base URLs from a provider name.

Both the LLM client and the API reranker talk to OpenAI-compatible
`/chat/completions` and `/embeddings` endpoints. Rather than forcing every user
to know the exact base URL, they may set a `provider` name and have the base URL
looked up here. An explicit `base_url` always wins, so any provider not listed
below (or a self-hosted endpoint) still works by setting the URL directly.
"""

# Known OpenAI-compatible providers -> base URL. Keys are matched case-insensitively.
PROVIDER_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1/",
    "claude": "https://api.anthropic.com/v1/",
    "siliconflow": "https://api.siliconflow.cn/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "together": "https://api.together.xyz/v1",
    "groq": "https://api.groq.com/openai/v1",
}


def resolve_base_url(provider: str | None, base_url: str | None) -> str:
    """Return the API base URL, preferring an explicit `base_url` over `provider`.

    Raises a clear error if neither is usable so misconfiguration fails loudly at
    startup rather than as an opaque HTTP error later.
    """
    if base_url:
        return base_url
    if provider:
        key = provider.strip().lower()
        if key in PROVIDER_BASE_URLS:
            return PROVIDER_BASE_URLS[key]
        known = ", ".join(sorted(PROVIDER_BASE_URLS))
        raise ValueError(
            f"Unknown API provider '{provider}'. Set a known provider ({known}) "
            "or set base_url explicitly."
        )
    raise ValueError(
        "No API endpoint configured: set a provider (e.g. AI_PROVIDER=anthropic) "
        "or a base_url explicitly."
    )
