"""Compare local SQLite vs Supabase question counts."""
import json
import os
import sqlite3
from pathlib import Path

DB_NAME = "coreai_vault.db"
SUPABASE_URL = "https://pyeddkjbcfzfcajcqhnj.supabase.co"
PROGRESS_FILE = "ingest_progress.json"


def load_supabase_key() -> str | None:
    key = os.environ.get("SUPABASE_KEY")
    if key:
        return key
    secrets_path = Path(".streamlit/secrets.toml")
    if not secrets_path.exists():
        return None
    try:
        import tomllib
        data = tomllib.loads(secrets_path.read_text(encoding="utf-8"))
        return data.get("SUPABASE_KEY")
    except Exception:
        # fallback naive parse
        for line in secrets_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("SUPABASE_KEY"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def local_counts():
    if not Path(DB_NAME).exists():
        return None
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    total = cur.execute("SELECT COUNT(*) FROM academic_vault").fetchone()[0]
    by_board = cur.execute(
        "SELECT COALESCE(board,'(none)'), COUNT(*) FROM academic_vault GROUP BY board ORDER BY 2 DESC"
    ).fetchall()
    conn.close()
    return {"total": total, "by_board": by_board}


def progress_counts():
    if not Path(PROGRESS_FILE).exists():
        return None
    data = json.loads(Path(PROGRESS_FILE).read_text(encoding="utf-8"))
    return {
        "ingested_ids": len(data.get("ingested_ids", [])),
        "total_inserted": data.get("total_inserted", 0),
        "total_skipped": data.get("total_skipped", 0),
        "total_failed": data.get("total_failed", 0),
        "last_updated": data.get("last_updated"),
    }


def supabase_counts(key: str):
    from supabase import create_client

    sb = create_client(SUPABASE_URL, key)

    def head_count(table: str) -> int | str:
        try:
            res = (
                sb.table(table)
                .select("id", count="exact")
                .limit(1)
                .execute()
            )
            return res.count if res.count is not None else len(res.data or [])
        except Exception as exc:
            return f"error: {exc}"

    vault = head_count("academic_vault")
    documents = head_count("documents")
    ai_logs = head_count("ai_logs")

    vault_by_board = []
    try:
        # sample boards via RPC-free pagination (top groups)
        res = sb.table("academic_vault").select("board").limit(2000).execute()
        from collections import Counter
        c = Counter(r.get("board") or "(none)" for r in (res.data or []))
        vault_by_board = c.most_common(8)
    except Exception:
        pass

    return {
        "academic_vault": vault,
        "documents": documents,
        "ai_logs": ai_logs,
        "vault_board_sample": vault_by_board,
    }


def main():
    print("=" * 60)
    print("LOCAL DATABASE (coreai_vault.db)")
    print("=" * 60)
    local = local_counts()
    if not local:
        print("  Not found.")
    else:
        print(f"  academic_vault rows: {local['total']:,}")
        print("  By board (top):")
        for board, n in local["by_board"][:8]:
            print(f"    {board}: {n:,}")

    print()
    print("=" * 60)
    print("INGEST PROGRESS (local → documents RAG)")
    print("=" * 60)
    prog = progress_counts()
    if not prog:
        print("  No ingest_progress.json")
    else:
        print(f"  IDs processed:     {prog['ingested_ids']:,}")
        print(f"  Rows inserted:     {prog['total_inserted']:,}")
        print(f"  Rows skipped:      {prog['total_skipped']:,}")
        print(f"  Rows failed:       {prog['total_failed']:,}")
        print(f"  Last updated:      {prog['last_updated']}")

    print()
    print("=" * 60)
    print("SUPABASE (cloud)")
    print("=" * 60)
    key = load_supabase_key()
    cloud = {}
    if not key:
        print("  No SUPABASE_KEY in env or .streamlit/secrets.toml — skipping live query.")
    else:
        try:
            cloud = supabase_counts(key)
            av = cloud["academic_vault"]
            doc = cloud["documents"]
            logs = cloud["ai_logs"]
            print(f"  academic_vault rows: {av:,}" if isinstance(av, int) else f"  academic_vault: {av}")
            print(f"  documents (RAG) rows: {doc:,}" if isinstance(doc, int) else f"  documents: {doc}")
            print(f"  ai_logs (chat) rows:  {logs:,}" if isinstance(logs, int) else f"  ai_logs: {logs}")
            if cloud.get("vault_board_sample"):
                print("  academic_vault board sample (first 2k rows):")
                for board, n in cloud["vault_board_sample"]:
                    print(f"    {board}: {n:,}")
        except Exception as exc:
            print(f"  Supabase query failed: {exc}")

    print()
    if local and isinstance(cloud.get("academic_vault"), int):
        diff = local["total"] - cloud["academic_vault"]
        print(f"  Gap (local − Supabase academic_vault): {diff:+,}")
    if local and isinstance(cloud.get("documents"), int):
        print(f"  RAG coverage: {cloud['documents']:,} / {local['total']:,} local ({100*cloud['documents']/local['total']:.1f}%)")


if __name__ == "__main__":
    main()
