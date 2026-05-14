"""Knowledge-graph linker — creates edges between entries and auto-groups them."""

from __future__ import annotations
from linkwiki.core import database as db, vectors
from linkwiki.core.config import SEMANTIC_THRESHOLD, CLUSTER_EPS, CLUSTER_MIN_SAMPLES


# ── Per-entry linking (called after every ingest) ──────────────────────────

def link_entry(entry_id: str) -> None:
    """Create all edge types for a newly ingested entry vs existing entries."""
    _tag_links_for(entry_id)
    _entity_links_for(entry_id)
    _semantic_links_for(entry_id)
    _discovered_links_for(entry_id)


# ── Tag-based linking ──────────────────────────────────────────────────────

def _tag_links_for(entry_id: str) -> int:
    entry = db.get_entry(entry_id)
    if not entry or not entry["tags"]:
        return 0

    all_entries = db.get_all_entries_for_linking()
    my_tags = set(entry["tags"])
    count = 0

    for other in all_entries:
        if other["id"] == entry_id:
            continue
        other_tags = set(other["tags"])
        shared = my_tags & other_tags
        if len(shared) >= 2:
            strength = round(len(shared) / min(len(my_tags), len(other_tags)) * 0.8, 4)
            db.upsert_link(entry_id, other["id"], "shared_tag", strength,
                           {"shared_tags": list(shared)})
            count += 1
    return count


def link_by_tags() -> int:
    """Re-link all entry pairs by shared tags."""
    all_entries = db.get_all_entries_for_linking()
    count = 0
    for i, a in enumerate(all_entries):
        tags_a = set(a["tags"])
        if not tags_a:
            continue
        for b in all_entries[i + 1:]:
            tags_b = set(b["tags"])
            shared = tags_a & tags_b
            if len(shared) >= 2:
                strength = round(len(shared) / min(len(tags_a), len(tags_b)) * 0.8, 4)
                db.upsert_link(a["id"], b["id"], "shared_tag", strength,
                               {"shared_tags": list(shared)})
                count += 1
    return count


# ── Entity-based linking ───────────────────────────────────────────────────

def _entity_names(entry: dict) -> set[str]:
    return {e["name"].lower() for e in entry.get("entities", []) if e.get("name")}


def _entity_links_for(entry_id: str) -> int:
    entry = db.get_entry(entry_id)
    if not entry or not entry["entities"]:
        return 0

    all_entries = db.get_all_entries_for_linking()
    my_entities = _entity_names(entry)
    count = 0

    for other in all_entries:
        if other["id"] == entry_id:
            continue
        other_entities = _entity_names(other)
        shared = my_entities & other_entities
        if shared:
            strength = round(len(shared) / min(len(my_entities), len(other_entities)) * 0.7, 4)
            db.upsert_link(entry_id, other["id"], "shared_entity", strength,
                           {"shared_entities": list(shared)})
            count += 1
    return count


def link_by_entities() -> int:
    """Re-link all entry pairs by shared entities."""
    all_entries = db.get_all_entries_for_linking()
    count = 0
    for i, a in enumerate(all_entries):
        ents_a = _entity_names(a)
        if not ents_a:
            continue
        for b in all_entries[i + 1:]:
            ents_b = _entity_names(b)
            shared = ents_a & ents_b
            if shared:
                strength = round(len(shared) / min(len(ents_a), len(ents_b)) * 0.7, 4)
                db.upsert_link(a["id"], b["id"], "shared_entity", strength,
                               {"shared_entities": list(shared)})
                count += 1
    return count


# ── Semantic linking ───────────────────────────────────────────────────────

def _semantic_links_for(entry_id: str) -> int:
    neighbours = vectors.similar_to(entry_id, n=20)
    count = 0
    for n in neighbours:
        if n["similarity"] >= SEMANTIC_THRESHOLD:
            db.upsert_link(entry_id, n["id"], "semantic", n["similarity"],
                           {"similarity_score": n["similarity"]})
            count += 1
    return count


def link_by_semantic() -> int:
    """Re-create semantic edges for all embedded entries."""
    ids, matrix = vectors.get_all_embeddings()
    if ids is None or len(ids) < 2:
        return 0

    import numpy as np
    # Normalise rows for cosine similarity
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normed = matrix / norms

    sim_matrix = normed @ normed.T
    count = 0
    n = len(ids)
    for i in range(n):
        for j in range(i + 1, n):
            sim = float(sim_matrix[i, j])
            if sim >= SEMANTIC_THRESHOLD:
                db.upsert_link(ids[i], ids[j], "semantic", round(sim, 4),
                               {"similarity_score": round(sim, 4)})
                count += 1
    return count


# ── Discovered-link edges ──────────────────────────────────────────────────

