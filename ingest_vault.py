"""
Academic Vault → RAG Ingester
==============================
Reads directly from your `academic_vault` Supabase table.
Embeds each Q&A row using Gemini text-embedding-004 (768 dims).
Writes to your `documents` table for RAG retrieval.

Key features:
  - RESUMABLE: saves progress to ingest_progress.json; safe to Ctrl+C and re-run
  - PRIORITIZED: NEET first, then by helpfulness_score DESC
  - STORAGE GUARD: warns and stops before hitting Supabase free tier limit
  - NO LOCAL FILES: pure Supabase-to-Supabase pipeline

Usage:
    pip install supabase google-genai tqdm
    
    # Set env vars (use SERVICE ROLE key, not anon key)
    export SUPABASE_KEY="your_service_role_key"
    export GEMINI_API_KEY="your_gemini_api_key"

    # Dry run first — no writes, just shows what would happen
    python ingest_vault.py --dry-run

    # Ingest NEET only (recommended first pass — highest value)
    python ingest_vault.py --board "Competitive/Professional" --limit 10000

    # Ingest everything up to row budget
    python ingest_vault.py --limit 50000

    # Resume after a crash (reads ingest_progress.json automatically)
    python ingest_vault.py --resume
"""

import os
import sys
import json
import time
import hashlib
import logging
import argparse
from datetime import datetime
from pathlib import Path

try:
    from supabase import create_client, Client
    from google import genai
    from tqdm import tqdm
except ImportError as e:
    sys.exit(f"Missing dependency: {e}\nRun: pip install supabase google-genai tqdm")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
SUPABASE_URL    = "https://pyeddkjbcfzfcajcqhnj.supabase.co"
SUPABASE_KEY    = os.environ.get("SUPABASE_KEY", "")       # SERVICE ROLE key
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")

EMBED_MODEL     = "gemini-embedding-001"   # 768 dims — must match app.py

SOURCE_TABLE    = "academic_vault"
DEST_TABLE      = "documents"
PROGRESS_FILE   = "ingest_progress.json"

# Batching & rate limits
FETCH_BATCH     = 500    # rows fetched from Supabase per page
EMBED_BATCH     = 20     # rows embedded per Gemini API call
RATE_DELAY      = 0.6    # seconds between embed batches

# Storage guard
# Free Supabase = 500MB database. Each vector = 768 * 4 bytes ≈ 3KB.
# Plus ~2KB average text content = ~5KB per row.
# Safe budget: 60,000 rows ≈ 300MB (leaves room for ai_logs + other tables)
MAX_ROWS_BUDGET = 60_000   # hard stop — change if you upgrade to Pro

