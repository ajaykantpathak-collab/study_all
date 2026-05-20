import sqlite3
import re
import sys
import json
import time
import traceback

DB_NAME = "coreai_vault.db"

# ─────────────────────────────────────────────
# EXPECTED QUESTION COUNTS (full ingestion)
# ─────────────────────────────────────────────
# NEET    (medmcqa)          → ~182,000 rows
# JEE     (lighteval/MATH)   → ~7,500 rows
# BANKING (math_qa)          → ~23,000 rows
# UPSC    (cais/mmlu)        → ~2,500 rows
# ─────────────────────────────────────────────
# TOTAL EXPECTED             → ~215,000 rows
# ─────────────────────────────────────────────


def init_database():
    """Creates table if missing, safely migrates any existing DB, and creates indexes."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Create table if it doesn't exist at all
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS academic_vault (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        board             TEXT,
        level             TEXT,
        subject           TEXT,
        question          TEXT UNIQUE,
        solution_en       TEXT,
        solution_hi       TEXT,
        diagram_code      TEXT,
        difficulty        TEXT,
        question_type     TEXT,
        source            TEXT,
        helpfulness_score REAL    DEFAULT 0.5,
        times_served      INTEGER DEFAULT 0,
        created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ── Safe migration: add any columns missing from older DB versions ──
    migrations = [
        "ALTER TABLE academic_vault ADD COLUMN difficulty        TEXT",
        "ALTER TABLE academic_vault ADD COLUMN question_type     TEXT",
        "ALTER TABLE academic_vault ADD COLUMN source            TEXT",
        "ALTER TABLE academic_vault ADD COLUMN solution_hi       TEXT",
        "ALTER TABLE academic_vault ADD COLUMN diagram_code      TEXT",
        "ALTER TABLE academic_vault ADD COLUMN board             TEXT",
        "ALTER TABLE academic_vault ADD COLUMN helpfulness_score REAL    DEFAULT 0.5",
        "ALTER TABLE academic_vault ADD COLUMN times_served      INTEGER DEFAULT 0",
    ]
    for sql in migrations:
        try:
            cursor.execute(sql)
        except sqlite3.OperationalError:
            pass  # column already exists — skip silently

    # ── Indexes for fast app-side filtering ──
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_source     ON academic_vault(source)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_level      ON academic_vault(level)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_difficulty ON academic_vault(difficulty)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_subject    ON academic_vault(subject)")

    conn.commit()
    conn.close()
    print("✅ Database schema verified, migrated, and indexes created.")


def clean_and_stringify(value):
    """Converts any input type to a clean normalised string."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(value)
    text = str(value).strip()
    return re.sub(r'\s+', ' ', text)


