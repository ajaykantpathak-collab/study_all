"""
Curriculum taxonomy and pedagogy profiles for the Intellect Engine edtech app.
"""

from __future__ import annotations

# ── School boards ─────────────────────────────────────────────────────────────
SCHOOL_BOARDS = ["CBSE", "ICSE", "International (IGCSE / IB / Cambridge)"]

SCHOOL_CLASSES = [str(i) for i in range(1, 13)]

STREAMS_11_12 = [
    "Science — PCM (Physics, Chemistry, Maths)",
    "Science — PCB (Physics, Chemistry, Biology)",
    "Commerce",
    "Humanities / Arts",
]

SUBJECTS_BY_CLASS: dict[str, list[str]] = {
    "1-5": [
        "Mathematics", "English", "Hindi", "EVS / Science", "Social Studies",
        "Computer Science", "General Knowledge",
    ],
    "6-8": [
        "Mathematics", "Science", "English", "Hindi", "Social Science",
        "Sanskrit", "Computer Science", "General Knowledge",
    ],
    "9-10": [
        "Mathematics", "Science", "English", "Hindi", "Social Science",
        "Information Technology", "Economics (optional)",
    ],
    "11-12": [
        "Physics", "Chemistry", "Mathematics", "Biology",
        "Accountancy", "Business Studies", "Economics",
        "History", "Political Science", "Geography", "English",
        "Computer Science", "Informatics Practices",
    ],
}

# ── Competitive exams ─────────────────────────────────────────────────────────
COMPETITIVE_EXAMS: dict[str, dict] = {
    "JEE (Mains & Advanced)": {
        "board": "Competitive/Professional",
        "level": "JEE Mains & Advanced",
        "subjects": ["Physics", "Chemistry", "Mathematics"],
        "style": "multi-step derivations, NCERT + HC Verma level rigour, previous-year pattern",
    },
    "NEET (UG Medical)": {
        "board": "Competitive/Professional",
        "level": "NEET",
        "subjects": ["Physics", "Chemistry", "Biology (Botany & Zoology)"],
        "style": "NCERT-line facts, clinical applications, assertion-reason and MCQ drill",
    },
    "CAT (MBA)": {
        "board": "Competitive/Professional",
        "level": "CAT",
        "subjects": ["Quantitative Aptitude", "Verbal Ability", "Data Interpretation & LR"],
        "style": "speed tricks, set-based logic, no unnecessary theory",
    },
    "MAT (Management)": {
        "board": "Competitive/Professional",
        "level": "MAT",
        "subjects": ["Quantitative Aptitude", "Language Comprehension", "Data Analysis"],
        "style": "concise MCQ-oriented explanations",
    },
    "CA (Chartered Accountancy)": {
        "board": "Competitive/Professional",
        "level": "CA Foundation / Inter",
        "subjects": ["Accounting", "Law", "Taxation", "Audit", "Economics"],
        "style": "Indian standards, section references where known, worked numericals",
    },
    "CS (Company Secretary)": {
        "board": "Competitive/Professional",
        "level": "CS Executive",
        "subjects": ["Corporate Law", "Governance", "Tax", "Capital Markets"],
        "style": "Companies Act framing, bullet compliance points",
    },
    "Bank PO / IBPS": {
        "board": "Competitive/Professional",
        "level": "Bank PO",
        "subjects": ["Quantitative Aptitude", "Reasoning", "English", "Banking Awareness"],
        "style": "shortcut methods, exam-time efficiency",
    },
    "SSC (CGL / CHSL / MTS)": {
        "board": "Competitive/Professional",
        "level": "SSC",
        "subjects": ["Quantitative Aptitude", "Reasoning", "English", "General Awareness"],
        "style": "straightforward steps, government-exam brevity",
    },
    "IT / GATE (Computer Science)": {
        "board": "Competitive/Professional",
        "level": "GATE CS / IT",
        "subjects": [
            "Algorithms", "Data Structures", "Operating Systems",
            "DBMS", "Computer Networks", "Theory of Computation",
        ],
        "style": "formal definitions, complexity analysis, standard textbook references",
    },
}

LEARNING_MODES = ["School (Class 1–12)", "Competitive Exams"]


def class_band(class_num: str) -> str:
    n = int(class_num)
    if n <= 5:
        return "1-5"
    if n <= 8:
        return "6-8"
    if n <= 10:
        return "9-10"
    return "11-12"


