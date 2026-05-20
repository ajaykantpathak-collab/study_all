
import os
import zipfile

DB_NAME = "coreai_vault.db"
ZIP_NAME = "coreai_vault.zip"

def verify_and_unpack_database():
    """
    Checks if the raw database is present. If missing (e.g. during a fresh deployment
    on Streamlit Cloud), it automatically unpacks the compressed archive.
    """
    if os.path.exists(DB_NAME):
        # Database already exists locally, do nothing
        return True

    if os.path.exists(ZIP_NAME):
        print("📦 Raw database not found. Unpacking compressed repository archive...")
        try:
            with zipfile.ZipFile(ZIP_NAME, 'r') as zip_ref:
                zip_ref.extractall(".")
            print("✅ Database successfully unpacked and ready!")
            return True
        except Exception as e:
            print(f"❌ Error unpacking database archive: {e}")
            return False
            
    print("❌ Fatal Error: Neither 'coreai_vault.db' nor 'coreai_vault.zip' was found!")
    return False
