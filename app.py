"""
app.py — AGENTBENCHMARKING (AAVA Design System v2)
Light mode only. Dark mode removed.
"""

import base64
import logging
import os
import threading
import time

import streamlit as st

from backend.workflow import run_benchmark_pipeline
from ui.components import (
    render_coverage_panel,
    render_detail_files_panel,
    render_execution_panel,
    render_full_results_page,
    render_preview_panel,
    render_results_panel,
    render_summary_panel,
    render_top_upload_bar,
)
from utils.file_helpers import get_file_bytes

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="AgentBenchmarking",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Session bootstrap ──────────────────────────────────────────────────────────
def _init_session():
    defaults = {
        "page":                   "upload",
        "status_dict":            {},
        "cancel_event":           None,
        "pipeline_thread":        None,
        "results":                [],
        "coverage_result":        None,
        "summary_result":         None,
        "benchmark_error":        None,
        "_instr_name":            None,
        "_input_name":            None,
        "_output_names":          [],
        "_files_locked":          False,
        "_draft_instr_bytes":     None,
        "_draft_instr_name":      None,
        "_draft_input_bytes":     None,
        "_draft_input_name":      None,
        "_draft_output_files":    None,
        "_pipeline_start_time":   None,
        "_instr_up_gen":          0,
        "_inp_up_gen":            0,
        "_outs_up_gen":           0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_session()

# ── Light mode CSS ─────────────────────────────────────────────────────────────
def _inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:opsz,wght@6..12,300;6..12,400;6..12,500;6..12,600;6..12,700;6..12,800&family=Poppins:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

/* ════════════════════════════════════════════════════════════════
   AAVA DESIGN SYSTEM — Polish Pass v3
   Diagnosis-driven fixes from live screenshots
   ════════════════════════════════════════════════════════════════ */

/* ── Design tokens ───────────────────────────────────────────────── */
:root {
    --accent:    #9B6DFF;
    --accent-dk: #7C4FE0;
    --blue:      #1A73E8;
    --green:     #22C48A;
    --orange:    #F59E0B;
    --red:       #EF4444;
    --t1:        #1A1033;
    --t2:        #3D3260;
    --t3:        #7B6FA0;
    --t4:        #A89DC5;
    --border:    #E2DCF8;
    --border-m:  #C8C0EC;
    --bg-card:   #FFFFFF;
    --bg-tint:   #F8F6FF;
    --bg-input:  #F4F1FD;
    --r-xs: 4px; --r-sm: 8px; --r-md: 12px; --r-lg: 16px; --r-xl: 20px;
    --sh-xs: 0 1px 3px rgba(100,70,200,0.06), 0 1px 2px rgba(100,70,200,0.04);
    --sh-sm: 0 2px 8px rgba(100,70,200,0.08), 0 1px 3px rgba(100,70,200,0.05);
    --sh-md: 0 4px 16px rgba(100,70,200,0.11), 0 2px 6px rgba(100,70,200,0.07);
    --sh-lg: 0 8px 28px rgba(100,70,200,0.14), 0 4px 10px rgba(100,70,200,0.08);
    --tr-fast: 0.14s ease;
    --tr-base: 0.20s ease;
    --background-color: #FFFFFF !important;
    --secondary-background-color: #F8F6FF !important;
}

/* ── Base ────────────────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Nunito Sans', sans-serif !important;
    color: var(--t1) !important;
    -webkit-font-smoothing: antialiased !important;
    -moz-osx-font-smoothing: grayscale !important;
}
h1, h2, h3, h4, h5 {
    font-family: 'Poppins', sans-serif !important;
    color: var(--t1) !important;
    line-height: 1.25 !important;
}
p, span, div, label, li, td, th { color: var(--t1); }
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span { color: var(--t1) !important; }
[data-testid="stText"] { color: var(--t1) !important; }

/* ── App background ──────────────────────────────────────────────── */
.stApp {
    background: linear-gradient(145deg,
        #EAE6FB 0%, #E0DAFA 25%,
        #D5CFFA 55%, #CAC4F7 80%,
        #BDB5F3 100%) !important;
    min-height: 100vh;
}
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 !important; max-width: 100% !important; }
[data-testid="column"] { padding: 0 !important; }

/* ── Scrollbar ───────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-m); border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }

/* ════════════════════════════════════════════════════════════════
   TOP BAR
   Screenshot issue: logo area and title need tighter vertical rhythm
   ════════════════════════════════════════════════════════════════ */
.top-bar {
    background: rgba(255,255,255,0.97);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border-bottom: 1px solid rgba(226,220,248,0.80);
    padding: 0 2rem;
    display: flex; align-items: center; justify-content: space-between;
    position: sticky; top: 0; z-index: 200;
    height: 64px;
    box-shadow: 0 1px 0 rgba(226,220,248,0.60), 0 4px 20px rgba(100,70,200,0.07);
}
.top-bar-left  { flex: 1; display: flex; justify-content: flex-start; align-items: center; }
.top-bar-center { flex: 2; display: flex; justify-content: center; align-items: center; }
.top-bar-right { flex: 1; display: flex; justify-content: flex-end; align-items: center; }
.logo { height: 40px; width: auto; }
.top-bar-title {
    font-family: 'Poppins', sans-serif !important;
    font-size: 1.55rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.03em !important;
    color: var(--t1) !important;
    margin: 0 !important; line-height: 1 !important;
}
.top-bar-title .accent { color: var(--accent) !important; font-weight: 700 !important; }

/* ── Breadcrumb ──────────────────────────────────────────────────── */
.page-indicator {
    font-family: 'Nunito Sans', sans-serif;
    font-size: 0.77rem; font-weight: 600; color: var(--t4);
    display: flex; align-items: center; gap: 4px;
    letter-spacing: 0.01em;
}
.page-indicator .pi-active {
    color: var(--accent); background: rgba(155,109,255,0.10);
    padding: 2px 12px; border-radius: 99px; font-weight: 700;
}
.page-indicator .pi-sep { color: var(--border-m); font-size: 0.82rem; font-weight: 400; }

/* ════════════════════════════════════════════════════════════════
   UPLOAD BAR
   Screenshot issue: columns feel uneven; dropzone height inconsistent
   Fix: equal padding, tighter gap, unified min-height
   ════════════════════════════════════════════════════════════════ */
[data-testid="stHorizontalBlock"]:has(.upload-cell-title) > [data-testid="column"],
[data-testid="stHorizontalBlock"]:has(.upload-cell-title) > [data-testid="stColumn"] {
    background: rgba(255,255,255,0.98) !important;
    border-bottom: 1px solid var(--border) !important;
    padding: 0.9rem 1.25rem 1rem !important;
    vertical-align: top !important;
}
[data-testid="stHorizontalBlock"]:has(.upload-cell-title) > [data-testid="column"]:first-child,
[data-testid="stHorizontalBlock"]:has(.upload-cell-title) > [data-testid="stColumn"]:first-child {
    padding-left: 1.75rem !important;
}
[data-testid="stHorizontalBlock"]:has(.upload-cell-title) > [data-testid="column"]:last-child,
[data-testid="stHorizontalBlock"]:has(.upload-cell-title) > [data-testid="stColumn"]:last-child {
    padding-right: 1.75rem !important;
}
[data-testid="stHorizontalBlock"]:has(.upload-cell-title) > [data-testid="column"]:not(:last-child),
[data-testid="stHorizontalBlock"]:has(.upload-cell-title) > [data-testid="stColumn"]:not(:last-child) {
    border-right: 1px solid var(--border) !important;
}

/* ════════════════════════════════════════════════════════════════
   SPLIT PANELS
   Screenshot issue: left/right panels slightly different whites
   Fix: unified alpha, same padding on both sides
   ════════════════════════════════════════════════════════════════ */
[data-testid="stHorizontalBlock"]:nth-of-type(2) > [data-testid="column"]:first-child {
    background: rgba(255,255,255,0.96) !important;
    border-right: 1px solid var(--border);
    padding: 1.6rem 1.75rem 2.5rem 1.75rem !important;
    min-height: calc(100vh - 130px);
}
[data-testid="stHorizontalBlock"]:nth-of-type(2) > [data-testid="column"]:last-child {
    background: rgba(255,255,255,0.96) !important;
    padding: 1.6rem 1.75rem 2.5rem 1.75rem !important;
}

/* ════════════════════════════════════════════════════════════════
   SECTION LABELS
   Screenshot issue: letter-spacing at 0.95rem is too loose
   Fix: tighter tracking, better margin rhythm
   ════════════════════════════════════════════════════════════════ */
.section-label {
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.02em !important;
    color: var(--accent) !important;
    border-left: 3px solid var(--accent);
    padding-left: 0.65rem;
    margin-bottom: 1.1rem !important;
    text-transform: uppercase !important;
    line-height: 1.4 !important;
    display: block !important;
}

/* ════════════════════════════════════════════════════════════════
   CARDS
   ════════════════════════════════════════════════════════════════ */
.panel-box {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--r-md);
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
    min-height: 80px;
    box-shadow: var(--sh-sm);
    transition: box-shadow var(--tr-base), transform var(--tr-base);
}
.panel-box:hover { box-shadow: var(--sh-md); transform: translateY(-1px); }
.panel-box-empty {
    display: flex; align-items: center; justify-content: center;
    color: var(--t4);
    font-family: 'Nunito Sans', sans-serif;
    font-size: 0.84rem; font-weight: 500;
    min-height: 90px;
    border: 1.5px dashed var(--border-m);
    border-radius: var(--r-md);
    background: rgba(255,255,255,0.45);
    letter-spacing: 0.01em;
}