def subjects_for_school(class_num: str) -> list[str]:
    return SUBJECTS_BY_CLASS[class_band(class_num)]


def pedagogy_profile(
    *,
    learning_mode: str,
    board: str,
    class_num: str | None,
    stream: str | None,
    exam: str | None,
    subject: str,
    lang: str,
    ncert_chapter: str | None = None,
    hindi_only: bool = False,
) -> dict:
    """Return RAG filters + tone rules for the active student profile."""
    if learning_mode == "Competitive Exams" and exam:
        meta = COMPETITIVE_EXAMS[exam]
        chapter_note = f" · {ncert_chapter}" if ncert_chapter else ""
        return {
            "display_label": f"{exam} · {subject or 'General'}{chapter_note}",
            "rag_board": meta["board"],
            "rag_level": meta["level"],
            "rag_subject": subject or None,
            "class_num": None,
            "stream": None,
            "exam": exam,
            "ncert_chapter": ncert_chapter,
            "hindi_only": hindi_only,
            "tone": _competitive_tone(exam, meta["style"]),
            "vocab": "exam-oriented; precise terminology",
            "depth": "exam-ready with shortcuts only when standard",
            "diagrams": "flowcharts, reaction schemes, FBDs, logic trees as Mermaid",
        }

    cls = class_num or "10"
    band = class_band(cls)
    stream_note = f", Stream: {stream}" if stream and int(cls) >= 11 else ""
    chapter_note = f" · {ncert_chapter}" if ncert_chapter else ""
    return {
        "display_label": f"{board} · Class {cls}{stream_note} · {subject or 'General'}{chapter_note}",
        "rag_board": _board_to_rag(board),
        "rag_level": f"Class {cls}",
        "rag_subject": subject or None,
        "class_num": cls,
        "stream": stream,
        "exam": None,
        "ncert_chapter": ncert_chapter,
        "hindi_only": hindi_only,
        "tone": _school_tone(cls, board),
        "vocab": _school_vocab(cls),
        "depth": _school_depth(cls, band),
        "diagrams": _school_diagrams(cls, band),
    }


def _board_to_rag(board: str) -> str:
    if board.startswith("CBSE"):
        return "CBSE"
    if board.startswith("ICSE"):
        return "ICSE"
    if "International" in board:
        return "International"
    return board


def _school_tone(cls: str, board: str) -> str:
    n = int(cls)
    if n <= 3:
        return "warm, playful teacher; very short sentences; relate to daily life"
    if n <= 5:
        return "friendly primary teacher; simple analogies; encourage curiosity"
    if n <= 8:
        return "patient middle-school teacher; build intuition before formulas"
    if n <= 10:
        return f"focused {board} board-exam tutor; NCERT-aligned; mark-scheme aware"
    return f"senior secondary {board} tutor; rigorous but clear; board + competitive foundation"


def _school_vocab(cls: str) -> str:
    n = int(cls)
    if n <= 3:
        return "very simple words only; avoid jargon"
    if n <= 5:
        return "simple; define every new term in one line"
    if n <= 8:
        return "grade-appropriate; define technical terms on first use"
    if n <= 10:
        return "standard textbook vocabulary for Classes 9–10"
    return "advanced textbook vocabulary; precise scientific terms"


def _school_depth(cls: str, band: str) -> str:
    n = int(cls)
    if band == "1-5":
        return "short answers; 1 example; no heavy algebra"
    if band == "6-8":
        return "step-by-step; connect concepts; light exam tips"
    if band == "9-10":
        return "board-pattern answers; labelled diagrams; common mistakes"
    return "detailed derivations where needed; numericals with units; exam traps"


def _school_diagrams(cls: str, band: str) -> str:
    if band in ("1-5", "6-8"):
        return "simple ASCII or Mermaid: number lines, place value, life cycles, maps"
    return "Mermaid flowcharts, labeled structures, graphs; ASCII geometry when quick"


def _competitive_tone(exam: str, style: str) -> str:
    return f"expert {exam} coach — {style}"


