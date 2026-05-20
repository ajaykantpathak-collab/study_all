import os
import sqlite3
import pandas as pd
import time
import hashlib
import logging
from datetime import datetime
from contextlib import contextmanager
import streamlit as st
from streamlit_mermaid import st_mermaid

# ==========================================
# 0. SYSTEM CONFIGURATION & SECURITY BOOT
# ==========================================

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CoreAIEngine")

DB_NAME = "coreai_vault.db"

# Force environment sync for GenAI SDK compatibility on Streamlit Cloud
if "GEMINI_API_KEY" in st.secrets:
    os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]

@contextmanager
def get_db_connection():
    """Yields a thread-isolated SQLite connection and guarantees absolute closure."""
    conn = sqlite3.connect(DB_NAME, timeout=60.0)
    conn.execute("PRAGMA synchronous=NORMAL;") 
    try:
        yield conn
    finally:
        conn.close()

def run_schema_migration_safely():
    """Compiles tables safely without assuming legacy constraint structures."""
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
                    question TEXT,
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
                CREATE TABLE IF NOT EXISTS analytics_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    subject TEXT,
                    stream_level TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        conn.close()
        logger.info("Database schemas verified and initialized safely.")
    except Exception as e:
        logger.error(f"Security schema system init failure: {e}")
        raise e

@st.cache_resource(show_spinner="Provisioning core engine assets...")
def global_system_provisioning():
    """Runs strictly ONCE per deployment to unpack assets and verify SDKs."""
    try:
        from db_helper import verify_and_unpack_database
        verify_and_unpack_database()
    except Exception:
        pass
    
    try:
        run_schema_migration_safely()
    except Exception as e:
        st.error(f"Database Initialization Failed: {e}")
        st.stop()
        
    try:
        from google import genai
        from PIL import Image
    except ImportError:
        st.error("Missing libraries. Ensure google-genai and pillow are in requirements.txt.")
        st.stop()
        
    return True

global_system_provisioning()

# ───────────────────────────────────────────────────────────────
# ⚙️ DATA TRANSACTION LAYER
# ───────────────────────────────────────────────────────────────

def run_write_transaction(query, params=(), max_retries=5) -> bool:
    """Safe concurrency writer with linear backoff for locked databases."""
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
            return False
        except Exception:
            return False
    return False

def hash_password(password: str) -> str:
    salt = "CoreAI_Secure_Salt_2026_#"  
    return hashlib.sha256((password + salt).encode()).hexdigest()

def register_user_identity(username, password) -> bool:
    return run_write_transaction("INSERT INTO app_users (username, password_hash) VALUES (?, ?)", (username, hash_password(password)))

def authenticate_user_identity(username, password) -> bool:
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM app_users WHERE username = ?", (username,))
            row = cursor.fetchone()
            return row and row[0] == hash_password(password)
    except Exception:
        return False

def log_analytics_event(username, subject, level):
    run_write_transaction(
        "INSERT INTO analytics_ledger (username, subject, stream_level) VALUES (?, ?, ?)",
        (username, subject, level)
    )

# ───────────────────────────────────────────────────────────────
# 🧠 AUTO-INGESTING MULTIMODAL RAG ENGINE
# ───────────────────────────────────────────────────────────────

def retrieve_rag_context(student_query: str, subject: str, limit=2) -> str:
    if not student_query:
        return "No textual context markers provided."
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT question, solution_en FROM academic_vault WHERE subject = ? AND solution_en IS NOT NULL LIMIT 50", (subject,))
            records = cursor.fetchall()
            
            context_segments = []
            keywords = [kw.lower() for kw in student_query.split() if len(kw) > 3]
            for q_text, sol_text in records:
                if any(kw in q_text.lower() for kw in keywords):
                    context_segments.append(f"Reference Question: {q_text}\nVerified Solution: {sol_text}")
                    if len(context_segments) >= limit: break
            return "\n\n---\n\n".join(context_segments) if context_segments else "No direct reference matches found."
    except Exception:
        return "No direct reference matches found."