/* ════════════════════════════════════════════════════════════════
   PIPELINE OP ROWS
   Screenshot issue: grid columns unbalanced; status badge cramped;
   message text clipped too hard; left-border not using status color
   Fix: better grid ratio, status badge width, message max-width
   ════════════════════════════════════════════════════════════════ */
.ops-grid { display: flex; flex-direction: column; gap: 5px; margin-bottom: 0.9rem; }
.op-row {
    display: grid;
    grid-template-columns: 2rem 1fr 5rem 2fr;
    align-items: center; gap: 0.65rem;
    padding: 0.62rem 1rem;
    border-radius: var(--r-sm);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    border: 1px solid var(--border);
    border-left: 3px solid var(--border-m);
    transition: background var(--tr-fast), box-shadow var(--tr-fast);
    background: var(--bg-card);
    box-shadow: var(--sh-xs);
}
.op-row:hover {
    background: var(--bg-tint) !important;
    box-shadow: var(--sh-sm);
}
.op-icon   { font-size: 1rem; white-space: nowrap; text-align: center; }
.op-label  {
    color: var(--t1); font-weight: 600; font-size: 0.83rem;
    font-family: 'Nunito Sans', sans-serif;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.op-status {
    font-size: 0.62rem; letter-spacing: 0.08em; text-align: right;
    font-weight: 700; text-transform: uppercase;
    padding: 0.18rem 0.5rem;
    border-radius: 99px;
    white-space: nowrap;
}
.op-message {
    color: var(--t3); font-size: 0.70rem; overflow: hidden;
    text-overflow: ellipsis; white-space: nowrap;
    min-width: 0;
}

/* ── Spinner ─────────────────────────────────────────────────────── */
@keyframes spin { to { transform: rotate(360deg); } }
.spinner {
    display: inline-block; width: 9px; height: 9px;
    border: 1.5px solid rgba(245,158,11,0.2);
    border-top-color: #F59E0B; border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-left: 3px; vertical-align: middle;
}

/* ════════════════════════════════════════════════════════════════
   BUTTONS
   Screenshot issue: primary button height fine; CANCEL needs
   cleaner border; Export CSV button needs more visual weight
   ════════════════════════════════════════════════════════════════ */
div[data-testid="stButton"] > button,
div[data-testid="stButton"] > button:focus {
    font-family: 'Nunito Sans', sans-serif !important;
    font-size: 0.875rem !important; font-weight: 700 !important;
    border-radius: var(--r-sm) !important;
    letter-spacing: 0.015em !important;
    transition: all var(--tr-fast) !important;
    background-color: var(--bg-tint) !important;
    background-image: none !important;
    color: var(--t2) !important;
    -webkit-text-fill-color: var(--t2) !important;
    outline: none !important;
}
/* PRIMARY — BENCHMARK / RUN AGAIN */
div[data-testid="stButton"] > button[kind="primary"],
div[data-testid="stButton"] > button[kind="primary"]:focus {
    background: linear-gradient(135deg, #9B6DFF 0%, #7C4FE0 100%) !important;
    background-color: #9B6DFF !important;
    border: none !important;
    color: #fff !important; -webkit-text-fill-color: #fff !important;
    height: 46px !important;
    font-size: 0.9rem !important;
    box-shadow: 0 3px 12px rgba(155,109,255,0.35), 0 1px 4px rgba(155,109,255,0.20) !important;
    letter-spacing: 0.04em !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #A87DFF 0%, #8B5FEF 100%) !important;
    background-color: #A87DFF !important;
    color: #fff !important; -webkit-text-fill-color: #fff !important;
    box-shadow: 0 6px 20px rgba(155,109,255,0.45), 0 2px 8px rgba(155,109,255,0.25) !important;
    transform: translateY(-1px) !important;
}
div[data-testid="stButton"] > button[kind="primary"]:active {
    transform: translateY(0) !important;
    box-shadow: 0 1px 6px rgba(155,109,255,0.30) !important;
}
div[data-testid="stButton"] > button[kind="primary"]:disabled,
div[data-testid="stButton"] > button[kind="primary"][disabled] {
    background: rgba(155,109,255,0.15) !important;
    background-color: rgba(155,109,255,0.15) !important;
    color: rgba(155,109,255,0.45) !important;
    -webkit-text-fill-color: rgba(155,109,255,0.45) !important;
    box-shadow: none !important; transform: none !important;
    cursor: not-allowed !important;
}
/* SECONDARY — CANCEL */
div[data-testid="stButton"] > button[kind="secondary"],
div[data-testid="stButton"] > button[kind="secondary"]:focus {
    background: rgba(255,255,255,0.95) !important;
    background-color: rgba(255,255,255,0.95) !important;
    border: 1.5px solid var(--border-m) !important;
    color: var(--t2) !important; -webkit-text-fill-color: var(--t2) !important;
    box-shadow: var(--sh-xs) !important;
    height: 38px !important;
}
div[data-testid="stButton"] > button[kind="secondary"]:hover {
    border-color: var(--red) !important;
    color: var(--red) !important; -webkit-text-fill-color: var(--red) !important;
    background: rgba(239,68,68,0.04) !important; background-color: rgba(239,68,68,0.04) !important;
    box-shadow: 0 2px 8px rgba(239,68,68,0.15) !important;
}
/* ✕ REMOVE BUTTONS */
div[data-testid="stButton"] > button[kind="secondaryFormSubmit"],
div[data-testid="stButton"] > button[kind="secondaryFormSubmit"]:focus {
    background: #FFFFFF !important; background-color: #FFFFFF !important;
    background-image: none !important;
    border: 1px solid var(--border-m) !important;
    color: var(--t3) !important; -webkit-text-fill-color: var(--t3) !important;
    font-size: 0.75rem !important; font-weight: 700 !important;
    border-radius: var(--r-xs) !important;
    padding: 2px 7px !important;
    height: 26px !important; min-height: 26px !important;
    line-height: 1 !important; box-shadow: none !important;
    transition: all var(--tr-fast) !important;
}
div[data-testid="stButton"] > button[kind="secondaryFormSubmit"]:hover {
    border-color: var(--red) !important; color: var(--red) !important;
    -webkit-text-fill-color: var(--red) !important;
    background: rgba(239,68,68,0.05) !important;
    background-color: rgba(239,68,68,0.05) !important;
}
/* DOWNLOAD — Export CSV needs more weight */
div[data-testid="stDownloadButton"] > button {
    font-family: 'Nunito Sans', sans-serif !important;
    font-size: 0.83rem !important; font-weight: 700 !important;
    background: rgba(155,109,255,0.08) !important;
    border: 1.5px solid rgba(155,109,255,0.28) !important;
    color: var(--accent) !important; border-radius: var(--r-sm) !important;
    transition: all var(--tr-fast) !important;
    padding: 0.35rem 1rem !important;
    letter-spacing: 0.01em !important;
}
div[data-testid="stDownloadButton"] > button:hover {
    background: rgba(155,109,255,0.14) !important;
    border-color: rgba(155,109,255,0.45) !important;
    box-shadow: 0 2px 10px rgba(155,109,255,0.22) !important;
    transform: translateY(-1px) !important;
}

/* ════════════════════════════════════════════════════════════════
   FILE UPLOADER — equal-height dropzones, no ghost button
   Streamlit renders: [dropzone] > [div.text-section] + [div.button-section]
   The ghost rectangle is the button-section div getting visible styles.
   Fix: row layout with text left / button right, equal fixed height.
   ════════════════════════════════════════════════════════════════ */
[data-testid="stFileUploader"],
section[data-testid="stFileUploader"] {
    background: transparent !important;
}
[data-testid="stFileUploaderDropzone"] {
    background: var(--bg-input) !important;
    border: 1.5px dashed var(--border-m) !important;
    border-radius: var(--r-sm) !important;
    padding: 0.6rem 1rem !important;
    /* Fixed equal height across all 3 columns */
    height: 86px !important;
    min-height: 86px !important;
    max-height: 86px !important;
    /* Row: text on left, Browse button on right */
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    justify-content: space-between !important;
    gap: 0.75rem !important;
    overflow: hidden !important;
    box-sizing: border-box !important;
    transition: border-color var(--tr-fast), background var(--tr-fast);
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--accent) !important;
    background: rgba(155,109,255,0.03) !important;
}
/* Text container (first child div inside dropzone) */
[data-testid="stFileUploaderDropzone"] > div:first-child {
    display: flex !important;
    flex-direction: column !important;
    align-items: flex-start !important;
    justify-content: center !important;
    gap: 0 !important;
    flex: 1 1 auto !important;
    min-width: 0 !important;
    background: transparent !important;
}
/* Ghost button container (second child) — hide the wrapper div,
   keep the button itself visible via the button selector below */
[data-testid="stFileUploaderDropzone"] > div:last-child {
    display: flex !important;
    flex: 0 0 auto !important;
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
}
[data-testid="stFileUploaderDropzone"] p,
[data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] small {
    color: var(--t3) !important;
    font-family: 'Nunito Sans', sans-serif !important;
    font-size: 0.80rem !important; font-weight: 500 !important;
    line-height: 1.45 !important;
    margin: 0 !important;
    white-space: normal !important;
}
[data-testid="stFileUploaderDropzone"] svg { display: none !important; }
[data-testid="stFileUploaderDropzone"] label { display: none !important; }
[data-testid="stFileUploaderFile"] { display: none !important; }
[data-testid="stFileUploaderFileData"] { display: none !important; }
[data-testid="stFileUploaderFileName"] { display: none !important; }
section[data-testid="stFileUploader"] > div:last-child > div { display: none !important; }
/* Browse files button — right-aligned in the row */
[data-testid="stFileUploaderDropzone"] button,
[data-testid="stFileUploader"] button {
    background: var(--bg-card) !important; background-color: var(--bg-card) !important;
    border: 1px solid var(--border-m) !important;
    color: var(--t2) !important; -webkit-text-fill-color: var(--t2) !important;
    font-family: 'Nunito Sans', sans-serif !important;
    font-size: 0.80rem !important; font-weight: 600 !important;
    border-radius: var(--r-sm) !important;
    padding: 0.32rem 1rem !important;
    height: 34px !important;
    cursor: pointer !important;
    transition: all var(--tr-fast) !important;
    box-shadow: var(--sh-xs) !important;
    white-space: nowrap !important;
    flex-shrink: 0 !important;
}
[data-testid="stFileUploaderDropzone"] button:hover,
[data-testid="stFileUploader"] button:hover {
    border-color: var(--accent) !important; color: var(--accent) !important;
    -webkit-text-fill-color: var(--accent) !important;
    box-shadow: 0 2px 8px rgba(155,109,255,0.16) !important;
}

/* ════════════════════════════════════════════════════════════════
   SELECT BOX
   ════════════════════════════════════════════════════════════════ */
div[data-testid="stSelectbox"] [data-baseweb="select"] > div:first-child {
    background: #FFFFFF !important;
    border: 1px solid var(--border-m) !important;
    border-radius: var(--r-sm) !important;
    box-shadow: var(--sh-xs) !important;
    min-height: 38px !important;
    transition: border-color var(--tr-fast), box-shadow var(--tr-fast) !important;
}
div[data-testid="stSelectbox"] [data-baseweb="select"] > div:first-child:hover {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(155,109,255,0.10) !important;
}
div[data-testid="stSelectbox"] [data-baseweb="select"] span,
div[data-testid="stSelectbox"] [data-baseweb="select"] div[class*="singleValue"] {
    color: #1A1033 !important;
    font-family: 'Nunito Sans', sans-serif !important;
    font-size: 0.88rem !important; font-weight: 500 !important;
    background: transparent !important;
}
[data-baseweb="popover"] > div, [data-baseweb="popover"] [data-baseweb="menu"] {
    background: #FFFFFF !important;
    border: 1px solid var(--border-m) !important;
    border-radius: var(--r-sm) !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.09), 0 2px 8px rgba(0,0,0,0.06) !important;
    overflow: hidden !important;
}
[data-baseweb="menu"] li, [data-baseweb="option"], [role="option"] {
    background: #FFFFFF !important; color: #1A1033 !important;
    font-family: 'Nunito Sans', sans-serif !important;
    font-size: 0.86rem !important; font-weight: 500 !important;
    border-radius: 6px !important; padding: 0.4rem 0.75rem !important;
    transition: background var(--tr-fast) !important;
}
[data-baseweb="menu"] li:hover, [data-baseweb="option"]:hover,
[role="option"][aria-selected="true"] {
    background: rgba(155,109,255,0.08) !important; color: var(--accent) !important;
}

