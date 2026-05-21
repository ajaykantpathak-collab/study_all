import streamlit as st
import time
import logging
import base64
from supabase import create_client
from google import genai
from google.genai import types as genai_types
import openai
import anthropic

# -----------------------------------------------------------------------------
# 1. LOGGING SETUP & CONSTANTS
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

MAX_CONTEXT_TURNS   = 10      # Max conversation turns sent to AI
MAX_TEXT_FILE_CHARS = 12_000  # Truncate large text files before sending
MAX_FILE_MB         = 5       # Reject files larger than this

# -----------------------------------------------------------------------------
# 2. LANGUAGE STRINGS (English + Hindi)
# -----------------------------------------------------------------------------
LANG = {
    "en": {
        "login_title":        "🔐 v2Secure System Login",
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
        "app_title":          "🧠 Intellect Engine (Multi-Node RAG)",
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
        "login_title":        "🔐 सुरक्षित सिस्टम लॉगिन",
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
        "app_title":          "🧠 बुद्धि इंजन (मल्टी-नोड RAG)",
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

# -----------------------------------------------------------------------------
# 3. INFRASTRUCTURE & CREDENTIALS
# -----------------------------------------------------------------------------
@st.cache_resource
def init_clients():
    supabase_url = "https://pyeddkjbcfzfcajcqhnj.supabase.co"
    supabase = create_client(supabase_url, st.secrets["SUPABASE_KEY"])
    gemini   = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    oai      = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    claude   = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    return supabase, gemini, oai, claude

supabase_client, gemini_client, openai_client, anthropic_client = init_clients()

# -----------------------------------------------------------------------------
# 4. AUTH HELPERS
# -----------------------------------------------------------------------------
def authenticate_user(email: str, password: str, max_retries: int = 3):
    last_exc = None
    for attempt in range(max_retries):
        try:
            return supabase_client.auth.sign_in_with_password(
                {"email": email, "password": password}
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

def fetch_rag_context(prompt: str) -> str:
    clean_prompt = prompt.strip()
    try:
        embed_res = gemini_client.models.embed_content(
            model='text-embedding-004',
            contents=clean_prompt
        )
        query_vector = embed_res.embeddings[0].values
        
        docs = supabase_client.rpc("match_documents", {
            "query_embedding": query_vector,
            "match_threshold": 0.7, 
            "match_count": 3
        }).execute()
        
        if docs.data:
            return "\n\n".join([doc["content"] for doc in docs.data])
    except Exception as e:
        logger.warning("RAG Retrieval failed: %s", e)
    return ""

def log_to_database(user_id: str, prompt: str, response: str, engine: str):
    try:
        supabase_client.table("ai_logs").insert({
            "user_id":     user_id,
            "prompt":      prompt.strip(),
            "ai_response": response,
            "engine_used": engine,
        }).execute()
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
# 9. TRIPLE-THREAT AI ROUTER (With RAG + Diagram Instructions)
# -----------------------------------------------------------------------------
def stream_intelligence(user_prompt, file_content, file_mime, history, output_placeholder):
    trimmed_history, was_trimmed = safe_history(history)
    if was_trimmed:
        st.caption(t("context_trimmed"))

    rag_context = fetch_rag_context(user_prompt)
    
    system_instruction = f"""
    You are an expert engineering tutor. Answer the user's question clearly. 
    Use the following contextual documents to inform your answer if they are relevant:
    
    CONTEXT:
    {rag_context}
    
    CRITICAL INSTRUCTIONS:
    1. Always include at least one concrete example.
    2. If explaining a complex, structural, or visual concept, you MUST use Markdown tables or ASCII art to create a simple text-based diagram for the user.
    """

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
                    temperature=0.0,
                    system_instruction=system_instruction
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
            max_tokens=1000,
            temperature=0.0,
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
            temperature=0.0,
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
# 10. LANGUAGE SELECTOR (Sidebar)
# -----------------------------------------------------------------------------
with st.sidebar:
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
# 11. AUTH UI 
# -----------------------------------------------------------------------------
def auth_ui():
    if "auth_view" not in st.session_state:
        st.session_state.auth_view = "login"   

    view = st.session_state.auth_view

    if view == "register":
        st.title(t("register_title"))
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
        st.title("🔑 " + t("forgot_password"))
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
        st.title(t("login_title"))
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
                    except Exception:
                        st.error(t("login_failed"))

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
# 12. SIDEBAR HISTORY & SETTINGS
# -----------------------------------------------------------------------------
with st.sidebar:
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
# 13. MAIN APP EXECUTION
# -----------------------------------------------------------------------------
st.title(t("app_title"))

with st.expander(t("diagram_expander"), expanded=False):
    st.markdown("""
```mermaid
flowchart TD
    A([👤 User Query]) --> B{🗄️ Check DB Cache}
    B -->|Found Match| C([⚡ Instant Free Response])
    B -->|No Match| D[🔍 RAG Vector Search]
    D --> E[🚦 Triple-Threat AI Router]
    E --> F[Gemini 2.5 Flash]
    F -->|Fails| G[Claude Haiku 4.5]
    G -->|Fails| H[GPT-4o-mini]
    F -->|Success| I([✅ Response to User])
    G -->|Success| I
    H -->|Success| I
    I --> J[(💾 Save to Supabase Cache)]
    
    style A fill:#4A90D9,color:#fff
    style B fill:#0F9D58,color:#fff
    style C fill:#0F9D58,color:#fff
    style D fill:#7B68EE,color:#fff
    style E fill:#7B68EE,color:#fff
    style I fill:#4A90D9,color:#fff
    style J fill:#0F9D58,color:#fff
                """)
st.divider()

for turn in st.session_state.chat_history:
    with st.chat_message("user"):
        st.markdown(turn["user"])
        if turn.get("file_name"):
            st.caption(t("file_note", name=turn["file_name"]))
    with st.chat_message("assistant"):
        st.markdown(turn["assistant"])
        st.caption(f"— {turn['provider']}")

uploaded_file = st.file_uploader(
    t("upload_label"),
    type=["txt", "csv", "json", "pdf", "png", "jpg", "jpeg", "webp"],
    label_visibility="visible",
)

query = st.chat_input(t("query_label"))

if query:
    clean_query = f"[{uploaded_file.name}] {query}" if uploaded_file else query
    
    with st.chat_message("user"):
        st.markdown(query)
        if uploaded_file:
            st.caption(t("file_note", name=uploaded_file.name))

    # PHASE 1: CACHE
    cached_answer = check_cache(clean_query)
    if cached_answer:
        with st.chat_message("assistant"):
            st.markdown(cached_answer)
            st.caption("— ⚡ Loaded from Cache (Free)")
            
        st.session_state.chat_history.append({
            "user":      query,
            "assistant": cached_answer,
            "provider":  "Cache Hit",
            "file_name": uploaded_file.name if uploaded_file else None,
        })
        st.stop()

    # PHASE 2 & 3: RAG + GENERATION
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
            )
            st.caption(f"— {provider}")

            st.session_state.chat_history.append({
                "user":      query,
                "assistant": answer,
                "provider":  provider,
                "file_name": file_name,
            })

            # PHASE 4: SAVE CACHE
            log_to_database(
                user_id=st.session_state.user.id,
                prompt=clean_query,
                response=answer,
                engine=provider,
            )

        except RuntimeError as err:
            st.error(str(err))

if st.session_state.chat_history:
    if st.button(t("clear_chat"), type="secondary"):
        st.session_state.chat_history = []
        st.rerun()