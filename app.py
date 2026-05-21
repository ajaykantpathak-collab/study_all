import re
import streamlit as st
import time
import logging
import base64
import os
from supabase import create_client
from google import genai
from google.genai import types as genai_types
import openai
import anthropic

st.set_page_config(
    page_title="Intellect Engine",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

from edtech_config import (
    SCHOOL_BOARDS,
    SCHOOL_CLASSES,
    STREAMS_11_12,
    COMPETITIVE_EXAMS,
    LEARNING_MODES,
    DEFAULT_HINDI_ONLY_SUBJECTS,
    subjects_for_school,
    pedagogy_profile,
    build_system_instruction,
    build_rag_query,
    filter_rag_docs,
    cache_key,
)
from ncert_data import (
    CHAPTER_ANY,
    ncert_chapters_for,
    chapter_available,
)
from dashboard import render_dashboard
from vault_lookup import lookup_vault_answer
from db_helper import verify_and_unpack_database

try:
    import streamlit_mermaid as stmd
except ImportError:
    stmd = None

# -----------------------------------------------------------------------------
# 1. LOGGING SETUP & CONSTANTS
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

MAX_CONTEXT_TURNS   = 10      # Max conversation turns sent to AI
MAX_TEXT_FILE_CHARS = 12_000  # Truncate large text files before sending
MAX_FILE_MB         = 5       # Reject files larger than this
EMBED_MODEL         = "gemini-embedding-001"  # 768 dims — must match ingest_vault.py
MAX_OUTPUT_TOKENS   = 4096

# -----------------------------------------------------------------------------
# 2. LANGUAGE STRINGS (English + Hindi)
# -----------------------------------------------------------------------------
LANG = {
    "en": {
        "login_title":        "🔐 Secure Login",
        "register_title":     "📝 Create Account",
        "email":              "Email",
        "password":           "Password",
        "confirm_password":   "Confirm Password",
        "password_mismatch":  "Passwords do not match.",
        "password_short":     "Password must be at least 6 characters.",
        "login_btn":          "Login",
        "register_btn":       "Create Account",
        "go_register":        "Don't have an account? Sign up",
        "go_login":           "Already have an account? Login",
        "fill_both":          "Please enter both email and password.",
        "connecting":         "Connecting to Cloud Database...",
        "registering":        "Creating your account...",
        "login_failed":       "Login failed: invalid credentials or database unreachable.",
        "register_success":   "✅ Account created successfully! You can now login.",
        "register_failed":    "Registration failed: {e}",
        "forgot_password":    "Forgot Password? Reset via Email",
        "reset_sent":         "✅ Password reset email sent! Check your inbox.",
        "reset_failed":       "Reset failed: email not found or error occurred.",
        "reset_email_label":  "Enter your registered email to reset password:",
        "send_reset":         "Send Reset Link",
        "back_to_login":      "← Back to Login",
        "app_title":          "📚 Intellect Engine — Syllabus-Aligned Tutor",
        "curriculum_header":  "🎓 Your Learning Profile",
        "learning_mode":      "Learning path",
        "school_mode":        "School (Class 1–12)",
        "competitive_mode":   "Competitive Exams",
        "board_label":        "Board",
        "class_label":        "Class",
        "stream_label":       "Stream (Class 11–12)",
        "exam_label":         "Competitive exam",
        "subject_label":      "Subject (optional)",
        "subject_any":        "— General / All subjects —",
        "active_profile":     "Active profile",
        "guardrails_note":    "Answers are locked to your profile and textbook vault. AI will not invent citations.",
        "chapter_header":     "📖 NCERT Chapter",
        "chapter_label":      "Select chapter",
        "chapter_hint":       "Answers stay within this NCERT chapter when selected.",
        "chapter_na":         "Select a subject to see NCERT chapters.",
        "hindi_mode_header":  "🇮🇳 Hindi-only answers",
        "hindi_mode_help":    "Listed subjects always get full Hindi answers (Devanagari), regardless of UI language.",
        "hindi_subjects_label": "Hindi-only for subjects",
        "tab_chat":           "💬 Tutor Chat",
        "tab_dashboard":      "📊 Parent / Teacher Dashboard",
        "dashboard_title":    "📊 Learning Analytics",
        "dashboard_subtitle": "Activity for {email}",
        "dashboard_empty":    "No queries logged yet. Start chatting to see analytics.",
        "metric_total":       "Total queries",
        "metric_week":        "This week",
        "metric_today":       "Today",
        "metric_engines":     "AI engines used",
        "chart_engines":      "Queries by AI engine",
        "chart_subjects":     "Top subjects",
        "chart_activity":     "Daily activity (last sessions)",
        "no_activity_data":   "No dated activity yet.",
        "recent_queries":     "Recent questions",
        "col_time":           "Time",
        "col_subject":        "Subject / Profile",
        "col_engine":         "Engine",
        "col_question":       "Question",
        "insights_expander":  "💡 Insights for parents & teachers",
        "insight_top_subject": "Most studied: **{subject}** ({count} queries)",
        "insight_top_engine":  "Preferred engine: **{engine}** ({count} responses)",
        "insight_inactive_week": "No queries this week — encourage daily practice.",
        "vault_searching":    "Searching your question bank (semantic match)…",
        "session":            "Secure Session",
        "logout":             "Logout",
        "diagram_expander":   "📊 View AI Routing Architecture (Mermaid)",
        "no_history":         "No past conversations found.",
        "delete_history":     "🗑️ Delete All History",
        "delete_confirm":     "Are you sure? This cannot be undone.",
        "delete_done":        "✅ All history deleted.",
        "delete_failed":      "Delete failed: {e}",
        "upload_label":       "📎 Attach file (PDF, image, or text — max 5 MB):",
        "file_too_large":     "File too large. Maximum size is 5 MB.",
        "file_truncated":     "File truncated to {n} chars to fit context window.",
        "query_label":        "Enter your query…",
        "routing":            "Routing request through AI cluster...",
        "success":            "Response via **{provider}** — saved to Cloud.",
        "db_warn":            "Response generated, but failed to save to cloud history: {e}",
        "all_failed":         "CRITICAL: All three AI engines failed. Please try again in a few moments.",
        "language_label":     "🌐 Language / भाषा",
        "clear_chat":         "🗑️ Clear Chat",
        "you":                "You",
        "assistant":          "Assistant",
        "file_note":          "📄 File attached: {name}",
        "new_chat":           "➕ New Chat",
        "sidebar_history":    "💬 Past Conversations",
        "sidebar_settings":   "⚙️ Settings",
        "context_trimmed":    "ℹ️ Older messages trimmed to stay within context limits.",
    },
    "hi": {
        "login_title":        "🔐 सुरक्षित लॉगिन",
        "register_title":     "📝 खाता बनाएं",
        "email":              "ईमेल",
        "password":           "पासवर्ड",
        "confirm_password":   "पासवर्ड की पुष्टि करें",
        "password_mismatch":  "पासवर्ड मेल नहीं खाते।",
        "password_short":     "पासवर्ड कम से कम 6 अक्षर का होना चाहिए।",
        "login_btn":          "लॉगिन करें",
        "register_btn":       "खाता बनाएं",
        "go_register":        "खाता नहीं है? साइन अप करें",
        "go_login":           "पहले से खाता है? लॉगिन करें",
        "fill_both":          "कृपया ईमेल और पासवर्ड दोनों दर्ज करें।",
        "connecting":         "क्लाउड डेटाबेस से जोड़ा जा रहा है...",
        "registering":        "आपका खाता बनाया जा रहा है...",
        "login_failed":       "लॉगिन विफल: गलत क्रेडेंशियल या डेटाबेस अनुपलब्ध।",
        "register_success":   "✅ खाता बनाया गया! कृपया अपना ईमेल सत्यापित करें, फिर लॉगिन करें।",
        "register_failed":    "पंजीकरण विफल: {e}",
        "forgot_password":    "पासवर्ड भूल गए? ईमेल से रीसेट करें",
        "reset_sent":         "✅ पासवर्ड रीसेट ईमेल भेजा गया!",
        "reset_failed":       "रीसेट विफल।",
        "reset_email_label":  "अपना पंजीकृत ईमेल दर्ज करें:",
        "send_reset":         "रीसेट लिंक भेजें",
        "back_to_login":      "← लॉगिन पर वापस जाएं",
        "app_title":          "📚 बुद्धि इंजन — पाठ्यक्रम-संरेखित ट्यूटर",
        "curriculum_header":  "🎓 आपकी शिक्षा प्रोफ़ाइल",
        "learning_mode":      "शिक्षा मार्ग",
        "school_mode":        "स्कूल (कक्षा 1–12)",
        "competitive_mode":   "प्रतियोगी परीक्षाएं",
        "board_label":        "बोर्ड",
        "class_label":        "कक्षा",
        "stream_label":       "स्ट्रीम (कक्षा 11–12)",
        "exam_label":         "प्रतियोगी परीक्षा",
        "subject_label":      "विषय (वैकल्पिक)",
        "subject_any":        "— सामान्य / सभी विषय —",
        "active_profile":     "सक्रिय प्रोफ़ाइल",
        "guardrails_note":    "उत्तर आपकी प्रोफ़ाइल और पाठ्य पुस्तक वॉल्ट से बंधे हैं। AI गढ़ी उद्धरण नहीं देगा।",
        "chapter_header":     "📖 NCERT अध्याय",
        "chapter_label":      "अध्याय चुनें",
        "chapter_hint":       "चयनित अध्याय के भीतर उत्तर दिए जाएंगे।",
        "chapter_na":         "अध्याय देखने के लिए विषय चुनें।",
        "hindi_mode_header":  "🇮🇳 केवल हिंदी उत्तर",
        "hindi_mode_help":    "चुने विषयों के उत्तर हमेशा देवनागरी हिंदी में।",
        "hindi_subjects_label": "हिंदी-केवल विषय",
        "tab_chat":           "💬 ट्यूटर चैट",
        "tab_dashboard":      "📊 अभिभावक / शिक्षक डैशबोर्ड",
        "dashboard_title":    "📊 सीखने का विश्लेषण",
        "dashboard_subtitle": "{email} की गतिविधि",
        "dashboard_empty":    "अभी कोई प्रश्न लॉग नहीं। चैट शुरू करें।",
        "metric_total":       "कुल प्रश्न",
        "metric_week":        "इस सप्ताह",
        "metric_today":       "आज",
        "metric_engines":     "AI इंजन",
        "chart_engines":      "AI इंजन के अनुसार",
        "chart_subjects":     "शीर्ष विषय",
        "chart_activity":     "दैनिक गतिविधि",
        "no_activity_data":   "कोई दिनांकित गतिविधि नहीं।",
        "recent_queries":     "हाल के प्रश्न",
        "col_time":           "समय",
        "col_subject":        "विषय / प्रोफ़ाइल",
        "col_engine":         "इंजन",
        "col_question":       "प्रश्न",
        "insights_expander":  "💡 अभिभावक / शिक्षक के लिए सुझाव",
        "insight_top_subject": "सबसे अधिक: **{subject}** ({count} प्रश्न)",
        "insight_top_engine":  "प्रमुख इंजन: **{engine}** ({count} उत्तर)",
        "insight_inactive_week": "इस सप्ताह कोई प्रश्न नहीं — रोज़ अभ्यास करें।",
        "vault_searching":    "आपके प्रश्न बैंक में खोज (अर्थ-आधारित)…",
        "session":            "सुरक्षित सत्र",
        "logout":             "लॉगआउट",
        "diagram_expander":   "📊 AI रूटिंग आर्किटेक्चर देखें (Mermaid)",
        "no_history":         "कोई पिछली बातचीत नहीं मिली।",
        "delete_history":     "🗑️ सारा इतिहास मिटाएं",
        "delete_confirm":     "क्या आप निश्चित हैं? यह पूर्ववत नहीं किया जा सकता।",
        "delete_done":        "✅ सारा इतिहास मिटा दिया गया।",
        "delete_failed":      "मिटाना विफल: {e}",
        "upload_label":       "📎 फ़ाइल संलग्न करें (PDF, इमेज, या टेक्स्ट — अधिकतम 5 MB):",
        "file_too_large":     "फ़ाइल बहुत बड़ी है। अधिकतम आकार 5 MB है।",
        "file_truncated":     "फ़ाइल को {n} अक्षरों तक छोटा किया गया।",
        "query_label":        "अपना प्रश्न दर्ज करें…",
        "routing":            "AI क्लस्टर के माध्यम से अनुरोध रूट किया जा रहा है...",
        "success":            "**{provider}** के माध्यम से उत्तर — क्लाउड में सहेजा गया।",
        "db_warn":            "उत्तर तैयार हुआ, लेकिन क्लाउड हिस्ट्री में सहेजना विफल: {e}",
        "all_failed":         "गंभीर त्रुटि: तीनों AI इंजन विफल हो गए।",
        "language_label":     "🌐 Language / भाषा",
        "clear_chat":         "🗑️ चैट साफ़ करें",
        "you":                "आप",
        "assistant":          "सहायक",
        "file_note":          "📄 फ़ाइल संलग्न: {name}",
        "new_chat":           "➕ नई चैट",
        "sidebar_history":    "💬 पिछली बातचीत",
        "sidebar_settings":   "⚙️ सेटिंग्स",
        "context_trimmed":    "ℹ️ संदर्भ सीमा के लिए पुराने संदेश हटाए गए।",
    },
}

def t(key: str, **kwargs) -> str:
    lang = st.session_state.get("lang", "en")
    text = LANG[lang].get(key, LANG["en"].get(key, key))
    return text.format(**kwargs) if kwargs else text

def get_secret(name: str) -> str:
    value = os.environ.get(name)
    if value:
        return value
    try:
        return st.secrets[name]
    except Exception:
        return ""

# -----------------------------------------------------------------------------
# 3. INFRASTRUCTURE & CREDENTIALS
# -----------------------------------------------------------------------------
@st.cache_resource
def init_clients():
    supabase_url = "https://pyeddkjbcfzfcajcqhnj.supabase.co"
    supabase_key = get_secret("SUPABASE_ANON_KEY") or get_secret("SUPABASE_KEY")
    gemini_key = get_secret("GEMINI_API_KEY")
    openai_key = get_secret("OPENAI_API_KEY")
    anthropic_key = get_secret("ANTHROPIC_API_KEY")
    missing = [
        name for name, value in {
            "SUPABASE_ANON_KEY or SUPABASE_KEY": supabase_key,
            "GEMINI_API_KEY": gemini_key,
            "OPENAI_API_KEY": openai_key,
            "ANTHROPIC_API_KEY": anthropic_key,
        }.items()
        if not value
    ]
    if missing:
        st.error(f"Missing required secret(s): {', '.join(missing)}")
        st.stop()
    supabase = create_client(supabase_url, supabase_key)
    gemini   = genai.Client(api_key=gemini_key)
    oai      = openai.OpenAI(api_key=openai_key)
    claude   = anthropic.Anthropic(api_key=anthropic_key)
    return supabase, gemini, oai, claude

supabase_client, gemini_client, openai_client, anthropic_client = init_clients()

# Ensure local vault exists for fuzzy fallback (Streamlit Cloud unpacks zip)
verify_and_unpack_database()

# -----------------------------------------------------------------------------
# 4. AUTH HELPERS
# -----------------------------------------------------------------------------
def authenticate_user(email: str, password: str, max_retries: int = 3):
    last_exc = None
    for attempt in range(max_retries):
        try:
            return supabase_client.auth.sign_in_with_password(
                {"email": email.strip(), "password": password}
            )
        except Exception as exc:
            last_exc = exc
            logger.warning("Login attempt %d failed: %s", attempt + 1, exc)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    raise last_exc

def register_user(email: str, password: str):
    return supabase_client.auth.sign_up({"email": email, "password": password})

def reset_password(email: str):
    supabase_client.auth.reset_password_email(email)

# -----------------------------------------------------------------------------
# 5. DATABASE & RAG HELPERS
# -----------------------------------------------------------------------------
def check_cache(prompt: str) -> str | None:
    clean_prompt = prompt.strip()
    try:
        db_check = supabase_client.table("ai_logs").select("ai_response").eq("prompt", clean_prompt).execute()
        if db_check.data and len(db_check.data) > 0:
            return db_check.data[0]["ai_response"]
    except Exception as e:
        logger.warning("Cache check failed: %s", e)
    return None

def embed_text(text: str) -> list[float] | None:
    try:
        embed_res = gemini_client.models.embed_content(
            model=EMBED_MODEL,
            contents=text,
            config={"output_dimensionality": 768},
        )
        if not getattr(embed_res, "embeddings", None):
            return None
        values = getattr(embed_res.embeddings[0], "values", None)
        return values or None
    except Exception as e:
        logger.warning("Embedding failed: %s", e)
        return None

def fetch_rag_context(prompt: str, profile: dict) -> str:
    rag_query = build_rag_query(prompt, profile)
    try:
        query_vector = embed_text(rag_query)
        if not query_vector:
            return ""

        docs = supabase_client.rpc("match_documents", {
            "query_embedding": query_vector,
            "match_threshold": 0.65,
            "match_count": 8,
        }).execute()

        if docs.data:
            ranked = filter_rag_docs(docs.data, profile)[:5]
            return "\n\n---\n\n".join(doc["content"] for doc in ranked)
    except Exception as e:
        logger.warning("RAG Retrieval failed: %s", e)
    return ""


def log_to_database(
    user_id: str,
    prompt: str,
    response: str,
    engine: str,
    profile: dict,
):
    base = {
        "user_id":     user_id,
        "prompt":      prompt.strip(),
        "ai_response": response,
        "engine_used": engine,
    }
    extended = {
        **base,
        "learning_mode": st.session_state.get("learning_mode"),
        "board":         profile.get("rag_board"),
        "level":         profile.get("rag_level"),
        "subject":       profile.get("rag_subject"),
        "exam":          profile.get("exam"),
        "class_num":     profile.get("class_num"),
        "stream":        profile.get("stream"),
        "profile_label": profile.get("display_label"),
        "ncert_chapter":   profile.get("ncert_chapter"),
        "hindi_only":      profile.get("hindi_only"),
    }
    try:
        supabase_client.table("ai_logs").insert(extended).execute()
    except Exception:
        try:
            supabase_client.table("ai_logs").insert(base).execute()
        except Exception as exc:
            logger.warning("DB log failed: %s", exc)
            st.warning(t("db_warn", e=exc))

def fetch_history(user_id: str, limit: int = 20) -> list[dict]:
    try:
        result = (
            supabase_client.table("ai_logs")
            .select("id, prompt, ai_response, engine_used, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as exc:
        logger.warning("History fetch failed: %s", exc)
        return []

def delete_all_history(user_id: str):
    supabase_client.table("ai_logs").delete().eq("user_id", user_id).execute()

def delete_single_log(log_id: str):
    supabase_client.table("ai_logs").delete().eq("id", log_id).execute()

    # -----------------------------------------------------------------------------
# 6. FILE PROCESSING
# -----------------------------------------------------------------------------
def extract_file_content(uploaded_file) -> tuple[str | None, str | None, str | None]:
    size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    if size_mb > MAX_FILE_MB:
        return None, None, t("file_too_large")

    mime = uploaded_file.type
    raw  = uploaded_file.read()

    if mime in ("text/plain", "text/csv", "application/json"):
        text = raw.decode("utf-8", errors="replace")
        if len(text) > MAX_TEXT_FILE_CHARS:
            st.info(t("file_truncated", n=MAX_TEXT_FILE_CHARS))
            text = text[:MAX_TEXT_FILE_CHARS]
        return text, "text", None

    b64 = base64.b64encode(raw).decode("utf-8")
    return b64, mime, None

# -----------------------------------------------------------------------------
# 7. CONTEXT WINDOW GUARD
# -----------------------------------------------------------------------------
def safe_history(history: list[dict]) -> tuple[list[dict], bool]:
    if len(history) > MAX_CONTEXT_TURNS:
        return history[-MAX_CONTEXT_TURNS:], True
    return history, False

# -----------------------------------------------------------------------------
# 8. MESSAGE BUILDERS
# -----------------------------------------------------------------------------
def build_openai_messages(history, user_prompt, file_content, file_mime, system_instruction):
    messages = [{"role": "system", "content": system_instruction}]
    for turn in history:
        messages.append({"role": "user",      "content": turn["user"]})
        messages.append({"role": "assistant", "content": turn["assistant"]})

    if file_content and file_mime and file_mime.startswith("image/"):
        content = [
            {"type": "image_url", "image_url": {"url": f"data:{file_mime};base64,{file_content}"}},
            {"type": "text", "text": user_prompt},
        ]
    elif file_content and file_mime == "text":
        content = f"{user_prompt}\n\n--- Attached file ---\n{file_content}"
    else:
        content = user_prompt

    messages.append({"role": "user", "content": content})
    return messages

def build_anthropic_messages(history, user_prompt, file_content, file_mime):
    messages = []
    for turn in history:
        messages.append({"role": "user",      "content": turn["user"]})
        messages.append({"role": "assistant", "content": turn["assistant"]})

    if file_content and file_mime and file_mime not in (None, "text"):
        block_type = "image" if file_mime.startswith("image/") else "document"
        content = [
            {"type": block_type, "source": {"type": "base64", "media_type": file_mime, "data": file_content}},
            {"type": "text", "text": user_prompt},
        ]
    elif file_content and file_mime == "text":
        content = f"{user_prompt}\n\n--- Attached file ---\n{file_content}"
    else:
        content = user_prompt

    messages.append({"role": "user", "content": content})
    return messages

# -----------------------------------------------------------------------------
# 9. RENDER HELPERS
# -----------------------------------------------------------------------------
def render_mermaid_blocks(text: str):
    """Render markdown body and inline Mermaid diagrams."""
    pattern = r"```mermaid\s*\n(.*?)```"
    parts = re.split(pattern, text, flags=re.DOTALL | re.IGNORECASE)
    for i, part in enumerate(parts):
        if i % 2 == 0:
            if part.strip():
                st.markdown(part)
        elif stmd is not None:
            try:
                stmd.st_mermaid(part.strip())
            except Exception:
                st.code(part.strip(), language="mermaid")
        else:
            st.code(part.strip(), language="mermaid")

def apply_premium_theme():
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg: #0b1020;
    --panel: rgba(15, 23, 42, 0.72);
    --panel-strong: rgba(15, 23, 42, 0.92);
    --stroke: rgba(148, 163, 184, 0.22);
    --text: #e5e7eb;
    --muted: #94a3b8;
    --brand: #8b5cf6;
    --brand-2: #06b6d4;
    --gold: #fbbf24;
}

html, body, [class*="css"] {
    font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
}

.stApp {
    color: var(--text);
    background:
        radial-gradient(circle at top left, rgba(139, 92, 246, 0.32), transparent 34rem),
        radial-gradient(circle at top right, rgba(6, 182, 212, 0.22), transparent 32rem),
        linear-gradient(135deg, #020617 0%, #0f172a 48%, #111827 100%);
}

[data-testid="stHeader"] {
    background: rgba(2, 6, 23, 0.08);
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(15, 23, 42, 0.98), rgba(2, 6, 23, 0.98));
    border-right: 1px solid var(--stroke);
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p {
    color: var(--text);
}

.block-container {
    max-width: 1220px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}

.premium-hero {
    position: relative;
    overflow: hidden;
    padding: 2.2rem;
    margin-bottom: 1.4rem;
    border: 1px solid var(--stroke);
    border-radius: 28px;
    background:
        linear-gradient(135deg, rgba(139, 92, 246, 0.22), rgba(6, 182, 212, 0.12)),
        rgba(15, 23, 42, 0.72);
    box-shadow: 0 30px 80px rgba(2, 6, 23, 0.36);
    backdrop-filter: blur(18px);
}

.premium-hero:after {
    content: "";
    position: absolute;
    width: 240px;
    height: 240px;
    right: -70px;
    top: -90px;
    border-radius: 999px;
    background: radial-gradient(circle, rgba(251, 191, 36, 0.28), transparent 68%);
}

.premium-kicker {
    display: inline-flex;
    align-items: center;
    gap: .45rem;
    padding: .42rem .78rem;
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 999px;
    color: #cffafe;
    background: rgba(6, 182, 212, 0.12);
    font-size: .82rem;
    font-weight: 700;
    letter-spacing: .02em;
    text-transform: uppercase;
}

.premium-hero h1 {
    margin: .85rem 0 .45rem 0;
    color: #f8fafc;
    font-size: clamp(2.2rem, 5vw, 4.6rem);
    line-height: .95;
    letter-spacing: -0.075em;
}

.premium-hero p {
    max-width: 760px;
    color: #cbd5e1;
    font-size: 1.08rem;
    line-height: 1.7;
}

.premium-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1rem;
    margin: 1.1rem 0 1.4rem 0;
}

.premium-card, .auth-card {
    border: 1px solid var(--stroke);
    border-radius: 24px;
    background: var(--panel);
    box-shadow: 0 20px 55px rgba(2, 6, 23, 0.26);
    backdrop-filter: blur(16px);
}

.premium-card {
    padding: 1rem;
}

.premium-card b {
    color: #f8fafc;
}

.premium-card span {
    display: block;
    margin-top: .35rem;
    color: var(--muted);
    font-size: .9rem;
}

.auth-shell {
    min-height: 78vh;
    display: flex;
    align-items: center;
    justify-content: center;
}

.auth-card {
    width: min(100%, 460px);
    padding: 2rem;
    margin: 1.5rem auto;
}

.auth-card h1 {
    margin: 0 0 .4rem 0;
    color: #f8fafc;
    letter-spacing: -0.05em;
}

.auth-card p {
    color: var(--muted);
}

.profile-pill {
    display: inline-flex;
    padding: .65rem .9rem;
    border: 1px solid rgba(139, 92, 246, 0.32);
    border-radius: 999px;
    background: rgba(139, 92, 246, 0.16);
    color: #ede9fe;
    font-weight: 700;
}

.sidebar-brand {
    padding: 1rem;
    margin: .2rem 0 1rem 0;
    border: 1px solid var(--stroke);
    border-radius: 22px;
    background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(6, 182, 212, 0.12));
}

.sidebar-brand h2 {
    margin: 0;
    color: #f8fafc;
    font-size: 1.25rem;
    letter-spacing: -0.04em;
}

.sidebar-brand p {
    margin: .35rem 0 0 0;
    color: var(--muted);
    font-size: .86rem;
}

[data-testid="stMetric"] {
    padding: 1rem;
    border: 1px solid var(--stroke);
    border-radius: 20px;
    background: rgba(15, 23, 42, 0.62);
    box-shadow: 0 16px 40px rgba(2, 6, 23, 0.18);
}

[data-testid="stChatMessage"] {
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 22px;
    background: rgba(15, 23, 42, 0.58);
    box-shadow: 0 16px 46px rgba(2, 6, 23, 0.16);
}

.stButton > button, .stDownloadButton > button {
    border-radius: 999px;
    border: 1px solid rgba(255, 255, 255, 0.16);
    font-weight: 700;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--brand), var(--brand-2));
    border: 0;
    color: white;
    box-shadow: 0 14px 32px rgba(6, 182, 212, 0.24);
}

.stTextInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea {
    border-radius: 16px;
}

[data-testid="stFileUploader"] {
    padding: 1rem;
    border: 1px dashed rgba(148, 163, 184, 0.32);
    border-radius: 22px;
    background: rgba(15, 23, 42, 0.46);
}

.stTabs [data-baseweb="tab-list"] {
    gap: .5rem;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 999px;
    padding: .65rem 1.05rem;
    background: rgba(15, 23, 42, 0.7);
}

@media (max-width: 760px) {
    .premium-grid {
        grid-template-columns: 1fr;
    }
    .premium-hero {
        padding: 1.3rem;
    }
}
</style>
        """,
        unsafe_allow_html=True,
    )

def render_sidebar_brand():
    st.markdown(
        """
<div class="sidebar-brand">
    <h2>📚 Intellect Engine</h2>
    <p>Premium AI tutor with syllabus guardrails, RAG, and learning analytics.</p>
</div>
        """,
        unsafe_allow_html=True,
    )

def render_hero(profile: dict):
    st.markdown(
        f"""
<div class="premium-hero">
    <div class="premium-kicker">⚡ AI Tutor · RAG Vault · Secure Learning</div>
    <h1>Intellect Engine</h1>
    <p>A premium syllabus-aligned tutor for Indian students. Ask doubts, attach files, retrieve verified vault answers, and track learning progress.</p>
    <div class="profile-pill">🎯 {profile["display_label"]}</div>