/* ════════════════════════════════════════════════════════════════
   EXPANDERS
   Screenshot issue: double-arrow still visible from competing selectors
   Fix: hide both SVG and the icon wrapper element absolutely
   Also: expander details border-top gives clear content separation
   ════════════════════════════════════════════════════════════════ */
div[data-testid="stExpander"] {
    background: #FFFFFF !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r-md) !important;
    box-shadow: var(--sh-xs) !important;
    overflow: hidden !important;
    margin-bottom: 6px !important;
    transition: box-shadow var(--tr-fast) !important;
}
div[data-testid="stExpander"]:hover { box-shadow: var(--sh-sm) !important; }
div[data-testid="stExpander"] > div { background: #FFFFFF !important; }
div[data-testid="stExpander"] summary {
    background: #FFFFFF !important;
    padding: 0.75rem 1.1rem !important;
    display: flex !important; align-items: center !important;
    gap: 0.55rem !important; cursor: pointer !important;
    list-style: none !important;
    transition: background var(--tr-fast) !important;
    min-height: 48px !important;
}
div[data-testid="stExpander"] summary:hover { background: rgba(155,109,255,0.025) !important; }
/* Kill ALL native Streamlit toggle icons — every possible selector */
div[data-testid="stExpander"] summary::-webkit-details-marker { display: none !important; }
div[data-testid="stExpander"] summary::marker { display: none !important; content: '' !important; }
div[data-testid="stExpander"] summary svg { display: none !important; visibility: hidden !important; width: 0 !important; height: 0 !important; }
div[data-testid="stExpander"] summary [data-testid="stExpanderToggleIcon"] { display: none !important; width: 0 !important; height: 0 !important; overflow: hidden !important; }
div[data-testid="stExpander"] summary [data-testid="stExpanderToggleIcon"] * { display: none !important; }
/* Single custom arrow */
div[data-testid="stExpander"] summary::before {
    content: '▶' !important;
    font-size: 0.55rem !important; color: var(--t4) !important;
    flex: 0 0 auto !important; line-height: 1 !important;
    transition: color var(--tr-fast) !important;
    display: inline-block !important;
    margin-right: 0.1rem !important;
}
div[data-testid="stExpander"] details[open] summary::before,
details[open] div[data-testid="stExpander"] summary::before,
div[data-testid="stExpander"] > details[open] > summary::before {
    content: '▼' !important; color: var(--accent) !important;
}
div[data-testid="stExpander"] summary > span,
div[data-testid="stExpander"] summary > p {
    color: var(--t1) !important;
    font-family: 'Nunito Sans', sans-serif !important;
    font-size: 0.90rem !important; font-weight: 600 !important;
    background: transparent !important;
    white-space: nowrap !important; overflow: hidden !important;
    text-overflow: ellipsis !important; flex: 1 !important; min-width: 0 !important;
}
div[data-testid="stExpander"] div[data-testid="stExpanderDetails"],
div[data-testid="stExpander"] div[data-testid="stExpanderDetails"] > div {
    background: #FFFFFF !important;
    padding: 0.75rem 1.1rem 1.1rem !important;
    border-top: 1px solid var(--border) !important;
}
div[data-testid="stExpander"] p,
div[data-testid="stExpander"] div:not([data-testid]),
div[data-testid="stExpander"] span:not([class*="keyboard"]):not([class*="shortcut"]) {
    color: var(--t1) !important; background: transparent !important;
}

/* ════════════════════════════════════════════════════════════════
   TABS
   ════════════════════════════════════════════════════════════════ */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: transparent !important; gap: 2px !important;
    border-bottom: 2px solid var(--border) !important;
    padding-bottom: 0 !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent !important; border-radius: 6px 6px 0 0 !important;
    color: var(--t3) !important;
    font-family: 'Nunito Sans', sans-serif !important;
    font-size: 0.84rem !important; font-weight: 600 !important;
    padding: 0.5rem 1rem !important;
    transition: color var(--tr-fast), background var(--tr-fast) !important;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover {
    color: var(--t2) !important;
    background: rgba(155,109,255,0.04) !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: rgba(155,109,255,0.07) !important; color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important; font-weight: 700 !important;
}
[data-testid="stTabs"] [role="tabpanel"] { padding-top: 0.75rem !important; }

/* ════════════════════════════════════════════════════════════════
   SCORE TABLE — full width, proper border, visual separation
   Screenshot issue: table is too narrow, only 25% of page width
   The table inherits proper width from its container — ensure
   container is full width and table has consistent cell sizing
   ════════════════════════════════════════════════════════════════ */
.score-table {
    width: 100% !important;
    border-collapse: collapse !important;
    background: #FFFFFF !important;
    border-radius: var(--r-md) !important;
    overflow: hidden !important;
    font-family: 'Nunito Sans', sans-serif !important;
}
.score-table thead tr {
    border-bottom: 2px solid var(--border) !important;
}
.score-table th {
    background: var(--bg-tint) !important;
    padding: 0.85rem 1.25rem !important;
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.84rem !important; font-weight: 700 !important;
    color: var(--t1) !important;
    text-align: left !important;
    white-space: nowrap !important;
    letter-spacing: 0.01em !important;
}
.score-table td {
    padding: 0.78rem 1.25rem !important;
    font-size: 0.86rem !important;
    border-bottom: 1px solid var(--border) !important;
    vertical-align: middle !important;
}
.score-table tr:last-child td { border-bottom: none !important; }
.score-table tbody tr:hover { background: rgba(155,109,255,0.03) !important; }

/* ════════════════════════════════════════════════════════════════
   ALERTS / HR
   ════════════════════════════════════════════════════════════════ */
.stSuccess, .stInfo, .stError, .stWarning {
    border-radius: var(--r-sm) !important;
    font-size: 0.86rem !important;
    font-family: 'Nunito Sans', sans-serif !important;
}
hr {
    border: none !important;
    border-top: 1px solid var(--border) !important;
    margin: 1.25rem 0 !important;
    opacity: 0.8;
}
</style>
""", unsafe_allow_html=True)



# ── Logo loader ────────────────────────────────────────────────────────────────
@st.cache_data
def _load_logo() -> str:
    for path in ("logo.png", "image (1).png"):
        if os.path.exists(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
    return ""

_logo_b64 = _load_logo()


def _top_bar(page_label: str = "UPLOAD"):
    page_steps = ["UPLOAD", "RUNNING", "RESULTS"]
    crumbs_html = ""
    for i, s in enumerate(page_steps):
        if i > 0:
            crumbs_html += '<span class="pi-sep">›</span>'
        if s == page_label:
            crumbs_html += f'<span class="pi-active">{s}</span>'
        else:
            crumbs_html += f'<span style="color:#A89DC5">{s}</span>'

    logo_img = (
        f'<img src="data:image/png;base64,{_logo_b64}" class="logo">'
        if _logo_b64 else ""
    )
    st.markdown(
        f"""
        <div class="top-bar">
            <div class="top-bar-left">{logo_img}</div>
            <div class="top-bar-center">
                <h1 class="top-bar-title">Agent<span class="accent" style="color:#9B6DFF !important;font-family:'Poppins',sans-serif;font-weight:700;">Benchmarking</span></h1>
            </div>
            <div class="top-bar-right">
                <div class="page-indicator">{crumbs_html}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )




