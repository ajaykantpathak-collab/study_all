"""
Semantic Q→A lookup against academic_vault (Supabase vectors + local SQLite fallback).
"""

from __future__ import annotations

import difflib
import logging
import os
import re
import sqlite3
from dataclasses import dataclass

from edtech_config import build_rag_query, filter_rag_docs

logger = logging.getLogger(__name__)

LOCAL_DB = "coreai_vault.db"
EMBED_MODEL = "gemini-embedding-001"

# Vector similarity (cosine) from match_documents — direct vault answer
VAULT_HIT_THRESHOLD = 0.82
# Fuzzy text match on local SQLite (different scale)
LOCAL_HIT_THRESHOLD = 0.72
LOCAL_CANDIDATE_LIMIT = 2500
LOCAL_TOKEN_CANDIDATE_LIMIT = 6000


@dataclass
class VaultMatch:
    answer: str
    matched_question: str
    similarity: float
    source: str
    vault_id: int | None
    provider_label: str


def _parse_document_content(content: str) -> dict:
    """Parse ingest_vault format_row text back into fields."""
    out = {"question": "", "solution_en": "", "solution_hi": "", "diagram_code": ""}
    if not content:
        return out

    for line in content.splitlines():
        if line.startswith("Question:"):
            out["question"] = line[len("Question:"):].strip()
        elif line.startswith("Answer (English):"):
            out["solution_en"] = line[len("Answer (English):"):].strip()
        elif line.startswith("Answer (Hindi):"):
            out["solution_hi"] = line[len("Answer (Hindi):"):].strip()
        elif line.startswith("Diagram:"):
            out["diagram_code"] = line[len("Diagram:"):].strip()

    if not out["solution_en"] and not out["solution_hi"]:
        m = re.search(r"Answer \(English\):\s*(.+?)(?=\nAnswer|\nDiagram|\Z)", content, re.S)
        if m:
            out["solution_en"] = m.group(1).strip()
    return out


def _pick_solution(row: dict, hindi_only: bool) -> str:
    hi = (row.get("solution_hi") or "").strip()
    en = (row.get("solution_en") or "").strip()
    if hindi_only and hi:
        return hi
    if hindi_only and en:
        return en + "\n\n*(Hindi solution not in vault; showing English.)*"
    return hi if hi and not en else (en or hi)


def _format_answer(
    row: dict,
    *,
    matched_question: str,
    similarity: float,
    source: str,
    hindi_only: bool,
    profile_label: str,
) -> str:
    body = _pick_solution(row, hindi_only)
    diagram = (row.get("diagram_code") or "").strip()
    parts = [
        f"### 📚 From your question bank",
        f"*Profile: {profile_label} · Match: **{similarity:.0%}** ({source})*",
        "",
        f"**Matched question:** {matched_question}",
        "",
        body,
    ]
    if diagram:
        parts.extend(["", "**Diagram:**", diagram])
    parts.extend([
        "",
        "---",
        "*Answer retrieved from your vault — not generated from scratch.*",
    ])
    return "\n".join(parts)


def _embed_query(gemini_client, text: str) -> list[float] | None:
    try:
        res = gemini_client.models.embed_content(
            model=EMBED_MODEL,
            contents=text,
            config={"output_dimensionality": 768},
        )
        if not getattr(res, "embeddings", None):
            return None
        values = getattr(res.embeddings[0], "values", None)
        return values or None
    except Exception as exc:
        logger.warning("Vault embed failed: %s", exc)
        return None


def _fetch_vault_row(supabase, vault_id: int) -> dict | None:
    try:
        res = (
            supabase.table("academic_vault")
            .select("id, question, solution_en, solution_hi, diagram_code, board, level, subject")
            .eq("id", vault_id)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]
    except Exception as exc:
        logger.warning("Vault row fetch failed: %s", exc)
    return None


def _similarity_from_hit(hit: dict) -> float:
    if "similarity" in hit and hit["similarity"] is not None:
        return float(hit["similarity"])
    if "distance" in hit and hit["distance"] is not None:
        return max(0.0, 1.0 - float(hit["distance"]))
    return 0.0


def lookup_supabase_vector(
    query: str,
    profile: dict,
    supabase,
    gemini_client,
) -> VaultMatch | None:
    """Semantic match via documents embeddings (question+answer chunks)."""
    rag_query = build_rag_query(query, profile)
    vector = _embed_query(gemini_client, rag_query)
    if not vector:
        return None

    try:
        res = supabase.rpc("match_documents", {
            "query_embedding": vector,
            "match_threshold": 0.70,
            "match_count": 5,
        }).execute()
    except Exception as exc:
        logger.warning("match_documents RPC failed: %s", exc)
        return None

    hits = filter_rag_docs(res.data or [], profile)
    if not hits:
        return None

    best = max(hits, key=_similarity_from_hit)
    sim = _similarity_from_hit(best)
    if sim < VAULT_HIT_THRESHOLD:
        return None

    meta = best.get("metadata") or {}
    vault_id = meta.get("vault_id")
    row = None
    if vault_id:
        row = _fetch_vault_row(supabase, int(vault_id))

    parsed = _parse_document_content(best.get("content", ""))
    if row:
        matched_q = row.get("question") or parsed["question"]
    else:
        row = parsed
        matched_q = parsed["question"]

    if not matched_q or not (_pick_solution(row, profile.get("hindi_only", False))):
        return None

    answer = _format_answer(
        row,
        matched_question=matched_q,
        similarity=sim,
        source="Supabase vector",
        hindi_only=profile.get("hindi_only", False),
        profile_label=profile.get("display_label", ""),
    )
    return VaultMatch(
        answer=answer,
        matched_question=matched_q,
        similarity=sim,
        source="supabase_vector",
        vault_id=int(vault_id) if vault_id else None,
        provider_label=f"📚 Vault Match ({sim:.0%})",
    )


