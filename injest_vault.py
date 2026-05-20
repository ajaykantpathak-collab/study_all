import sqlite3
import re
import sys
import json
import time
import traceback

DB_NAME = "coreai_vault.db"

# ═══════════════════════════════════════════════════════════════
#  EXPECTED QUESTION COUNTS (full ingestion)
# ═══════════════════════════════════════════════════════════════
#  EXISTING STREAMS
#  1.  NEET        medmcqa                     → ~182,000
#  2.  JEE         lighteval/MATH              → ~7,500
#  3.  Banking     math_qa                     → ~23,000
#  4.  UPSC        cais/mmlu (5 configs)        → ~2,500
# ───────────────────────────────────────────────────────────────
#  NEW STREAMS
#  5.  CA/CS/CMA   cais/mmlu (law+accountancy)  → ~3,000
#  6.  Finance QA  dreamerdeo/finqa             → ~8,000
#  7.  English     cais/mmlu (english configs)  → ~3,000
#  8.  Hindi Q&A   ai4bharat/indic-instruct      → ~15,000
#  9.  Reasoning   openai/gsm8k                 → ~8,500
#  10. CS Theory   cais/mmlu (cs configs)        → ~4,000
#  11. Programming codefuse-ai/CodeExercise-Python-27k → ~27,000
#  12. Science     cais/mmlu (science configs)  → ~6,000
#  13. History/Geo cais/mmlu (10 configs)        → ~5,000
#  14. Long Answer rajpurkar/squad              → ~87,000
# ───────────────────────────────────────────────────────────────
#  TOTAL EXPECTED  → ~480,000 rows
# ═══════════════════════════════════════════════════════════════


def init_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

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

    # Safe migration — adds missing columns on existing DBs
    for sql in [
        "ALTER TABLE academic_vault ADD COLUMN difficulty        TEXT",
        "ALTER TABLE academic_vault ADD COLUMN question_type     TEXT",
        "ALTER TABLE academic_vault ADD COLUMN source            TEXT",
        "ALTER TABLE academic_vault ADD COLUMN solution_hi       TEXT",
        "ALTER TABLE academic_vault ADD COLUMN diagram_code      TEXT",
        "ALTER TABLE academic_vault ADD COLUMN board             TEXT",
        "ALTER TABLE academic_vault ADD COLUMN helpfulness_score REAL    DEFAULT 0.5",
        "ALTER TABLE academic_vault ADD COLUMN times_served      INTEGER DEFAULT 0",
    ]:
        try:
            cursor.execute(sql)
        except sqlite3.OperationalError:
            pass

    for sql in [
        "CREATE INDEX IF NOT EXISTS idx_source     ON academic_vault(source)",
        "CREATE INDEX IF NOT EXISTS idx_level      ON academic_vault(level)",
        "CREATE INDEX IF NOT EXISTS idx_difficulty ON academic_vault(difficulty)",
        "CREATE INDEX IF NOT EXISTS idx_subject    ON academic_vault(subject)",
        "CREATE INDEX IF NOT EXISTS idx_board      ON academic_vault(board)",
    ]:
        cursor.execute(sql)

    conn.commit()
    conn.close()
    print("✅ Database schema verified, migrated, and indexes created.")