# ── PAGE: UPLOAD ───────────────────────────────────────────────────────────────
def page_upload():
    _inject_css()
    _top_bar("UPLOAD")

    instr_f, input_f, out_fs, run_clicked = render_top_upload_bar(page="upload")

    left, right = st.columns([70, 30], gap="small")

    t1     = "#1A1033"
    t2     = "#3D3260"
    t3     = "#7B6FA0"
    green  = "#22C48A"
    border = "#E2DCF8"

    with left:
        render_preview_panel(instr_f, input_f, out_fs)

    with right:
        st.markdown('<div class="section-label">BENCHMARK</div>', unsafe_allow_html=True)

        checks = [
            ("📋 Instruction file", instr_f is not None),
            ("📥 Input file",        input_f is not None),
            ("📤 Output file(s)",    len(out_fs) > 0),
        ]
        check_html = '<div style="display:flex;flex-direction:column;gap:5px;margin-bottom:1rem;">'
        for label, ok in checks:
            icon  = "✅" if ok else "⬜"
            color = green if ok else t3
            bg    = "rgba(34,196,138,0.06)" if ok else "rgba(255,255,255,0.5)"
            bd    = "rgba(34,196,138,0.20)" if ok else border
            check_html += (
                f'<div style="font-family:Nunito Sans,sans-serif;font-size:0.88rem;'
                f'font-weight:600;color:{color};padding:0.4rem 0.75rem;'
                f'background:{bg};border-radius:8px;border:1px solid {bd};'
                f'display:flex;align-items:center;gap:0.5rem;">'
                f'{icon} {label}</div>'
            )
        check_html += "</div>"
        st.markdown(check_html, unsafe_allow_html=True)

        if not all(ok for _, ok in checks):
            st.markdown(
                '<div class="panel-box-empty">Upload all three files to begin benchmarking</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="panel-box" style="display:flex;align-items:center;justify-content:center;'
                f'color:{green};font-family:Nunito Sans,sans-serif;font-size:0.95rem;font-weight:700;">'
                f'✅ All files ready — click BENCHMARK to start'
                f'</div>',
                unsafe_allow_html=True,
            )

    all_ready = instr_f is not None and input_f is not None and len(out_fs) > 0
    if run_clicked and all_ready:
        st.session_state._instr_name   = instr_f.name
        st.session_state._input_name   = input_f.name
        st.session_state._output_names = [f.name for f in out_fs]
        _start_pipeline(instr_f, input_f, out_fs)


