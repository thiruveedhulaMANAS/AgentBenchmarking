"""
ui/components.py — AAVA Design System v2
Light mode only. Dark mode removed.
"""

import io
import re
import time
from collections import OrderedDict

import streamlit as st

from backend.workflow import (
    STATUS_CANCELLED,
    STATUS_DONE,
    STATUS_ERROR,
    STATUS_PENDING,
    STATUS_RUNNING,
)
from utils.file_helpers import parse_display_content


# ---------------------------------------------------------------------------
# Light palette — single fixed theme
# ---------------------------------------------------------------------------
def _palette(dark: bool = False) -> dict:
    """Always returns light-mode palette. `dark` parameter kept for API compatibility."""
    return dict(
        bg_card      = "#FFFFFF",
        bg_tint      = "#F8F6FF",
        bg_upload    = "#F4F1FD",
        border       = "#E2DCF8",
        border_m     = "#C8C0EC",
        t1           = "#1A1033",
        t2           = "#3D3260",
        t3           = "#7B6FA0",
        t4           = "#A89DC5",
        log_bg       = "#F8F6FF",
        code_bg      = "#F8F6FF",
        sel_bg       = "#FFFFFF",
        sel_text     = "#1A1033",
        exp_bg       = "#FFFFFF",
        row_even     = "#FFFFFF",
        row_alt      = "#FAFBFF",
        row_total    = "rgba(155,109,255,0.06)",
        pill_bg      = "#F0ECFF",
        hint_color   = "#7B6FA0",
        badge_bg     = "rgba(34,196,138,0.08)",
        badge_border = "rgba(34,196,138,0.25)",
    )


# ---------------------------------------------------------------------------
# Status config
# ---------------------------------------------------------------------------
_STATUS_ICON = {
    STATUS_PENDING:   ("⬜", "#A89DC5"),
    STATUS_RUNNING:   ("🔄", "#F59E0B"),
    STATUS_DONE:      ("✅", "#22C48A"),
    STATUS_ERROR:     ("❌", "#EF4444"),
    STATUS_CANCELLED: ("🚫", "#7B6FA0"),
}

def _status_bg(status, dark: bool = False):
    p = _palette()
    return {
        STATUS_PENDING:   p["bg_tint"],
        STATUS_RUNNING:   "#FFFBF0",
        STATUS_DONE:      "#F0FDF8",
        STATUS_ERROR:     "#FFF4F4",
        STATUS_CANCELLED: p["bg_tint"],
    }.get(status, p["bg_tint"])

def _status_border(status):
    return {
        STATUS_PENDING:   "#C8C0EC",
        STATUS_RUNNING:   "#F59E0B",
        STATUS_DONE:      "#22C48A",
        STATUS_ERROR:     "#EF4444",
        STATUS_CANCELLED: "#7B6FA0",
    }.get(status, "#C8C0EC")

_OP_LABELS = {
    "upload":        "Uploading files",
    "coverage_call": "Coverage Agent — Submit",
    "coverage_wait": "Coverage Agent — Response",
    "scoring_call":  "Scoring Agent — Dispatch",
    "scoring_jobs":  "Scoring Jobs — Running",
    "summary_call":  "Summary Agent",
    "collect":       "Collecting Results",
}

_RANK_COLORS = ["#9B6DFF", "#22C48A", "#1A73E8"]
_RANK_MEDALS = ["🥇", "🥈", "🥉"]


def _fmt_bytes(n: int) -> str:
    if n < 1024:          return f"{n} B"
    if n < 1024 * 1024:   return f"{n/1024:.1f} KB"
    return f"{n/1024/1024:.1f} MB"