def build_system_instruction(
    profile: dict,
    rag_context: str,
    lang: str,
) -> str:
    if profile.get("hindi_only"):
        lang_rule = (
            "MANDATORY: Write the ENTIRE answer in Hindi (Devanagari script) only. "
            "Use English only for standard symbols (H2O, sin θ, DNA) and proper nouns. "
            "Section headings, steps, diagrams labels, and practice questions must be in Hindi."
        )
    elif lang == "hi":
        lang_rule = (
            "Respond in Hindi (Devanagari) with key terms in English where standard."
        )
    else:
        lang_rule = "Respond in clear Indian English suitable for Indian students."

    chapter_rule = ""
    ch = profile.get("ncert_chapter")
    if ch:
        chapter_rule = (
            f"\n- **NCERT focus:** Restrict explanations to NCERT chapter **「{ch}」** "
            f"for {profile.get('rag_subject') or 'the selected subject'}. "
            "Do not jump to out-of-syllabus topics unless the student explicitly asks."
        )

    context_block = rag_context.strip() if rag_context.strip() else (
        "No verified vault excerpts matched this query. "
        "Use only widely accepted syllabus facts for the profile below. "
        "Do NOT invent chapter names, page numbers, or statistics."
    )

    return f"""You are **Intellect Engine**, a strict, syllabus-aligned tutor for Indian students.

## Active student profile
- **Profile:** {profile["display_label"]}
- **Tone:** {profile["tone"]}
- **Vocabulary:** {profile["vocab"]}
- **Depth:** {profile["depth"]}
- **Language:** {lang_rule}{chapter_rule}

## Verified reference material (RAG vault)
Treat the block below as the ONLY authoritative source when it contains relevant content.
If it is empty or irrelevant, answer from standard curriculum knowledge for this profile ONLY,
and clearly label uncertainty.

--- BEGIN VAULT CONTEXT ---
{context_block}
--- END VAULT CONTEXT ---

## Anti-hallucination guardrails (MANDATORY)
1. **Source priority:** Vault context > standard syllabus facts > say you are unsure.
2. **Never fabricate:** No fake citations, page numbers, years, or "according to page X".
3. **Separate sections** when inferring beyond vault:
   - **From textbook/vault:** (facts grounded in context or standard syllabus)
   - **Reasoning / extension:** (logical steps — mark as inference)
4. If the question is outside the selected class/exam level, say so and offer to reframe.
5. For numericals: show **Given → Formula → Steps → Answer with units**.
6. Match explanation depth to **{profile["display_label"]}** — not university unless competitive exam demands it.

## Answer format (always follow)
1. **Quick answer** (1–2 lines appropriate to level)
2. **Step-by-step explanation**
3. **Example** (concrete, level-appropriate)
4. **Visual aid:** Include at least one **Mermaid** diagram OR ASCII diagram when the topic is structural, procedural, or geometric ({profile["diagrams"]}).
5. **Common mistakes** (1–3 bullets, if applicable)
6. **Practice check** — one short question for the student (do not solve it)

## Diagram rules
- Use fenced ```mermaid blocks for flowcharts, cycles, mind maps, timelines.
- Use markdown tables for comparisons (e.g., plant vs animal cell).
- Keep diagrams readable; label nodes; use simple English/Hindi labels per language setting.

## Quality bar
Answers must feel like the best teacher for **{profile["display_label"]}** — not generic ChatGPT.
Be encouraging but never sloppy with facts."""


def build_rag_query(prompt: str, profile: dict) -> str:
    parts = [
        profile.get("rag_board"),
        profile.get("rag_level"),
        profile.get("rag_subject"),
        profile.get("ncert_chapter"),
        prompt,
    ]
    return " | ".join(p for p in parts if p)


def filter_rag_docs(docs: list[dict], profile: dict) -> list[dict]:
    """Prefer documents matching board/level; fall back to all if none match."""
    if not docs:
        return []

    def matches(doc: dict) -> bool:
        meta = doc.get("metadata") or {}
        if profile.get("rag_board") and meta.get("board"):
            rb = profile["rag_board"].lower()
            mb = str(meta["board"]).lower()
            if rb not in mb and mb not in rb:
                return False
        if profile.get("rag_level") and meta.get("level"):
            rl = profile["rag_level"].lower()
            ml = str(meta["level"]).lower()
            if rl not in ml and ml not in rl:
                return False
        return True

    filtered = [d for d in docs if matches(d)]
    return filtered if filtered else docs


def cache_key(prompt: str, profile: dict) -> str:
    tag = profile["display_label"]
    hindi = "|hi-only" if profile.get("hindi_only") else ""
    return f"[{tag}{hindi}] {prompt.strip()}"


# Subjects commonly taught in Hindi medium
DEFAULT_HINDI_ONLY_SUBJECTS = ["Hindi", "Sanskrit", "हिन्दी"]