</div>
<div class="premium-grid">
    <div class="premium-card"><b>📚 Verified Vault</b><span>Retrieves strong matches from your question bank before using AI.</span></div>
    <div class="premium-card"><b>🧭 Syllabus Guardrails</b><span>Answers stay aligned to class, exam, subject, and chapter profile.</span></div>
    <div class="premium-card"><b>📊 Learning Insights</b><span>Dashboard tracks activity for parents and teachers.</span></div>
</div>
        """,
        unsafe_allow_html=True,
    )

apply_premium_theme()


# -----------------------------------------------------------------------------
# 10. TRIPLE-THREAT AI ROUTER (RAG + syllabus guardrails)
# -----------------------------------------------------------------------------
def stream_intelligence(user_prompt, file_content, file_mime, history, output_placeholder, profile):
    trimmed_history, was_trimmed = safe_history(history)
    if was_trimmed:
        st.caption(t("context_trimmed"))

    rag_context = fetch_rag_context(user_prompt, profile)
    effective_lang = "hi" if profile.get("hindi_only") else st.session_state.get("lang", "en")
    system_instruction = build_system_instruction(profile, rag_context, effective_lang)

    full_prompt_text = user_prompt
    if file_content and file_mime == "text":
        full_prompt_text = f"{user_prompt}\n\n--- Attached file ---\n{file_content}"

    # ── ENGINE 1: GEMINI ─────────────────────────────────────────────────────
    for attempt in range(3):
        try:
            contents = []
            for turn in trimmed_history:
                contents.append({"role": "user",  "parts": [{"text": turn["user"]}]})
                contents.append({"role": "model", "parts": [{"text": turn["assistant"]}]})

            if file_content and file_mime and file_mime not in (None, "text"):
                current_parts = [
                    {"inline_data": {"mime_type": file_mime, "data": file_content}},
                    {"text": user_prompt},
                ]
            else:
                current_parts = [{"text": full_prompt_text}]
            contents.append({"role": "user", "parts": current_parts})

            full_text = ""
            for chunk in gemini_client.models.generate_content_stream(
                model="gemini-2.5-flash",
                contents=contents,
                config=genai_types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                    system_instruction=system_instruction,
                ),
            ):
                if chunk.text:
                    full_text += chunk.text
                    output_placeholder.markdown(full_text + "▌")

            output_placeholder.markdown(full_text)
            return full_text, "Google Gemini"

        except Exception as exc:
            err = str(exc).lower()
            is_retryable = any(c in err for c in ("429", "503", "quota", "overloaded"))
            logger.warning("Gemini attempt %d: %s", attempt + 1, exc)
            if is_retryable and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            break

    # ── ENGINE 2: CLAUDE ─────────────────────────────────────────────────────
    try:
        claude_messages = build_anthropic_messages(trimmed_history, user_prompt, file_content, file_mime)
        full_text = ""
        with anthropic_client.messages.stream(
            model="claude-haiku-4-5-20251001",
            max_tokens=MAX_OUTPUT_TOKENS,
            temperature=0.1,
            system=system_instruction,
            messages=claude_messages,
        ) as stream:
            for token in stream.text_stream:
                full_text += token
                output_placeholder.markdown(full_text + "▌")

        output_placeholder.markdown(full_text)
        return full_text, "Anthropic Claude"
    except Exception as exc:
        logger.warning("Claude stream failed: %s", exc)

    # ── ENGINE 3: OPENAI ─────────────────────────────────────────────────────
    try:
        oai_messages = build_openai_messages(trimmed_history, user_prompt, file_content, file_mime, system_instruction)
        full_text = ""
        for chunk in openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=oai_messages,
            temperature=0.1,
            max_tokens=MAX_OUTPUT_TOKENS,
            stream=True,
        ):
            delta = chunk.choices[0].delta.content or ""
            full_text += delta
            output_placeholder.markdown(full_text + "▌")

        output_placeholder.markdown(full_text)
        return full_text, "OpenAI GPT"
    except Exception as exc:
        logger.error("OpenAI stream failed: %s", exc)

    raise RuntimeError(t("all_failed"))

# -----------------------------------------------------------------------------
# 11. CURRICULUM PROFILE (Sidebar)
# -----------------------------------------------------------------------------
def init_curriculum_defaults():
    st.session_state.setdefault("learning_mode", LEARNING_MODES[0])
    st.session_state.setdefault("school_board", SCHOOL_BOARDS[0])
    st.session_state.setdefault("school_class", "10")
    st.session_state.setdefault("school_stream", STREAMS_11_12[0])
    st.session_state.setdefault("competitive_exam", list(COMPETITIVE_EXAMS.keys())[0])
    st.session_state.setdefault("subject_choice", t("subject_any"))
    st.session_state.setdefault("ncert_chapter", CHAPTER_ANY)
    st.session_state.setdefault(
        "hindi_only_subjects",
        [s for s in DEFAULT_HINDI_ONLY_SUBJECTS],
    )


def _resolve_subject() -> str:
    subject = st.session_state.subject_choice
    return "" if subject == t("subject_any") else subject


def _resolve_chapter(subject: str) -> str | None:
    ch = st.session_state.get("ncert_chapter", CHAPTER_ANY)
    if not subject or ch == CHAPTER_ANY:
        return None
    return ch


def _is_hindi_only(subject: str) -> bool:
    if not subject:
        return False
    hindi_list = st.session_state.get("hindi_only_subjects", [])
    return any(
        subject.lower() == h.lower() or h.lower() in subject.lower()
        for h in hindi_list
    )


def get_student_profile() -> dict:
    init_curriculum_defaults()
    subject = _resolve_subject()
    chapter = _resolve_chapter(subject)
    hindi_only = _is_hindi_only(subject)
    lang = st.session_state.get("lang", "en")

    if st.session_state.learning_mode == LEARNING_MODES[1]:
        return pedagogy_profile(
            learning_mode="Competitive Exams",
            board="",
            class_num=None,
            stream=None,
            exam=st.session_state.competitive_exam,
            subject=subject,
            lang=lang,
            ncert_chapter=chapter,
            hindi_only=hindi_only,
        )

    stream = None
    if int(st.session_state.school_class) >= 11:
        stream = st.session_state.school_stream

    return pedagogy_profile(
        learning_mode="School (Class 1–12)",
        board=st.session_state.school_board,
        class_num=st.session_state.school_class,
        stream=stream,
        exam=None,
        subject=subject,
        lang=lang,
        ncert_chapter=chapter,
        hindi_only=hindi_only,
    )


def _sync_widget_value(widget_key: str, state_key: str):
    if widget_key in st.session_state:
        st.session_state[state_key] = st.session_state[widget_key]


def render_curriculum_controls(key_prefix: str = "sidebar", show_summary: bool = True):
    init_curriculum_defaults()
    st.subheader(t("curriculum_header"))

    mode = st.segmented_control(
        t("learning_mode"),
        LEARNING_MODES,
        default=st.session_state.learning_mode,
        key=f"{key_prefix}_learning_mode",
    )
    st.session_state.learning_mode = mode or st.session_state.learning_mode

    if st.session_state.learning_mode == LEARNING_MODES[0]:
        st.markdown(
            """
