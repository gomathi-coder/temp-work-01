from dataclasses import dataclass, field


@dataclass
class ExtractionResult:
    url: str
    url_type: str
    title: str | None = None
    author: str | None = None
    raw_content: str | None = None
    discovered_links: list[dict] = field(default_factory=list)
    status: str = "done"        # done | partial | error
    error_msg: str | None = None