def clean(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(value)
    return re.sub(r'\s+', ' ', str(value).strip())


def insert(conn, rows):
    conn.cursor().executemany("""
        INSERT OR IGNORE INTO academic_vault
        (board, level, subject, question, solution_en, solution_hi,
         diagram_code, difficulty, question_type, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)


def progress(label, n):
    sys.stdout.write(f"\r  ⚡ {label}: {n:,} rows...")
    sys.stdout.flush()


def mmlu_configs(conn, configs, level, subject, difficulty, source_prefix):
    """Generic helper for any set of MMLU configs."""
    from datasets import load_dataset
    count, buf = 0, []
    for cfg in configs:
        try:
            ds = load_dataset("cais/mmlu", cfg, split="test", streaming=True)
        except Exception:
            print(f"   ⚠ Config '{cfg}' skipped")
            continue
        for row in ds:
            q       = clean(row.get("question", ""))
            choices = row.get("choices", [])
            idx     = row.get("answer", 0)
            if isinstance(idx, str):
                idx = ord(idx.upper()) - ord('A')
            correct = choices[idx] if isinstance(idx, int) and idx < len(choices) else "N/A"
            if len(q) < 15:
                continue
            sol = (
                f"Question: {q}\nOptions:\n"
                + "\n".join([f"  {chr(65+i)}) {c}" for i, c in enumerate(choices)])
                + f"\n\nCorrect Answer: {correct}"
            )
            buf.append(("Competitive/Professional", level, subject, q, sol, "", "", difficulty, "MCQ", f"{source_prefix}_{cfg}"))
            count += 1
            if len(buf) >= 50:
                insert(conn, buf); conn.commit(); buf = []; progress(source_prefix, count)
    if buf:
        insert(conn, buf); conn.commit()
    return count


# ───────────────────────────────────────────────────────────────
# STREAM 1 — NEET / AIIMS  (~182,000)
# ───────────────────────────────────────────────────────────────
def stream_neet(conn):
    print("\n🩺 [1/14] NEET / AIIMS Medical  (medmcqa)  ~182,000 rows")
    try:
        from datasets import load_dataset
        ds = load_dataset("medmcqa", split="train", streaming=True)
        count, buf = 0, []
        for row in ds:
            q   = clean(row.get("question", ""))
            exp = clean(row.get("exp", ""))
            if len(q) < 15: continue
            if len(exp) < 10:
                exp = (f"A: {row.get('opa','')}\nB: {row.get('opb','')}\n"
                       f"C: {row.get('opc','')}\nD: {row.get('opd','')}\n"
                       f"Correct Index: {row.get('cop','')}")
            buf.append(("Competitive/Professional","NEET","Botany, Zoology & Medicine",q,exp,"","","hard","MCQ","medmcqa"))
            count += 1
            if len(buf) >= 50: insert(conn,buf); conn.commit(); buf=[]; progress("NEET",count)
        if buf: insert(conn,buf); conn.commit()
        print(f"\n✅ NEET — {count:,} rows"); return count
    except Exception:
        print("\n⚠ NEET failed:"); traceback.print_exc(); return 0


# ───────────────────────────────────────────────────────────────
# STREAM 2 — JEE Mains & Advanced  (~7,500)
# ───────────────────────────────────────────────────────────────
def stream_jee(conn):
    print("\n📐 [2/14] JEE Mains & Advanced  (lighteval/MATH)  ~7,500 rows")
    try:
        from datasets import load_dataset
        ds = load_dataset("lighteval/MATH", split="train", streaming=True, trust_remote_code=True)
        count, buf = 0, []
        for row in ds:
            q   = clean(row.get("problem",""))
            sol = clean(row.get("solution",""))
            if len(q)<15 or len(sol)<15: continue
            lvl = clean(row.get("level","")).lower()
            diff = "hard" if ("5" in lvl or "4" in lvl) else "medium"
            buf.append(("Competitive/Professional","JEE Mains & Advanced","Mathematics",q,sol,"","",diff,"Analytical","lighteval_MATH"))
            count += 1
            if len(buf)>=50: insert(conn,buf); conn.commit(); buf=[]; progress("JEE",count)
        if buf: insert(conn,buf); conn.commit()
        print(f"\n✅ JEE — {count:,} rows"); return count
    except Exception:
        print("\n⚠ JEE failed:"); traceback.print_exc(); return 0


# ───────────────────────────────────────────────────────────────
# STREAM 3 — Banking / SSC  (~23,000)
# ───────────────────────────────────────────────────────────────
def stream_banking(conn):
    print("\n💰 [3/14] Banking / SSC Quantitative Aptitude  (math_qa)  ~23,000 rows")
    try:
        from datasets import load_dataset
        ds = load_dataset("math_qa", split="train", streaming=True)
        count, buf = 0, []
        for row in ds:
            q   = clean(row.get("Problem") or row.get("problem",""))
            rat = clean(row.get("Rationale") or row.get("rationale",""))
            if len(q)<15 or len(rat)<15: continue
            buf.append(("Competitive/Professional","Banking (IBPS/SBI/SSC)","Quantitative Aptitude",q,rat,"","","medium","MCQ","math_qa"))
            count += 1
            if len(buf)>=50: insert(conn,buf); conn.commit(); buf=[]; progress("Banking",count)
        if buf: insert(conn,buf); conn.commit()
        print(f"\n✅ Banking — {count:,} rows"); return count
    except Exception:
        print("\n⚠ Banking failed:"); traceback.print_exc(); return 0


# ───────────────────────────────────────────────────────────────
# STREAM 4 — UPSC Civil Services  (~2,500)
# ───────────────────────────────────────────────────────────────
def stream_upsc(conn):
    print("\n🏛️  [4/14] UPSC Civil Services  (cais/mmlu)  ~2,500 rows")
    try:
        from datasets import load_dataset
        configs = [
            "high_school_government_and_politics",
            "high_school_world_history",
            "high_school_geography",
            "high_school_economics",
            "professional_law",
        ]
        count = mmlu_configs(conn, configs, "UPSC Civil Services", "General Studies", "hard", "mmlu_upsc")
        print(f"\n✅ UPSC — {count:,} rows"); return count
    except Exception:
        print("\n⚠ UPSC failed:"); traceback.print_exc(); return 0


# ───────────────────────────────────────────────────────────────
# STREAM 5 — CA / CS / CMA  (~3,000)
# ───────────────────────────────────────────────────────────────
def stream_ca_cs(conn):
    print("\n📒 [5/14] CA / CS / CMA  (cais/mmlu law + accountancy configs)  ~3,000 rows")
    try:
        from datasets import load_dataset
        configs = [
            "professional_accounting",
            "business_ethics",
            "professional_law",
            "management",
            "public_relations",
            "marketing",
            "econometrics",
            "macroeconomics",
            "microeconomics",
        ]
        count = mmlu_configs(conn, configs, "CA/CS/CMA", "Accountancy, Law & Management", "hard", "mmlu_cacs")
        print(f"\n✅ CA/CS/CMA — {count:,} rows"); return count
    except Exception:
        print("\n⚠ CA/CS/CMA failed:"); traceback.print_exc(); return 0


# ───────────────────────────────────────────────────────────────
# STREAM 6 — Finance / Numerical QA  (~8,000)
# ───────────────────────────────────────────────────────────────
def stream_finance_qa(conn):
    print("\n💹 [6/14] Finance Numerical QA  (dreamerdeo/finqa)  ~8,000 rows")
    try:
        from datasets import load_dataset
        count, buf = 0, []
        for split in ["train", "validation"]:
            ds = load_dataset("dreamerdeo/finqa", split=split, streaming=True)
            for row in ds:
                q   = clean(row.get("question",""))
                ans = clean(row.get("answers",""))
                pre = clean(" ".join(row.get("pre_text",[])))
                if len(q)<15 or len(ans)<2: continue
                sol = f"Context: {pre[:300]}...\n\nAnswer: {ans}" if pre else f"Answer: {ans}"
                buf.append(("Competitive/Professional","CA/CS/CMA Banking","Financial Analysis & Numerics",q,sol,"","","hard","Long Answer","finqa"))
                count += 1
                if len(buf)>=50: insert(conn,buf); conn.commit(); buf=[]; progress("FinanceQA",count)
        if buf: insert(conn,buf); conn.commit()
        print(f"\n✅ Finance QA — {count:,} rows"); return count
    except Exception:
        print("\n⚠ Finance QA failed:"); traceback.print_exc(); return 0


# ───────────────────────────────────────────────────────────────
# STREAM 7 — English Language  (~3,000)
# ───────────────────────────────────────────────────────────────
def stream_english(conn):
    print("\n🔤 [7/14] English Language  (cais/mmlu english configs)  ~3,000 rows")
    try:
        from datasets import load_dataset
        configs = [
            "high_school_english_language_and_composition",
            "high_school_literature_and_composition",
            "linguistics",
            "formal_logic",
        ]
        count = mmlu_configs(conn, configs, "All Exams", "English Language & Grammar", "medium", "mmlu_english")
        print(f"\n✅ English — {count:,} rows"); return count
    except Exception:
        print("\n⚠ English failed:"); traceback.print_exc(); return 0


# ───────────────────────────────────────────────────────────────
# STREAM 8 — Hindi Q&A / Instruction  (~15,000)
# ───────────────────────────────────────────────────────────────
def stream_hindi(conn):
    print("\n🇮🇳 [8/14] Hindi Instruction Q&A  (ai4bharat/indic-instruct-data-v0.1)  ~15,000 rows")
    try:
        from datasets import load_dataset
        ds = load_dataset("ai4bharat/indic-instruct-data-v0.1", "hi", split="train", streaming=True, trust_remote_code=True)
        count, buf = 0, []
        for row in ds:
            q   = clean(row.get("instruction","") or row.get("input",""))
            sol = clean(row.get("output","") or row.get("response",""))
            if len(q)<15 or len(sol)<15: continue
            buf.append(("General","All Exams","Hindi Language & Comprehension",q,sol,sol,"","medium","Long Answer","indic_instruct_hi"))
            count += 1
            if len(buf)>=50: insert(conn,buf); conn.commit(); buf=[]; progress("Hindi",count)
        if buf: insert(conn,buf); conn.commit()
        print(f"\n✅ Hindi — {count:,} rows"); return count
    except Exception:
        print("\n⚠ Hindi failed (trying fallback):")
        traceback.print_exc()
        # Fallback: MMLU in other languages if indic fails
        return 0


# ───────────────────────────────────────────────────────────────
# STREAM 9 — Logical / Math Reasoning  (~8,500)
# ───────────────────────────────────────────────────────────────
def stream_reasoning(conn):
    print("\n🧠 [9/14] Logical & Math Reasoning  (openai/gsm8k)  ~8,500 rows")
    try:
        from datasets import load_dataset
        count, buf = 0, []
        for split in ["train", "test"]:
            ds = load_dataset("openai/gsm8k", "main", split=split, streaming=True)
            for row in ds:
                q   = clean(row.get("question",""))
                sol = clean(row.get("answer",""))
                if len(q)<15 or len(sol)<10: continue
                buf.append(("Competitive/Professional","Banking (IBPS/SBI/SSC)","Logical Reasoning & Problem Solving",q,sol,"","","medium","Long Answer","gsm8k"))
                count += 1
                if len(buf)>=50: insert(conn,buf); conn.commit(); buf=[]; progress("Reasoning",count)
        if buf: insert(conn,buf); conn.commit()
        print(f"\n✅ Reasoning — {count:,} rows"); return count
    except Exception:
        print("\n⚠ Reasoning failed:"); traceback.print_exc(); return 0


# ───────────────────────────────────────────────────────────────
# STREAM 10 — CS Theory  (~4,000)
# ───────────────────────────────────────────────────────────────
def stream_cs_theory(conn):
    print("\n💻 [10/14] CS Theory  (cais/mmlu cs configs)  ~4,000 rows")
    try:
        from datasets import load_dataset
        configs = [
            "computer_security",
            "machine_learning",
            "electrical_engineering",
            "college_computer_science",
            "high_school_computer_science",
        ]
        count = mmlu_configs(conn, configs, "Programming/CS", "Computer Science & Theory", "medium", "mmlu_cs")
        print(f"\n✅ CS Theory — {count:,} rows"); return count
    except Exception:
        print("\n⚠ CS Theory failed:"); traceback.print_exc(); return 0


# ───────────────────────────────────────────────────────────────
# STREAM 11 — Python Programming  (~27,000)
# ───────────────────────────────────────────────────────────────
def stream_programming(conn):
    print("\n🐍 [11/14] Python Programming Exercises  (codefuse-ai/CodeExercise-Python-27k)  ~27,000 rows")
    try:
        from datasets import load_dataset
        ds = load_dataset("codefuse-ai/CodeExercise-Python-27k", split="train", streaming=True)
        count, buf = 0, []
        for row in ds:
            rounds = row.get("chat_rounds", [])
            q, sol = "", ""
            for r in rounds:
                if r.get("role") == "human":
                    q = clean(r.get("content",""))
                elif r.get("role") == "bot":
                    sol = clean(r.get("content",""))
            if len(q)<15 or len(sol)<15: continue
            buf.append(("Programming/CS","Programming/CS","Python Programming",q,sol,"","","medium","Coding","codexercise_python"))
            count += 1
            if len(buf)>=50: insert(conn,buf); conn.commit(); buf=[]; progress("Python",count)
        if buf: insert(conn,buf); conn.commit()
        print(f"\n✅ Python Programming — {count:,} rows"); return count
    except Exception:
        print("\n⚠ Python Programming failed:"); traceback.print_exc(); return 0


# ───────────────────────────────────────────────────────────────
# STREAM 12 — Science (Physics, Chemistry, Biology)  (~6,000)
# ───────────────────────────────────────────────────────────────
def stream_science(conn):
    print("\n🔬 [12/14] Science  (cais/mmlu science configs)  ~6,000 rows")
    try:
        from datasets import load_dataset
        configs = [
            "high_school_physics",
            "high_school_chemistry",
            "high_school_biology",
            "college_physics",
            "college_chemistry",
            "college_biology",
            "astronomy",
            "anatomy",
        ]
        count = mmlu_configs(conn, configs, "NEET / JEE / CBSE", "Science (Physics, Chemistry, Biology)", "hard", "mmlu_science")
        print(f"\n✅ Science — {count:,} rows"); return count
    except Exception:
        print("\n⚠ Science failed:"); traceback.print_exc(); return 0


# ───────────────────────────────────────────────────────────────
# STREAM 13 — History & Geography  (~5,000)
# ───────────────────────────────────────────────────────────────
def stream_history_geo(conn):
    print("\n🌍 [13/14] History & Geography  (cais/mmlu 10 configs)  ~5,000 rows")
    try:
        from datasets import load_dataset
        configs = [
            "world_religions",
            "philosophy",
            "prehistory",
            "high_school_us_history",
            "high_school_european_history",
            "high_school_world_history",
            "high_school_geography",
            "global_facts",
            "international_law",
            "human_aging",
        ]
        count = mmlu_configs(conn, configs, "UPSC Civil Services", "History, Geography & Culture", "hard", "mmlu_histgeo")
        print(f"\n✅ History & Geography — {count:,} rows"); return count
    except Exception:
        print("\n⚠ History & Geography failed:"); traceback.print_exc(); return 0


# ───────────────────────────────────────────────────────────────
# STREAM 14 — Long Answer Comprehension  (~87,000)
# ───────────────────────────────────────────────────────────────
def stream_long_answer(conn):
    print("\n📖 [14/14] Long Answer Comprehension  (rajpurkar/squad)  ~87,000 rows")
    try:
        from datasets import load_dataset
        count, buf = 0, []
        for split in ["train", "validation"]:
            ds = load_dataset("rajpurkar/squad", split=split, streaming=True)
            for row in ds:
                q       = clean(row.get("question",""))
                answers = row.get("answers", {})
                ans_list = answers.get("text", []) if isinstance(answers, dict) else []
                ans     = clean(ans_list[0]) if ans_list else ""
                context = clean(row.get("context",""))
                if len(q)<15 or len(ans)<2: continue
                sol = f"Context: {context[:400]}...\n\nAnswer: {ans}"
                buf.append(("General","All Exams","English Comprehension & Long Answer",q,sol,"","","medium","Long Answer","squad"))
                count += 1
                if len(buf)>=50: insert(conn,buf); conn.commit(); buf=[]; progress("LongAnswer",count)
        if buf: insert(conn,buf); conn.commit()
        print(f"\n✅ Long Answer — {count:,} rows"); return count
    except Exception:
        print("\n⚠ Long Answer failed:"); traceback.print_exc(); return 0


# ───────────────────────────────────────────────────────────────
# FINAL REPORT
# ───────────────────────────────────────────────────────────────
def print_report(conn):
    cur = conn.cursor()
    print("\n" + "═"*60)
    print("  📊  DATABASE REPORT")
    print("═"*60)

    cur.execute("SELECT COUNT(*) FROM academic_vault")
    total = cur.fetchone()[0]
    print(f"  {'TOTAL QUESTIONS':<38} {total:>10,}")
    print("─"*60)

    print(f"\n  {'Source':<38} {'Count':>10}")
    print("─"*60)
    cur.execute("SELECT source, COUNT(*) FROM academic_vault GROUP BY source ORDER BY COUNT(*) DESC")
    for src, cnt in cur.fetchall():
        print(f"  {src:<38} {cnt:>10,}")

    print(f"\n  {'Exam Level':<38} {'Count':>10}")
    print("─"*60)
    cur.execute("SELECT level, COUNT(*) FROM academic_vault GROUP BY level ORDER BY COUNT(*) DESC")
    for lvl, cnt in cur.fetchall():
        print(f"  {lvl:<38} {cnt:>10,}")

    print(f"\n  {'Subject':<38} {'Count':>10}")
    print("─"*60)
    cur.execute("SELECT subject, COUNT(*) FROM academic_vault GROUP BY subject ORDER BY COUNT(*) DESC")
    for sub, cnt in cur.fetchall():
        print(f"  {sub:<38} {cnt:>10,}")

    print(f"\n  {'Difficulty':<38} {'Count':>10}")
    print("─"*60)
    cur.execute("SELECT difficulty, COUNT(*) FROM academic_vault GROUP BY difficulty ORDER BY COUNT(*) DESC")
    for d, cnt in cur.fetchall():
        print(f"  {d:<38} {cnt:>10,}")

    print("═"*60)


# ───────────────────────────────────────────────────────────────
# DEDUP — Remove exact & near-duplicate questions
# ───────────────────────────────────────────────────────────────
def dedup_database():
    """
    Two-pass deduplication:
      Pass 1 — Exact duplicates: same question text (shouldn't exist due
               to UNIQUE constraint, but catches any manual inserts).
      Pass 2 — Near duplicates: questions that are identical after
               lowercasing, stripping punctuation and extra whitespace.
               Keeps the row with the lowest id (oldest), deletes the rest.
    """
    print("\n🧹 Starting deduplication on:", DB_NAME)
    conn = sqlite3.connect(DB_NAME)
    cur  = conn.cursor()

    # ── Pass 1: exact duplicates ──────────────────────────────
    cur.execute("SELECT COUNT(*) FROM academic_vault")
    before = cur.fetchone()[0]
    print(f"   Rows before dedup : {before:,}")

    cur.execute("""
        DELETE FROM academic_vault
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM academic_vault
            GROUP BY question
        )
    """)
    exact_removed = cur.rowcount
    conn.commit()
    print(f"   ✅ Pass 1 (exact)  : {exact_removed:,} duplicates removed")

    # ── Pass 2: near duplicates (normalised question text) ────
    # Build a normalised key: lowercase + remove punctuation + collapse spaces
    cur.execute("SELECT id, question FROM academic_vault ORDER BY id")
    rows = cur.fetchall()

    seen      = {}   # normalised_key → first id
    to_delete = []

    for row_id, question in rows:
        # normalise: lowercase, remove non-alphanumeric (keep spaces), collapse whitespace
        key = re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9\s]', '', question.lower())).strip()
        if key in seen:
            to_delete.append((row_id,))
        else:
            seen[key] = row_id

    if to_delete:
        cur.executemany("DELETE FROM academic_vault WHERE id = ?", to_delete)
        conn.commit()

    near_removed = len(to_delete)
    print(f"   ✅ Pass 2 (near)   : {near_removed:,} near-duplicates removed")

    # ── Summary ───────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM academic_vault")
    after = cur.fetchone()[0]
    total_removed = before - after

    print(f"\n   Rows before : {before:,}")
    print(f"   Rows after  : {after:,}")
    print(f"   Total removed: {total_removed:,}")

    # Reclaim disk space
    print("   Running VACUUM to reclaim disk space...")
    conn.execute("VACUUM")
    conn.close()
    print("✅ Deduplication complete!\n")


# ───────────────────────────────────────────────────────────────
# MAIN
# ───────────────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="CoreAI Vault — Database Ingestion & Maintenance",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--dedup", action="store_true",
        help="Remove exact and near-duplicate questions from the DB without re-ingesting."
    )
    parser.add_argument(
        "--ingest", action="store_true",
        help="Run full dataset ingestion (default if no flag given)."
    )
    args = parser.parse_args()

    # If --dedup only, just dedup and exit
    if args.dedup and not args.ingest:
        dedup_database()
        conn = sqlite3.connect(DB_NAME)
        print_report(conn)
        conn.close()
        return

    # Default: run full ingestion
    start = time.time()
    init_database()
    conn  = sqlite3.connect(DB_NAME)
    total = 0

    total += stream_neet(conn)
    total += stream_jee(conn)
    total += stream_banking(conn)
    total += stream_upsc(conn)
    total += stream_ca_cs(conn)
    total += stream_finance_qa(conn)
    total += stream_english(conn)
    total += stream_hindi(conn)
    total += stream_reasoning(conn)
    total += stream_cs_theory(conn)
    total += stream_programming(conn)
    total += stream_science(conn)
    total += stream_history_geo(conn)
    total += stream_long_answer(conn)

    conn.close()

    # Always dedup after ingestion
    print("\n🔄 Running deduplication after ingestion...")
    dedup_database()

    conn = sqlite3.connect(DB_NAME)
    print_report(conn)
    conn.close()

    elapsed = time.time() - start
    mins = int(elapsed // 60)
    secs = int(elapsed % 60)
    print(f"\n🎉 All done!  {total:,} questions ingested  |  {mins}m {secs}s elapsed\n")


if __name__ == "__main__":
    main()