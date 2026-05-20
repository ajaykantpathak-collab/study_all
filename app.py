
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
import requests
import time

DB_NAME = "coreai_vault.db"

# Page configuration
st.set_page_config(
    page_title="CoreAI Academic Engine",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling to match your premium workspace
st.markdown("""
    <style>
    .main {
        background-color: #0f1116;
        color: #e2e8f0;
    }
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #38bdf8;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .question-box {
        background-color: #1e293b;
        border-left: 5px solid #38bdf8;
        border-radius: 6px;
        padding: 18px;
        margin-bottom: 15px;
    }
    .explanation-box {
        background-color: #0f172a;
        border: 1px dashed #475569;
        border-radius: 6px;
        padding: 18px;
        margin-top: 10px;
        color: #cbd5e1;
    }
    </style>
""", unsafe_allow_html=True)

# ───────────────────────────────────────────────────────────────
# DATABASE UTILITY FUNCTIONS
# ───────────────────────────────────────────────────────────────
def run_query(query, params=(), fetchall=True):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetchall:
            result = cursor.fetchall()
        else:
            conn.commit()
            result = cursor.fetchone()
        conn.close()
        return result
    except Exception as e:
        st.error(f"Database Error: {e}")
        return []

def get_dynamic_levels():
    """Fetches all unique exam specifications present in the database."""
    query = "SELECT DISTINCT level FROM academic_vault WHERE level IS NOT NULL AND level != '' ORDER BY level ASC"
    rows = run_query(query)
    levels = [r[0] for r in rows]
    if not levels:
        return ["Class 11-12 (NEET)", "JEE Mains & Advanced", "Banking (IBPS/SBI)", "UPSC Civil Services", "CA/CS/CMA"]
    return levels

def get_dynamic_subjects(level):
    """Fetches all subjects available for a chosen exam specification."""
    query = "SELECT DISTINCT subject FROM academic_vault WHERE level = ? AND subject IS NOT NULL AND subject != '' ORDER BY subject ASC"
    rows = run_query(query, (level,))
    subjects = [r[0] for r in rows]
    if not subjects:
        return ["All Verticals"]
    return subjects

# ───────────────────────────────────────────────────────────────
# LIVE GEMINI FALLBACK API ENGINE (WITH BACKOFF)
# ───────────────────────────────────────────────────────────────
def generate_gemini_resolution(prompt, api_key):
    """Calls Gemini API using exponential backoff with robust fallbacks."""
    # System prompt to ensure professional competitive format
    system_instruction = (
        "You are the CoreAI Academic Resolution Engine. "
        "Provide a highly detailed, accurate, step-by-step academic explanation "
        "suitable for competitive national-level exams (NEET, JEE, UPSC, CA)."
    )
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system_instruction}]}
    }
    
    # Exponential backoff: 1s, 2s, 4s, 8s, 16s
    delays = [1, 2, 4, 8, 16]
    for delay in delays:
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if text:
                    return text
        except Exception:
            pass
        time.sleep(delay)
        
    # Standard Model Fallback
    fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    try:
        response = requests.post(fallback_url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    except Exception:
        pass
        
    return None

def save_new_question_to_vault(level, subject, question, answer):
    """Learns and appends live resolutions directly to your local database on-the-fly."""
    query = """
    INSERT OR IGNORE INTO academic_vault 
    (board, level, subject, question, solution_en, difficulty, question_type, source) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    run_query(query, ("National Board", level, subject, question, answer, "medium", "Theoretical", "live_gemini_fallback"), fetchall=False)

# ───────────────────────────────────────────────────────────────
# API KEY RESOLUTION (STREAMLIT SECRETS + FALLBACK)
# ───────────────────────────────────────────────────────────────
api_key = None
if hasattr(st, "secrets"):
    # Scans for standard permutations of your key
    api_key = st.secrets.get("GEMINI_API_KEY") or st.secrets.get("api_key")

# Sidebar Stats Portal
with st.sidebar:
    st.header("📊 CoreAI System Matrix")
    
    # Status Indicators
    if api_key:
        st.markdown("🟢 **Gemini Live Fallback:** `Active`")
    else:
        st.markdown("🔴 **Gemini Live Fallback:** `Inactive (Enter Secrets)`")
        
    total_q_row = run_query("SELECT COUNT(*) FROM academic_vault", fetchall=False)
    total_q = total_q_row[0] if total_q_row else 0
    
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{total_q:,}</div>
        <div class="metric-label">Vault Capacity</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.write("📌 **System Composition:**")
    composition = run_query("SELECT level, COUNT(*) FROM academic_vault GROUP BY level ORDER BY COUNT(*) DESC")
    for lvl, cnt in composition:
        st.markdown(f"**{lvl}**: `{cnt:,} questions`")

# ───────────────────────────────────────────────────────────────
# MAIN USER INTERFACE
# ───────────────────────────────────────────────────────────────
st.title("🛡️ Academic Question Resolution Layer")
st.caption("Dual-Core Processing: Searches 420k+ offline records instantly, with automated live AI generation.")

tabs = st.tabs(["🔎 Smart Question Solver", "📝 Practice Portal"])

# ==========================================
# TAB 1: SMART QUESTION SOLVER
# ==========================================
with tabs[0]:
    st.subheader("Input Exam Specifications")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_board = st.selectbox("Exam Board / Segment", ["National Board", "State Board", "International"])
    with col2:
        available_levels = get_dynamic_levels()
        selected_level = st.selectbox("Exam Specification", options=available_levels)
    with col3:
        available_subjects = get_dynamic_subjects(selected_level)
        selected_subject = st.selectbox("Academic Verticals", options=available_subjects)
        
    user_query = st.text_area(
        "Input your complex exam question or problem case scenario here:",
        placeholder="Type or paste your question (e.g., 'WHAT IS PHOTOSYNTHESIS ?')"
    ).strip()
    
    submit_btn = st.button("Compute Step-by-Step Architecture", use_container_width=True)
    
    if submit_btn and user_query:
        # Search the database for exact or near matching questions
        search_query = "SELECT solution_en, source FROM academic_vault WHERE question LIKE ? LIMIT 1"
        match = run_query(search_query, (f"%{user_query}%",))
        
        if match:
            solution, source = match[0]
            st.success(f"🎉 Direct Match Found in Database (Source: `{source}`)!")
            st.markdown(f"""
            <div class="explanation-box">
                <strong>Step-by-Step Explanation:</strong><br><br>
                {solution}
            </div>
            """, unsafe_allow_html=True)
        else:
            # Activate live fallback engine
            st.info("🔎 Item not matched in the initial database. Activating Live Fallback API Engine...")
            
            if not api_key:
                st.warning("⚠️ Enter your API Key integration details on Streamlit Secrets to handle active global external generation.")
            else:
                with st.spinner("🧠 Generating step-by-step academic resolution key via Gemini..."):
                    generated_solution = generate_gemini_resolution(
                        f"Subject: {selected_subject}, Level: {selected_level}. Question: {user_query}", 
                        api_key
                    )
                    
                    if generated_solution:
                        st.success("✨ Resolution Key Generated Successfully!")
                        st.markdown(f"""
                        <div class="explanation-box">
                            <strong>Step-by-Step Explanation (Live Fallback):</strong><br><br>
                            {generated_solution}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Save back to database so next time it is instant
                        save_new_question_to_vault(selected_level, selected_subject, user_query, generated_solution)
                    else:
                        st.error("❌ Failed to reach the fallback API. Please check your internet connection or API Key limits.")

# ==========================================
# TAB 2: PRACTICE PORTAL
# ==========================================
with tabs[1]:
    st.subheader("📝 Dynamic Assessment Builder")
    
    num_questions = st.slider("Select number of questions for test generation:", min_value=1, max_value=25, value=5)
    generate_btn = st.button("⚡ Generate Random Assessment", use_container_width=True)

    if generate_btn:
        st.session_state.current_test = run_query(
            "SELECT question, solution_en, difficulty, source FROM academic_vault WHERE level = ? AND subject = ? ORDER BY RANDOM() LIMIT ?",
            (selected_level, selected_subject, num_questions)
        )

    if "current_test" in st.session_state and st.session_state.current_test:
        st.write("---")
        st.success(f"Generated a {len(st.session_state.current_test)}-question test for **{selected_level} - {selected_subject}**!")
        
        for idx, (question, solution, difficulty, source) in enumerate(st.session_state.current_test):
            st.markdown(f"### Question {idx+1}")
            st.markdown(f"<span style='color:#38bdf8; font-weight:bold;'>[{difficulty.upper()}]</span> — Source: `{source}`", unsafe_allow_html=True)
            st.markdown(f'<div class="question-box"><strong>{question}</strong></div>', unsafe_allow_html=True)
            
            with st.expander(f"🔑 View Answer Key for Question {idx+1}"):
                st.markdown(f'<div class="explanation-box">{solution}</div>', unsafe_allow_html=True)
            st.write("---")

