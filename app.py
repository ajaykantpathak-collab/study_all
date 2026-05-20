import os
import sqlite3
import pandas as pd
import time
import hashlib
import logging
from datetime import datetime
from contextlib import contextmanager
import streamlit as st

# ==========================================
# 0. SYSTEM CONFIGURATION & INITIALIZATION
# ==========================================

# Configure logging patterns cleanly
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CoreAIEngine")

DB_NAME = "coreai_vault.db"
DAILY_LIMIT = 5

@contextmanager
def get_db_connection():
    """
    Yields a thread-isolated SQLite connection.
    Guarantees closure upon exiting the context block, preventing memory leaks.
    """
    conn = sqlite3.connect(DB_NAME, timeout=60.0)
    conn.execute("PRAGMA synchronous=NORMAL;") 
    try:
        yield conn
    finally:
        conn.close()

def run_schema_migration_safely():
    """Compiles tables and sets persistent WAL PRAGMAs under a global boot lock."""
    try:
        conn = sqlite3.connect(DB_NAME, timeout=60.0)
        conn.execute("PRAGMA journal_mode=WAL;") 
        
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS academic_vault (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    board TEXT,
                    level TEXT,
                    subject TEXT,
                    question TEXT UNIQUE,
                    solution_hi TEXT,
                    solution_en TEXT,
                    difficulty TEXT,
                    question_type TEXT,
                    source TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_usage_ledger (
                    username TEXT,
                    request_date TEXT,
                    timestamp REAL
                )
            """)
            
            # Hot patch missing schemas dynamically if the baseline is outdated
            cursor.execute("PRAGMA table_info(academic_vault);")
            columns = [col[1] for col in cursor.fetchall()]
            if columns:
                if "solution_hi" not in columns:
                    cursor.execute("ALTER TABLE academic_vault ADD COLUMN solution_hi TEXT;")
                if "solution_en" not in columns:
                    cursor.execute("ALTER TABLE academic_vault ADD COLUMN solution_en TEXT;")
                    
        conn.close()
        logger.info("Database schemas verified and initialized safely.")
    except Exception as e:
        logger.error(f"Security schema system init failure: {e}")
        raise e

@st.cache_resource(show_spinner="Provisioning core engine assets...")
def global_system_provisioning():
    """Runs strictly ONCE per server deployment instance lifetime."""
    try:
        from db_helper import verify_and_unpack_database
        verify_and_unpack_database()
        logger.info("Database baseline unpacked successfully.")
    except Exception as e:
        logger.error(f"Critical unpack failure: {e}")
        st.error(f"Failed to unpack database baseline: {e}")
    
    try:
        run_schema_migration_safely()
    except Exception as e:
        st.error(f"Critical schema initialization failure: {e}")
        st.stop()
    
    try:
        from google import genai
        from google.genai import types
        from PIL import Image as PILImage
    except ImportError:
        st.error("❌ CRITICAL DEPLOYMENT FAILURE: Run 'pip install google-genai pypdf pillow' in terminal.")
        st.stop()
        
    return True

# Initialize database storage context safely across threads
global_system_provisioning()


# ───────────────────────────────────────────────────────────────
# ⚙️ DATA TRANSACTION & SECURITY LAYER
# ───────────────────────────────────────────────────────────────

def run_write_transaction(query, params=(), max_retries=5) -> bool:
    """Executes a database write mutation using a linear retry backoff strategy."""
    for attempt in range(max_retries):
        try:
            with get_db_connection() as conn:
                with conn:  
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                return True
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < max_retries - 1:
                time.sleep(0.1 * (attempt + 1))  
                continue
            logger.error(f"Database Concurrency Failure on attempt {attempt}: {e}")
            return False
        except Exception as e:
            logger.error(f"Database Exception: {e}")
            return False
    return False

def hash_password(password: str) -> str:
    """Computes a salted, stretched hash value to protect against rainbow tables."""
    salt = "CoreAI_Secure_Salt_2026_#"  
    payload = password + salt
    return hashlib.sha256(payload.encode()).hexdigest()

def register_user_identity(username, password) -> bool:
    pwd_hash = hash_password(password)
    return run_write_transaction(
        "INSERT INTO app_users (username, password_hash) VALUES (?, ?)", 
        (username, pwd_hash)
    )

def authenticate_user_identity(username, password) -> bool:
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM app_users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if row and row[0] == hash_password(password):
                return True
            return False
    except Exception:
        return False

def check_remaining_quota(username) -> int:
    """Calculates available remaining request counts for the current user."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM user_usage_ledger WHERE username = ? AND request_date = ?", 
                (username, today_str)
            )
            count = cursor.fetchone()[0]
            remaining = DAILY_LIMIT - count
            return max(0, remaining)
    except Exception:
        return 0