def bulk_insert(cursor, buffer):
    """Reusable insert helper — skips duplicates silently."""
    cursor.executemany("""
        INSERT OR IGNORE INTO academic_vault
        (board, level, subject, question, solution_en, solution_hi,
         diagram_code, difficulty, question_type, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, buffer)


def print_progress(label, count):
    sys.stdout.write(f"\r  ⚡ {label}: {count:,} saved...")
    sys.stdout.flush()


# ─────────────────────────────────────────────
# STREAM 1 — NEET / AIIMS  (medmcqa)
# Full dataset: ~182,000 rows
# ─────────────────────────────────────────────
def stream_neet(conn):
    print("\n🩺 Ingesting: MedMCQA  (NEET / AIIMS Medical)")
    print("   Dataset : medmcqa  |  Full dataset ~182,000 rows")
    try:
        from datasets import load_dataset
        ds = load_dataset("medmcqa", split="train", streaming=True)
        count, buffer = 0, []

        for row in ds:
            q   = clean_and_stringify(row.get("question", ""))
            exp = clean_and_stringify(row.get("exp", ""))

            if len(q) < 15:
                continue

            if len(exp) < 10:
                opts = (
                    f"A: {row.get('opa','')}\n"
                    f"B: {row.get('opb','')}\n"
                    f"C: {row.get('opc','')}\n"
                    f"D: {row.get('opd','')}"
                )
                exp = f"Multiple Choice Question.\n{opts}\nCorrect Option Index: {row.get('cop','')}"

            buffer.append((
                "Competitive/Professional", "NEET", "Botany, Zoology & Medicine",
                q, exp, "", "", "hard", "MCQ", "medmcqa"
            ))
            count += 1

            if len(buffer) >= 50:
                bulk_insert(conn.cursor(), buffer)
                conn.commit()
                buffer = []
                print_progress("NEET", count)

        if buffer:
            bulk_insert(conn.cursor(), buffer)
            conn.commit()

        print(f"\n✅ NEET complete — {count:,} rows added.")
        return count

    except Exception:
        print("\n⚠️  NEET stream failed:")
        traceback.print_exc()
        return 0


# ─────────────────────────────────────────────
# STREAM 2 — JEE Mains & Advanced  (lighteval/MATH)
# Full dataset: ~7,500 rows
# ─────────────────────────────────────────────
def stream_jee(conn):
    print("\n📐 Ingesting: Competition Math  (JEE Mains & Advanced)")
    print("   Dataset : lighteval/MATH  |  Full dataset ~7,500 rows")
    try:
        from datasets import load_dataset
        ds = load_dataset("lighteval/MATH", split="train", streaming=True, trust_remote_code=True)
        count, buffer = 0, []

        for row in ds:
            q   = clean_and_stringify(row.get("problem", ""))
            sol = clean_and_stringify(row.get("solution", ""))

            if len(q) < 15 or len(sol) < 15:
                continue

            level      = clean_and_stringify(row.get("level", "")).lower()
            difficulty = "hard" if "5" in level or "4" in level else "medium"

            buffer.append((
                "Competitive/Professional", "JEE Mains & Advanced", "Mathematics",
                q, sol, "", "", difficulty, "Analytical", "lighteval_MATH"
            ))
            count += 1

            if len(buffer) >= 50:
                bulk_insert(conn.cursor(), buffer)
                conn.commit()
                buffer = []
                print_progress("JEE", count)

        if buffer:
            bulk_insert(conn.cursor(), buffer)
            conn.commit()

        print(f"\n✅ JEE complete — {count:,} rows added.")
        return count

    except Exception:
        print("\n⚠️  JEE stream failed:")
        traceback.print_exc()
        return 0


# ─────────────────────────────────────────────
# STREAM 3 — Banking / SSC  (math_qa)
# Full dataset: ~23,000 rows
# ─────────────────────────────────────────────
def stream_banking(conn):
    print("\n💰 Ingesting: MathQA  (Banking Quantitative Aptitude / SSC)")
    print("   Dataset : math_qa  |  Full dataset ~23,000 rows")
    try:
        from datasets import load_dataset
        ds = load_dataset("math_qa", split="train", streaming=True)
        count, buffer = 0, []

        for row in ds:
            q         = clean_and_stringify(row.get("Problem") or row.get("problem", ""))
            rationale = clean_and_stringify(row.get("Rationale") or row.get("rationale", ""))

            if len(q) < 15 or len(rationale) < 15:
                continue

            buffer.append((
                "Competitive/Professional", "Banking (IBPS/SBI/SSC)", "Quantitative Aptitude",
                q, rationale, "", "", "medium", "MCQ", "math_qa"
            ))
            count += 1

            if len(buffer) >= 50:
                bulk_insert(conn.cursor(), buffer)
                conn.commit()
                buffer = []
                print_progress("Banking", count)

        if buffer:
            bulk_insert(conn.cursor(), buffer)
            conn.commit()

        print(f"\n✅ Banking complete — {count:,} rows added.")
        return count

    except Exception:
        print("\n⚠️  Banking stream failed:")
        traceback.print_exc()
        return 0


# ─────────────────────────────────────────────
# STREAM 4 — UPSC Civil Services  (cais/mmlu)
# Full dataset: ~2,500 rows across 5 configs
# ─────────────────────────────────────────────
def stream_upsc(conn):
    print("\n🏛️  Ingesting: MMLU Civics & History  (UPSC Civil Services)")
    configs = [
        "high_school_government_and_politics",
        "high_school_world_history",
        "high_school_geography",
        "high_school_economics",
        "professional_law",
    ]
    print(f"   Dataset : cais/mmlu  |  {len(configs)} configs  |  Full dataset ~2,500 rows")
    count = 0
    try:
        from datasets import load_dataset

        for config in configs:
            try:
                ds = load_dataset("cais/mmlu", config, split="test", streaming=True)
            except Exception:
                print(f"   ⚠️  Config '{config}' unavailable, skipping.")
                continue

            buffer = []
            for row in ds:
                q       = clean_and_stringify(row.get("question", ""))
                choices = row.get("choices", [])
                ans_idx = row.get("answer", 0)

                if isinstance(ans_idx, str):
                    ans_idx = ord(ans_idx.upper()) - ord('A')

                correct = choices[ans_idx] if isinstance(ans_idx, int) and ans_idx < len(choices) else "N/A"

                if len(q) < 15:
                    continue

                sol = (
                    f"Question: {q}\nOptions:\n"
                    + "\n".join([f"  {chr(65+i)}) {c}" for i, c in enumerate(choices)])
                    + f"\n\nCorrect Answer: {correct}"
                )

                buffer.append((
                    "Competitive/Professional", "UPSC Civil Services", "General Studies",
                    q, sol, "", "", "hard", "MCQ", f"mmlu_{config}"
                ))
                count += 1

                if len(buffer) >= 50:
                    bulk_insert(conn.cursor(), buffer)
                    conn.commit()
                    buffer = []
                    print_progress("UPSC", count)

            if buffer:
                bulk_insert(conn.cursor(), buffer)
                conn.commit()

        print(f"\n✅ UPSC complete — {count:,} rows added.")
        return count

    except Exception:
        print("\n⚠️  UPSC stream failed:")
        traceback.print_exc()
        return 0


# ─────────────────────────────────────────────
# FINAL REPORT
# ─────────────────────────────────────────────
def print_report(conn):
    cursor = conn.cursor()

    print("\n" + "═" * 55)
    print("  📊  DATABASE REPORT")
    print("═" * 55)

    cursor.execute("SELECT COUNT(*) FROM academic_vault")
    total = cursor.fetchone()[0]
    print(f"  {'TOTAL QUESTIONS':<30} {total:>10,}")
    print("─" * 55)

    cursor.execute("""
        SELECT source, COUNT(*) as cnt
        FROM academic_vault
        GROUP BY source ORDER BY cnt DESC
    """)
    print(f"  {'Source':<35} {'Count':>8}")
    print("─" * 55)
    for source, cnt in cursor.fetchall():
        print(f"  {source:<35} {cnt:>8,}")

    print("─" * 55)

    cursor.execute("""
        SELECT level, COUNT(*) as cnt
        FROM academic_vault
        GROUP BY level ORDER BY cnt DESC
    """)
    print(f"\n  {'Exam Level':<35} {'Count':>8}")
    print("─" * 55)
    for level, cnt in cursor.fetchall():
        print(f"  {level:<35} {cnt:>8,}")

    print("─" * 55)

    cursor.execute("""
        SELECT difficulty, COUNT(*) as cnt
        FROM academic_vault
        GROUP BY difficulty ORDER BY cnt DESC
    """)
    print(f"\n  {'Difficulty':<35} {'Count':>8}")
    print("─" * 55)
    for diff, cnt in cursor.fetchall():
        print(f"  {diff:<35} {cnt:>8,}")

    print("═" * 55)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    start = time.time()

    # Works on fresh DB AND existing DB with missing columns
    init_database()

    conn  = sqlite3.connect(DB_NAME)
    total = 0

    total += stream_neet(conn)
    total += stream_jee(conn)
    total += stream_banking(conn)
    total += stream_upsc(conn)

    print_report(conn)
    conn.close()

    elapsed = time.time() - start
    print(f"\n🎉 Ingestion complete!  {total:,} questions added  |  {elapsed:.1f}s elapsed\n")


if __name__ == "__main__":
    main()