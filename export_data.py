import sqlite3
import pandas as pd

def extract_to_csv():
    print("Connecting to local database...")
    conn = sqlite3.connect('coreai_vault.db')

    tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table';", conn)
    
    if tables.empty:
        print("No tables found in coreai_vault.db!")
        return

    for table_name in tables['name']:
        df = pd.read_sql_query(f"SELECT * from {table_name}", conn)
        csv_filename = f"{table_name}_cloud_upload.csv"
        df.to_csv(csv_filename, index=False)
        print(f"✅ Successfully exported {len(df)} rows to {csv_filename}")

    conn.close()

if __name__ == "__main__":
    extract_to_csv()