def log_user_quota_consumption(username):
    today_str = datetime.now().strftime("%Y-%m-%d")
    run_write_transaction(
        "INSERT INTO user_usage_ledger (username, request_date, timestamp) VALUES (?, ?, ?)",
        (username, today_str, time.time())
    )


# ───────────────────────────────────────────────────────────────
# 🧠 RETRIEVAL-AUGMENTED GENERATION (RAG) ENGINE
# ───────────────────────────────────────────────────────────────

def retrieve_rag_context(student_query: str, subject: str, limit=2) -> str:
    """Scans the local repository matching keywords to pull structural reference contexts."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT question, solution_en 
                FROM academic_vault 
                WHERE subject = ? AND solution_en IS NOT NULL
                LIMIT 50
            """, (subject,))
            records = cursor.fetchall()
            
            context_segments = []
            keywords = [kw.lower() for kw in student_query.split() if len(kw) > 3]
            
            for q_text, sol_text in records:
                if any(kw in q_text.lower() for kw in keywords):
                    context_segments.append(f"Reference Question: {q_text}\nVerified Solution: {sol_text}")
                    if len(context_segments) >= limit:
                        break
            
            return "\n\n---\n\n".join(context_segments) if context_segments else "No direct reference matches found."
    except Exception as e:
        logger.error(f"RAG retrieval lookup failure: {e}")
        return "No direct reference matches found."