# ── PAGE: RUNNING ──────────────────────────────────────────────────────────────
def page_running():
    _inject_css()
    _top_bar("RUNNING")
    render_top_upload_bar(page="running")

    sd         = st.session_state.status_dict
    cov_result = st.session_state.get("coverage_result")
    t3         = "#7B6FA0"

    start_t = st.session_state.get("_pipeline_start_time")
    if start_t:
        elapsed = int(time.time() - start_t)
        mins, secs = divmod(elapsed, 60)
        st.markdown(
            f'<div style="font-family:JetBrains Mono,monospace;font-size:0.72rem;'
            f'color:{t3};text-align:right;padding:0.3rem 1.75rem 0.1rem;'
            f'letter-spacing:0.03em;opacity:0.85;">'
            f'⏱ {mins:02d}:{secs:02d}</div>',
            unsafe_allow_html=True,
        )

    left, right = st.columns([60, 40], gap="small")

    with left:
        render_coverage_panel(sd, cov_result)

    with right:
        _, btn_col = st.columns([7, 3])
        with btn_col:
            if st.button("⛔  CANCEL", type="secondary", use_container_width=True):
                if st.session_state.cancel_event:
                    st.session_state.cancel_event.set()
                st.session_state.status_dict     = {}
                st.session_state.results         = []
                st.session_state.coverage_result = None
                st.session_state.pipeline_thread = None
                st.session_state.benchmark_error = None
                st.session_state._files_locked   = False
                st.session_state.page = "upload"
                st.rerun()

        render_execution_panel(sd, cov_result)

        pipeline_done  = sd.get("_done", False)
        pipeline_error = sd.get("_error")
        cancelled      = st.session_state.cancel_event and st.session_state.cancel_event.is_set()

        if pipeline_done:
            _transfer_results_if_ready()
            st.session_state.page = "results"
            st.rerun()
        elif pipeline_error:
            st.error(f"🚨 {pipeline_error}")
        elif cancelled:
            st.warning("Benchmarking cancelled.")
        else:
            cov_in_dict = sd.get("_coverage_result")
            if cov_in_dict and not st.session_state.get("coverage_result"):
                st.session_state.coverage_result = cov_in_dict
            time.sleep(1)
            st.rerun()