# Priority order for ingestion (highest value first)
PRIORITY_BOARDS = [
    "Competitive/Professional",   # NEET — 70,450 rows
    "National Board",             # 11,400 rows
    "CBSE",                       # Class 9 first within CBSE
]

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# PROGRESS TRACKER  (makes script resumable after crashes)
# ─────────────────────────────────────────────────────────────────────────────
class Progress:
    def __init__(self, path: str = PROGRESS_FILE):
        self.path = Path(path)
        self.data = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text())
            except Exception:
                pass
        return {
            "ingested_ids":    [],     # list of academic_vault ids already done
            "total_inserted":  0,
            "total_skipped":   0,
            "total_failed":    0,
            "started_at":      datetime.now().isoformat(),
            "last_updated":    datetime.now().isoformat(),
        }

    def save(self):
        self.data["last_updated"] = datetime.now().isoformat()
        self.path.write_text(json.dumps(self.data, indent=2))

    def mark_done(self, ids: list[int], inserted: int, skipped: int, failed: int):
        self.data["ingested_ids"].extend(ids)
        self.data["total_inserted"] += inserted
        self.data["total_skipped"]  += skipped
        self.data["total_failed"]   += failed
        self.save()

    @property
    def done_ids(self) -> set:
        return set(self.data["ingested_ids"])

    def summary(self) -> str:
        return (
            f"Inserted: {self.data['total_inserted']}  "
            f"Skipped: {self.data['total_skipped']}  "
            f"Failed: {self.data['total_failed']}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# FORMAT ROW → TEXT DOCUMENT
# ─────────────────────────────────────────────────────────────────────────────
def format_row(row: dict) -> str:
    """
    Convert one academic_vault row into a rich text document for embedding.
    Combines all semantically useful fields.
    """
    parts = []

    # Metadata header — helps RAG return board/level-specific context
    meta = " | ".join(filter(None, [
        row.get("board"),
        row.get("level"),
        row.get("subject"),
        row.get("question_type"),
        f"Difficulty: {row['difficulty']}" if row.get("difficulty") else None,
    ]))
    if meta:
        parts.append(f"[{meta}]")

    # The question itself
    if row.get("question"):
        parts.append(f"Question: {row['question'].strip()}")

    # English solution
    if row.get("solution_en"):
        parts.append(f"Answer (English): {row['solution_en'].strip()}")

    # Hindi solution — important for your bilingual user base
    if row.get("solution_hi"):
        parts.append(f"Answer (Hindi): {row['solution_hi'].strip()}")

    # Diagram code — Mermaid/visual content aids concept-level RAG
    if row.get("diagram_code") and row["diagram_code"].strip():
        parts.append(f"Diagram: {row['diagram_code'].strip()}")

    return "\n".join(parts)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# EMBED WITH RETRY
# ─────────────────────────────────────────────────────────────────────────────
def embed_batch(gemini: genai.Client, texts: list[str], retries: int = 4) -> list | None:
    for attempt in range(retries):
        try:
            res = gemini.models.embed_content(model=EMBED_MODEL, contents=texts, config={"output_dimensionality": 768})
            return [e.values for e in res.embeddings]
        except Exception as e:
            err = str(e).lower()
            is_rate = any(x in err for x in ("429", "quota", "resource_exhausted"))
            delay   = 2.0 * (2 ** attempt)
            if is_rate:
                log.warning("Rate limit — waiting %.1fs (attempt %d/%d)", delay, attempt+1, retries)
            else:
                log.warning("Embed error (attempt %d/%d): %s", attempt+1, retries, e)
            time.sleep(delay)
    log.error("All embed retries failed for this batch.")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# UPSERT TO documents TABLE
# ─────────────────────────────────────────────────────────────────────────────
def upsert_batch(
    sb: Client,
    rows: list[dict],
    embeddings: list[list[float]],
    source_label: str,
) -> tuple[int, int]:
    records = []
    for row, emb in zip(rows, embeddings):
        content = format_row(row)
        records.append({
            "content":     content,
            "embedding":   emb,
            "source":      source_label,
            "chunk_index": row["id"],    # use original id as chunk_index for traceability
            "checksum":    sha256(content),
            "metadata": {
                "vault_id":      row["id"],
                "board":         row.get("board"),
                "level":         row.get("level"),
                "subject":       row.get("subject"),
                "difficulty":    row.get("difficulty"),
                "question_type": row.get("question_type"),
            },
        })

    try:
        res = (
            sb.table(DEST_TABLE)
            .upsert(records, on_conflict="checksum", ignore_duplicates=True)
            .execute()
        )
        inserted = len(res.data) if res.data else 0
        skipped  = len(records) - inserted
        return inserted, skipped
    except Exception as e:
        log.error("Upsert failed: %s", e)
        return 0, len(records)


# ─────────────────────────────────────────────────────────────────────────────
# FETCH FROM academic_vault (paginated, with priority ordering)
# ─────────────────────────────────────────────────────────────────────────────
def fetch_rows(
    sb: Client,
    board_filter: str | None,
    offset: int,
    limit: int,
) -> list[dict]:
    """
    Fetch rows ordered by helpfulness_score DESC so best content is embedded first.
    """
    try:
        query = (
            sb.table(SOURCE_TABLE)
            .select("id, board, level, subject, question, solution_en, solution_hi, "
                    "diagram_code, difficulty, question_type, helpfulness_score")
            .order("helpfulness_score", desc=True)
            .range(offset, offset + limit - 1)
        )
        if board_filter:
            query = query.eq("board", board_filter)

        res = query.execute()
        return res.data or []
    except Exception as e:
        log.error("Fetch failed at offset %d: %s", offset, e)
        return []


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────
def run(
    board_filter: str | None,
    row_limit:    int,
    dry_run:      bool,
    resume:       bool,
):
    # Validate credentials
    if not SUPABASE_KEY:
        sys.exit("[FATAL] Set SUPABASE_KEY env var (use SERVICE ROLE key, not anon key)")
    if not GEMINI_API_KEY:
        sys.exit("[FATAL] Set GEMINI_API_KEY env var")

    sb     = create_client(SUPABASE_URL, SUPABASE_KEY)
    gemini = genai.Client(api_key=GEMINI_API_KEY)
    prog   = Progress()

    effective_limit = min(row_limit, MAX_ROWS_BUDGET)
    if row_limit > MAX_ROWS_BUDGET:
        log.warning(
            "Requested %d rows but storage budget is %d. Capping at %d.",
            row_limit, MAX_ROWS_BUDGET, MAX_ROWS_BUDGET
        )

    source_label = f"academic_vault_{board_filter.replace('/', '_')}" \
                   if board_filter else "academic_vault"

    log.info("=" * 65)
    log.info("Academic Vault → RAG Ingester")
    log.info("  Board filter  : %s", board_filter or "ALL")
    log.info("  Row limit     : %d", effective_limit)
    log.info("  Dry run       : %s", dry_run)
    log.info("  Resume mode   : %s", resume)
    if resume:
        log.info("  Already done  : %d rows", len(prog.done_ids))
        log.info("  %s", prog.summary())
    log.info("=" * 65)

    already_done   = prog.done_ids if resume else set()
    total_processed = 0
    offset         = 0

    with tqdm(total=effective_limit, desc="Rows processed", unit="row") as pbar:
        while total_processed < effective_limit:
            fetch_size = min(FETCH_BATCH, effective_limit - total_processed)
            rows       = fetch_rows(sb, board_filter, offset, fetch_size)

            if not rows:
                log.info("No more rows to fetch.")
                break

            # Skip already-ingested rows (resume mode)
            if resume:
                rows = [r for r in rows if r["id"] not in already_done]

            if not rows:
                offset += FETCH_BATCH
                continue

            if dry_run:
                log.info("[DRY RUN] Would process %d rows from offset %d", len(rows), offset)
                for r in rows[:3]:
                    preview = format_row(r)[:200].replace("\n", " ")
                    log.info("  Preview: %s…", preview)
                offset          += FETCH_BATCH
                total_processed += len(rows)
                pbar.update(len(rows))
                continue

            # Embed in sub-batches
            for batch_start in range(0, len(rows), EMBED_BATCH):
                batch   = rows[batch_start : batch_start + EMBED_BATCH]
                texts   = [format_row(r) for r in batch]
                ids     = [r["id"] for r in batch]

                embeddings = embed_batch(gemini, texts)
                if embeddings is None:
                    log.error("Skipping batch at offset %d — embed failed", offset + batch_start)
                    prog.mark_done(ids, inserted=0, skipped=0, failed=len(batch))
                    continue

                inserted, skipped = upsert_batch(sb, batch, embeddings, source_label)
                prog.mark_done(ids, inserted=inserted, skipped=skipped, failed=0)

                pbar.update(len(batch))
                pbar.set_postfix({"ins": prog.data["total_inserted"],
                                  "skip": prog.data["total_skipped"]})

                time.sleep(RATE_DELAY)

            total_processed += len(rows)
            offset          += FETCH_BATCH

    log.info("")
    log.info("=" * 65)
    log.info("INGESTION COMPLETE")
    log.info("  %s", prog.summary())
    log.info("  Progress saved to: %s", PROGRESS_FILE)
    log.info("=" * 65)

    # Storage estimate
    est_mb = prog.data["total_inserted"] * 5 / 1024
    log.info("Estimated storage used by documents table: ~%.0f MB", est_mb)
    if est_mb > 350:
        log.warning(
            "You're using ~%.0fMB. Supabase free tier limit is 500MB total. "
            "Consider upgrading to Pro ($25/mo) before ingesting more.", est_mb
        )


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest academic_vault into RAG documents table",
        epilog="""
Recommended run order (respects free tier storage budget):

  Pass 1 — NEET first (highest value, 80k rows but budget-cap will stop at 60k):
    python ingest_vault.py --board "Competitive/Professional" --limit 40000

  Pass 2 — National Board:
    python ingest_vault.py --board "National Board" --limit 10000

  Pass 3 — CBSE (whatever budget remains):
    python ingest_vault.py --board "CBSE" --limit 10000

  If interrupted at any point, resume with:
    python ingest_vault.py --resume --limit 60000
        """
    )
    parser.add_argument("--board",   type=str, help="Filter by board (exact match)")
    parser.add_argument("--limit",   type=int, default=10_000, help="Max rows to process")
    parser.add_argument("--dry-run", action="store_true",  help="Preview only, no writes")
    parser.add_argument("--resume",  action="store_true",  help="Resume from saved progress")
    args = parser.parse_args()

    run(
        board_filter=args.board,
        row_limit=args.limit,
        dry_run=args.dry_run,
        resume=args.resume,
    )