
import sqlite3
import os

DB_NAME = "coreai_vault.db"

def check_database_inventory():
    if not os.path.exists(DB_NAME):
        print(f"❌ Error: Database file '{DB_NAME}' not found in the current folder!")
        print("Please make sure you are running this script in the same folder as your database.")
        return

    print("🔍 Opening database file and reading tables...")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        # Check if the master table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='academic_vault'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("⚠️ Table 'academic_vault' does not exist in this database yet.")
            conn.close()
            return

        # 1. Fetch Total Count
        cursor.execute("SELECT COUNT(*) FROM academic_vault")
        total_questions = cursor.fetchone()[0]

        print("\n" + "═"*60)
        print("  🏆  COREAI ACADEMIC VAULT SUMMARY")
        print("═"*60)
        print(f"  Total Ingested Questions : {total_questions:,}")
        print("─"*60)

        # 2. Breakdown by Source
        print("\n  📦 QUESTIONS BY SOURCE/DATASET:")
        print("  " + "-"*52)
        cursor.execute("""
            SELECT COALESCE(source, 'Unknown Source'), COUNT(*) as count 
            FROM academic_vault 
            GROUP BY source 
            ORDER BY count DESC
        """)
        for source, count in cursor.fetchall():
            print(f"  ➔ {source[:35]:<35} : {count:,} questions")

        # 3. Breakdown by Exam Level
        print("\n  🎓 QUESTIONS BY EXAM LEVEL:")
        print("  " + "-"*52)
        cursor.execute("""
            SELECT COALESCE(level, 'Unclassified Level'), COUNT(*) as count 
            FROM academic_vault 
            GROUP BY level 
            ORDER BY count DESC
        """)
        for level, count in cursor.fetchall():
            print(f"  ➔ {level[:35]:<35} : {count:,} questions")

        # 4. Breakdown by Subject (Top 15)
        print("\n  📚 TOP SUBJECTS POPULATED:")
        print("  " + "-"*52)
        cursor.execute("""
            SELECT COALESCE(subject, 'General Subject'), COUNT(*) as count 
            FROM academic_vault 
            GROUP BY subject 
            ORDER BY count DESC 
            LIMIT 15
        """)
        for subject, count in cursor.fetchall():
            print(f"  ➔ {subject[:35]:<35} : {count:,} questions")

        print("═"*60 + "\n")

    except Exception as e:
        print(f"❌ Error querying database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_database_inventory()