<div class="premium-card">
    <b>🏫 School Learning</b>
    <span>Choose your board, class, and subject to keep answers syllabus-aligned.</span>
</div>
            """,
            unsafe_allow_html=True,
        )
        st.selectbox(
            t("board_label"),
            SCHOOL_BOARDS,
            index=SCHOOL_BOARDS.index(st.session_state.school_board),
            key=f"{key_prefix}_school_board",
            on_change=_sync_widget_value,
            args=(f"{key_prefix}_school_board", "school_board"),
        )
        st.selectbox(
            t("class_label"),
            SCHOOL_CLASSES,
            index=SCHOOL_CLASSES.index(st.session_state.school_class),
            key=f"{key_prefix}_school_class",
            on_change=_sync_widget_value,
            args=(f"{key_prefix}_school_class", "school_class"),
        )
        if int(st.session_state.school_class) >= 11:
            st.selectbox(
                t("stream_label"),
                STREAMS_11_12,
                index=STREAMS_11_12.index(st.session_state.school_stream),
                key=f"{key_prefix}_school_stream",
                on_change=_sync_widget_value,
                args=(f"{key_prefix}_school_stream", "school_stream"),
            )
        subjects = [t("subject_any")] + subjects_for_school(st.session_state.school_class)
        if st.session_state.subject_choice not in subjects:
            st.session_state.subject_choice = t("subject_any")
        st.selectbox(
            t("subject_label"),
            subjects,
            index=subjects.index(st.session_state.subject_choice),
            key=f"{key_prefix}_subject_choice",
            on_change=_sync_widget_value,
            args=(f"{key_prefix}_subject_choice", "subject_choice"),
        )

        subject = _resolve_subject()
        st.markdown(f"**{t('chapter_header')}**")
        if subject and chapter_available(st.session_state.school_class, subject):
            chapters = ncert_chapters_for(st.session_state.school_class, subject)
            if st.session_state.ncert_chapter not in chapters:
                st.session_state.ncert_chapter = CHAPTER_ANY
            st.selectbox(
                t("chapter_label"),
                chapters,
                index=chapters.index(st.session_state.ncert_chapter),
                key=f"{key_prefix}_ncert_chapter",
                on_change=_sync_widget_value,
                args=(f"{key_prefix}_ncert_chapter", "ncert_chapter"),
            )
            st.caption(t("chapter_hint"))
        else:
            st.caption(t("chapter_na") if not subject else t("chapter_hint"))
    else:
        st.markdown(
            """