# ── PAGE: RESULTS ──────────────────────────────────────────────────────────────
def page_results():
    _inject_css()
    _top_bar("RESULTS")
    render_top_upload_bar(page="results")

    results      = st.session_state.results
    cov_result   = st.session_state.get("coverage_result")
    summ_result  = st.session_state.get("summary_result")

    _, btn_col = st.columns([7, 3])
    with btn_col:
        if st.button("🔄  RUN AGAIN", type="primary", use_container_width=True):
            st.session_state.status_dict     = {}
            st.session_state.results         = []
            st.session_state.coverage_result = None
            st.session_state.summary_result  = None
            st.session_state.cancel_event    = None
            st.session_state.pipeline_thread = None
            st.session_state.benchmark_error = None
            st.session_state._files_locked   = False
            st.session_state._pipeline_start_time = None

            # ── Restore previous run files into draft state ───────────────
            # Cycle uploader generation keys so widgets are fresh (no stale
            # native file-list UI), then re-populate drafts from saved bytes.
            st.session_state["_instr_up_gen"] = st.session_state.get("_instr_up_gen", 0) + 1
            st.session_state["_inp_up_gen"]   = st.session_state.get("_inp_up_gen",   0) + 1
            st.session_state["_outs_up_gen"]  = st.session_state.get("_outs_up_gen",  0) + 1

            if st.session_state.get("_saved_instruction_bytes"):
                st.session_state["_draft_instr_bytes"] = st.session_state["_saved_instruction_bytes"]
                st.session_state["_draft_instr_name"]  = st.session_state["_saved_instruction_name"]

            if st.session_state.get("_saved_input_bytes"):
                st.session_state["_draft_input_bytes"] = st.session_state["_saved_input_bytes"]
                st.session_state["_draft_input_name"]  = st.session_state["_saved_input_name"]

            if st.session_state.get("_saved_output_file_data"):
                st.session_state["_draft_output_files"] = [
                    {"name": f["name"], "bytes": f["bytes"]}
                    for f in st.session_state["_saved_output_file_data"]
                ]

            st.session_state.page = "upload"
            st.rerun()

    st.markdown("<div style='padding:0.8rem 1.5rem 1.5rem;'>", unsafe_allow_html=True)
    render_full_results_page(results, cov_result, summ_result)
    st.markdown("</div>", unsafe_allow_html=True)