def _discovered_links_for(entry_id: str) -> int:
    entry = db.get_entry(entry_id)
    if not entry:
        return 0
    count = 0
    for lnk in entry.get("discovered_links", []):
        existing = db.url_exists(lnk["url"])
        if existing and existing != entry_id:
            db.upsert_link(entry_id, existing, "discovered", 0.6,
                           {"label": lnk.get("label", ""), "context": lnk.get("context", "")})
            count += 1
    return count


def link_discovered_all() -> int:
    """Create discovered edges across all entries."""
    all_entries = db.get_all_entries_for_linking()
    count = 0
    for entry in all_entries:
        count += _discovered_links_for(entry["id"])
    return count


# ── Auto-grouping ──────────────────────────────────────────────────────────

def auto_group_by_tags(min_entries: int = 3) -> int:
    """Create one group per tag that appears in ≥ min_entries entries."""
    all_entries = db.get_all_entries_for_linking()
    tag_map: dict[str, list[str]] = {}
    for e in all_entries:
        for tag in e["tags"]:
            tag_map.setdefault(tag, []).append(e["id"])

    created = 0
    for tag, entry_ids in tag_map.items():
        if len(entry_ids) < min_entries:
            continue
        name = tag.upper() if len(tag) <= 4 else tag.replace("-", " ").title()
        gid = db.get_or_create_group(name, "auto-tag")
        for eid in entry_ids:
            db.assign_to_group(eid, gid, "auto")
        created += 1
    return created


def auto_group_by_entities(min_entries: int = 3) -> int:
    """Create one group per entity name appearing in ≥ min_entries entries."""
    all_entries = db.get_all_entries_for_linking()
    entity_map: dict[str, list[str]] = {}
    for e in all_entries:
        for ent in e.get("entities", []):
            name = ent.get("name", "").strip()
            if name:
                entity_map.setdefault(name, []).append(e["id"])

    created = 0
    for entity_name, entry_ids in entity_map.items():
        if len(entry_ids) < min_entries:
            continue
        gid = db.get_or_create_group(entity_name, "auto-entity")
        for eid in entry_ids:
            db.assign_to_group(eid, gid, "auto")
        created += 1
    return created


def auto_group_semantic() -> int:
    """Cluster entries by embedding similarity, ask Claude to name each cluster."""
    from linkwiki.core import ai as claude_ai

    ids, matrix = vectors.get_all_embeddings()
    if ids is None or len(ids) < CLUSTER_MIN_SAMPLES * 2:
        return 0

    import numpy as np
    from sklearn.cluster import DBSCAN  # type: ignore

    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normed = (matrix / norms).astype(np.float64)

    labels = DBSCAN(eps=CLUSTER_EPS, min_samples=CLUSTER_MIN_SAMPLES,
                    metric="cosine").fit_predict(normed)

    cluster_map: dict[int, list[str]] = {}
    for entry_id, label in zip(ids, labels):
        if label == -1:   # noise — not part of any cluster
            continue
        cluster_map.setdefault(int(label), []).append(entry_id)

    created = 0
    # Remove stale auto-semantic groups before rebuilding
    for g in db.list_groups():
        if g["group_type"] == "auto-semantic":
            db.delete_group(g["name"])

    for label, entry_ids in cluster_map.items():
        entries = [db.get_entry(eid) for eid in entry_ids if db.get_entry(eid)]
        if not entries:
            continue

        cluster_info = [
            {"title": e.get("title") or e["url"], "tags": e["tags"][:5]}
            for e in entries
        ]
        try:
            named = claude_ai.name_cluster(cluster_info)
            group_name = named.get("name", f"Cluster {label}")
            description = named.get("description", "")
        except Exception:
            group_name = f"Cluster {label}"
            description = ""

        gid = db.get_or_create_group(group_name, "auto-semantic")
        if description:
            with db._conn() as conn:
                conn.execute("UPDATE groups SET description = ? WHERE id = ?",
                             (description, gid))
        for eid in entry_ids:
            db.assign_to_group(eid, gid, "auto")
        created += 1

    return created


# ── Full sync ──────────────────────────────────────────────────────────────

def sync_all(
    run_tags: bool = True,
    run_entities: bool = True,
    run_semantic: bool = True,
) -> dict:
    results: dict[str, int] = {}
    if run_tags:
        results["tag_links"] = link_by_tags()
        results["tag_groups"] = auto_group_by_tags()
    if run_entities:
        results["entity_links"] = link_by_entities()
        results["entity_groups"] = auto_group_by_entities()
    if run_semantic:
        results["semantic_links"] = link_by_semantic()
        results["semantic_groups"] = auto_group_semantic()
    results["discovered_links"] = link_discovered_all()
    return results