<div class="premium-card">
    <b>🏆 Competitive Exams</b>
    <span>Select your exam and target subject for focused preparation.</span>
</div>
            """,
            unsafe_allow_html=True,
        )
        st.selectbox(
            t("exam_label"),
            list(COMPETITIVE_EXAMS.keys()),
            index=list(COMPETITIVE_EXAMS.keys()).index(st.session_state.competitive_exam),
            key=f"{key_prefix}_competitive_exam",
            on_change=_sync_widget_value,
            args=(f"{key_prefix}_competitive_exam", "competitive_exam"),
        )
        exam_meta = COMPETITIVE_EXAMS[st.session_state.competitive_exam]
        subjects = [t("subject_any")] + exam_meta["subjects"]
        if st.session_state.subject_choice not in subjects:
            st.session_state.subject_choice = t("subject_any")
        st.selectbox(
            t("subject_label"),
            subjects,
            index=subjects.index(st.session_state.subject_choice),
            key=f"{key_prefix}_subject_choice",
            on_change=_sync_widget_value,
            args=(f"{key_prefix}_subject_choice", "subject_choice"),
        )

    st.divider()
    st.markdown(f"**{t('hindi_mode_header')}**")
    st.caption(t("hindi_mode_help"))
    all_subjects = sorted(set(
        subjects_for_school(st.session_state.get("school_class", "10"))
        + [s for ex in COMPETITIVE_EXAMS.values() for s in ex["subjects"]]
        + DEFAULT_HINDI_ONLY_SUBJECTS
    ))
    st.multiselect(
        t("hindi_subjects_label"),
        options=all_subjects,
        default=st.session_state.hindi_only_subjects,
        key=f"{key_prefix}_hindi_only_subjects",
        on_change=_sync_widget_value,
        args=(f"{key_prefix}_hindi_only_subjects", "hindi_only_subjects"),
    )

    profile = get_student_profile()
    if show_summary:
        if profile.get("hindi_only"):
            st.success("🇮🇳 Hindi-only mode active for this subject")
        st.info(f"**{t('active_profile')}:** {profile['display_label']}")
        st.caption(t("guardrails_note"))
    return profile


def render_curriculum_sidebar():
    return render_curriculum_controls("sidebar", show_summary=True)


# -----------------------------------------------------------------------------
# 12. LANGUAGE SELECTOR (Sidebar)
# -----------------------------------------------------------------------------
with st.sidebar:
    render_sidebar_brand()
    lang_choice = st.radio(
        t("language_label"),
        options=["en", "hi"],
        format_func=lambda x: "English" if x == "en" else "हिन्दी",
        index=0 if st.session_state.get("lang", "en") == "en" else 1,
        horizontal=True,
    )
    if lang_choice != st.session_state.get("lang", "en"):
        st.session_state.lang = lang_choice
        st.rerun()

# -----------------------------------------------------------------------------
# 13. AUTH UI 
# -----------------------------------------------------------------------------
def auth_ui():
    if "auth_view" not in st.session_state:
        st.session_state.auth_view = "login"   

    view = st.session_state.auth_view

    st.markdown(
        """