def _local_filter_sql(profile: dict) -> tuple[str, list]:
    clauses = ["1=1"]
    params: list = []

    board = profile.get("rag_board")
    if board:
        clauses.append("(board = ? OR board IS NULL OR board = '')")
        params.append(board)

    level = profile.get("rag_level")
    if level:
        clauses.append("(level LIKE ? OR level IS NULL OR level = '')")
        params.append(f"%{level}%")

    subject = profile.get("rag_subject")
    if subject:
        clauses.append("(subject LIKE ? OR subject IS NULL OR subject = '')")
        params.append(f"%{subject}%")

    where = " AND ".join(clauses)
    sql = f"""
        SELECT id, question, solution_en, solution_hi, diagram_code
        FROM academic_vault
        WHERE {where}
        LIMIT {LOCAL_CANDIDATE_LIMIT}
    """
    return sql, params


def _local_token_filter_sql(query: str, profile: dict) -> tuple[str, list]:
    base_sql, params = _local_filter_sql(profile)
    terms = [
        token for token in re.findall(r"[A-Za-z0-9]+", query.lower())
        if len(token) >= 4
    ][:6]
    if not terms:
        return base_sql, params

    where_start = base_sql.index("WHERE ") + len("WHERE ")
    where_end = base_sql.index(f"\n        LIMIT {LOCAL_CANDIDATE_LIMIT}")
    where = base_sql[where_start:where_end].strip()
    token_clause = " OR ".join(["LOWER(question) LIKE ?"] * len(terms))
    sql = f"""
        SELECT id, question, solution_en, solution_hi, diagram_code
        FROM academic_vault
        WHERE ({where}) AND ({token_clause})
        LIMIT {LOCAL_TOKEN_CANDIDATE_LIMIT}
    """
    return sql, params + [f"%{term}%" for term in terms]


def lookup_local_fuzzy(query: str, profile: dict, db_path: str = LOCAL_DB) -> VaultMatch | None:
    """Fallback when vector RPC fails — fuzzy match on local SQLite questions."""
    if not os.path.exists(db_path):
        return None

    q_norm = re.sub(r"\s+", " ", query.strip().lower())
    if len(q_norm) < 8:
        return None

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        sql, params = _local_token_filter_sql(query, profile)
        rows = conn.execute(sql, params).fetchall()
        if not rows:
            sql, params = _local_filter_sql(profile)
            rows = conn.execute(sql, params).fetchall()
        conn.close()
    except Exception as exc:
        logger.warning("Local vault query failed: %s", exc)
        return None

    if not rows:
        return None

    best_row = None
    best_score = 0.0
    for row in rows:
        question = (row["question"] or "").strip()
        if len(question) < 10:
            continue
        q_low = question.lower()
        ratio = difflib.SequenceMatcher(None, q_norm, q_low).ratio()
        # Token overlap boost for rephrased questions
        q_tokens = set(q_norm.split())
        t_tokens = set(q_low.split())
        if q_tokens and t_tokens:
            overlap = len(q_tokens & t_tokens) / max(len(q_tokens), 1)
            ratio = max(ratio, overlap * 0.85)
        if ratio > best_score:
            best_score = ratio
            best_row = row

    if not best_row or best_score < LOCAL_HIT_THRESHOLD:
        return None

    row_dict = dict(best_row)
    matched_q = row_dict.get("question", "")
    if not _pick_solution(row_dict, profile.get("hindi_only", False)):
        return None

    answer = _format_answer(
        row_dict,
        matched_question=matched_q,
        similarity=best_score,
        source="Local database (fuzzy)",
        hindi_only=profile.get("hindi_only", False),
        profile_label=profile.get("display_label", ""),
    )
    return VaultMatch(
        answer=answer,
        matched_question=matched_q,
        similarity=best_score,
        source="local_fuzzy",
        vault_id=row_dict.get("id"),
        provider_label=f"📚 Local Vault ({best_score:.0%})",
    )


def lookup_vault_answer(
    query: str,
    profile: dict,
    supabase,
    gemini_client,
) -> VaultMatch | None:
    """
    Try Supabase semantic vector match first, then local fuzzy fallback.
    Returns a ready-to-display answer when confidence is high enough.
    """
    hit = lookup_supabase_vector(query, profile, supabase, gemini_client)
    if hit:
        return hit
    return lookup_local_fuzzy(query, profile)


def vault_context_for_ai(match: VaultMatch | None) -> str:
    """Optional context string when vault match is partial — for future use."""
    if not match:
        return ""
    return (
        f"Similar vault Q: {match.matched_question}\n"
        f"Vault answer excerpt: {match.answer[:2000]}"
    )
