"""
Parent / teacher analytics dashboard from Supabase ai_logs.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st


def _parse_ts(row: dict) -> datetime | None:
    raw = row.get("created_at")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _extract_subject(row: dict) -> str:
    for key in ("subject", "profile_label", "level", "exam"):
        val = row.get(key)
        if val and str(val).strip():
            if key == "profile_label" and "·" in str(val):
                parts = [p.strip() for p in str(val).split("·")]
                if len(parts) >= 2:
                    return parts[-1]
            return str(val)
    prompt = row.get("prompt", "")
    if "]" in prompt:
        return prompt.split("]")[0].replace("[", "").strip()[:40]
    return "General"


def fetch_dashboard_logs(supabase, user_id: str, limit: int = 500) -> list[dict]:
    cols = (
        "id, prompt, ai_response, engine_used, created_at, "
        "learning_mode, board, level, subject, exam, class_num, stream, profile_label"
    )
    try:
        res = (
            supabase.table("ai_logs")
            .select(cols)
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception:
        try:
            res = (
                supabase.table("ai_logs")
                .select("id, prompt, ai_response, engine_used, created_at")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []
        except Exception:
            return []


def build_stats(logs: list[dict]) -> dict:
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total = len(logs)
    week_count = 0
    today_count = 0
    engines: Counter = Counter()
    subjects: Counter = Counter()
    boards: Counter = Counter()
    daily: Counter = Counter()

    for row in logs:
        engines[row.get("engine_used") or "Unknown"] += 1
        subjects[_extract_subject(row)] += 1
        board = row.get("board") or row.get("exam") or "—"
        boards[str(board)] += 1

        ts = _parse_ts(row)
        if ts:
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= week_ago:
                week_count += 1
            if ts >= today_start:
                today_count += 1
            daily[ts.strftime("%Y-%m-%d")] += 1

    return {
        "total": total,
        "week_count": week_count,
        "today_count": today_count,
        "engines": engines,
        "subjects": subjects,
        "boards": boards,
        "daily": daily,
    }


def render_dashboard(supabase, user_id: str, user_email: str, t):
    st.header(t("dashboard_title"))
    st.caption(t("dashboard_subtitle", email=user_email))

    logs = fetch_dashboard_logs(supabase, user_id)
    if not logs:
        st.info(t("dashboard_empty"))
        return

    stats = build_stats(logs)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("metric_total"), stats["total"])
    c2.metric(t("metric_week"), stats["week_count"])
    c3.metric(t("metric_today"), stats["today_count"])
    c4.metric(t("metric_engines"), len(stats["engines"]))

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader(t("chart_engines"))
        eng_df = pd.DataFrame(
            [{"Engine": k, "Queries": v} for k, v in stats["engines"].most_common()]
        )
        if not eng_df.empty:
            st.bar_chart(eng_df.set_index("Engine"))

    with right:
        st.subheader(t("chart_subjects"))
        sub_df = pd.DataFrame(
            [{"Subject": k, "Queries": v} for k, v in stats["subjects"].most_common(8)]
        )
        if not sub_df.empty:
            st.bar_chart(sub_df.set_index("Subject"))

    st.subheader(t("chart_activity"))
    if stats["daily"]:
        daily_df = pd.DataFrame(
            [{"Date": d, "Queries": c} for d, c in sorted(stats["daily"].items())]
        )
        st.line_chart(daily_df.set_index("Date"))
    else:
        st.caption(t("no_activity_data"))

    st.subheader(t("recent_queries"))
    rows = []
    for item in logs[:25]:
        ts = item.get("created_at", "")[:16].replace("T", " ")
        prompt = item.get("prompt", "")
        if len(prompt) > 120:
            prompt = prompt[:117] + "..."
        rows.append({
            t("col_time"): ts,
            t("col_subject"): _extract_subject(item),
            t("col_engine"): item.get("engine_used", "—"),
            t("col_question"): prompt,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with st.expander(t("insights_expander")):
        top_subject = stats["subjects"].most_common(1)
        top_engine = stats["engines"].most_common(1)
        if top_subject:
            st.write(t("insight_top_subject", subject=top_subject[0][0], count=top_subject[0][1]))
        if top_engine:
            st.write(t("insight_top_engine", engine=top_engine[0][0], count=top_engine[0][1]))
        if stats["week_count"] == 0 and stats["total"] > 0:
            st.write(t("insight_inactive_week"))
