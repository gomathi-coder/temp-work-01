"""Claude API — summarise, tag, and extract entities from content."""

from __future__ import annotations
import json
import time
import anthropic
from linkwiki.core.config import ANTHROPIC_API_KEY, CLAUDE_MODEL, MAX_CONTENT_CHARS

_client: anthropic.Anthropic | None = None

_SYSTEM_PROMPT = """\
You are an expert research assistant building a personal knowledge base.
Analyse the provided content and return a single JSON object with exactly these fields:

- "summary": string — 3 to 5 sentences capturing the key ideas
- "tags": array of strings — 5 to 15 lowercase, hyphen-separated keyword tags \
(technology names, domains, content format, maturity level, key concepts)
- "entities": array of objects, each with:
    - "name": canonical name (e.g. "GPT-4", "Andrej Karpathy", "LoRA")
    - "type": one of person | tool | paper | organisation | concept | dataset | model
    - "description": one short sentence
- "suggested_groups": array of 0 to 3 short group names (2–5 words each) \
this content most naturally belongs to

Return ONLY valid JSON. No markdown fences, no commentary."""


def _client_instance() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def _truncate(text: str) -> str:
    if len(text) <= MAX_CONTENT_CHARS:
        return text
    half = MAX_CONTENT_CHARS // 2
    return text[:half] + "\n\n[... content truncated ...]\n\n" + text[-half:]


def summarise_and_tag(
    url_type: str,
    title: str | None,
    author: str | None,
    content: str,
) -> dict:
    """
    Call Claude to produce summary, tags, entities, and group suggestions.
    Returns a dict with keys: summary, tags, entities, suggested_groups.
    Retries up to 3 times with exponential backoff on transient errors.
    """
    user_text = f"URL type: {url_type}\n"
    if title:
        user_text += f"Title: {title}\n"
    if author:
        user_text += f"Author/Creator: {author}\n"
    user_text += f"\nContent:\n{_truncate(content)}"

    client = _client_instance()
    last_err: Exception | None = None

    for attempt in range(3):
        try:
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=1024,
                system=[
                    {
                        "type": "text",
                        "text": _SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_text}],
            )
            raw = response.content[0].text.strip()
            # Strip accidental markdown fences
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw)

        except json.JSONDecodeError as e:
            last_err = e
            # Retry once with an explicit reminder
            user_text += "\n\nIMPORTANT: Return only raw JSON, no markdown."

        except anthropic.RateLimitError as e:
            last_err = e
            time.sleep(2 ** attempt * 5)

        except (anthropic.APIConnectionError, anthropic.InternalServerError) as e:
            last_err = e
            time.sleep(2 ** attempt * 2)

    raise RuntimeError(f"Claude API failed after 3 attempts: {last_err}")


def name_cluster(entries: list[dict]) -> dict:
    """
    Ask Claude to name a semantic cluster given a list of entry titles and tags.
    Returns {"name": "...", "description": "..."}.
    """
    lines = "\n".join(
        f'- "{e.get("title", "(no title)")}"  [tags: {", ".join(e.get("tags", []))}]'
        for e in entries[:12]
    )
    prompt = (
        "Given these entries from a personal knowledge base that have been "
        "clustered together by semantic similarity:\n\n"
        f"{lines}\n\n"
        'Suggest a concise group name (2–5 words) and a one-sentence description.\n'
        'Return JSON only: {"name": "...", "description": "..."}'
    )
    client = _client_instance()
    for attempt in range(3):
        try:
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=150,
                system=[{"type": "text", "text": "Return only valid JSON.",
                          "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip().lstrip("```json").rstrip("```").strip()
            return json.loads(raw)
        except (json.JSONDecodeError, Exception):
            time.sleep(2 ** attempt)
    return {"name": "Unnamed Cluster", "description": ""}
