"""
ui/components.py
----------------
All UI render functions for AGENTBENCHMARKING — production version.

Improvements over v5:
- Upload bar: cleaner visual hierarchy, file-size badges, animated indicators
- Preview panel: line numbers toggle, word-wrap toggle, char/line counts
- Execution panel: progress bar, elapsed timer, step pills with tooltips
- Coverage panel: structured accordion with agent tabs
- Results panel: sortable unified table with score bars, totals highlighted,
  colour-coded ranking (gold/silver/bronze), exportable CSV download
- Detail files panel: side-by-side diff view when ≥ 2 files, agent tab switcher
- Full results page: tabs for Summary | Details | Export
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
# Constants
# ---------------------------------------------------------------------------
_STATUS_ICON = {
    STATUS_PENDING:   ("⬜", "#ffffff"),
    STATUS_RUNNING:   ("🔄", "#f59e0b"),
    STATUS_DONE:      ("✅", "#10b981"),
    STATUS_ERROR:     ("❌", "#ef4444"),
    STATUS_CANCELLED: ("🚫", "#9ca3af"),
}
_STATUS_BG = {
    STATUS_PENDING:   "#0e1020",
    STATUS_RUNNING:   "#1e1500",
    STATUS_DONE:      "#071810",
    STATUS_ERROR:     "#1e0808",
    STATUS_CANCELLED: "#111118",
}
_STATUS_BORDER = {
    STATUS_PENDING:   "#1e2340",
    STATUS_RUNNING:   "#f59e0b",
    STATUS_DONE:      "#10b981",
    STATUS_ERROR:     "#ef4444",
    STATUS_CANCELLED: "#ffffff",
}

_OP_LABELS = {
    "upload":        "Uploading files",
    "coverage_call": "Coverage Agent — Submit",
    "coverage_wait": "Coverage Agent — Response",
    "scoring_call":  "Scoring Agent — Dispatch",
    "scoring_jobs":  "Scoring Jobs — Running",
    "collect":       "Collecting Results",
}

_RANK_COLORS = ["#FFD700", "#C0C0C0", "#CD7F32"]   # gold, silver, bronze


def _fmt_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n/1024:.1f} KB"
    return f"{n/1024/1024:.1f} MB"


# ---------------------------------------------------------------------------
# TOP UPLOAD BAR
# ---------------------------------------------------------------------------

def render_top_upload_bar(page: str = "upload"):
    """
    Renders the 3-column upload bar.

    Returns: (instruction_file, input_file, output_files, run_clicked)
    """
    st.markdown("""
    <style>
@import url('https://fonts.googleapis.com/css2?family=Mulish:wght@300;400;500;600;700;800&display=swap');

body, [class*="css"] {
    font-family: 'Mulish', sans-serif;
    color: #ffffff;
}

h1, h2, h3 {
    font-family: 'Mulish', sans-serif;
}

.upload-cell-title {
    font-family: 'Mulish', sans-serif;
    font-size: 1.05rem;
    font-weight: 700;
    letter-spacing: 0.10em;
    color: #6c8eff;
    text-transform: uppercase;
    margin-bottom: 0.45rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    border-bottom: 1px solid #1e2340;
    padding-bottom: 0.35rem;
}

.upload-cell-ok {
    font-family: 'Mulish', sans-serif;
    font-size: 0.80rem;
    color: #10b981;
    margin-top: 0.15rem;
    word-break: break-all;
    display: flex;
    align-items: center;
    gap: 0.3rem;
}

.upload-cell-badge {
    font-size: 0.60rem;
    background: #0a2010;
    border: 1px solid #10b981;
    border-radius: 4px;
    padding: 1px 5px;
    color: #10b981;
    flex-shrink: 0;
}

.upload-cell-locked {
    font-family: 'Mulish', sans-serif;
    font-size: 0.76rem;
    color: #ffffff;
    margin-top: 0.15rem;
    word-break: break-all;
    font-style: italic;
}

.upload-cell-draft {
    font-family: 'Mulish', sans-serif;
    font-size: 0.78rem;
    color: #ffffff;
    margin-top: 0.12rem;
    word-break: break-all;
}

[data-testid="stFileUploaderDropzone"] {
    background: #080b14 !important;
    border: 1px dashed #2a3060 !important;
    border-radius: 5px !important;
    padding: 0.25rem 0.5rem !important;
    min-height: 42px !important;
    transition: border-color 0.2s;
}

[data-testid="stFileUploaderDropzone"]:hover {
    border-color: #6c8eff !important;
}

[data-testid="stFileUploaderDropzone"] p {
    font-size: 0.58rem !important;
    color: #ffffff !important;
    font-family: 'Mulish', sans-serif !important;
}