<div class="auth-card">
    <div class="premium-kicker">Secure AI Learning Workspace</div>
    <h1>Intellect Engine</h1>
    <p>Login to access your premium syllabus-aligned tutor, semantic vault, and learning analytics.</p>
</div>
        """,
        unsafe_allow_html=True,
    )

    if view == "register":
        st.subheader(t("register_title"))
        email    = st.text_input(t("email"), key="reg_email")
        password = st.text_input(t("password"), type="password", key="reg_pass")
        confirm  = st.text_input(t("confirm_password"), type="password", key="reg_confirm")

        if st.button(t("register_btn"), type="primary"):
            if not email or not password:
                st.warning(t("fill_both"))
            elif password != confirm:
                st.warning(t("password_mismatch"))
            elif len(password) < 6:
                st.warning(t("password_short"))
            else:
                with st.spinner(t("registering")):
                    try:
                        register_user(email, password)
                        st.success(t("register_success"))
                    except Exception as exc:
                        st.error(t("register_failed", e=exc))

        if st.button(t("go_login")):
            st.session_state.auth_view = "login"
            st.rerun()

    elif view == "reset":
        st.subheader("🔑 " + t("forgot_password"))
        reset_email = st.text_input(t("reset_email_label"))

        if st.button(t("send_reset"), type="primary"):
            if not reset_email:
                st.warning(t("fill_both"))
            else:
                try:
                    reset_password(reset_email)
                    st.success(t("reset_sent"))
                except Exception:
                    st.error(t("reset_failed"))

        if st.button(t("back_to_login")):
            st.session_state.auth_view = "login"
            st.rerun()

    else:
        st.subheader(t("login_title"))
        email    = st.text_input(t("email"), key="login_email")
        password = st.text_input(t("password"), type="password", key="login_pass")

        if st.button(t("login_btn"), type="primary"):
            if not email or not password:
                st.warning(t("fill_both"))
            else:
                with st.spinner(t("connecting")):
                    try:
                        res = authenticate_user(email, password)
                        st.session_state.user         = res.user
                        st.session_state.chat_history = []
                        st.rerun()
                    except Exception as exc:
                        logger.exception("Login failed")
                        st.error(t("login_failed"))
                        with st.expander("Technical details"):
                            st.code(str(exc))

        col1, col2 = st.columns(2)
        with col1:
            if st.button(t("go_register")):
                st.session_state.auth_view = "register"
                st.rerun()
        with col2:
            if st.button(t("forgot_password")):
                st.session_state.auth_view = "reset"
                st.rerun()

if "user" not in st.session_state:
    auth_ui()
    st.stop()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# -----------------------------------------------------------------------------
# 14. SIDEBAR HISTORY & SETTINGS
# -----------------------------------------------------------------------------
with st.sidebar:
    active_profile = render_curriculum_sidebar()
    st.divider()
    st.subheader(t("sidebar_settings"))
    st.caption(f"{t('session')}: {st.session_state.user.email}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button(t("new_chat"), use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
    with col2:
        if st.button(t("logout"), use_container_width=True, type="secondary"):
            del st.session_state.user
            st.session_state.chat_history = []
            st.rerun()

    st.divider()
    st.subheader(t("sidebar_history"))

    db_history = fetch_history(st.session_state.user.id, limit=20)

    if db_history:
        if st.button(t("delete_history"), type="secondary", use_container_width=True):
            st.session_state.confirm_delete_all = True

        if st.session_state.get("confirm_delete_all"):
            st.warning(t("delete_confirm"))
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Yes", use_container_width=True):
                    try:
                        delete_all_history(st.session_state.user.id)
                        st.session_state.confirm_delete_all = False
                        st.success(t("delete_done"))
                        st.rerun()
                    except Exception as exc:
                        st.error(t("delete_failed", e=exc))
            with c2:
                if st.button("❌ No", use_container_width=True):
                    st.session_state.confirm_delete_all = False
                    st.rerun()

        for item in db_history:
            ts = item["created_at"][:16].replace("T", " ")
            with st.expander(f"🕐 {ts} — {item['engine_used']}", expanded=False):
                st.markdown(f"**{t('you')}:** {item['prompt']}")
                st.markdown(f"**{t('assistant')}:** {item['ai_response']}")
                if st.button("🗑️ Delete", key=f"del_{item['id']}"):
                    try:
                        delete_single_log(item["id"])
                        st.rerun()
                    except Exception as exc:
                        st.error(t("delete_failed", e=exc))
    else:
        st.caption(t("no_history"))

# -----------------------------------------------------------------------------
# 15. MAIN APP EXECUTION
# -----------------------------------------------------------------------------
tab_chat, tab_dashboard = st.tabs([t("tab_chat"), t("tab_dashboard")])

with tab_dashboard:
    render_dashboard(
        supabase_client,
        st.session_state.user.id,
        st.session_state.user.email,
        t,
    )

with tab_chat:
    profile_banner = get_student_profile()
    render_hero(profile_banner)
    with st.expander("🎓 Change class, subject, or exam", expanded=False):
        render_curriculum_controls("main", show_summary=True)
        profile_banner = get_student_profile()
    if profile_banner.get("hindi_only"):
        st.caption("🇮🇳 " + t("hindi_mode_header"))

    for turn in st.session_state.chat_history:
        with st.chat_message("user"):
            st.markdown(turn["user"])
            if turn.get("file_name"):
                st.caption(t("file_note", name=turn["file_name"]))
        with st.chat_message("assistant"):
            render_mermaid_blocks(turn["assistant"])
            st.caption(f"— {turn['provider']}")

    uploaded_file = st.file_uploader(
        t("upload_label"),
        type=["txt", "csv", "json", "pdf", "png", "jpg", "jpeg", "webp"],
        label_visibility="visible",
    )

    query = st.chat_input(t("query_label"))

    if query:
        profile = get_student_profile()
        base_query = f"[{uploaded_file.name}] {query}" if uploaded_file else query
        clean_query = cache_key(base_query, profile)

        with st.chat_message("user"):
            st.markdown(query)
            if uploaded_file:
                st.caption(t("file_note", name=uploaded_file.name))

        cached_answer = check_cache(clean_query)
        if cached_answer:
            with st.chat_message("assistant"):
                render_mermaid_blocks(cached_answer)
                st.caption("— ⚡ Loaded from Cache (Free)")

            st.session_state.chat_history.append({
                "user":      query,
                "assistant": cached_answer,
                "provider":  "Cache Hit",
                "file_name": uploaded_file.name if uploaded_file else None,
            })
            log_to_database(
                user_id=st.session_state.user.id,
                prompt=clean_query,
                response=cached_answer,
                engine="Cache Hit",
                profile=profile,
            )
            st.stop()

        # PHASE 2: Semantic Q→A from vault (rephrased questions OK; skips API if strong match)
        if not uploaded_file:
            with st.spinner(t("vault_searching")):
                vault_hit = lookup_vault_answer(
                    query, profile, supabase_client, gemini_client
                )
            if vault_hit:
                with st.chat_message("assistant"):
                    render_mermaid_blocks(vault_hit.answer)
                    st.caption(f"— {vault_hit.provider_label}")

                st.session_state.chat_history.append({
                    "user":      query,
                    "assistant": vault_hit.answer,
                    "provider":  vault_hit.provider_label,
                    "file_name": None,
                })
                log_to_database(
                    user_id=st.session_state.user.id,
                    prompt=clean_query,
                    response=vault_hit.answer,
                    engine=vault_hit.provider_label,
                    profile=profile,
                )
                st.stop()

        file_content, file_mime, file_error = None, None, None
        file_name = None
        if uploaded_file:
            file_content, file_mime, file_error = extract_file_content(uploaded_file)
            if file_error:
                st.error(file_error)
                st.stop()
            file_name = uploaded_file.name

        with st.chat_message("assistant"):
            placeholder = st.empty()
            try:
                answer, provider = stream_intelligence(
                    user_prompt=query,
                    file_content=file_content,
                    file_mime=file_mime,
                    history=st.session_state.chat_history,
                    output_placeholder=placeholder,
                    profile=profile,
                )
                placeholder.empty()
                render_mermaid_blocks(answer)
                st.caption(f"— {provider}")

                st.session_state.chat_history.append({
                    "user":      query,
                    "assistant": answer,
                    "provider":  provider,
                    "file_name": file_name,
                })

                log_to_database(
                    user_id=st.session_state.user.id,
                    prompt=clean_query,
                    response=answer,
                    engine=provider,
                    profile=profile,
                )

            except RuntimeError as err:
                st.error(str(err))

    if st.session_state.chat_history:
        if st.button(t("clear_chat"), type="secondary"):
            st.session_state.chat_history = []
            st.rerun()