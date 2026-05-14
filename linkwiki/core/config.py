import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

DATA_DIR = Path(os.getenv("LINKWIKI_DATA_DIR", "") or Path.home() / ".linkwiki")
DB_PATH = DATA_DIR / "links.db"
CHROMA_DIR = DATA_DIR / "vectors"

EMBED_MODEL = "all-MiniLM-L6-v2"
SEMANTIC_THRESHOLD = 0.70   # cosine similarity → create an edge
CLUSTER_EPS = 0.30          # DBSCAN epsilon (cosine distance)
CLUSTER_MIN_SAMPLES = 3     # minimum entries to form a cluster

CLAUDE_MODEL = "claude-sonnet-4-6"
MAX_CONTENT_CHARS = 80_000
