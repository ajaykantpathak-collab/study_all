
import sqlite3
import re
import sys
import os

DB_NAME = "coreai_vault.db"

def clean_question_text(text):
    """Fuzzy matching normalizer to isolate duplicate variations."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text) # Remove punctuation
    return " ".join(text.split()) # Strip and flatten spacing

def run_db_cleanup():
    if not os.path.exists(DB_NAME):
        print(f"❌ Error: Database file '{DB_NAME}' not found!")
        return

    print("🔌 Connecting to CoreAI Vault and preparing database diagnostic...")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        # Check initial database row count
        cursor.execute("SELECT COUNT(*) FROM academic_vault")
        initial_count = cursor.fetchone()[0]
        print(f"📊 Live database size: {initial_count:,} rows")

        # ───────────────────────────────────────────────────────────────
        # 1. VERIFY AND AUDIT ANSWERS
        # ───────────────────────────────────────────────────────────────
        print("\n🔍 Auditing answer key integrity across all columns...")
        cursor.execute("""
            SELECT COUNT(*) FROM academic_vault 
            WHERE solution_en IS NOT NULL AND TRIM(solution_en) != ''
        """)
        solved_count = cursor.fetchone()[0]
        solved_percentage = (solved_count / initial_count) * 100

        print(f"  ➔ Questions with populated answers/explanations : {solved_count:,} ({solved_percentage:.2f}%)")
        print(f"  ➔ Questions missing answers                   : {initial_count - solved_count:,}")

        # ───────────────────────────────────────────────────────────────
        # 2. RUN PASS 2: FUZZY DEDUPLICATION
        # ───────────────────────────────────────────────────────────────
        print("\n🧹 Scanning for near-duplicates (case-insensitive & spacing variations)...")
        cursor.execute("SELECT id, question FROM academic_vault ORDER BY id ASC")
        all_rows = cursor.fetchall()

        seen_normalized = {}
        ids_to_delete = []

        for idx, (row_id, question) in enumerate(all_rows):
            normalized = clean_question_text(question)
            
            if normalized in seen_normalized:
                ids_to_delete.append(row_id)
            else:
                seen_normalized[normalized] = row_id

            if idx % 50000 == 0 and idx > 0:
                sys.stdout.write(f"\r  Audited {idx:,}/{initial_count:,} items...")
                sys.stdout.flush()

        print(f"\r  Audited {initial_count:,}/{initial_count:,} items successfully.")

        # Delete duplicates in batches to optimize SQLite transactions
        total_dups = len(ids_to_delete)
        if total_dups > 0:
            print(f"  🔥 Found {total_dups:,} duplicate variations. Deleting from disk...")
            
            chunk_size = 500
            for i in range(0, total_dups, chunk_size):
                chunk = ids_to_delete[i:i + chunk_size]
                cursor.execute(f"DELETE FROM academic_vault WHERE id IN ({','.join(map(str, chunk))})")
                sys.stdout.write(f"\r  Deleted {min(i + chunk_size, total_dups):,}/{total_dups:,}...")
                sys.stdout.flush()
            
            conn.commit()
            print("\n  ✅ Duplicate entries successfully purged.")
        else:
            print("  🎉 All questions in your database are completely unique! No duplicates found.")

        # ───────────────────────────────────────────────────────────────
        # 3. VACUUM AND DEFRAGMENT DATABASE
        # ───────────────────────────────────────────────────────────────
        print("\n🚀 Reclaiming empty hard drive space (defragmenting DB)...")
        cursor.execute("VACUUM")
        conn.commit()

        # Final recount
        cursor.execute("SELECT COUNT(*) FROM academic_vault")
        final_count = cursor.fetchone()[0]

        print("\n" + "═"*60)
        print("  🏁  DATABASE AUDIT AND CLEANUP COMPLETE")
        print("═"*60)
        print(f"  Starting Rows : {initial_count:,}")
        print(f"  Ending Rows   : {final_count:,}")
        print(f"  Wiped Rows    : {initial_count - final_count:,} duplicates deleted")
        print("─"*60)

        # ───────────────────────────────────────────────────────────────
        # 4. VIEW SAMPLE QUESTIONS AND SOLUTIONS
        # ───────────────────────────────────────────────────────────────
        print("\n📝 PREVIEWING RANDOM EXAMPLES AND ANSWERS FROM YOUR VAULT:")
        print("  " + "-"*52)
        cursor.execute("""
            SELECT level, subject, question, solution_en 
            FROM academic_vault 
            WHERE solution_en IS NOT NULL AND TRIM(solution_en) != '' 
            ORDER BY RANDOM() LIMIT 2
        """)
        samples = cursor.fetchall()
        for i, (level, subject, q, sol) in enumerate(samples, 1):
            print(f"\n[{i}] EXAM LEVEL: {level} | SUBJECT: {subject}")
            print(f"❓ QUESTION: {q[:140]}...")
            print(f"🔑 ANSWER KEY / EXPLANATION:\n{sol[:250]}...")
            print("  " + "-"*52)
        print("═"*60 + "\n")

    except Exception as e:
        print(f"❌ Error during database audit: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_db_cleanup()


   
   
 