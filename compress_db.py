
import os
import zipfile
import sys

DB_NAME = "coreai_vault.db"
ZIP_NAME = "coreai_vault.zip"

def compress_database():
    if not os.path.exists(DB_NAME):
        print(f"❌ Error: Could not find database file '{DB_NAME}' to compress!")
        return

    original_size_mb = os.path.getsize(DB_NAME) / (1024 * 1024)
    print(f"📊 Original Database Size: {original_size_mb:.2f} MB")
    print("⚡ Compacting and compressing your vault... This might take a moment.")

    try:
        # Compress using ZIP_DEFLATED to maximize space reduction
        with zipfile.ZipFile(ZIP_NAME, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(DB_NAME, arcname=DB_NAME)
        
        compressed_size_mb = os.path.getsize(ZIP_NAME) / (1024 * 1024)
        reduction = (1 - (compressed_size_mb / original_size_mb)) * 100

        print("\n" + "═"*60)
        print("  🎉 DATABASE COMPRESSION SUCCESSFUL!")
        print("═"*60)
        print(f"  📦 Compressed File Name  : {ZIP_NAME}")
        print(f"  📉 Compressed File Size  : {compressed_size_mb:.2f} MB")
        print(f"  📉 Space Reduction       : {reduction:.1f}% smaller!")
        print("─"*60)
        print("  💡 This compressed file is now perfectly optimized for GitHub!")
        print("═"*60 + "\n")

    except Exception as e:
        print(f"❌ Error during compression: {e}")

if __name__ == "__main__":
    compress_database()
