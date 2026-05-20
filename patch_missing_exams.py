
import sqlite3
import re
import sys
import json
import time
import traceback

DB_NAME = "coreai_vault.db"

def init_database():
    """Ensures structure exists and indexes are active."""
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
    conn.commit()
    conn.close()

def clean(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except:
            return str(value)
    return re.sub(r'\s+', ' ', str(value).strip())

def insert_rows(conn, rows):
    conn.cursor().executemany("""
        INSERT OR IGNORE INTO academic_vault
        (board, level, subject, question, solution_en, solution_hi,
         diagram_code, difficulty, question_type, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)

def progress_bar(label, count):
    sys.stdout.write(f"\r  ⚡ [Patching] {label}: {count:,} questions committed...")
    sys.stdout.flush()

# ───────────────────────────────────────────────────────────────
# PATCH 1 — JEE Mathematics (With Multi-Layer Resilient Fallbacks)
# ───────────────────────────────────────────────────────────────
def patch_jee(conn, limit=3000):
    print("\n📐 Patching Segment: JEE Mathematics & Quantitative Analysis...")
    from datasets import load_dataset
    
    # List of reliable math reasoning repos to try sequentially
    math_sources = [
        {"repo": "competition_math", "config": None, "q_col": "problem", "a_col": "solution", "lvl": "JEE Mains & Advanced", "sub": "Mathematics"},
        {"repo": "hendrycks/competition_math", "config": None, "q_col": "problem", "a_col": "solution", "lvl": "JEE Mains & Advanced", "sub": "Mathematics"},
        {"repo": "microsoft/orca-math-word-problems-200k", "config": None, "q_col": "question", "a_col": "answer", "lvl": "JEE Mains & Advanced", "sub": "Analytical Mathematics"}
    ]
    
    ds = None
    active_source = None
    for src in math_sources:
        print(f"   Trying mathematics hub: {src['repo']}...")
        try:
            ds = load_dataset(src["repo"], split="train", streaming=True, trust_remote_code=True)
            active_source = src
            print(f"   🚀 Success! Streaming data from {src['repo']}.")
            break
        except Exception:
            continue
            
    if not ds:
        print("   ⚠️ All math streaming servers are busy. Skipping JEE patch segment.")
        return

    try:
        count, buf = 0, []
        for row in ds:
            if count >= limit:
                break
            q = clean(row.get(active_source["q_col"], ""))
            sol = clean(row.get(active_source["a_col"], ""))
            if len(q) < 15 or len(sol) < 15: continue
            
            buf.append((
                "Competitive/Professional", 
                active_source["lvl"], 
                active_source["sub"], 
                q, sol, "", "", "hard", "Analytical", 
                active_source["repo"]
            ))
            count += 1
            if len(buf) >= 50:
                insert_rows(conn, buf)
                conn.commit()
                buf = []
                progress_bar("Math Analytics", count)
        if buf:
            insert_rows(conn, buf)
            conn.commit()
        print(f"\n✅ Completed JEE Mathematics patch: Added {count:,} questions.")
    except Exception as e:
        print(f"\n⚠️ Math ingestion event: {e}")

# ───────────────────────────────────────────────────────────────
# PATCH 2 — CA / CS / CMA (With Correct MMLU Config Names)
# ───────────────────────────────────────────────────────────────
def patch_ca_cs(conn, limit=3000):
    print("\n📒 Patching Segment: CA / CS Accountancy, Law & Management...")
    # FIXED: Replaced raw 'macroeconomics' & 'microeconomics' with corrected MMLU config tags
    configs = [
        "professional_accounting", 
        "business_ethics", 
        "management", 
        "high_school_macroeconomics", 
        "high_school_microeconomics",
        "marketing",
        "econometrics"
    ]
    try:
        from datasets import load_dataset
        count, buf = 0, []
        for cfg in configs:
            if count >= limit: break
            try:
                ds = load_dataset("cais/mmlu", cfg, split="test", streaming=True)
            except Exception:
                continue
                
            for row in ds:
                if count >= limit: break
                q = clean(row.get("question", ""))
                choices = row.get("choices", [])
                idx = row.get("answer", 0)
                if isinstance(idx, str):
                    idx = ord(idx.upper()) - ord('A')
                correct = choices[idx] if isinstance(idx, int) and idx < len(choices) else "N/A"
                if len(q) < 15: continue
                
                sol = f"Question: {q}\nOptions:\n" + "\n".join([f"  {chr(65+i)}) {c}" for i, c in enumerate(choices)]) + f"\n\nCorrect Answer: {correct}"
                buf.append(("Competitive/Professional", "CA/CS/CMA", "Accountancy, Law & Management", q, sol, "", "", "hard", "MCQ", f"mmlu_{cfg}"))
                count += 1
                if len(buf) >= 50:
                    insert_rows(conn, buf)
                    conn.commit()
                    buf = []
                    progress_bar("CA/CS/CMA", count)
        if buf:
            insert_rows(conn, buf)
            conn.commit()
        print(f"\n✅ Completed CA/CS/CMA patch: Added {count:,} questions.")
    except Exception as e:
        print(f"\n⚠️ CA/CS patch skipped: {e}")

# ───────────────────────────────────────────────────────────────
# PATCH 3 — UPSC General Studies
# ───────────────────────────────────────────────────────────────
def patch_upsc(conn, limit=3000):
    print("\n🏛️  Patching Segment: UPSC Civil Services General Studies...")
    configs = ["high_school_government_and_politics", "high_school_geography", "high_school_economics", "professional_law"]
    try:
        from datasets import load_dataset
        count, buf = 0, []
        for cfg in configs:
            if count >= limit: break
            try:
                ds = load_dataset("cais/mmlu", cfg, split="test", streaming=True)
            except Exception:
                continue
                
            for row in ds:
                if count >= limit: break
                q = clean(row.get("question", ""))
                choices = row.get("choices", [])
                idx = row.get("answer", 0)
                if isinstance(idx, str):
                    idx = ord(idx.upper()) - ord('A')
                correct = choices[idx] if isinstance(idx, int) and idx < len(choices) else "N/A"
                if len(q) < 15: continue
                
                sol = f"Question: {q}\nOptions:\n" + "\n".join([f"  {chr(65+i)}) {c}" for i, c in enumerate(choices)]) + f"\n\nCorrect Answer: {correct}"
                buf.append(("Competitive/Professional", "UPSC Civil Services", "History, Geography & Culture", q, sol, "", "", "hard", "MCQ", f"mmlu_{cfg}"))
                count += 1
                if len(buf) >= 50:
                    insert_rows(conn, buf)
                    conn.commit()
                    buf = []
                    progress_bar("UPSC GS", count)
        if buf:
            insert_rows(conn, buf)
            conn.commit()
        print(f"\n✅ Completed UPSC GS patch: Added {count:,} questions.")
    except Exception as e:
        print(f"\n⚠️ UPSC patch skipped: {e}")

# ───────────────────────────────────────────────────────────────
# PATCH 4 — Computer Science & Programming
# ───────────────────────────────────────────────────────────────
def patch_programming(conn, limit=3000):
    print("\n💻 Patching Segment: Python Programming & CS Theory...")
    try:
        from datasets import load_dataset
        count, buf = 0, []
        configs = ["college_computer_science", "high_school_computer_science", "computer_security"]
        for cfg in configs:
            if count >= limit: break
            try:
                ds = load_dataset("cais/mmlu", cfg, split="test", streaming=True)
            except Exception:
                continue
                
            for row in ds:
                if count >= limit: break
                q = clean(row.get("question", ""))
                choices = row.get("choices", [])
                idx = row.get("answer", 0)
                correct = choices[idx] if isinstance(idx, int) and idx < len(choices) else "N/A"
                if len(q) < 15: continue
                
                sol = f"Question: {q}\nOptions:\n" + "\n".join([f"  {chr(65+i)}) {c}" for i, c in enumerate(choices)]) + f"\n\nCorrect Answer: {correct}"
                buf.append(("Programming/CS", "Programming/CS", "Python Programming & Theory", q, sol, "", "", "medium", "MCQ", f"mmlu_{cfg}"))
                count += 1
                if len(buf) >= 50:
                    insert_rows(conn, buf)
                    conn.commit()
                    buf = []
                    progress_bar("Computer Science", count)
        if buf:
            insert_rows(conn, buf)
            conn.commit()
        print(f"\n✅ Completed Computer Science patch: Added {count:,} questions.")
    except Exception as e:
        print(f"\n⚠️ Programming patch skipped: {e}")

def main():
    init_database()
    conn = sqlite3.connect(DB_NAME)
    
    patch_jee(conn, limit=3000)
    patch_ca_cs(conn, limit=3000)
    patch_upsc(conn, limit=3000)
    patch_programming(conn, limit=3000)
    
    conn.close()
    print("\n🎉 Master Database Patch Complete! Run 'python check_db.py' to verify your new balanced layout.")

if __name__ == "__main__":
    main()