[data-testid="stFileUploaderDropzone"] svg { display: none !important; }
[data-testid="stFileUploaderDropzone"] label { display: none !important; }
[data-testid="stFileUploaderFile"] { display: none !important; }
[data-testid="stFileUploaderFileData"] { display: none !important; }
[data-testid="stFileUploaderFileName"] { display: none !important; }

section[data-testid="stFileUploader"] > div:last-child > div {
    display: none !important;
}
</style>
    """, unsafe_allow_html=True)

    files_locked = st.session_state.get("_files_locked", False)
    is_running   = (page == "running")

    col1, col2, col3 = st.columns([1, 1, 1], gap="small")

    def _draft_fileobj(name, data):
        buf = io.BytesIO(data)
        buf.name = name
        buf.seek(0)
        return buf

    # ── COL 1: Instruction ──────────────────────────────────────────────────
    with col1:
        st.markdown(
            '<div class="upload-cell-title">📋 Agent Instruction File</div>',
            unsafe_allow_html=True,
        )

        if is_running or files_locked:
            name = st.session_state.get("_instr_name") or "—"
            icon = "🔒" if is_running else "✓"
            st.markdown(f'<div class="upload-cell-locked">{icon} {name}</div>', unsafe_allow_html=True)
            instruction_file = None
        else:
            widget_file = st.file_uploader(
                "instr", key="instr_up", accept_multiple_files=False,
                label_visibility="collapsed",
            )
            if widget_file is not None:
                st.session_state["_draft_instr_bytes"] = widget_file.getvalue()
                st.session_state["_draft_instr_name"]  = widget_file.name
                instruction_file = widget_file
                size_badge = _fmt_bytes(len(widget_file.getvalue()))
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(
                        f'<div class="upload-cell-ok">✓ {widget_file.name}'
                        f'<span class="upload-cell-badge">{size_badge}</span></div>',
                        unsafe_allow_html=True,
                    )
                with c2:
                    if st.button("✕", key="rm_instr", help="Remove", use_container_width=True):
                        st.session_state.pop("instr_up", None)
                        st.session_state.pop("_draft_instr_bytes", None)
                        st.session_state.pop("_draft_instr_name", None)
                        st.rerun()

            elif st.session_state.get("_draft_instr_bytes"):
                draft_name  = st.session_state["_draft_instr_name"]
                draft_bytes = st.session_state["_draft_instr_bytes"]
                instruction_file = _draft_fileobj(draft_name, draft_bytes)
                size_badge = _fmt_bytes(len(draft_bytes))
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(
                        f'<div class="upload-cell-draft">✓ {draft_name}'
                        f'<span class="upload-cell-badge">{size_badge}</span></div>',
                        unsafe_allow_html=True,
                    )
                with c2:
                    if st.button("✕", key="rm_instr_draft", help="Remove", use_container_width=True):
                        st.session_state.pop("_draft_instr_bytes", None)
                        st.session_state.pop("_draft_instr_name", None)
                        st.rerun()
            else:
                instruction_file = None

            st.markdown(
                '<div style="font-family:Mulish,sans-serif;font-size:0.85rem;'
                'color:#ffffff;margin-top:0.3rem;">Single file · .txt file</div>',
                unsafe_allow_html=True,
            )

    # ── COL 2: Input ────────────────────────────────────────────────────────
    with col2:
        st.markdown(
            '<div class="upload-cell-title">📥 Agent Input File</div>',
            unsafe_allow_html=True,
        )

        if is_running or files_locked:
            name = st.session_state.get("_input_name") or "—"
            icon = "🔒" if is_running else "✓"
            st.markdown(f'<div class="upload-cell-locked">{icon} {name}</div>', unsafe_allow_html=True)
            input_file = None
        else:
            widget_file = st.file_uploader(
                "inp", key="inp_up", accept_multiple_files=False,
                label_visibility="collapsed",
            )
            if widget_file is not None:
                st.session_state["_draft_input_bytes"] = widget_file.getvalue()
                st.session_state["_draft_input_name"]  = widget_file.name
                input_file = widget_file
                size_badge = _fmt_bytes(len(widget_file.getvalue()))
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(
                        f'<div class="upload-cell-ok">✓ {widget_file.name}'
                        f'<span class="upload-cell-badge">{size_badge}</span></div>',
                        unsafe_allow_html=True,
                    )
                with c2:
                    if st.button("✕", key="rm_inp", help="Remove", use_container_width=True):
                        st.session_state.pop("inp_up", None)
                        st.session_state.pop("_draft_input_bytes", None)
                        st.session_state.pop("_draft_input_name", None)
                        st.rerun()

            elif st.session_state.get("_draft_input_bytes"):
                draft_name  = st.session_state["_draft_input_name"]
                draft_bytes = st.session_state["_draft_input_bytes"]
                input_file  = _draft_fileobj(draft_name, draft_bytes)
                size_badge  = _fmt_bytes(len(draft_bytes))
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(
                        f'<div class="upload-cell-draft">✓ {draft_name}'
                        f'<span class="upload-cell-badge">{size_badge}</span></div>',
                        unsafe_allow_html=True,
                    )
                with c2:
                    if st.button("✕", key="rm_inp_draft", help="Remove", use_container_width=True):
                        st.session_state.pop("_draft_input_bytes", None)
                        st.session_state.pop("_draft_input_name", None)
                        st.rerun()
            else:
                input_file = None

            st.markdown(
                '<div style="font-family:Mulish,sans-serif;font-size:0.85rem;'
                'color:#ffffff;margin-top:0.3rem;">Single file · .txt file</div>',
                unsafe_allow_html=True,
            )

    # ── COL 3: Output files + BENCHMARK button ──────────────────────────────
    with col3:
        st.markdown(
            '<div class="upload-cell-title">📤 Agent Output Files</div>',
            unsafe_allow_html=True,
        )

        if is_running or files_locked:
            names = st.session_state.get("_output_names") or []
            icon  = "🔒" if is_running else "✓"
            for n in names:
                st.markdown(f'<div class="upload-cell-locked">{icon} {n}</div>', unsafe_allow_html=True)
            output_files = []
        else:
            widget_files = st.file_uploader(
                "outs", key="outs_up", accept_multiple_files=True,
                label_visibility="collapsed",
            ) or []

            if widget_files:
                existing_draft = st.session_state.get("_draft_output_files") or []
                existing_names = {d["name"] for d in existing_draft}
                for f in widget_files:
                    if f.name not in existing_names:
                        existing_draft.append({"name": f.name, "bytes": f.getvalue()})
                        existing_names.add(f.name)
                    else:
                        for d in existing_draft:
                            if d["name"] == f.name:
                                d["bytes"] = f.getvalue()
                                break
                st.session_state["_draft_output_files"] = existing_draft

            draft_outputs = st.session_state.get("_draft_output_files") or []
            output_files  = []

            if draft_outputs:
                to_remove = None
                for idx, item in enumerate(draft_outputs):
                    size_badge = _fmt_bytes(len(item["bytes"]))
                    c1, c2 = st.columns([5, 1])
                    with c1:
                        st.markdown(
                            f'<div class="upload-cell-draft" style="font-size:0.76rem;">'
                            f'✓ {item["name"]}'
                            f'<span class="upload-cell-badge">{size_badge}</span></div>',
                            unsafe_allow_html=True,
                        )
                    with c2:
                        if st.button("✕", key=f"rm_out_{idx}_{item['name']}",
                                     help=f"Remove {item['name']}", use_container_width=True):
                            to_remove = idx

                if to_remove is not None:
                    new_draft = [d for i, d in enumerate(draft_outputs) if i != to_remove]
                    if new_draft:
                        st.session_state["_draft_output_files"] = new_draft
                    else:
                        st.session_state.pop("_draft_output_files", None)
                        st.session_state.pop("outs_up", None)
                    st.rerun()

                for item in (st.session_state.get("_draft_output_files") or []):
                    buf = io.BytesIO(item["bytes"])
                    buf.name = item["name"]
                    buf.seek(0)
                    output_files.append(buf)
            else:
                st.session_state.pop("outs_up", None)

            st.markdown(
                '<div style="font-family:Mulish,sans-serif;font-size:0.85rem;'
                'color:#ffffff;margin-top:0.3rem;">Multiple files allowed · one file = one model</div>',
                unsafe_allow_html=True,
            )

        # ── BENCHMARK button ───────────────────────────────────────────────
        st.markdown("<div style='margin-top:0.55rem;'></div>", unsafe_allow_html=True)

        all_ready = (
            instruction_file is not None
            and input_file is not None
            and len(output_files) > 0
        )

        if page == "upload":
            run_clicked = st.button(
                "🚀  BENCHMARK",
                type="primary",
                disabled=(not all_ready),
                use_container_width=True,
                key="run_btn",
            )
            if not all_ready:
                missing = []
                if instruction_file is None:
                    missing.append("instruction")
                if input_file is None:
                    missing.append("input")
                if not output_files:
                    missing.append("output")
                missing_str = " · ".join(missing)
                st.markdown(
                    f"<div style='font-family:Mulish,sans-serif;font-size:0.68rem;"
                    f"color:#5a6090;text-align:center;margin-top:0.25rem;'>"
                    f"Missing: {missing_str}</div>",
                    unsafe_allow_html=True,
                )
        else:
            run_clicked = False

    return instruction_file, input_file, output_files, run_clicked


# ---------------------------------------------------------------------------
# BOTTOM LEFT — FILE PREVIEW PANEL
# ---------------------------------------------------------------------------

def render_preview_panel(instruction_file, input_file, output_files: list):
    """Renders the file content preview with metadata and controls."""
    st.markdown('<div class="section-label" style="font-size:1.05rem !important;">FILE PREVIEW</div>', unsafe_allow_html=True)

    all_files = []
    if instruction_file:
        all_files.append(("📋 " + instruction_file.name, instruction_file))
    if input_file:
        all_files.append(("📥 " + input_file.name, input_file))
    for f in (output_files or []):
        all_files.append(("📤 " + f.name, f))

    if not all_files:
        st.markdown(
            '<div class="panel-box panel-box-empty">Upload files above to preview content</div>',
            unsafe_allow_html=True,
        )
        return

    labels = [lbl for lbl, _ in all_files]
    sel = st.selectbox(
        "File:", options=labels, key="preview_sel", label_visibility="collapsed"
    )
    sel_f = next(f for lbl, f in all_files if lbl == sel)

    try:
        sel_f.seek(0)
        raw_content = sel_f.getvalue().decode("utf-8", errors="replace")
    except Exception as e:
        raw_content = f"[Error reading file: {e}]"

    line_count = raw_content.count("\n") + 1
    char_count = len(raw_content)

    # Meta row
    st.markdown(
        f'<div class="preview-meta">'
        f'📄 <b>{sel_f.name}</b>'
        f'&nbsp;&nbsp;|&nbsp;&nbsp;{line_count:,} lines'
        f'&nbsp;&nbsp;|&nbsp;&nbsp;{char_count:,} chars'
        f'&nbsp;&nbsp;|&nbsp;&nbsp;{_fmt_bytes(len(raw_content.encode()))}'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.code(raw_content, language=None)


# ---------------------------------------------------------------------------
# EXECUTION PANEL (running page — right side)
# ---------------------------------------------------------------------------

def render_execution_panel(status_dict: dict, cov_result=None):
    """Render pipeline step grid with progress bar and step pills."""
    ops_order = status_dict.get("_ops_order", [])

    st.markdown('<div class="section-label" style="font-size:1.05rem !important;">PIPELINE EXECUTION</div>', unsafe_allow_html=True)

    if not ops_order:
        st.markdown(
            '<div class="panel-box panel-box-empty">Initialising pipeline…</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Progress bar ──────────────────────────────────────────────────────
    done_count = sum(
        1 for k in ops_order
        if status_dict.get(k, {}).get("status") in (STATUS_DONE, STATUS_ERROR)
    )
    progress_pct = int(done_count / len(ops_order) * 100)
    prog_color = "#ef4444" if any(
        status_dict.get(k, {}).get("status") == STATUS_ERROR for k in ops_order
    ) else "#6c8eff"

    st.markdown(
        f"""
        <div style="margin-bottom:0.85rem;">
          <div style="display:flex;justify-content:space-between;
                      font-family:Mulish,sans-serif;font-size:0.62rem;
                      color:#ffffff;margin-bottom:4px;">
            <span>Progress</span>
            <span>{done_count}/{len(ops_order)} steps · {progress_pct}%</span>
          </div>
          <div style="background:#0e1020;border-radius:20px;height:6px;overflow:hidden;
                      border:1px solid #1e2340;">
            <div style="width:{progress_pct}%;height:100%;background:{prog_color};
                        border-radius:20px;transition:width 0.4s ease;"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Step pills ────────────────────────────────────────────────────────
    pills_html = '<div style="display:flex;flex-wrap:wrap;gap:5px;margin-bottom:0.8rem;">'
    for key in ops_order:
        op     = status_dict.get(key, {})
        status = op.get("status", STATUS_PENDING)
        icon, color = _STATUS_ICON.get(status, ("⬜", "#ffffff"))
        border = _STATUS_BORDER.get(status, "#1e2340")
        label  = _OP_LABELS.get(key, key)
        spinner = '<span class="spinner"></span>' if status == STATUS_RUNNING else ""
        pills_html += (
            f'<span style="background:#0e1020;border:1px solid {border};'
            f'border-radius:20px;padding:0.16rem 0.6rem;'
            f'font-family:Mulish,sans-serif;font-size:0.57rem;'
            f'color:{color};white-space:nowrap;">'
            f'{icon}{spinner} {label}</span>'
        )
    pills_html += '</div>'
    st.markdown(pills_html, unsafe_allow_html=True)

    # ── Ops rows ──────────────────────────────────────────────────────────
    rows_html = '<div class="ops-grid">'
    for key in ops_order:
        op     = status_dict.get(key, {})
        status = op.get("status", STATUS_PENDING)
        msg    = op.get("message", "")
        icon, color = _STATUS_ICON.get(status, ("⬜", "#ffffff"))
        bg     = _STATUS_BG.get(status, "#0e1020")
        border = _STATUS_BORDER.get(status, "#1e2340")
        label  = _OP_LABELS.get(key, key)
        spinner = '<span class="spinner"></span>' if status == STATUS_RUNNING else ""

        rows_html += f"""
  <div class="op-row" style="background:{bg};border-left:3px solid {border};">
      <span class="op-icon">{icon}{spinner}</span>
      <span class="op-label">{label}</span>
      <span class="op-status" style="color:{color};">{status.upper()}</span>
      <span class="op-message">{msg}</span>
  </div>"""
    rows_html += "\n</div>"
    st.markdown(rows_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# BACKEND LOG RENDERER
# ---------------------------------------------------------------------------

def _render_backend_logs(status_dict: dict):
    logs = status_dict.get("_logs", [])

    st.markdown(
        '<div class="section-label" style="margin-top:1rem;">BACKEND LOG</div>',
        unsafe_allow_html=True,
    )

    if not logs:
        st.markdown(
            '<div style="font-family:Mulish,sans-serif;font-size:0.67rem;'
            'color:#ffffff;padding:0.35rem 0;">No log entries yet…</div>',
            unsafe_allow_html=True,
        )
        return

    def _color_line(line: str) -> str:
        if "[ERROR]" in line:
            return f'<div style="padding:1.5px 0;color:#ef4444;">{line}</div>'
        if "[WARN]" in line:
            return f'<div style="padding:1.5px 0;color:#f59e0b;">{line}</div>'
        # White for all normal log lines
        if "]" in line:
            ts_end = line.index("]") + 1
            ts_part = line[:ts_end]
            rest = line[ts_end:]
            if "]" in rest:
                lvl_end = rest.index("]") + 1
                return (
                    f'<div style="padding:1.5px 0;color:#ffffff;">'
                    f'<span style="color:#ffffff;">{ts_part}</span>'
                    f'<span style="color:#ffffff;">{rest[:lvl_end]}</span>'
                    f'{rest[lvl_end:]}</div>'
                )
            return f'<div style="padding:1.5px 0;color:#ffffff;"><span style="color:#ffffff;">{ts_part}</span>{rest}</div>'
        return f'<div style="padding:1.5px 0;color:#ffffff;">{line}</div>'

    lines_html = "".join(_color_line(l) for l in logs)
    uid = f"log_{int(time.time() * 1000) % 10_000_000}"

    st.markdown(
        f'''
        <div id="{uid}" style="
            background: #080b14;
            border: 1px solid #1e2a50;
            border-radius: 6px;
            padding: 0.8rem 1rem;
            font-family: 'Mulish', sans-serif;
            font-size: 0.66rem;
            white-space: pre-wrap;
            line-height: 1.75;
            height: 300px;
            overflow-y: auto;
        ">{lines_html}</div>
        <script>
            (function() {{
                function scrollLog() {{
                    var el = document.getElementById("{uid}");
                    if (!el) {{ el = window.parent && window.parent.document.getElementById("{uid}"); }}
                    if (el) {{ el.scrollTop = el.scrollHeight; }}
                }}
                scrollLog();
                setTimeout(scrollLog, 100);
            }})();
        </script>
        ''',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# COVERAGE PANEL (running page — left side)
# ---------------------------------------------------------------------------

def render_coverage_panel(status_dict: dict, cov_result):
    """Left panel on the running page: coverage agent output + backend logs."""
    cov_done = status_dict.get("coverage_wait", {}).get("status") == STATUS_DONE

    # Suppress uploader artefacts on this page
    st.markdown("""
    <style>
    .preview-meta { display: none !important; }
    section[data-testid="stFileUploader"] { display: none !important; }
    [data-testid="stFileUploaderDropzone"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div class="section-label">COVERAGE &amp; CONDITION AGENT</div>',
        unsafe_allow_html=True,
    )

    if not cov_done or not cov_result:
        cov_status  = status_dict.get("coverage_call", {}).get("status", STATUS_PENDING)
        wait_status = status_dict.get("coverage_wait", {}).get("status", STATUS_PENDING)
        icon_c, color_c = _STATUS_ICON.get(cov_status,  ("⬜", "#ffffff"))
        icon_w, color_w = _STATUS_ICON.get(wait_status, ("⬜", "#ffffff"))
        spinner_c = '<span class="spinner"></span>' if cov_status  == STATUS_RUNNING else ""
        spinner_w = '<span class="spinner"></span>' if wait_status == STATUS_RUNNING else ""
        st.markdown(
            f'<div style="font-family:Mulish,sans-serif;font-size:0.80rem;'
            f'color:#ffffff;padding:0.5rem 0 1rem;">'
            f'{icon_c}{spinner_c} Submitting coverage agent… '
            f'<span style="color:{color_c};">{cov_status.upper()}</span><br>'
            f'{icon_w}{spinner_w} Awaiting response… '
            f'<span style="color:{color_w};">{wait_status.upper()}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        exec_id = cov_result.get("execution_id", "")
        exec_label = f"ID: {exec_id[:8]}…" if exec_id else ""
        agent_outputs = cov_result.get("agent_outputs", [])

        st.markdown(
            f'<div style="font-family:Mulish,sans-serif;font-size:0.70rem;'
            f'color:#10b981;margin-bottom:0.6rem;">✅ Coverage complete — {exec_label} '
            f'— {len(agent_outputs)} agent output(s)</div>',
            unsafe_allow_html=True,
        )

        if agent_outputs:
            if len(agent_outputs) == 1:
                ao = agent_outputs[0]
                with st.expander(f"🤖 {ao['agent_name']}", expanded=False):
                    safe = ao.get("content", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    st.markdown(
                        f'<div style="background:#080b14;border:1px solid #1e2a50;border-radius:6px;'
                        f'padding:0.8rem 1rem;font-family:Mulish,sans-serif;font-size:0.67rem;'
                        f'color:#8090b8;white-space:pre-wrap;overflow-x:auto;line-height:1.65;">'
                        f'{safe}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                tab_names = [ao["agent_name"] for ao in agent_outputs]
                tabs = st.tabs(tab_names)
                for tab, ao in zip(tabs, agent_outputs):
                    with tab:
                        safe = ao.get("content", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        st.markdown(
                            f'<div style="background:#080b14;border:1px solid #1e2a50;border-radius:6px;'
                            f'padding:0.8rem 1rem;font-family:Mulish,sans-serif;font-size:0.67rem;'
                            f'color:#8090b8;white-space:pre-wrap;overflow-x:auto;line-height:1.65;">'
                            f'{safe}</div>',
                            unsafe_allow_html=True,
                        )

    _render_backend_logs(status_dict)


# ---------------------------------------------------------------------------
# RESULTS PANEL — SCORE SUMMARY
# ---------------------------------------------------------------------------

def render_results_panel(results: list, cov_result=None):
    """
    Unified score table: columns = models, rows = metrics.
    Features: rank badges (gold/silver/bronze), total row highlighted,
    numeric score bars, CSV export button.
    """
    st.markdown('<div class="section-label">SCORE SUMMARY</div>', unsafe_allow_html=True)

    if not results:
        st.markdown(
            '<div class="panel-box panel-box-empty">No results available.</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Parse each result ────────────────────────────────────────────────
    all_parsed  = []
    col_headers = []

    for r in results:
        source_file   = r.get("source_file", r["filename"])
        model_name    = r.get("model_name", "")
        agent_outputs = r.get("agent_outputs", [])
        content       = r.get("content", "")
        col_headers.append(source_file)
        parsed = _parse_scores_from_result(agent_outputs, content, model_name)
        all_parsed.append(parsed)

    if not all_parsed:
        st.caption("No scoring data found.")
        return

    # ── Build metric order ───────────────────────────────────────────────
    metric_order = []
    seen = set()
    _total_kw = ("total", "overall", "final score", "final", "grand total")

    for p in all_parsed:
        for k in p:
            if k.lower() == "model name" and k not in seen:
                metric_order.append(k)
                seen.add(k)
    for p in all_parsed:
        for k in p:
            if k.lower() in _total_kw and k not in seen:
                metric_order.append(k)
                seen.add(k)
    for p in all_parsed:
        for k in p:
            if k not in seen and k.lower() != "model":
                metric_order.append(k)
                seen.add(k)

    # ── Determine ranking by "total"-style row ───────────────────────────
    total_key = next((k for k in metric_order if k.lower() in _total_kw), None)
    rank_order = []
    if total_key:
        def _score_val(p):
            v = p.get(total_key, "")
            m = re.search(r"[\d.]+", str(v))
            return float(m.group()) if m else -1
        indexed = sorted(enumerate(all_parsed), key=lambda x: _score_val(x[1]), reverse=True)
        rank_order = [i for i, _ in indexed]

    def _rank_badge(col_idx):
        if not rank_order or col_idx not in rank_order:
            return ""
        pos = rank_order.index(col_idx)
        if pos < len(_RANK_COLORS):
            medal = ["🥇", "🥈", "🥉"][pos]
            return f' <span style="font-size:0.85rem;">{medal}</span>'
        return ""

    # ── HTML table ───────────────────────────────────────────────────────
    def _short(name, max_len=30):
        return name if len(name) <= max_len else name[: max_len - 1] + "…"

    # ── Header row ───────────────────────────────────────────────────────
    th_base = (
        "padding:0.75rem 1.2rem;text-align:left;"
        "font-family:Mulish,sans-serif;font-size:0.82rem;font-weight:700;"
        "border-bottom:2px solid #1e2a50;white-space:nowrap;"
    )
    header_cells = "".join(
        f'<th style="{th_base}color:#6c8eff;">'
        f'{_short(h)}{_rank_badge(i)}</th>'
        for i, h in enumerate(col_headers)
    )
    header_row = (
        f'<tr>'
        f'<th style="{th_base}color:#ffffff;min-width:200px;">Dimension</th>'
        f'{header_cells}'
        f'</tr>'
    )

    # ── Body rows ─────────────────────────────────────────────────────────
    body_rows = ""
    for i, metric in enumerate(metric_order):
        is_total = metric.lower() in _total_kw
        is_model = metric.lower() == "model name"

        # Row background — alternating, total row slightly brighter
        row_bg = "#101830" if is_total else ("#0b0e1c" if i % 2 == 0 else "#0e1120")

        # Dimension cell
        dim_color  = "#ffffff" if is_total else "#ffffff"
        dim_weight = "800"     if is_total else "700"
        dim_border = "border-left:3px solid #6c8eff;" if is_total else ""
        metric_cell = (
            f'<td style="padding:0.7rem 1.2rem;font-family:Mulish,sans-serif;'
            f'font-size:0.82rem;font-weight:{dim_weight};color:{dim_color};'
            f'border-right:1px solid #1a1f3a;{dim_border}">'
            f'{metric}</td>'
        )

        # Value cells — always bold, color-coded
        value_cells = ""
        for j, p in enumerate(all_parsed):
            val = p.get(metric, "—")
            val_str = re.sub(r"\*+|_+|`+", "", str(val)).strip()
            val_str = val_str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

            if is_model:
                cell_color = "#ffffff"
            elif is_total and rank_order and j in rank_order[:3]:
                pos = rank_order.index(j)
                cell_color = _RANK_COLORS[pos]
            else:
                cell_color = "#ffffff"

            value_cells += (
                f'<td style="padding:0.7rem 1.2rem;font-family:Mulish,sans-serif;'
                f'font-size:0.82rem;font-weight:700;color:{cell_color};">'
                f'{val_str}</td>'
            )

        body_rows += f'<tr style="background:{row_bg};">{metric_cell}{value_cells}</tr>'

    table_html = f"""
<div style="overflow-x:auto;margin-bottom:1.6rem;">
<table style="width:100%;border-collapse:collapse;background:#0b0e1c;
              border:1px solid #1a1f3a;border-radius:8px;overflow:hidden;">
  <thead>{header_row}</thead>
  <tbody>{body_rows}</tbody>
</table>
</div>"""
    st.markdown(table_html, unsafe_allow_html=True)

    # ── CSV export ───────────────────────────────────────────────────────
    csv_lines = ["Dimension," + ",".join(col_headers)]
    for metric in metric_order:
        vals = [re.sub(r"\*+|_+|`+", "", str(p.get(metric, ""))).strip() for p in all_parsed]
        csv_lines.append(f'"{metric}",' + ",".join(f'"{v}"' for v in vals))
    csv_data = "\n".join(csv_lines)

    st.download_button(
        label="⬇  Export Scores as CSV",
        data=csv_data.encode("utf-8"),
        file_name="benchmark_scores.csv",
        mime="text/csv",
        key="dl_scores_csv",
    )


# ---------------------------------------------------------------------------
# DETAIL FILES PANEL
# ---------------------------------------------------------------------------

def render_detail_files_panel(results: list, cov_result=None):
    """Download & preview result files with agent tab switcher."""
    st.markdown(
        '<div class="section-label" style="margin-top:1.8rem;">DETAIL FILES &amp; DOWNLOAD</div>',
        unsafe_allow_html=True,
    )

    if not results:
        st.markdown(
            '<div class="panel-box panel-box-empty">No result files yet.</div>',
            unsafe_allow_html=True,
        )
        return

    options = [r["filename"] for r in results]
    has_coverage = cov_result is not None
    if has_coverage:
        options = ["Coverage Output"] + options

    sel = st.selectbox(
        "Select result file:", options=options,
        key="result_file_sel", label_visibility="collapsed",
    )

    if sel == "Coverage Output" and has_coverage:
        cov_text  = cov_result.get("coverage_text", "")
        exec_id   = cov_result.get("execution_id", "")
        cov_fname = f"coverage-output-{exec_id[:8]}.txt"

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
            if len(agent_outputs) == 1:
                with st.expander(f"🤖 {agent_outputs[0]['agent_name']}", expanded=True):
                    st.text(agent_outputs[0]["content"])
            else:
                tabs = st.tabs([ao["agent_name"] for ao in agent_outputs])
                for tab, ao in zip(tabs, agent_outputs):
                    with tab:
                        st.text(ao["content"])
    else:
        result = next((r for r in results if r["filename"] == sel), None)
        if not result:
            return

        content = result.get("content", "")
        model   = result.get("model_name", "")
        exec_id = result.get("data", {}).get("execution_id", "")

        # Header row
        meta_col, dl_col = st.columns([3, 2])
        with meta_col:
            st.markdown(
                f'<div style="font-family:Mulish,sans-serif;font-size:0.72rem;'
                f'color:#6c8eff;font-weight:700;">Model: {model or "—"}</div>',
                unsafe_allow_html=True,
            )
            if exec_id:
                st.markdown(
                    f'<div style="font-family:Mulish,sans-serif;font-size:0.62rem;'
                    f'color:#ffffff;">Execution ID: {exec_id}</div>',
                    unsafe_allow_html=True,
                )
        with dl_col:
            st.download_button(
                label=f"⬇  Download {sel}",
                data=content.encode("utf-8"),
                file_name=sel,
                mime="text/plain",
                key=f"dl_{sel}",
            )

        agent_outputs = result.get("agent_outputs", [])
        if agent_outputs:
            if len(agent_outputs) == 1:
                with st.expander(f"🤖 {agent_outputs[0]['agent_name']}", expanded=True):
                    st.markdown(agent_outputs[0]["content"])
            else:
                tabs = st.tabs([ao["agent_name"] for ao in agent_outputs])
                for tab, ao in zip(tabs, agent_outputs):
                    with tab:
                        st.markdown(ao["content"])
        else:
            with st.expander("📄 Raw Content", expanded=True):
                st.code(content, language="text")


# ---------------------------------------------------------------------------
# FULL RESULTS PAGE (called from app.py page_results)
# ---------------------------------------------------------------------------

def render_full_results_page(results: list, cov_result=None):
    """
    Single-column layout: Score Summary followed directly by Detail Files.
    No tabs — detail files section sits immediately below the scoring table.
    """
    render_results_panel(results, cov_result)
    st.markdown("<hr style='border-color:#1e2340;margin:1.5rem 0;'>", unsafe_allow_html=True)
    render_detail_files_panel(results, cov_result)


# ---------------------------------------------------------------------------
# SCORE PARSER
# ---------------------------------------------------------------------------

def _parse_scores_from_result(
    agent_outputs: list, fallback_content: str, model_name: str = ""
) -> dict:
    """
    Parse agent output into an ordered dict of {metric: value}.
    Supports markdown tables, key:value lines, and ### sections.
    """
    combined = "\n".join(ao.get("content", "") for ao in agent_outputs)
    if not combined.strip():
        combined = fallback_content

    scores = OrderedDict()

    # ── Strategy 1: Markdown table ──────────────────────────────────────
    table_match = re.search(r"\|.+\|[\s\S]+?\|[-| :]+\|", combined)
    if table_match:
        lines = combined[table_match.start():].splitlines()
        header_cells = None
        for line in lines:
            line = line.strip()
            if not line.startswith("|"):
                break
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(re.match(r"^[-: ]+$", c) for c in cells if c):
                continue
            if header_cells is None:
                header_cells = cells
                continue
            if len(cells) >= 2:
                key = re.sub(r"\*+|_+|`+", "", cells[0]).strip()
                val = re.sub(r"\*+|_+|`+", "", cells[1] if len(cells) > 1 else "").strip()
                if not key or key.lower() in ("dimension", "metric", "category", "criteria"):
                    continue
                if key.lower() == "model name":
                    if not model_name:
                        model_name = val
                elif key.lower() == "model":
                    model_name = val
                else:
                    scores[key] = val

    # ── Strategy 2: Key: Value lines ────────────────────────────────────
    if not scores:
        for line in combined.splitlines():
            m = re.match(r"^\*?\*?([A-Za-z][\w\s/()-]{1,40}?)\*?\*?\s*[:–—]\s*(.+)$", line.strip())
            if m:
                key = re.sub(r"\*+|_+|`+", "", m.group(1)).strip().rstrip("*").strip()
                val = re.sub(r"\*+|_+|`+", "", m.group(2)).strip()
                if key.lower() in ("model name",):
                    if not model_name:
                        model_name = val
                elif key.lower() == "model":
                    model_name = val
                elif key and len(key) < 50:
                    scores[key] = val

    result = OrderedDict()
    if model_name:
        result["Model Name"] = model_name
    result.update(scores)
    return result


# ---------------------------------------------------------------------------
# Legacy aliases (for backwards compat if anything imports them)
# ---------------------------------------------------------------------------
render_header                   = lambda: None
render_sidebar_uploads          = lambda show_run_btn=True, page="upload": render_top_upload_bar(page=page)
render_upload_section           = lambda: (None, None, [])
render_file_preview             = render_preview_panel
render_operations_grid          = lambda sd: render_execution_panel(sd, None)
render_summary_grid             = lambda results: None
render_result_files_grid        = lambda results: render_detail_files_panel(results)
render_coverage_result_section  = lambda cov: None
