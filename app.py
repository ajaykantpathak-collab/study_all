# ==========================================
# 1. AUTOMATIC CLOUD DATABASE UNPACKER
# ==========================================
import os
from db_helper import verify_and_unpack_database
verify_and_unpack_database()
# ==========================================

import streamlit as st
import sqlite3
import pandas as pd
import time
import hashlib
import logging
from datetime import datetime
from io import BytesIO

# Try-except safety harness for critical enterprise visual libraries
try:
    from google import genai
    from google.genai import types
    from PIL import Image as PILImage
except ImportError:
    st.error("❌ CRITICAL DEPLOYMENT FAILURE: Run 'pip install google-genai pypdf pillow' inside your terminal environment.")
    st.stop()

# Enterprise Logging Configurations
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CoreAIEngine")

DB_NAME = "coreai_vault.db"
DAILY_LIMIT = 5

# ───────────────────────────────────────────────────────────────
# 🛡️ SECURITY & ACCOUNT COMPLIANCE MANAGEMENT
# ───────────────────────────────────────────────────────────────
def init_security_infrastructure():
    """Compiles local authentication and quota tracking structures safely into storage context."""
    try:
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        cursor = conn.cursor()
        # User credentials registration store
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_users (
                username TEXT PRIMARY KEY,
                password_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Quota allocation ledger
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_usage_ledger (
                username TEXT,
                request_date TEXT,
                timestamp REAL
            )
        """)
        # Localization schema patch
        cursor.execute("PRAGMA table_info(academic_vault);")
        columns = [col[1] for col in cursor.fetchall()]
        if columns and "solution_hi" not in columns:
            cursor.execute("ALTER TABLE academic_vault ADD COLUMN solution_hi TEXT;")
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Security schema system init failure: {e}")

init_security_infrastructure()

# Session State Initializations
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "current_test" not in st.session_state:
    st.session_state.current_test = None

def run_write_transaction(query, params=()):
    attempts = 3
    for attempt in range(attempts):
        try:
            conn = sqlite3.connect(DB_NAME, timeout=30.0)
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            conn.close()
            return True
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < attempts - 1:
                time.sleep(0.5 * (attempt + 1))
                continue
            logger.error(f"Database Concurrency Lockout: {e}")
            return False
        except Exception as e:
            logger.error(f"Database Transaction Error: {e}")
            return False

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def register_user_identity(username, password) -> bool:
    pwd_hash = hash_password(password)
    return run_write_transaction(
        "INSERT INTO app_users (username, password_hash) VALUES (?, ?)", 
        (username, pwd_hash)
    )

def authenticate_user_identity(username, password) -> bool:
    try:
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM app_users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        if row and row[0] == hash_password(password):
            return True
        return False
    except Exception:
        return False

def check_user_quota_allowance(username) -> int:
    """Computes exact consumption matrix allocations under current date bound parameters."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM user_usage_ledger WHERE username = ? AND request_date = ?", 
            (username, today_str)
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return DAILY_LIMIT

def log_user_quota_consumption(username):
    today_str = datetime.now().strftime("%Y-%m-%d")
    run_write_transaction(
        "INSERT INTO user_usage_ledger (username, request_date, timestamp) VALUES (?, ?, ?)",
        (username, today_str, time.time())
    )

@st.cache_data(ttl=600, show_spinner=False)
def get_cached_system_metrics():
    try:
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        df_count = pd.read_sql_query("SELECT COUNT(*) as total FROM academic_vault", conn)
        df_comp = pd.read_sql_query("SELECT level, COUNT(*) as cnt FROM academic_vault WHERE level IS NOT NULL GROUP BY level ORDER BY cnt DESC", conn)
        conn.close()
        return int(df_count["total"].iloc[0]), df_comp.values.tolist()
    except Exception:
        return 0, []

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_optimized_dropdown_bounds():
    try:
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        df = pd.read_sql_query("SELECT DISTINCT level, subject FROM academic_vault WHERE level IS NOT NULL AND subject IS NOT NULL", conn)
        conn.close()
        mapping = {}
        for _, row in df.iterrows():
            lvl, subj = row['level'], row['subject']
            if lvl not in mapping: mapping[lvl] = []
            if subj not in mapping[lvl]: mapping[lvl].append(subj)
        return mapping
    except Exception:
        return {"Class 11-12 (NEET)": ["Physics", "Chemistry", "Biology"], "JEE Mains & Advanced": ["Mathematics", "Physics"]}

STRUCTURED_MAP = fetch_optimized_dropdown_bounds()
SYSTEM_LEVELS = list(STRUCTURED_MAP.keys()) if STRUCTURED_MAP else ["JEE Mains", "NEET Core"]

# ───────────────────────────────────────────────────────────────
# 🧠 BILINGUAL CORE ENGINE + GRAPHVIZ VECTOR COMPILER
# ───────────────────────────────────────────────────────────────
def execute_safe_ai_resolution(prompt, mime_type, file_bytes, target_lang, api_key):
    try:
        client = genai.Client(api_key=api_key)
        if target_lang == "Hindi (हिन्दी)":
            sys_instruction = (
                "You are the CoreAI Academic Resolution Engine specialized in Indian competitive exams (NEET, JEE, UPSC, CA) for Hindi medium candidates.\n\n"
                "CRITICAL ARCHITECTURAL PROTOCOLS:\n"
                "1. Provide the complete resolution exclusively in the Hindi language using Devanagari script.\n"
                "2. Retain standard technical terms in brackets alongside Hindi terminology when helpful (e.g., प्रकाश संश्लेषण [Photosynthesis]).\n"
                "3. QUESTION-SPECIFIC VECTOR DIAGRAM FACTORY: You MUST construct a clean, highly relevant diagram using Graphviz DOT language syntax that maps the problem's exact variables. Do not use generic templates.\n"
                "4. CRITICAL DIAGRAM SEPARATION: Your raw DOT code must be completely separate from explanation texts. You MUST wrap the code block using the identifier tag: ```graphviz ... ```\n"
                "5. Present calculation steps clearly across individual lines with explicit operators (+, -, *, /)."
            )
        else:
            sys_instruction = (
                "You are the CoreAI Academic Resolution Engine for premium competitive national-level exams.\n\n"
                "CRITICAL ARCHITECTURAL PROTOCOLS:\n"
                "1. Provide a highly detailed, comprehensive step-by-step academic explanation. Never omit logical calculation layers.\n"
                "2. QUESTION-SPECIFIC VECTOR DIAGRAM FACTORY: You MUST construct a clean, highly relevant diagram using Graphviz DOT language syntax that maps the problem's exact variables. Do not use generic templates.\n"
                "3. CRITICAL DIAGRAM SEPARATION: Your raw DOT code must be completely separate from explanation texts. You MUST wrap the code block using the identifier tag: ```graphviz ... ```\n"
                "4. Format scientific calculations layout beautifully using clean, highly readable multiline transformations."
            )

        contents = []
        if file_bytes and mime_type:
            if mime_type.startswith("image/"):
                try:
                    img = PILImage.open(BytesIO(file_bytes))
                    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                    img.thumbnail((1800, 1800), PILImage.Resampling.LANCZOS)
                    buffer = BytesIO()
                    img.save(buffer, format="JPEG", quality=85)
                    optimized_bytes = buffer.getvalue()
                    contents.append(types.Part.from_bytes(data=optimized_bytes, mime_type="image/jpeg"))
                except Exception:
                    contents.append(types.Part.from_bytes(data=file_bytes, mime_type=mime_type))
            else:
                contents.append(types.Part.from_bytes(data=file_bytes, mime_type=mime_type))
        
        contents.append(prompt)
        response = client.models.generate_content(
            model='gemini-2.5-flash', contents=contents,
            config=types.GenerateContentConfig(system_instruction=sys_instruction, temperature=0.15, max_output_tokens=2048)
        )
        return response.text
    except Exception as e:
        logger.error(f"🚨 API Layer Exception Encountered: {e}")
        return None

def render_smart_response_blocks(raw_text):
    if "```graphviz" in raw_text:
        parts = raw_text.split("```graphviz")
        st.markdown(parts[0])
        for part in parts[1:]:
            if "```" in part:
                dot_code, remaining_text = part.split("```", 1)
                st.markdown("#### 📐 Structural Problem Architecture Matrix")
                try:
                    st.graphviz_chart(dot_code.strip())
                except Exception:
                    st.code(dot_code.strip(), language="text")
                if remaining_text.strip(): st.markdown(remaining_text)
            else:
                st.markdown(part)
    else:
        st.markdown(raw_text)

# ───────────────────────────────────────────────────────────────
# 🔐 AUTHENTICATION GATEWAY
# ───────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    st.title("🛡️ CoreAI Identity Gateway")
    st.caption("DPIIT Regulatory Protocol: Security access validation barrier.")
    
    auth_tab1, auth_tab2 = st.tabs(["🔒 Secure Login", "📝 Create Account"])
    
    with auth_tab1:
        login_user = st.text_input("Username:", key="login_usr_input").strip()
        login_pwd = st.text_input("Password:", type="password", key="login_pwd_input")
        if st.button("Authenticate Identity", type="primary", use_container_width=True):
            if authenticate_user_identity(login_user, login_pwd):
                st.session_state.logged_in = True
                st.session_state.username = login_user
                st.success("Access authorized. Redirecting workspace...")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Invalid credentials.")
                
    with auth_tab2:
        reg_user = st.text_input("Choose Username:", key="reg_usr_input").strip()
        reg_pwd = st.text_input("Choose Password:", type="password", key="reg_pwd_input")
        reg_pwd_conf = st.text_input("Confirm Password:", type="password", key="reg_pwd_conf_input")
        if st.button("Register Credentials", use_container_width=True):
            if not reg_user or not reg_pwd:
                st.warning("Fields cannot be left empty.")
            elif reg_pwd != reg_pwd_conf:
                st.error("Password configuration mismatch.")
            else:
                if register_user_identity(reg_user, reg_pwd):
                    st.success("Account created successfully. Shift to login panel.")
                else:
                    st.error("Username already claimed or system tracking locked.")
    st.stop()

# ───────────────────────────────────────────────────────────────
# 📊 SIDEBAR SETTINGS PORTAL (AUTHORIZED STATE)
# ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("👤 Identity Profile")
    st.markdown(f"**User Session:** `{st.session_state.username}`")
    
    consumed_tokens = check_user_quota_allowance(st.session_state.username)
    remaining_tokens = max(0, DAILY_LIMIT - consumed_tokens)
    
    st.metric(label="Daily Generation Allowance Balance", value=f"{remaining_tokens} / {DAILY_LIMIT} Left")
    if remaining_tokens == 0:
        st.error("⛔ Daily computation limit hit.")
        
    if st.button("Log Out Session", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()
        
    st.markdown("---")
    api_key = st.secrets.get("GEMINI_API_KEY") or st.secrets.get("api_key")
    if api_key: st.success("🟢 API Key Resolved")
    else: st.error("🔴 API Key Missing inside secrets configuration")
    
    target_language = st.radio("Processing Language Target:", ["English", "Hindi (हिन्दी)"])
    st.markdown("---")
    
    total_records, structural_composition = get_cached_system_metrics()
    st.markdown(f"**Cache Volume Capacity:** `{total_records:,} items`")

# ───────────────────────────────────────────────────────────────
# 💻 MAIN CORE APPLICATION INTERFACE
# ───────────────────────────────────────────────────────────────
st.title("🛡️ Academic Multimodal Resolution Layer")
st.caption("DPIIT Compliant Secure Environment. Verified Multi-user Core Framework.")

tabs = st.tabs(["🔎 Smart Multimodal Solver", "📝 Practice Portal"])

# ==========================================
# TAB 1: SMART MULTIMODAL SOLVER
# ==========================================
with tabs[0]:
    st.subheader("Input Exam Specifications")
    col1, col2, col3 = st.columns(3)
    with col1: selected_board = st.selectbox("Exam Board / Segment", ["National Board", "State Board", "International"])
    with col2: selected_level = st.selectbox("Exam Specification", options=SYSTEM_LEVELS)
    with col3:
        subject_options = STRUCTURED_MAP.get(selected_level, ["All Verticals"])
        selected_subject = st.selectbox("Academic Verticals", options=subject_options)
        
    uploaded_file = st.file_uploader("Upload Academic Attachments (PNG, JPEG, PDF)", type=["png", "jpg", "jpeg", "pdf"])
    
    file_bytes, mime_type = None, None
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        mime_type = uploaded_file.type
        st.info(f"📎 Asset verified: `{uploaded_file.name}`")

    user_query = st.text_area("Input problem statement context criteria here:", placeholder="Type here...").strip()
    submit_btn = st.button("Compute Multimodal Architecture", use_container_width=True, type="primary")
    
    if submit_btn:
        current_used = check_user_quota_allowance(st.session_state.username)
        if current_used >= DAILY_LIMIT:
            st.error("⛔ Account Blocked: You have run out of your 5 structural allocations for today. Balance resets at midnight.")
        elif not user_query and not file_bytes:
            st.warning("⚠️ Context missing: Provide a question context or an explicit image attachment tool.")
        else:
            match_found = False
            status_placeholder = st.empty()
            output_container = st.empty()
            
            if user_query and not file_bytes:
                target_col = "solution_hi" if target_language == "Hindi (हिन्दी)" else "solution_en"
                try:
                    conn = sqlite3.connect(DB_NAME, timeout=30.0)
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT {target_col}, source FROM academic_vault WHERE question LIKE ? LIMIT 1", (f"%{user_query}%",))
                    row = cursor.fetchone()
                    conn.close()
                    if row and row[0]:
                        status_placeholder.success(f"🎉 Cache Match Found (Source Tag: `{row[1]}`)!")
                        with output_container.container():
                            st.markdown(f"### 🎓 System Operational Solution Matrix ({target_language})")
                            st.markdown('<div class="solution-container">', unsafe_allow_html=True)
                            render_smart_response_blocks(row[0])
                            st.markdown('</div>', unsafe_allow_html=True)
                        match_found = True
                except Exception:
                    pass

            if not match_found:
                if not api_key:
                    st.error("❌ Key Vetting Error: Configure your API engine secrets to allow generation operations.")
                else:
                    status_placeholder.info("🧠 Activating CoreAI Multimodal Engine... Resolving definitions and charts...")
                    
                    contextual_prompt = (
                        f"Domain Field: {selected_subject}\nTarget Grade: {selected_level}\n"
                        f"Context String Input: {user_query if user_query else '[Attachment Core Run]'}"
                    )
                    
                    generated_output = execute_safe_ai_resolution(
                        prompt=contextual_prompt, mime_type=mime_type, file_bytes=file_bytes,
                        target_lang=target_language, api_key=api_key
                    )
                    
                    if generated_output:
                        log_user_quota_consumption(st.session_state.username)
                        status_placeholder.success("✨ Strategy Blueprint Synthesized Successfully!")
                        with output_container.container():
                            st.markdown(f"### 🎓 System Operational Solution Matrix ({target_language})")
                            st.markdown('<div class="solution-container">', unsafe_allow_html=True)
                            render_smart_response_blocks(generated_output)
                            st.markdown('</div>', unsafe_allow_html=True)
                        
                        cache_label_text = user_query if user_query else f"[Scanned File Run ID: {int(time.time())}]"
                        target_lang_suffix = "hi" if target_language == "Hindi (हिन्दी)" else "en"
                        target_col_save = "solution_hi" if target_lang_suffix == "hi" else "solution_en"
                        
                        write_query = f"""
                            INSERT OR IGNORE INTO academic_vault 
                            (board, level, subject, question, {target_col_save}, difficulty, question_type, source) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """
                        run_write_transaction(write_query, ("National Board", selected_level, selected_subject, cache_label_text, generated_output, "medium", "Theoretical", "live_multimodal_fallback"))
                        st.rerun()
                    else:
                        status_placeholder.error("❌ Generation failure. Check processing limits.")

# ==========================================
# TAB 2: PRACTICE PORTAL
# ==========================================
with tabs[1]:
    st.subheader("📝 Dynamic Assessment Builder")
    num_questions = st.slider("Select test length matrix limits:", min_value=1, max_value=25, value=5)
    generate_btn = st.button("⚡ Generate Random Assessment", use_container_width=True)

    if generate_btn:
        try:
            target_col_practice = "solution_hi" if target_language == "Hindi (हिन्दी)" else "solution_en"
            conn = sqlite3.connect(DB_NAME, timeout=30.0)
            query = f"SELECT question, {target_col_practice}, difficulty, source FROM academic_vault WHERE level = ? AND subject = ? ORDER BY RANDOM() LIMIT ?"
            df_test = pd.read_sql_query(query, conn, params=(selected_level, selected_subject, num_questions))
            conn.close()
            if not df_test.empty:
                st.session_state.current_test = df_test.values.tolist()
            else:
                st.session_state.current_test = []
                st.info("ℹ️ No entries matching this selection are loaded inside the database volume.")
        except Exception:
            st.error("Relational query breakdown error.")

    if st.session_state.current_test:
        st.success(f"Generated a {len(st.session_state.current_test)}-question test for **{selected_level} - {selected_subject}** ({target_language})!")
        for idx, row in enumerate(st.session_state.current_test):
            st.markdown(f"### Question {idx+1} `[{str(row[2]).upper()}]` — Source: `{row[3]}`")
            st.markdown(f'<div class="question-box"><strong>{row[0]}</strong></div>', unsafe_allow_html=True)
            with st.expander(f"🔑 View Answer Key for Question {idx+1}"):
                st.markdown('<div class="solution-container">', unsafe_allow_html=True)
                if row[1]: render_smart_response_blocks(row[1])
                else: st.warning("No translation key mapped for this entry row yet.")
                st.markdown('</div>', unsafe_allow_html=True)
            st.write("---")