# ---------------------------------------------------------------------------
# SHARED NOTEPAD FILE VIEW
# Renders file content exactly like opening in Notepad/TextEdit:
#  - monospace font (JetBrains Mono)
#  - line numbers in a gutter column
#  - hard tab stops preserved (tab → 4 spaces)
#  - no word-wrap by default (horizontal scroll for long lines)
#  - light grey gutter, white body, subtle border
# ---------------------------------------------------------------------------
def _render_notepad_view(content: str,
                         bg: str = "#FFFFFF",
                         text: str = "#1A1033",
                         border: str = "#E2DCF8",
                         max_height: str = "60vh",
                         min_height: str = "220px",
                         show_meta: bool = True,
                         show_line_numbers: bool = True,
                         filename: str = "") -> str:
    """Return an HTML string that renders `content` as a notepad-style view."""
    gutter_bg   = "#F4F1FD"
    gutter_text = "#A89DC5"
    lines = content.split("\n")
    line_count = len(lines)
    char_count = len(content)

    rows_html = ""
    for i, raw_line in enumerate(lines, start=1):
        safe = (raw_line
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\t", "    "))
        display = safe if safe.strip() else "&nbsp;"
        gutter_html = (
            f'<span style="'
            f'min-width:3.2em;width:3.2em;padding:0 0.6em 0 0.4em;'
            f'text-align:right;color:{gutter_text};'
            f'user-select:none;-webkit-user-select:none;'
            f'border-right:1px solid {border};'
            f'flex-shrink:0;font-size:0.78rem;line-height:1.55em;">'
            f'{i}</span>'
        ) if show_line_numbers else ""
        content_padding = "0 0.8em" if show_line_numbers else "0 1em"
        rows_html += (
            f'<div style="display:flex;min-height:1.55em;">'
            f'{gutter_html}'
            f'<span style="padding:{content_padding};white-space:pre;'
            f'line-height:1.55em;word-break:normal;overflow-x:visible;">{display}</span>'
            f'</div>'
        )

    meta_bar = ""
    if show_meta:
        name_part = f'<b style="color:{text};">{filename}</b>  · ' if filename else ""
        meta_bar = (
            f'<div style="'
            f'display:flex;align-items:center;gap:1.4rem;'
            f'background:{gutter_bg};'
            f'border:1px solid {border};border-bottom:none;'
            f'border-radius:10px 10px 0 0;'
            f'padding:0.45rem 1rem;'
            f'font-family:JetBrains Mono,monospace;font-size:0.75rem;color:{gutter_text};">'
            f'<span>📄 {name_part}'
            f'<span style="color:#9B6DFF;font-weight:700;">{line_count:,} lines</span></span>'
            f'<span>{char_count:,} chars</span>'
            f'<span>{_fmt_bytes(len(content.encode()))}</span>'
            f'</div>'
        )
        top_radius = "0 0 10px 10px"
    else:
        top_radius = "10px"

    body = (
        f'<div style="'
        f'background:{bg};'
        f'border:1px solid {border};'
        f'border-radius:{top_radius};'
        f'padding:0;'
        f'font-family:JetBrains Mono,monospace;'
        f'font-size:0.82rem;'
        f'line-height:1.55em;'
        f'color:{text};'
        f'overflow:auto;'
        f'max-height:{max_height};'
        f'min-height:{min_height};'
        f'box-shadow:0 2px 12px rgba(100,70,200,0.06);">'
        f'{rows_html}'
        f'</div>'
    )
    return meta_bar + body


# ---------------------------------------------------------------------------
# SHARED CSS — light mode only, uses CSS variables from _inject_css
# ---------------------------------------------------------------------------
def _component_css(dark: bool = False) -> str:
    p = _palette()
    return f"""
<style>
/* ── Upload cell typography ─── */
.upload-cell-title {{
    font-family:'Poppins',sans-serif;
    font-size:0.95rem; font-weight:700;
    letter-spacing:0.04em; color:#9B6DFF;
    text-transform:uppercase; margin-bottom:0.5rem;
    display:flex; align-items:center; gap:0.4rem;
    border-bottom:1px solid var(--border,#E2DCF8); padding-bottom:0.38rem;
}}
.upload-cell-ok {{
    font-family:'Nunito Sans',sans-serif;
    font-size:0.86rem; font-weight:600; color:#22C48A;
    margin-top:0.18rem; word-break:break-all;
    display:flex; align-items:center; gap:0.35rem; flex-wrap:wrap;
}}
.upload-cell-badge {{
    font-size:0.65rem;
    background:rgba(34,196,138,0.08);
    border:1px solid rgba(34,196,138,0.22);
    border-radius:4px; padding:1px 7px;
    color:#22C48A; flex-shrink:0; font-weight:700;
    letter-spacing:0.01em;
}}
.upload-cell-locked {{
    font-family:'Nunito Sans',sans-serif;
    font-size:0.84rem; font-weight:500; color:var(--t3,#7B6FA0);
    margin-top:0.18rem; word-break:break-all; font-style:italic;
}}
.upload-cell-draft {{
    font-family:'Nunito Sans',sans-serif;
    font-size:0.86rem; font-weight:600; color:var(--t2,#3D3260);
    margin-top:0.14rem; word-break:break-all;
    display:flex; align-items:center; gap:0.35rem; flex-wrap:wrap;
}}
.upload-hint {{
    font-family:'JetBrains Mono',monospace;
    font-size:0.70rem; color:var(--t4,#A89DC5); margin-top:0.38rem;
    letter-spacing:0.01em;
}}

/* ── Section label ── (mirrors app.py .section-label for inline use) */
.section-label {{
    font-family:'Poppins',sans-serif !important;
    font-size:0.95rem !important; font-weight:700 !important;
    letter-spacing:0.02em !important; color:#9B6DFF !important;
    border-left:3px solid #9B6DFF;
    padding-left:0.65rem; margin-bottom:1.1rem !important;
    text-transform:uppercase !important; line-height:1.4 !important;
    display:block !important;
}}
div[data-testid="stExpander"] {{
    background:#FFFFFF !important;
    border:1px solid var(--border,#E2DCF8) !important;
    border-radius:var(--r-md,14px) !important;
    box-shadow:0 1px 4px rgba(100,70,200,0.07) !important;
    overflow:hidden !important;
    margin-bottom:6px !important;
}}
div[data-testid="stExpander"] > div {{ background:#FFFFFF !important; }}
div[data-testid="stExpander"] summary {{
    background:#FFFFFF !important;
    padding:0.7rem 1.1rem !important;
    display:flex !important; align-items:center !important;
    gap:0.5rem !important; list-style:none !important;
    min-height:44px !important; cursor:pointer !important;
}}
div[data-testid="stExpander"] summary::-webkit-details-marker {{ display:none !important; }}
div[data-testid="stExpander"] summary::marker {{ display:none !important; }}
/* Hide ALL native Streamlit toggle icons */
div[data-testid="stExpander"] summary svg {{ display:none !important; }}
div[data-testid="stExpander"] summary [data-testid="stExpanderToggleIcon"] {{ display:none !important; }}
/* Single custom arrow */
div[data-testid="stExpander"] summary::before {{
    content:'▶' !important;
    font-size:0.60rem !important; color:var(--t3,#7B6FA0) !important;
    flex:0 0 auto !important; display:inline-block !important;
    line-height:1 !important; transition:color 0.18s !important;
}}
div[data-testid="stExpander"] details[open] summary::before,
details[open] div[data-testid="stExpander"] summary::before,
div[data-testid="stExpander"] > details[open] > summary::before {{
    content:'▼' !important; color:#9B6DFF !important;
}}
div[data-testid="stExpander"] summary > span,
div[data-testid="stExpander"] summary > p,
div[data-testid="stExpander"] summary span[data-testid="stExpanderToggleIcon"] {{
    color:#1A1033 !important;
    font-family:'Nunito Sans',sans-serif !important;
    font-size:0.92rem !important; font-weight:600 !important;
    background:transparent !important;
    flex:1 !important; min-width:0 !important;
    overflow:hidden !important; text-overflow:ellipsis !important;
    white-space:nowrap !important;
}}
div[data-testid="stExpanderDetails"],
div[data-testid="stExpanderDetails"] > div {{
    background:#FFFFFF !important;
    padding:0.4rem 0.9rem 0.9rem !important;
}}
div[data-testid="stExpander"] p,
div[data-testid="stExpander"] span:not(kbd) {{
    color:#1A1033 !important; background:transparent !important;
}}

/* ── Select box ─── */
div[data-testid="stSelectbox"] [data-baseweb="select"] > div:first-child {{
    background:#FFFFFF !important;
    border:1.5px solid var(--border-m,#C8C0EC) !important;
    border-radius:var(--r-sm,10px) !important;
    box-shadow:none !important; min-height:40px !important;
}}
div[data-testid="stSelectbox"] [data-baseweb="select"] span,
div[data-testid="stSelectbox"] [data-baseweb="select"] div[class*="singleValue"] {{
    color:#1A1033 !important; font-family:'Nunito Sans',sans-serif !important;
    font-size:0.90rem !important; font-weight:500 !important; background:transparent !important;
}}
[data-baseweb="popover"] > div, [data-baseweb="popover"] [data-baseweb="menu"] {{
    background:#FFFFFF !important;
    border:1.5px solid var(--border-m,#C8C0EC) !important;
    border-radius:var(--r-sm,10px) !important;
    box-shadow:0 8px 28px rgba(0,0,0,0.11) !important; overflow:hidden !important;
}}
[data-baseweb="menu"] li, [data-baseweb="option"], [role="option"] {{
    background:#FFFFFF !important; color:#1A1033 !important;
    font-family:'Nunito Sans',sans-serif !important;
    font-size:0.88rem !important; font-weight:500 !important;
    border-radius:6px !important; padding:0.42rem 0.75rem !important;
}}
[data-baseweb="menu"] li:hover, [data-baseweb="option"]:hover,
[role="option"][aria-selected="true"] {{
    background:rgba(155,109,255,0.09) !important; color:#9B6DFF !important;
}}

/* ── ✕ Remove buttons ─── */
div[data-testid="stButton"] > button,
div[data-testid="stButton"] > button:focus {{
    font-family:'Nunito Sans',sans-serif !important;
    font-size:0.78rem !important; font-weight:700 !important;
    border-radius:6px !important; transition:all 0.18s !important;
}}
div[data-testid="stButton"] > button[kind="secondaryFormSubmit"],
div[data-testid="stButton"] > button[kind="secondaryFormSubmit"]:focus {{
    background:#FFFFFF !important; background-color:#FFFFFF !important;
    background-image:none !important;
    border:1.5px solid var(--border-m,#C8C0EC) !important;
    color:var(--t2,#3D3260) !important; -webkit-text-fill-color:var(--t2,#3D3260) !important;
    font-size:0.78rem !important; font-weight:700 !important;
    border-radius:6px !important; padding:2px 8px !important;
    height:28px !important; min-height:28px !important;
    line-height:1 !important; box-shadow:none !important;
}}
div[data-testid="stButton"] > button[kind="secondaryFormSubmit"]:hover {{
    border-color:#EF4444 !important; color:#EF4444 !important;
    -webkit-text-fill-color:#EF4444 !important;
    background:#FFF0F0 !important; background-color:#FFF0F0 !important;
    background-image:none !important;
}}
</style>
"""



# ---------------------------------------------------------------------------
# TOP UPLOAD BAR
# ---------------------------------------------------------------------------

def render_top_upload_bar(page: str = "upload", dark: bool = False):
    p = _palette()
    st.markdown(_component_css(), unsafe_allow_html=True)

    files_locked = st.session_state.get("_files_locked", False)
    is_running   = (page == "running")

    col1, col2, col3 = st.columns([1, 1, 1], gap="small")

    def _draft_fileobj(name, data):
        buf = io.BytesIO(data); buf.name = name; buf.seek(0); return buf

    instruction_file = None
    input_file       = None
    output_files     = []

    # ── COL 1: Instruction ──────────────────────────────────────────────────
    with col1:
        st.markdown('<div class="upload-cell-title">📋 Agent Instruction File</div>', unsafe_allow_html=True)

        if is_running or files_locked:
            name = st.session_state.get("_instr_name") or "—"
            icon = "🔒" if is_running else "✓"
            st.markdown(f'<div class="upload-cell-locked">{icon} {name}</div>', unsafe_allow_html=True)
            # On running/locked: show nothing else — no uploader, no ok/draft rows, no hint
        else:
            instr_gen   = st.session_state.get("_instr_up_gen", 0)
            widget_file = st.file_uploader("instr", key=f"instr_up_{instr_gen}", accept_multiple_files=False, label_visibility="collapsed")
            if widget_file is not None:
                st.session_state["_draft_instr_bytes"] = widget_file.getvalue()
                st.session_state["_draft_instr_name"]  = widget_file.name
                instruction_file = widget_file
                size_badge = _fmt_bytes(len(widget_file.getvalue()))
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(f'<div class="upload-cell-ok">✓ {widget_file.name}<span class="upload-cell-badge">{size_badge}</span></div>', unsafe_allow_html=True)
                with c2:
                    if st.button("✕", key=f"rm_instr_{instr_gen}", help="Remove", use_container_width=True):
                        st.session_state.pop("_draft_instr_bytes", None)
                        st.session_state.pop("_draft_instr_name", None)
                        st.session_state["_instr_up_gen"] = instr_gen + 1
                        st.rerun()
            elif st.session_state.get("_draft_instr_bytes"):
                dn, db = st.session_state["_draft_instr_name"], st.session_state["_draft_instr_bytes"]
                instruction_file = _draft_fileobj(dn, db)
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(f'<div class="upload-cell-draft">✓ {dn}<span class="upload-cell-badge">{_fmt_bytes(len(db))}</span></div>', unsafe_allow_html=True)
                with c2:
                    if st.button("✕", key=f"rm_instr_draft_{instr_gen}", help="Remove", use_container_width=True):
                        st.session_state.pop("_draft_instr_bytes", None)
                        st.session_state.pop("_draft_instr_name", None)
                        st.session_state["_instr_up_gen"] = instr_gen + 1
                        st.rerun()
            st.markdown('<div class="upload-hint">Single file · .txt file</div>', unsafe_allow_html=True)

    # ── COL 2: Input ────────────────────────────────────────────────────────
    with col2:
        st.markdown('<div class="upload-cell-title">📥 Agent Input File</div>', unsafe_allow_html=True)

        if is_running or files_locked:
            name = st.session_state.get("_input_name") or "—"
            icon = "🔒" if is_running else "✓"
            st.markdown(f'<div class="upload-cell-locked">{icon} {name}</div>', unsafe_allow_html=True)
            # On running/locked: show nothing else
        else:
            inp_gen     = st.session_state.get("_inp_up_gen", 0)
            widget_file = st.file_uploader("inp", key=f"inp_up_{inp_gen}", accept_multiple_files=False, label_visibility="collapsed")
            if widget_file is not None:
                st.session_state["_draft_input_bytes"] = widget_file.getvalue()
                st.session_state["_draft_input_name"]  = widget_file.name
                input_file = widget_file
                size_badge = _fmt_bytes(len(widget_file.getvalue()))
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(f'<div class="upload-cell-ok">✓ {widget_file.name}<span class="upload-cell-badge">{size_badge}</span></div>', unsafe_allow_html=True)
                with c2:
                    if st.button("✕", key=f"rm_inp_{inp_gen}", help="Remove", use_container_width=True):
                        st.session_state.pop("_draft_input_bytes", None)
                        st.session_state.pop("_draft_input_name", None)
                        st.session_state["_inp_up_gen"] = inp_gen + 1
                        st.rerun()
            elif st.session_state.get("_draft_input_bytes"):
                dn, db = st.session_state["_draft_input_name"], st.session_state["_draft_input_bytes"]
                input_file = _draft_fileobj(dn, db)
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(f'<div class="upload-cell-draft">✓ {dn}<span class="upload-cell-badge">{_fmt_bytes(len(db))}</span></div>', unsafe_allow_html=True)
                with c2:
                    if st.button("✕", key=f"rm_inp_draft_{inp_gen}", help="Remove", use_container_width=True):
                        st.session_state.pop("_draft_input_bytes", None)
                        st.session_state.pop("_draft_input_name", None)
                        st.session_state["_inp_up_gen"] = inp_gen + 1
                        st.rerun()
            st.markdown('<div class="upload-hint">Single file · .txt file</div>', unsafe_allow_html=True)

    # ── COL 3: Outputs + BENCHMARK ──────────────────────────────────────────
    with col3:
        st.markdown('<div class="upload-cell-title">📤 Agent Output Files</div>', unsafe_allow_html=True)

        if is_running or files_locked:
            names = st.session_state.get("_output_names") or []
            icon  = "🔒" if is_running else "✓"
            for n in names:
                st.markdown(f'<div class="upload-cell-locked">{icon} {n}</div>', unsafe_allow_html=True)
        else:
            outs_gen = st.session_state.get("_outs_up_gen", 0)

            # ── STEP 1: Check for any pending removal BEFORE touching widget/draft.
            # This mirrors the col1/col2 pattern: capture click → cycle key → rerun.
            draft_outputs = st.session_state.get("_draft_output_files") or []
            to_remove     = None

            # ── STEP 2: Render the uploader at the TOP — same position as col1/col2.
            # On a fresh generation key the widget is empty (no stale file buffer).
            widget_files = st.file_uploader(
                "outs", key=f"outs_up_{outs_gen}",
                accept_multiple_files=True, label_visibility="collapsed"
            ) or []

            # ── STEP 3: Merge any newly dropped files into draft.
            if widget_files:
                existing_draft = st.session_state.get("_draft_output_files") or []
                existing_names = {d["name"] for d in existing_draft}
                changed = False
                for f in widget_files:
                    if f.name not in existing_names:
                        existing_draft.append({"name": f.name, "bytes": f.getvalue()})
                        existing_names.add(f.name)
                        changed = True
                    else:
                        for d in existing_draft:
                            if d["name"] == f.name:
                                d["bytes"] = f.getvalue()
                                break
                if changed:
                    st.session_state["_draft_output_files"] = existing_draft
                draft_outputs = st.session_state.get("_draft_output_files") or []

            # ── STEP 4: Render each file row EXACTLY like col1/col2 —
            # filename+badge on the LEFT, compact ✕ button on the RIGHT,
            # both in a tight [5,1] column split on the same line.
            if draft_outputs:
                for idx, item in enumerate(draft_outputs):
                    size_badge = _fmt_bytes(len(item["bytes"]))
                    c1, c2 = st.columns([5, 1])
                    with c1:
                        st.markdown(
                            f'<div class="upload-cell-ok">'
                            f'✓ {item["name"]}'
                            f'<span class="upload-cell-badge">{size_badge}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    with c2:
                        if st.button("✕", key=f"rm_out_{outs_gen}_{idx}_{item['name']}", help=f"Remove {item['name']}", use_container_width=True):
                            to_remove = idx

            # ── STEP 5: Process removal — cycle key so uploader resets on rerun.
            if to_remove is not None:
                new_draft = [d for i, d in enumerate(draft_outputs) if i != to_remove]
                if new_draft:
                    st.session_state["_draft_output_files"] = new_draft
                else:
                    st.session_state.pop("_draft_output_files", None)
                st.session_state["_outs_up_gen"] = outs_gen + 1
                st.rerun()

            # ── STEP 6: Build output_files list from final draft state.
            for item in (st.session_state.get("_draft_output_files") or []):
                buf = io.BytesIO(item["bytes"])
                buf.name = item["name"]
                buf.seek(0)
                output_files.append(buf)

            st.markdown('<div class="upload-hint">Multiple files allowed · one file = one model</div>', unsafe_allow_html=True)

        st.markdown("<div style='margin-top:0.55rem;'></div>", unsafe_allow_html=True)
        all_ready = (instruction_file is not None and input_file is not None and len(output_files) > 0)

        if page == "upload":
            run_clicked = st.button("🚀  BENCHMARK", type="primary", disabled=(not all_ready), use_container_width=True, key="run_btn")
            if not all_ready:
                missing = []
                if instruction_file is None: missing.append("instruction")
                if input_file is None: missing.append("input")
                if not output_files: missing.append("output")
                st.markdown(
                    f"<div style='font-family:JetBrains Mono,monospace;font-size:0.75rem;"
                    f"color:{p['t3']};text-align:center;margin-top:0.25rem;'>"
                    f"Missing: {' · '.join(missing)}</div>",
                    unsafe_allow_html=True,
                )
        else:
            run_clicked = False

    return instruction_file, input_file, output_files, run_clicked


# ---------------------------------------------------------------------------
# FILE PREVIEW PANEL
# ---------------------------------------------------------------------------

def render_preview_panel(instruction_file, input_file, output_files: list, dark: bool = False):
    p = _palette()
    st.markdown('<div class="section-label">FILE PREVIEW</div>', unsafe_allow_html=True)

    all_files = []
    if instruction_file: all_files.append(("📋 " + instruction_file.name, instruction_file))
    if input_file:       all_files.append(("📥 " + input_file.name, input_file))
    for f in (output_files or []): all_files.append(("📤 " + f.name, f))

    if not all_files:
        st.markdown('<div class="panel-box panel-box-empty">Upload files above to preview content</div>', unsafe_allow_html=True)
        return

    labels = [lbl for lbl, _ in all_files]
    sel    = st.selectbox("File:", options=labels, key="preview_sel", label_visibility="collapsed")
    sel_f  = next(f for lbl, f in all_files if lbl == sel)

    try:
        sel_f.seek(0)
        raw_content = sel_f.getvalue().decode("utf-8", errors="replace")
    except Exception as e:
        raw_content = f"[Error reading file: {e}]"

    st.markdown(
        _render_notepad_view(
            raw_content,
            max_height="65vh",
            min_height="260px",
            show_meta=True,
            show_line_numbers=False,
            filename=sel_f.name,
        ),
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# EXECUTION PANEL
# ---------------------------------------------------------------------------

def render_execution_panel(status_dict: dict, cov_result=None, dark: bool = False):
    p = _palette()
    ops_order = status_dict.get("_ops_order", [])

    st.markdown('<div class="section-label">PIPELINE EXECUTION</div>', unsafe_allow_html=True)

    if not ops_order:
        st.markdown('<div class="panel-box panel-box-empty">Initialising pipeline…</div>', unsafe_allow_html=True)
        return

    done_count   = sum(1 for k in ops_order if status_dict.get(k, {}).get("status") in (STATUS_DONE, STATUS_ERROR))
    progress_pct = int(done_count / len(ops_order) * 100)
    has_error    = any(status_dict.get(k, {}).get("status") == STATUS_ERROR for k in ops_order)
    prog_color   = "#EF4444" if has_error else "#9B6DFF"

    st.markdown(
        f"""
        <div style="margin-bottom:1rem;padding:0.9rem 1rem;
                    background:#FFFFFF;border:1px solid var(--border,#E2DCF8);
                    border-radius:var(--r-md,12px);box-shadow:0 1px 3px rgba(100,70,200,0.06);">
          <div style="display:flex;justify-content:space-between;
                      align-items:center;margin-bottom:0.5rem;">
            <span style="font-family:'Nunito Sans',sans-serif;font-size:0.82rem;
                         color:var(--t2,#3D3260);font-weight:700;">Progress</span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;
                         color:var(--t3,#7B6FA0);font-weight:500;">
              {done_count}/{len(ops_order)} steps &nbsp;·&nbsp; {progress_pct}%</span>
          </div>
          <div style="background:rgba(155,109,255,0.12);border-radius:99px;height:6px;overflow:hidden;">
            <div style="width:{progress_pct}%;height:100%;background:{prog_color};
                        border-radius:99px;transition:width 0.4s ease;
                        box-shadow:0 0 6px {prog_color}66;"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    pills_html = '<div style="display:flex;flex-wrap:wrap;gap:5px;margin-bottom:1rem;">'
    for key in ops_order:
        op     = status_dict.get(key, {})
        status = op.get("status", STATUS_PENDING)
        icon, color = _STATUS_ICON.get(status, ("⬜", p["t4"]))
        border = _status_border(status)
        bg     = _status_bg(status)
        label  = _OP_LABELS.get(key, key)
        spinner = '<span class="spinner"></span>' if status == STATUS_RUNNING else ""
        pills_html += (
            f'<span style="background:{bg};border:1px solid {border};'
            f'border-radius:99px;padding:0.22rem 0.75rem;'
            f'font-family:JetBrains Mono,monospace;font-size:0.65rem;'
            f'color:{p["t1"]};white-space:nowrap;font-weight:500;'
            f'display:inline-flex;align-items:center;gap:4px;">'
            f'{icon}{spinner} <span style="color:{color};font-weight:700;">{label}</span></span>'
        )
    pills_html += '</div>'
    st.markdown(pills_html, unsafe_allow_html=True)

    rows_html = '<div class="ops-grid">'
    for key in ops_order:
        op     = status_dict.get(key, {})
        status = op.get("status", STATUS_PENDING)
        msg    = op.get("message", "")
        icon, color = _STATUS_ICON.get(status, ("⬜", p["t4"]))
        bg     = _status_bg(status)
        border = _status_border(status)
        label  = _OP_LABELS.get(key, key)
        spinner = '<span class="spinner"></span>' if status == STATUS_RUNNING else ""
        # Status pill background per state
        pill_bg = {
            STATUS_PENDING:   "rgba(168,157,197,0.12)",
            STATUS_RUNNING:   "rgba(245,158,11,0.12)",
            STATUS_DONE:      "rgba(34,196,138,0.12)",
            STATUS_ERROR:     "rgba(239,68,68,0.12)",
            STATUS_CANCELLED: "rgba(123,111,160,0.10)",
        }.get(status, "rgba(168,157,197,0.10)")
        rows_html += f"""
  <div class="op-row" style="background:{bg};border-left:3px solid {border};">
      <span class="op-icon">{icon}{spinner}</span>
      <span class="op-label">{label}</span>
      <span class="op-status" style="color:{color};background:{pill_bg};">{status.upper()}</span>
      <span class="op-message">{msg}</span>
  </div>"""
    rows_html += "\n</div>"
    st.markdown(rows_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# BACKEND LOG
# ---------------------------------------------------------------------------

def _render_backend_logs(status_dict: dict, dark: bool = False):
    p    = _palette()
    logs = status_dict.get("_logs", [])

    st.markdown(
        '<div class="section-label" style="margin-top:1rem;">BACKEND LOG</div>',
        unsafe_allow_html=True,
    )

    if not logs:
        st.markdown(
            f'<div style="font-family:JetBrains Mono,monospace;font-size:0.78rem;'
            f'color:{p["t3"]};padding:0.35rem 0;">No log entries yet…</div>',
            unsafe_allow_html=True,
        )
        return

    def _color_line(line: str) -> str:
        if "[ERROR]" in line: return f'<div style="padding:2px 0;color:#EF4444;">{line}</div>'
        if "[WARN]"  in line: return f'<div style="padding:2px 0;color:#F59E0B;">{line}</div>'
        if "]" in line:
            ts_end = line.index("]") + 1
            ts_part = line[:ts_end]; rest = line[ts_end:]
            if "]" in rest:
                lvl_end = rest.index("]") + 1
                return (
                    f'<div style="padding:2px 0;color:{p["t2"]};">'
                    f'<span style="color:{p["t3"]};">{ts_part}</span>'
                    f'<span style="color:#9B6DFF;">{rest[:lvl_end]}</span>'
                    f'{rest[lvl_end:]}</div>'
                )
            return f'<div style="padding:2px 0;color:{p["t2"]};"><span style="color:{p["t3"]};">{ts_part}</span>{rest}</div>'
        return f'<div style="padding:2px 0;color:{p["t2"]};">{line}</div>'

    lines_html = "".join(_color_line(l) for l in logs)
    uid = f"log_{int(time.time() * 1000) % 10_000_000}"

    st.markdown(
        f'''
        <div id="{uid}" style="
            background:{p["log_bg"]};
            border:1px solid {p["border"]};
            border-radius:10px;
            padding:0.85rem 1.1rem;
            font-family:'JetBrains Mono',monospace;
            font-size:0.73rem;
            white-space:pre-wrap;
            line-height:1.75;
            height:300px;
            overflow-y:auto;
            color:{p["t2"]};
            box-shadow:inset 0 1px 4px rgba(100,70,200,0.04);
        ">{lines_html}</div>
        <script>
            (function() {{
                function scrollLog() {{
                    var el = document.getElementById("{uid}");
                    if (!el) {{ el = window.parent && window.parent.document.getElementById("{uid}"); }}
                    if (el) {{ el.scrollTop = el.scrollHeight; }}
                }}
                scrollLog(); setTimeout(scrollLog, 100);
            }})();
        </script>
        ''',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# COVERAGE PANEL
# ---------------------------------------------------------------------------

def render_coverage_panel(status_dict: dict, cov_result, dark: bool = False):
    st.markdown("""
    <style>
    /* ── Running page: hide ALL file uploader elements completely ── */
    /* The uploader widget is not called on the running page, but Streamlit's
       internal widget state can still render the native file list / confirmation
       row. Hide every possible element that could show uploaded file info. */
    section[data-testid="stFileUploader"]                      { display:none !important; }
    [data-testid="stFileUploaderDropzone"]                     { display:none !important; }
    [data-testid="stFileUploaderFile"]                         { display:none !important; }
    [data-testid="stFileUploaderFileData"]                     { display:none !important; }
    [data-testid="stFileUploaderFileName"]                     { display:none !important; }
    [data-testid="stFileUploaderDeleteBtn"]                    { display:none !important; }
    /* Hide the upload-cell-ok and upload-cell-draft rows (✓ filename + badge + X) */
    .upload-cell-ok                                            { display:none !important; }
    .upload-cell-draft                                         { display:none !important; }
    .upload-cell-badge                                         { display:none !important; }
    /* Hide the upload-hint on running page */
    .upload-hint                                               { display:none !important; }
    /* Hide any stButton that is a ✕ remove button inside upload columns */
    [data-testid="stHorizontalBlock"]:has(.upload-cell-title)
        div[data-testid="stButton"]                            { display:none !important; }
    /* Hide any stColumns row that wraps the ok/remove pair */
    [data-testid="stHorizontalBlock"]:has(.upload-cell-title)
        [data-testid="stHorizontalBlock"]                      { display:none !important; }
    </style>
    """, unsafe_allow_html=True)

    _render_backend_logs(status_dict)


# ---------------------------------------------------------------------------
# RESULTS PANEL — SCORE SUMMARY
# ---------------------------------------------------------------------------

def render_results_panel(results: list, cov_result=None, dark: bool = False):
    p = _palette()
    st.markdown('<div class="section-label">SCORE SUMMARY</div>', unsafe_allow_html=True)

    if not results:
        st.markdown('<div class="panel-box panel-box-empty">No results available.</div>', unsafe_allow_html=True)
        return

    all_parsed  = []
    col_headers = []
    for r in results:
        source_file   = r.get("source_file", r["filename"])
        model_name    = r.get("model_name", "")
        agent_outputs = r.get("agent_outputs", [])
        content       = r.get("content", "")
        col_headers.append(source_file)
        all_parsed.append(_parse_scores_from_result(agent_outputs, content, model_name))

    if not all_parsed:
        st.caption("No scoring data found.")
        return

    metric_order = []
    seen = set()
    _total_kw = ("total", "overall", "final score", "final", "grand total")

    for p_ in all_parsed:
        for k in p_:
            if k.lower() == "model name" and k not in seen: metric_order.append(k); seen.add(k)
    for p_ in all_parsed:
        for k in p_:
            if k.lower() in _total_kw and k not in seen: metric_order.append(k); seen.add(k)
    for p_ in all_parsed:
        for k in p_:
            if k not in seen and k.lower() != "model": metric_order.append(k); seen.add(k)

    total_key = next((k for k in metric_order if k.lower() in _total_kw), None)
    rank_order = []
    if total_key:
        def _score_val(parsed):
            v = parsed.get(total_key, ""); m = re.search(r"[\d.]+", str(v))
            return float(m.group()) if m else -1
        rank_order = [i for i, _ in sorted(enumerate(all_parsed), key=lambda x: _score_val(x[1]), reverse=True)]

    def _rank_badge(col_idx):
        if not rank_order or col_idx not in rank_order: return ""
        pos = rank_order.index(col_idx)
        if pos < len(_RANK_COLORS): return f' <span style="font-size:0.9rem;">{_RANK_MEDALS[pos]}</span>'
        return ""

    def _short(name, max_len=28):
        return name if len(name) <= max_len else name[:max_len-1] + "…"

    th_style = (
        f"padding:0.82rem 1.25rem;text-align:left;"
        f"font-family:Poppins,sans-serif;font-size:0.82rem;font-weight:700;"
        f"border-bottom:2px solid {p['border']};white-space:nowrap;"
        f"background:{p['bg_tint']};letter-spacing:0.01em;"
    )
    header_cells = "".join(
        f'<th style="{th_style}color:#9B6DFF;">{_short(h)}{_rank_badge(i)}</th>'
        for i, h in enumerate(col_headers)
    )
    header_row = f'<tr><th style="{th_style}color:{p["t1"]};min-width:210px;">Dimension</th>{header_cells}</tr>'

    body_rows = ""
    for i, metric in enumerate(metric_order):
        is_total = metric.lower() in _total_kw
        is_model = metric.lower() == "model name"
        row_bg   = p["row_total"] if is_total else (p["row_alt"] if i % 2 == 0 else p["row_even"])
        dim_weight = "700" if is_total else "600"
        dim_border = f"border-left:4px solid #9B6DFF;" if is_total else f"border-left:4px solid transparent;"
        metric_cell = (
            f'<td style="padding:0.75rem 1.25rem;font-family:Nunito Sans,sans-serif;'
            f'font-size:0.86rem;font-weight:{dim_weight};color:{p["t1"]};'
            f'border-right:1px solid {p["border"]};{dim_border}">{metric}</td>'
        )
        value_cells = ""
        for j, parsed in enumerate(all_parsed):
            val     = parsed.get(metric, "—")
            val_str = re.sub(r"\*+|_+|`+", "", str(val)).strip()
            val_str = val_str.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
            if is_model:                                           cell_color = p["t2"]
            elif is_total and rank_order and j in rank_order[:3]: cell_color = _RANK_COLORS[rank_order.index(j)]
            else:                                                  cell_color = p["t1"]
            cell_weight = "700" if is_total else "600"
            value_cells += (
                f'<td style="padding:0.75rem 1.25rem;font-family:JetBrains Mono,monospace;'
                f'font-size:0.86rem;font-weight:{cell_weight};color:{cell_color};">{val_str}</td>'
            )
        body_rows += f'<tr style="background:{row_bg};">{metric_cell}{value_cells}</tr>'

    table_html = f"""
<div style="overflow-x:auto;margin-bottom:1.6rem;border-radius:var(--r-md,12px);
            box-shadow:0 2px 12px rgba(100,70,200,0.09);
            border:1px solid var(--border,#E2DCF8);width:100%;">
<table class="score-table" style="width:100%;border-collapse:collapse;background:#FFFFFF;border-radius:12px;overflow:hidden;">
  <thead>{header_row}</thead>
  <tbody>{body_rows}</tbody>
</table>
</div>"""
    st.markdown(table_html, unsafe_allow_html=True)

    csv_lines = ["Dimension," + ",".join(col_headers)]
    for metric in metric_order:
        vals = [re.sub(r"\*+|_+|`+","",str(parsed.get(metric,""))).strip() for parsed in all_parsed]
        csv_lines.append(f'"{metric}",' + ",".join(f'"{v}"' for v in vals))
    st.download_button(
        label="⬇  Export Scores as CSV",
        data="\n".join(csv_lines).encode("utf-8"),
        file_name="benchmark_scores.csv",
        mime="text/csv",
        key="dl_scores_csv",
    )


# ---------------------------------------------------------------------------
# DETAIL FILES PANEL
# ---------------------------------------------------------------------------

def render_detail_files_panel(results: list, cov_result=None, dark: bool = False):
    p = _palette()
    st.markdown(
        '<div class="section-label" style="margin-top:1.8rem;">DETAIL FILES &amp; DOWNLOAD</div>',
        unsafe_allow_html=True,
    )

    if not results and cov_result is None:
        st.markdown('<div class="panel-box panel-box-empty">No result files yet.</div>', unsafe_allow_html=True)
        return

    if cov_result is not None:
        cov_text  = cov_result.get("coverage_text", "")
        exec_id   = cov_result.get("execution_id", "")
        cov_fname = f"coverage-output-{exec_id[:8]}.txt"

        with st.expander(f"📊 Coverage Output — {cov_fname}", expanded=False):
            dl_col, _ = st.columns([2, 5])
            with dl_col:
                st.download_button(
                    label=f"⬇  {cov_fname}",
                    data=cov_text.encode("utf-8"),
                    file_name=cov_fname,
                    mime="text/plain",
                    key="dl_coverage_result",
                )
            agent_outputs = cov_result.get("agent_outputs", [])
            if agent_outputs:
                for ao in agent_outputs:
                    st.markdown(
                        f'<div style="font-family:Poppins,sans-serif;font-size:0.80rem;'
                        f'font-weight:700;color:#9B6DFF;margin:0.6rem 0 0.3rem;">🤖 {ao["agent_name"]}</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        _render_notepad_view(ao.get("content", ""), max_height="500px", min_height="80px", show_line_numbers=False),
                        unsafe_allow_html=True,
                    )

    for result in results:
        filename      = result.get("filename", "")
        model         = result.get("model_name", "")
        content       = result.get("content", "")
        exec_id       = result.get("data", {}).get("execution_id", "")
        agent_outputs = result.get("agent_outputs", [])

        expander_label = f"📄 {filename}" + (f"  —  {model}" if model else "")

        with st.expander(expander_label, expanded=False):
            meta_col, dl_col = st.columns([3, 2])
            with meta_col:
                if model:
                    st.markdown(
                        f'<div style="font-family:Poppins,sans-serif;font-size:0.84rem;'
                        f'color:#9B6DFF;font-weight:700;margin-bottom:0.2rem;">Model: {model}</div>',
                        unsafe_allow_html=True,
                    )
                if exec_id:
                    st.markdown(
                        f'<div style="font-family:JetBrains Mono,monospace;font-size:0.72rem;'
                        f'color:{p["t3"]};">Execution ID: {exec_id}</div>',
                        unsafe_allow_html=True,
                    )
            with dl_col:
                st.download_button(
                    label=f"⬇  Download",
                    data=content.encode("utf-8"),
                    file_name=filename,
                    mime="text/plain",
                    key=f"dl_{filename}",
                )

            if agent_outputs:
                for ao in agent_outputs:
                    st.markdown(
                        f'<div style="font-family:Poppins,sans-serif;font-size:0.80rem;'
                        f'font-weight:700;color:#9B6DFF;margin:0.6rem 0 0.3rem;">🤖 {ao["agent_name"]}</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        _render_notepad_view(ao.get("content", ""), max_height="500px", min_height="80px", show_line_numbers=False),
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    _render_notepad_view(content, max_height="500px", min_height="80px", filename=filename, show_line_numbers=False),
                    unsafe_allow_html=True,
                )


# ---------------------------------------------------------------------------
# SUMMARY AGENT PANEL
# ---------------------------------------------------------------------------

def render_summary_panel(summ_result: dict, dark: bool = False):
    """
    Render the Summary Agent output between the score table and detail files.
    summ_result is the dict returned by call_summary_agent:
      { execution_id, agent_outputs, raw_result, summary_text }
    """
    p = _palette()
    st.markdown(
        '<div class="section-label" style="margin-top:1.8rem;">SUMMARY</div>',
        unsafe_allow_html=True,
    )

    if not summ_result:
        st.markdown(
            '<div class="panel-box panel-box-empty">No summary available.</div>',
            unsafe_allow_html=True,
        )
        return

    exec_id       = summ_result.get("execution_id", "")
    agent_outputs = summ_result.get("agent_outputs", [])
    summary_text  = summ_result.get("summary_text", "")
    exec_label    = f"ID: {exec_id[:8]}…" if exec_id else ""

    # Header badge
    st.markdown(
        f'<div style="'
        f'display:inline-flex;align-items:center;gap:0.5rem;'
        f'font-family:Nunito Sans,sans-serif;font-size:0.86rem;'
        f'color:#22C48A;margin-bottom:0.85rem;font-weight:700;'
        f'background:rgba(34,196,138,0.07);border:1px solid rgba(34,196,138,0.20);'
        f'border-radius:8px;padding:0.45rem 0.85rem;">'
        f'✅ Summary complete'
        f'<span style="font-weight:500;color:#3D3260;font-size:0.78rem;">·</span>'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:0.74rem;'
        f'color:#7B6FA0;font-weight:500;">{exec_label}</span>'
        f'<span style="font-weight:500;color:#3D3260;font-size:0.78rem;">·</span>'
        f'<span style="font-size:0.80rem;color:#3D3260;font-weight:600;">'
        f'{len(agent_outputs)} output(s)</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Render each agent output in a notepad view
    if agent_outputs:
        for ao in agent_outputs:
            st.markdown(
                f'<div style="font-family:Poppins,sans-serif;font-size:0.80rem;'
                f'font-weight:700;color:#9B6DFF;margin:0.6rem 0 0.3rem;">'
                f'🤖 {ao["agent_name"]}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                _render_notepad_view(
                    ao.get("content", ""),
                    max_height="500px",
                    min_height="120px",
                    show_line_numbers=False,
                ),
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            _render_notepad_view(
                summary_text,
                max_height="500px",
                min_height="120px",
                show_line_numbers=False,
            ),
            unsafe_allow_html=True,
        )

    # Download button for the full summary text
    dl_fname = f"summary-{exec_id[:8]}.txt" if exec_id else "summary.txt"
    dl_col, _ = st.columns([2, 5])
    with dl_col:
        st.download_button(
            label=f"⬇  {dl_fname}",
            data=summary_text.encode("utf-8"),
            file_name=dl_fname,
            mime="text/plain",
            key="dl_summary_result",
        )


# ---------------------------------------------------------------------------
# FULL RESULTS PAGE
# ---------------------------------------------------------------------------

def render_full_results_page(results: list, cov_result=None, summ_result=None, dark: bool = False):
    p = _palette()
    render_results_panel(results, cov_result)
    if summ_result:
        st.markdown(f"<hr style='border-color:{p['border']};margin:1.5rem 0;'>", unsafe_allow_html=True)
        render_summary_panel(summ_result)
    st.markdown(f"<hr style='border-color:{p['border']};margin:1.5rem 0;'>", unsafe_allow_html=True)
    render_detail_files_panel(results, cov_result)


# ---------------------------------------------------------------------------
# SCORE PARSER
# ---------------------------------------------------------------------------

def _parse_scores_from_result(agent_outputs: list, fallback_content: str, model_name: str = "") -> dict:
    combined = "\n".join(ao.get("content", "") for ao in agent_outputs)
    if not combined.strip(): combined = fallback_content

    scores = OrderedDict()
    _total_kw = ("total", "overall", "final score", "final", "grand total")

    table_match = re.search(r"\|.+\|[\s\S]+?\|[-| :]+\|", combined)
    if table_match:
        lines = combined[table_match.start():].splitlines()
        header_cells = None
        for line in lines:
            line = line.strip()
            if not line.startswith("|"): break
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(re.match(r"^[-: ]+$", c) for c in cells if c): continue
            if header_cells is None: header_cells = cells; continue
            if len(cells) >= 2:
                key = re.sub(r"\*+|_+|`+", "", cells[0]).strip()
                val = re.sub(r"\*+|_+|`+", "", cells[1] if len(cells) > 1 else "").strip()
                if not key or key.lower() in ("dimension","metric","category","criteria"): continue
                if key.lower() == "model name": model_name = model_name or val
                elif key.lower() == "model":    model_name = val
                else:                           scores[key] = val

    if not scores:
        for line in combined.splitlines():
            m = re.match(r"^\*?\*?([A-Za-z][\w\s/()-]{1,40}?)\*?\*?\s*[:–—]\s*(.+)$", line.strip())
            if m:
                key = re.sub(r"\*+|_+|`+", "", m.group(1)).strip().rstrip("*").strip()
                val = re.sub(r"\*+|_+|`+", "", m.group(2)).strip()
                if key.lower() in ("model name",): model_name = model_name or val
                elif key.lower() == "model":       model_name = val
                elif key and len(key) < 50:        scores[key] = val

    result = OrderedDict()
    if model_name: result["Model Name"] = model_name
    result.update(scores)
    return result


# ---------------------------------------------------------------------------
# Legacy aliases
# ---------------------------------------------------------------------------
render_header                   = lambda: None
render_sidebar_uploads          = lambda show_run_btn=True, page="upload": render_top_upload_bar(page=page)
render_upload_section           = lambda: (None, None, [])
render_file_preview             = render_preview_panel
render_operations_grid          = lambda sd: render_execution_panel(sd, None)
render_summary_grid             = lambda results: None
render_result_files_grid        = lambda results: render_detail_files_panel(results)
render_coverage_result_section  = lambda cov: None