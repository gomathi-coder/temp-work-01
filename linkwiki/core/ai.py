"""Claude API — summarise, tag, and extract entities from content."""

from __future__ import annotations
import json
import logging
import time
import anthropic
from linkwiki.core.config import ANTHROPIC_API_KEY, CLAUDE_MODEL, MAX_CONTENT_CHARS

log = logging.getLogger(__name__)

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
    content_chars = len(content)
    log.info(
        "summarisation started",
        extra={"url_type": url_type, "title": title, "content_chars": content_chars,
               "model": CLAUDE_MODEL},
    )

    user_text = f"URL type: {url_type}\n"
    if title:
        user_text += f"Title: {title}\n"
    if author:
        user_text += f"Author/Creator: {author}\n"
    user_text += f"\nContent:\n{_truncate(content)}"

    client = _client_instance()
    last_err: Exception | None = None
    t0 = time.monotonic()

    for attempt in range(3):
        attempt_num = attempt + 1
        log.debug(
            "sending request to Claude",
            extra={"url_type": url_type, "attempt": attempt_num, "model": CLAUDE_MODEL},
        )
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
            duration_ms = int((time.monotonic() - t0) * 1000)
            raw = response.content[0].text.strip()
            # Strip accidental markdown fences
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw)
            log.info(
                "Claude API call succeeded",
                extra={
                    "url_type": url_type,
                    "attempt": attempt_num,
                    "duration_ms": duration_ms,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "tags_returned": len(result.get("tags", [])),
                    "entities_returned": len(result.get("entities", [])),
                },
            )
            return result

        except json.JSONDecodeError as e:
            last_err = e
            log.warning(
                "JSON decode error, retrying with reminder",
                extra={"url_type": url_type, "attempt": attempt_num, "error": str(e)},
            )
            user_text += "\n\nIMPORTANT: Return only raw JSON, no markdown."

        except anthropic.RateLimitError as e:
            last_err = e
            wait_secs = 2 ** attempt * 5
            log.warning(
                "rate limit hit, backing off",
                extra={"url_type": url_type, "attempt": attempt_num,
                       "wait_secs": wait_secs, "error": str(e)},
            )
            time.sleep(wait_secs)

        except (anthropic.APIConnectionError, anthropic.InternalServerError) as e:
            last_err = e
            wait_secs = 2 ** attempt * 2
            log.warning(
                "API transient error, retrying",
                extra={"url_type": url_type, "attempt": attempt_num,
                       "wait_secs": wait_secs, "error": str(e)},
            )
            time.sleep(wait_secs)

    duration_ms = int((time.monotonic() - t0) * 1000)
    log.error(
        "Claude API failed after all attempts",
        extra={"url_type": url_type, "title": title,
               "duration_ms": duration_ms, "last_error": str(last_err)},
    )
    raise RuntimeError(f"Claude API failed after 3 attempts: {last_err}")


def name_cluster(entries: list[dict]) -> dict:
    """
    Ask Claude to name a semantic cluster given a list of entry titles and tags.
    Returns {"name": "...", "description": "..."}.
    """
    entry_count = len(entries)
    log.info("cluster naming started", extra={"entry_count": entry_count})
    t0 = time.monotonic()

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
        attempt_num = attempt + 1
        try:
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=150,
                system=[{"type": "text", "text": "Return only valid JSON.",
                          "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip().lstrip("```json").rstrip("```").strip()
            result = json.loads(raw)
            duration_ms = int((time.monotonic() - t0) * 1000)
            log.info(
                "cluster naming complete",
                extra={"entry_count": entry_count, "cluster_name": result.get("name"),
                       "attempt": attempt_num, "duration_ms": duration_ms},
            )
            return result
        except (json.JSONDecodeError, Exception) as e:
            log.warning(
                "cluster naming attempt failed",
                extra={"attempt": attempt_num, "error": str(e)},
            )
            time.sleep(2 ** attempt)

    log.warning("cluster naming exhausted retries, returning fallback", extra={"entry_count": entry_count})
    return {"name": "Unnamed Cluster", "description": ""}