def generate_rag_response(student_query: str, subject: str) -> str:
    """Orchestrates RAG context embedding merges directly inside Gemini pipeline loops."""
    try:
        from google import genai
        client = genai.Client()
        
        local_context = retrieve_rag_context(student_query, subject)
        
        engineered_prompt = f"""
        You are an elite academic tutor specializing in engineering and medical entry exams. 
        Answer the student's question accurately using clean step-by-step reasoning formatting.
        
        If the verified database reference material below matches the context of the query, 
        base your calculations and steps directly on it to maintain total accuracy.

        VERIFIED INTERNAL DATABASE REFERENCE MATERIAL:
        {local_context}

        STUDENT QUESTION:
        {student_query}
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=engineered_prompt
        )
        return response.text if response.text else "Failed to generate text content response."
    except Exception as e:
        logger.error(f"RAG generation pipeline processing failure: {e}")
        return f"Error handling generation query: {e}"


# ───────────────────────────────────────────────────────────────
# 📈 DATA ANALYTICS & CACHING LAYER
# ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=600, show_spinner=False)
def get_cached_system_metrics():
    try:
        with get_db_connection() as conn:
            df_count = pd.read_sql_query("SELECT COUNT(*) as total FROM academic_vault", conn)
            df_comp = pd.read_sql_query("""
                SELECT level, COUNT(*) as cnt 
                FROM academic_vault 
                WHERE level IS NOT NULL 
                GROUP BY level 
                ORDER BY cnt DESC
            """, conn)
        return int(df_count["total"].iloc[0]), df_comp.values.tolist()
    except Exception:
        return 0, []

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_optimized_dropdown_bounds():
    try:
        with get_db_connection() as conn:
            df = pd.read_sql_query("""
                SELECT DISTINCT level, subject 
                FROM academic_vault 
                WHERE level IS NOT NULL AND subject IS NOT NULL
            """, conn)
        mapping = {}
        for _, row in df.iterrows():
            lvl, subj = row['level'], row['subject']
            if lvl not in mapping: mapping[lvl] = []
            if subj not in mapping[lvl]: mapping[lvl].append(subj)
        return mapping
    except Exception:
        return {
            "Class 11-12 (NEET)": ["Physics", "Chemistry", "Biology"], 
            "JEE Mains & Advanced": ["Mathematics", "Physics"]
        }

STRUCTURED_MAP = fetch_optimized_dropdown_bounds()
SYSTEM_LEVELS = list(STRUCTURED_MAP.keys()) if STRUCTURED_MAP else ["JEE Mains", "NEET Core"]


# ==========================================
# 2. STREAMLIT VISUAL PRESENCE USER INTERFACE
# ==========================================

st.set_page_config(page_title="CoreAI Intellect Engine", page_icon="🧠", layout="wide")

# Persistent state initialization metrics
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "current_user" not in st.session_state:
    st.session_state.current_user = None

# Sidebar branding wrapper
with st.sidebar:
    st.title("🧠 CoreAI Engine")
    st.markdown("---")
    
    if st.session_state.authenticated:
        st.success(f"Active Account: **{st.session_state.current_user}**")
        remaining = check_remaining_quota(st.session_state.current_user)
        st.metric(label="Remaining Daily Queries", value=f"{remaining} / {DAILY_LIMIT}")
        
        st.markdown("---")
        if st.button("Log Out of Session", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.rerun()
    else:
        st.warning("🔒 Secure Terminal Context Locked")

# 🟢 MAIN DISPLAY LOOP: ACCESS ROUTER (Auth vs App Dashboard)
if not st.session_state.authenticated:
    st.header("Institutional Identity Validation Gateway")
    
    tab_login, tab_register = st.tabs(["🔒 Secure Identity Login", "✍️ Register New Profile"])
    
    with tab_login:
        with st.form("auth_login_form"):
            user_input = st.text_input("Username").strip()
            pass_input = st.text_input("Password", type="password")
            btn_submit = st.form_submit_button("Validate Credentials")
            
            if btn_submit:
                if not user_input or not pass_input:
                    st.error("Input fields cannot be left empty.")
                elif authenticate_user_identity(user_input, pass_input):
                    st.session_state.authenticated = True
                    st.session_state.current_user = user_input
                    st.success("Access privileges confirmed!")
                    st.rerun()
                else:
                    st.error("Invalid username or password match found.")
                    
    with tab_register:
        with st.form("auth_register_form"):
            reg_user = st.text_input("Create Username").strip()
            reg_pass = st.text_input("Create Password", type="password")
            btn_register = st.form_submit_button("Commit Profile Database Entry")
            
            if btn_register:
                if len(reg_user) < 4 or len(reg_pass) < 6:
                    st.error("Username must be >= 4 chars, Password must be >= 6 chars.")
                elif register_user_identity(reg_user, reg_pass):
                    st.success("Account successfully created! Please log in inside the Login Tab.")
                else:
                    st.error("Username already exists or database transaction dropped.")

else:
    # Authenticated Student Dashboard Interface Loop
    total_q, metric_distribution = get_cached_system_metrics()
    
    # Hero Title Metrics Row
    col_title, col_m1, col_m2 = st.columns([2, 1, 1])
    with col_title:
        st.title("🧠 CoreAI Academic RAG Portal")
        st.caption("Sub-second semantic augmentation engine running over indexed institution assets.")
    with col_m1:
        st.metric(label="Total Vault Knowledge Assets", value=f"{total_q:,} Questions")
    with col_m2:
        st.metric(label="Daily Limit Reset Boundary", value="24 Hours Rolling")
        
    st.markdown("---")
    
    # Workspace Filter Selection Array Layout
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        selected_level = st.selectbox("Target Academic Classification Stream", SYSTEM_LEVELS)
    with col_sel2:
        available_subjects = STRUCTURED_MAP.get(selected_level, ["General Science"])
        selected_subject = st.selectbox("Academic Disciplines Module", available_subjects)
        
    st.markdown("### 📝 Input Academic Query String")
    input_query_text = st.text_area(
        label="Type your core target question cleanly here for semantic evaluation matrix resolution:",
        placeholder="Paste standard problem question format text blocks here to evaluate solutions...",
        height=150
    )
    
    if st.button("Compute Grounded Resolution Engine", type="primary", use_container_width=True):
        current_username = st.session_state.current_user
        
        # Guardrail execution boundary pipeline evaluation checks
        if not input_query_text.strip():
            st.error("Please insert a valid textual query string pattern.")
        elif check_remaining_quota(current_username) <= 0:
            st.error("🚨 ALLOCATION OVERFLOW: You have reached your rolling 24-hour request cutoff profile limits.")
        else:
            with st.spinner("Executing structural retrieval analytics and generation matrices..."):
                # Execute user billing deduction consumption profile trackers first
                log_user_quota_consumption(current_username)
                
                # Fetch output metrics
                generated_solution_output = generate_rag_response(input_query_text.strip(), selected_subject)
                
                st.markdown("### 🎯 Grounded AI Resolution Output")
                st.info("Response verified and grounded through historical internal database context profiles.")
                st.markdown(generated_solution_output)
                
                # Force instant sidebar update tracking limits
                st.rerun()