# ── Pipeline launcher ──────────────────────────────────────────────────────────
def _start_pipeline(instruction_file, input_file, output_files):
    instruction_bytes = get_file_bytes(instruction_file)
    input_bytes       = get_file_bytes(input_file)
    output_file_data  = [{"name": f.name, "bytes": get_file_bytes(f)} for f in output_files]

    st.session_state._saved_instruction_bytes = instruction_bytes
    st.session_state._saved_instruction_name  = instruction_file.name
    st.session_state._saved_input_bytes       = input_bytes
    st.session_state._saved_input_name        = input_file.name
    st.session_state._saved_output_file_data  = output_file_data

    cancel_event   = threading.Event()
    status_dict    = {}
    results_holder = []

    def result_callback(results):
        results_holder.clear()
        results_holder.extend(results)

    thread = threading.Thread(
        target=run_benchmark_pipeline,
        kwargs=dict(
            instruction_bytes=instruction_bytes,
            instruction_filename=instruction_file.name,
            input_bytes=input_bytes,
            input_filename=input_file.name,
            output_files=output_file_data,
            status_dict=status_dict,
            cancel_event=cancel_event,
            result_callback=result_callback,
        ),
        daemon=True,
    )

    st.session_state.cancel_event          = cancel_event
    st.session_state.status_dict           = status_dict
    st.session_state._results_holder       = results_holder
    st.session_state.pipeline_thread       = thread
    st.session_state.coverage_result       = None
    st.session_state.page                  = "running"
    st.session_state._files_locked         = True
    st.session_state._pipeline_start_time  = time.time()

    # ── Clear all draft state + cycle uploader generation keys ────────────
    # Streamlit file uploader widgets hold their file in session state under
    # their key. Cycling the generation key forces a new empty widget on the
    # next render, completely purging the uploaded file from the widget state.
    # Without this, the uploader's native file-list UI bleeds into the running
    # page even though the Python if/else branch does not call st.file_uploader.
    st.session_state.pop("_draft_instr_bytes", None)
    st.session_state.pop("_draft_instr_name",  None)
    st.session_state.pop("_draft_input_bytes", None)
    st.session_state.pop("_draft_input_name",  None)
    st.session_state.pop("_draft_output_files", None)
    st.session_state["_instr_up_gen"] = st.session_state.get("_instr_up_gen", 0) + 1
    st.session_state["_inp_up_gen"]   = st.session_state.get("_inp_up_gen",   0) + 1
    st.session_state["_outs_up_gen"]  = st.session_state.get("_outs_up_gen",  0) + 1
    thread.start()
    st.rerun()


def _transfer_results_if_ready():
    holder = st.session_state.get("_results_holder", [])
    if holder and st.session_state.status_dict.get("_done"):
        st.session_state.results = list(holder)
    cov = st.session_state.status_dict.get("_coverage_result")
    if cov:
        st.session_state.coverage_result = cov
    summ = st.session_state.status_dict.get("_summary_result")
    if summ:
        st.session_state.summary_result = summ


# ── Router ─────────────────────────────────────────────────────────────────────
_transfer_results_if_ready()

_page = st.session_state.page
if _page == "upload":
    page_upload()
elif _page == "running":
    page_running()
elif _page == "results":
    page_results()
else:
    st.session_state.page = "upload"
    st.rerun()