import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

DATA_DIR = Path(os.getenv("LINKWIKI_DATA_DIR", "") or Path.home() / ".linkwiki")
DB_PATH = DATA_DIR / "links.db"

CLAUDE_MODEL = "claude-sonnet-4-6"
MAX_CONTENT_CHARS = 80_000
