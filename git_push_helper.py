
import os
import subprocess
import sys

ZIP_NAME = "coreai_vault.zip"
DB_NAME = "coreai_vault.db"

def run_command(command, error_msg):
    """Executes a terminal command and returns its output, or None on failure."""
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {error_msg}")
        print(f"Details: {e.stderr.strip() if e.stderr else e}")
        return None

def main():
    print("🚀 --- CoreAI Git & GitHub Push Assistant --- 🚀\n")

    # 1. Check for the compressed database file
    if not os.path.exists(ZIP_NAME):
        print(f"📦 '{ZIP_NAME}' not found! Compressing your active database first...")
        if os.path.exists("compress_db.py"):
            try:
                import compress_db
                compress_db.compress_database()
            except Exception as e:
                print(f"❌ Could not run compression utility automatically: {e}")
                return
        else:
            print("❌ Error: compress_db.py was not found in this folder. Please create it first.")
            return
    else:
        print(f"✅ Verified: Compressed '{ZIP_NAME}' is ready for upload.")

    # 2. Check if Git is installed on your Windows machine
    git_version = run_command("git --version", "Git is not installed on this computer. Please install Git to continue!")
    if not git_version:
        return
    print(f"✅ Git detected: {git_version}")

    # 3. Initialize local Git repository if needed
    if not os.path.exists(".git"):
        print("📁 Initializing fresh local Git repository...")
        run_command("git init", "Failed to initialize local git repository.")
    else:
        print("📁 Verified: Existing Git repository detected.")

    # 4. Stage your workspace files
    print("➕ Staging files (respecting your .gitignore config to bypass raw .db files)...")
    run_command("git add .", "Failed to stage project files.")

    # 5. Commit staged changes
    status = run_command("git status --porcelain", "Failed to check status.")
    if not status:
        print("🎉 All files up to date! Ready for remote connection.")
    else:
        run_command('git commit -m "feat: coreai portal with compressed db and auto-unpacker"', "Failed to commit files.")
        print("✅ Commit successfully created!")

    # 6. Prompt for GitHub repository link
    print("\n" + "═"*60)
    print("🔗 LINK YOUR GITHUB REPOSITORY")
    print("═"*60)
    print("1. Go to https://github.com and sign in.")
    print("2. Click 'New' to create a fresh repository.")
    print("3. Name your repository (e.g., 'coreai-question-vault').")
    print("4. DO NOT check 'Add a README', '.gitignore', or 'License'. Leave them blank.")
    print("5. Click the green 'Create repository' button.")
    print("6. Copy the repository URL (it ends with .git, e.g., https://github.com/username/repo.git)\n")
    
    repo_url = input("👉 Paste your GitHub Repository URL here and press Enter: ").strip()
    if not repo_url:
        print("❌ Error: Repository URL cannot be empty.")
        return

    # Set default branch and origin link
    run_command("git branch -M main", "Failed to set default branch to main.")
    run_command("git remote remove origin", "Resetting existing remote link...")
    run_command(f"git remote add origin {repo_url}", "Failed to link your remote repository.")
    
    # 7. Push up to GitHub!
    print("\n📤 Uploading your project and compressed database to GitHub...")
    push_result = run_command("git push -u origin main", "Upload failed. Verify your GitHub permissions and connection.")
    
    if push_result is not None:
        print("\n" + "═"*60)
        print("🎉 SUCCESS! YOUR COREAI PROJECT IS LIVE ON GITHUB!")
        print("═"*60)
        print(f"🔗 Repository URL: {repo_url.replace('.git', '')}")
        print("═"*60 + "\n")

if __name__ == "__main__":
    main()