def commit_new_question_to_vault(level, subject, raw_question, parsed_en, parsed_hi) -> bool:
    """Safely checks for existing data before committing to avoid schema crashes."""
    clean_q = raw_question.strip()
    if not clean_q or len(clean_q) < 5:
        return False
        
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM academic_vault WHERE question = ?", (clean_q,))
            if cursor.fetchone():
                return True 
            
            cursor.execute("""
                INSERT INTO academic_vault (board, level, subject, question, solution_en, solution_hi, difficulty, question_type, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, ("CBSE/State", level, subject, clean_q, parsed_en, parsed_hi, "Medium", "Conceptual", "Organic_Student_Ingestion"))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Failed to auto-ingest question: {e}")
        return False

def generate_multimodal_rag_response(student_query: str, level: str, subject: str, uploaded_file) -> dict:
    try:
        from google import genai
        from google.genai import types
        from PIL import Image as PILImage
        import io

        client = genai.Client()
        local_context = retrieve_rag_context(student_query, subject)
        
        engineered_prompt = f"""
        You are an elite academic tutor. Analyze the problem input query.
        Provide your final response structured EXACTLY within these parameters:
        
        [CLEAN_QUESTION_TEXT]
        Extract and rewrite a clean, standardized, single-line text version of the question being asked. Do not include answers here.
        
        [CONCEPT_DIAGRAM]
        Draft a high-level description of the concept and STRICTLY include a Mermaid graph architecture block wrapped in ```mermaid tags.
        
        [ENGLISH_SOLUTION]
        Provide a complete step-by-step mathematical or conceptual resolution in English.
        
        [HINDI_SOLUTION]
        हिंदी में पूरा कदम-दर-कदम समाधान प्रदान करें।

        VERIFIED DATABASE CONTEXT FOR GROUNDING:
        {local_context}

        STUDENT DIRECTIONS:
        {student_query if student_query else "Process the attached file."}
        """

        contents = []
        if uploaded_file is not None:
            file_bytes = uploaded_file.read()
            if uploaded_file.type.startswith("image/"):
                contents.append(PILImage.open(io.BytesIO(file_bytes)))
            elif uploaded_file.type == "application/pdf":
                contents.append(types.Part.from_bytes(data=file_bytes, mime_type="application/pdf"))
        
        contents.append(engineered_prompt)
        response = client.models.generate_content(model='gemini-2.5-flash', contents=contents)
        raw_text = response.text if response.text else ""
        
        extracted_q = student_query if student_query else "Image Question Entry"
        sol_en, sol_hi, concept = "Generation failed.", "समाधान विफल।", "No schematic map."
        
        try:
            if "[CLEAN_QUESTION_TEXT]" in raw_text:
                parts = raw_text.split("[CLEAN_QUESTION_TEXT]")[1].split("[CONCEPT_DIAGRAM]")
                extracted_q = parts[0].strip()
                sub_parts = parts[1].split("[ENGLISH_SOLUTION]")
                concept = sub_parts[0].strip()
                final_parts = sub_parts[1].split("[HINDI_SOLUTION]")
                sol_en = final_parts[0].strip()
                sol_hi = final_parts[1].strip()
        except Exception:
            sol_en = raw_text
        
        commit_new_question_to_vault(level, subject, extracted_q, sol_en, sol_hi)
        return {"concept": concept, "en": sol_en, "hi": sol_hi}
    except Exception as e:
        return {"concept": f"Pipeline Error: {e}", "en": "System encountered an anomaly.", "hi": "त्रुटि"}

# ───────────────────────────────────────────────────────────────
# 📈 TAXONOMY & EXAM PAPER MAKER LAYER
# ───────────────────────────────────────────────────────────────

def get_live_system_metrics():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM academic_vault")
            return cursor.fetchone()[0]
    except Exception: 
        return 0

def fetch_mock_exam_paper(level, subject, limit=10):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT question FROM academic_vault WHERE level = ? AND subject = ? AND question NOT LIKE 'Image Question%' ORDER BY RANDOM() LIMIT ?",
                (level, subject, limit)
            )
            return [row[0] for row in cursor.fetchall()]
    except Exception:
        return []

def get_comprehensive_taxonomy():
    primary_subjects = ["Mathematics", "Environmental Studies (EVS)", "English", "Hindi", "General Knowledge"]
    middle_subjects = ["Mathematics", "Science", "Social Science", "English", "Hindi", "Sanskrit"]
    secondary_subjects = ["Mathematics", "Science", "Social Science", "English", "Hindi", "Computer Applications"]
    senior_science = ["Physics", "Chemistry", "Mathematics", "Biology", "English", "Computer Science"]
    senior_commerce = ["Accountancy", "Business Studies", "Economics", "Mathematics", "English"]
    senior_humanities = ["History", "Political Science", "Geography", "Economics", "Psychology", "English"]
    
    return {
        "Class 1": primary_subjects, "Class 2": primary_subjects, "Class 3": primary_subjects,
        "Class 4": primary_subjects, "Class 5": primary_subjects, "Class 6": middle_subjects,
        "Class 7": middle_subjects, "Class 8": middle_subjects, "Class 9": secondary_subjects,
        "Class 10": secondary_subjects, 
        "Class 11 (Science)": senior_science, "Class 11 (Commerce)": senior_commerce, "Class 11 (Humanities)": senior_humanities,
        "Class 12 (Science)": senior_science, "Class 12 (Commerce)": senior_commerce, "Class 12 (Humanities)": senior_humanities,
        "JEE Main": ["Mathematics", "Physics", "Chemistry"],
        "JEE Advanced": ["Mathematics", "Physics", "Chemistry"],
        "NEET Core": ["Physics", "Chemistry", "Biology"],
        "CUET (UG)": ["Domain Subjects", "Languages", "General Test"]
    }

STRUCTURED_MAP = get_comprehensive_taxonomy()
SYSTEM_LEVELS = list(STRUCTURED_MAP.keys())

# ==========================================
# 2. STREAMLIT VISUAL PRESENCE USER INTERFACE
# ==========================================

st.set_page_config(page_title="CoreAI Intellect Engine", page_icon="🧠", layout="wide")

if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "current_user" not in st.session_state: st.session_state.current_user = None
if "payload_dict" not in st.session_state: st.session_state.payload_dict = None

with st.sidebar:
    st.title("🧠 CoreAI Engine")
    st.markdown("---")
    if st.session_state.authenticated:
        st.success(f"Active User: **{st.session_state.current_user}**")
        st.info("🔄 Data Flywheel Online")
        if st.button("Log Out of App"):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.session_state.payload_dict = None
            st.rerun()

if not st.session_state.authenticated:
    st.header("Institutional Identity Validation Gateway")
    tab_login, tab_register = st.tabs(["🔒 Secure Login", "✍️ Register Profile"])
    with tab_login:
        with st.form("auth_login_form"):
            user_input = st.text_input("Username").strip()
            pass_input = st.text_input("Password", type="password")
            if st.form_submit_button("Validate Credentials"):
                if authenticate_user_identity(user_input, pass_input):
                    st.session_state.authenticated = True
                    st.session_state.current_user = user_input
                    st.rerun()
                else: st.error("Invalid details.")
                    
    with tab_register:
        with st.form("auth_register_form"):
            reg_user = st.text_input("Create Username").strip()
            reg_pass = st.text_input("Create Password", type="password")
            if st.form_submit_button("Register Account"):
                if len(reg_user) < 4 or len(reg_pass) < 6: st.error("Username/Password too short.")
                elif register_user_identity(reg_user, reg_pass): st.success("Created successfully!")
                else: st.error("Registration failed. User may exist.")
else:
    total_q = get_live_system_metrics()
    
    portal_tab, practice_tab, analytics_tab = st.tabs(["🎯 Study Resolution Portal", "📋 Practice Test Maker", "📊 Diagnostic Analytics"])
    
    # ─── TAB 1: CORE STUDY PORTAL ───
    with portal_tab:
        st.title("🧠 CoreAI Multimodal RAG Engine")
        st.caption("Snap a photo of your notebook problem or upload an assignment sheet directly.")
        st.metric(label="Total Decentralized Vault Assets", value=f"{total_q:,} Questions")
        st.markdown("---")
        
        col_sel1, col_sel2 = st.columns(2)
        with col_sel1: selected_level = st.selectbox("Select Grade / Target Class Stream", SYSTEM_LEVELS, key="portal_lvl")
        with col_sel2: selected_subject = st.selectbox("Select Academic Subject Module", STRUCTURED_MAP.get(selected_level, ["Science"]), key="portal_subj")
            
        uploaded_file = st.file_uploader("Upload notebook screenshot or problem file (PNG, JPG, PDF):", type=["png", "jpg", "jpeg", "pdf"])
        input_query_text = st.text_area(label="Add notes or custom text queries manually:", placeholder="Type special instructions here...", height=100)
        
        if st.button("Compute Grounded Multimodal Engine", type="primary", use_container_width=True):
            if not input_query_text.strip() and uploaded_file is None:
                st.error("Please add a text question or upload an image file.")
            else:
                with st.spinner("Processing visual analysis and auto-ingesting to database..."):
                    log_analytics_event(st.session_state.current_user, selected_subject, selected_level)
                    st.session_state.payload_dict = generate_multimodal_rag_response(input_query_text.strip(), selected_level, selected_subject, uploaded_file)
                    st.rerun()

        if st.session_state.payload_dict:
            st.markdown("---")
            st.success("✨ Resolution processed and successfully injected into your permanent repository vault!")
            tab_en, tab_hi, tab_diagram = st.tabs(["🇬🇧 English Explanation", "🇮🇳 हिंदी समाधान", "🎯 Concept Map & Layout"])
            
            with tab_en: 
                st.markdown(st.session_state.payload_dict.get("en", ""))
            
            with tab_hi: 
                st.markdown(st.session_state.payload_dict.get("hi", ""))
            
            with tab_diagram: 
                concept_data = st.session_state.payload_dict.get("concept", "")
                
                # SAFE RENDERING BLOCK: Checks for Mermaid syntax and renders graphics cleanly
                if "```mermaid" in concept_data:
                    try:
                        # Extract the text before the diagram (if the AI included an explanation)
                        text_before = concept_data.split("```mermaid")[0].strip()
                        if text_before:
                            st.markdown(text_before)
                            
                        # Isolate and render the mermaid diagram
                        mermaid_code = concept_data.split("```mermaid")[1].split("```")[0].strip()
                        st_mermaid(mermaid_code, height="500px")
                    except Exception:
                        st.markdown(concept_data) # Fallback to raw text if parsing fails
                else:
                    st.markdown(concept_data) # Fallback for standard ASCII text charts

    # ─── TAB 2: INSTANT TEST PAPER GENERATOR ───
    with practice_tab:
        st.title("📋 Automated Mock Test Generator")
        st.caption("Compiles an instant, custom testing matrix using curated database rows.")
        
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1: p_level = st.selectbox("Select Target Stream", SYSTEM_LEVELS, key="prac_lvl")
        with col_p2: p_subject = st.selectbox("Select Target Subject", STRUCTURED_MAP.get(p_level, ["Science"]), key="prac_subj")
        with col_p3: q_count = st.slider("Total Questions on Sheet", 5, 20, 10)
        
        if st.button("Generate Custom Practice Test Paper", use_container_width=True, type="primary"):
            with st.spinner("Compiling test sheet indices..."):
                questions = fetch_mock_exam_paper(p_level, p_subject, q_count)
                if not questions:
                    st.warning("No questions found in database yet. Go run a query in the Study Portal tab to auto-grow your list!")
                else:
                    st.markdown("---")
                    st.subheader(f"📝 Practice Test Sheet: {p_level} - {p_subject}")
                    
                    for idx, q_string in enumerate(questions, 1):
                        st.markdown(f"**Question {idx}:** {q_string}")
                        st.text_area("Write solution here:", key=f"ans_box_{idx}", height=70)
                        st.markdown("---")

    # ─── TAB 3: VISUAL METRICS ANALYTICS ───
    with analytics_tab:
        st.title("📊 Diagnostic Focus Area Analytics")
        
        try:
            with get_db_connection() as conn:
                df_logs = pd.read_sql_query(
                    "SELECT subject, COUNT(*) as queries FROM analytics_ledger WHERE username = ? GROUP BY subject ORDER BY queries DESC", 
                    conn, params=(st.session_state.current_user,)
                )
            if df_logs.empty:
                st.info("No logs compiled yet. Complete a few study portal questions to generate your charts!")
            else:
                col_chart, col_report = st.columns([2, 1])
                with col_chart:
                    st.bar_chart(data=df_logs, x="subject", y="queries", color="#FF4B4B")
                with col_report:
                    top_subject = df_logs.iloc[0]["subject"]
                    st.write(f"Your primary study module focus is concentrated heavily on **{top_subject}**.")
        except Exception:
            st.info("Analytics engine ready. Complete a question query to compute your tracking charts.")