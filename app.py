"""
app.py
------
AGENTBENCHMARKING — wireframe-exact layout.

Layout (all pages):
  ┌──────────────────────────────────────────────────────────────────────┐
  │               AgentBenchmarking  (sticky top bar)                    │
  ├────────────────────┬──────────────────────┬──────────────────────────┤
  │ 📋 Instruction     │ 📥 Input File        │ 📤 Output Files          │
  │    [uploader]      │    [uploader]        │    [uploader]            │
  │                    │                      │    [🚀 BENCHMARK]        │
  ├────────────────────┴──────────────────────┴──────────────────────────┤
  │  LEFT (40%)                    │  RIGHT (60%)                        │
  │  Dropdown — file viewer        │  BENCHMARK ops grid + pills         │
  │                                │  SCORE SUMMARY                      │
  │                                │  DOWNLOAD & VIEW DETAIL FILES       │
  └────────────────────────────────┴─────────────────────────────────────┘
"""

import logging
import threading
import time

import streamlit as st

from ui.components import (
    render_top_upload_bar,
    render_preview_panel,
    render_execution_panel,
    render_coverage_panel,
    render_results_panel,
    render_detail_files_panel,
)
from backend.workflow import run_benchmark_pipeline
from utils.file_helpers import get_file_bytes

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AgentBenchmarking",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap');

/* ── reset / base ──────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background: #0b0d14;
    color: #d4d8e8;
}
.stApp { background: #0b0d14; }
#MainMenu, footer, header { visibility: hidden; }
.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}
[data-testid="column"] { padding: 0 !important; }

/* ── STICKY TOP BAR ────────────────────────────────────────────── */
.top-bar {
    background: #0e1020;
    border-bottom: 1px solid #1e2340;
    padding: 0.65rem 1.8rem;
    display: flex;
    align-items: center;
    justify-content: space-between; /* Pushes the 3 sections apart */
    position: sticky;
    top: 0;
    z-index: 100;
    height: 100px; /* Define a fixed height for better alignment */
}

.top-bar-left {
    flex: 1; /* Takes up 1/3 of space on the left */
    display: flex;
    justify-content: flex-start;
    align-items: center;
}

.top-bar-center {
    flex: 2; /* Takes up middle space */
    display: flex;
    justify-content: center;
    align-items: center;
}

.top-bar-right {
    flex: 1; /* Invisible counterweight to keep center perfect */
}

.logo {
    height: 75px; /* Adjust height to fit your preference */
    width: auto;
}

.top-bar-title {
    font-size:2rem !important; /* Larger impact for the main brand */
    font-weight: 800;
    letter-spacing: -0.02em; /* Tighter tracking for modern look */
}
.top-bar-title .accent { color: #6c8eff; }

/* ── UPLOAD BAR (3 cols) ───────────────────────────────────────── */
/* Slight background tint on all 3 upload columns */
[data-testid="stHorizontalBlock"]:nth-of-type(2) > [data-testid="column"] {
    background: #0e1020 !important;
    border-bottom: 1px solid #1e2340;
    padding: 0.7rem 1rem 0.8rem !important;
}
[data-testid="stHorizontalBlock"]:nth-of-type(2) > [data-testid="column"]:not(:last-child) {
    border-right: 1px solid #1e2340;
}

/* ── UPLOAD CELL styles (injected by component) ────────────────── */
.upload-cell-title {
    font-family: 'Space Mono', monospace;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: #8890b8;
    margin-bottom: 0.35rem;
}
.upload-cell-ok {
    font-size: 1.2rem !important; 
    font-weight: 500;
    margin-top: 0.4rem;
}

/* ── BOTTOM SPLIT — left 40% / right 60% ──────────────────────── */
/* Left col gets a subtle border */
[data-testid="stHorizontalBlock"]:nth-of-type(3) > [data-testid="column"]:first-child {
    border-right: 1px solid #1e2340;
    padding: 1.1rem 1.2rem 1.5rem !important;
    min-height: calc(100vh - 120px);
}
[data-testid="stHorizontalBlock"]:nth-of-type(3) > [data-testid="column"]:last-child {
    padding: 1.1rem 1.5rem 1.5rem !important;
}

/* ── Section labels ────────────────────────────────────────────── */
.section-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.92rem !important; /* Increased as requested */
    letter-spacing: 0.22em;
    color: #6c8eff; /* Changed to match primary accent for better visibility */
    border-left: 2px solid #6c8eff;
    padding-left: 0.55rem;
    margin-bottom: 1.2rem !important;
    text-transform: uppercase;
}

/* ── Panel boxes ───────────────────────────────────────────────── */
.panel-box {
    background: #0e1020;
    border: 1px solid #1e2340;
    border-radius: 8px;
    padding: 1.1rem 1.3rem;
    margin-bottom: 0.9rem;
    min-height: 120px;
}
.panel-box-empty {
    display: flex;
    align-items: center;
    justify-content: center;
    color: #afb2ba;
    font-family: 'Space Mono', monospace;
    font-size: 0.92rem;
    letter-spacing: 0.08em;
    min-height: 120px;
}

/* ── Ops grid ──────────────────────────────────────────────────── */
.ops-grid { display: flex; flex-direction: column; gap: 5px; }
.op-row {
    display: grid;
    grid-template-columns: 2rem 1.7fr 6.5rem 3fr;
    align-items: center;
    gap: 0.75rem;
    padding: 0.55rem 0.9rem;
    border-radius: 5px;
    font-family: 'Space Mono', monospace;
    font-size: 0.73rem;
}
.op-icon  { font-size: 0.95rem; white-space: nowrap; }
.op-label { color: #c8cce8; font-weight: 700; }
.op-status { font-size: 0.56rem; letter-spacing: 0.1em; text-align: right; }
.op-message { color: #5a6090; font-size: 0.67rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

@keyframes spin { to { transform: rotate(360deg); } }
.spinner {
    display: inline-block;
    width: 9px; height: 9px;
    border: 2px solid #f59e0b33;
    border-top-color: #f59e0b;
    border-radius: 50%;
    animation: spin 0.75s linear infinite;
    margin-left: 4px;
    vertical-align: middle;
}

/* ── Coverage box ──────────────────────────────────────────────── */
.coverage-box {
    background: #080b14;
    border: 1px solid #1e2a50;
    border-radius: 6px;
    padding: 0.85rem 1rem;
    margin-top: 0.5rem;
    font-family: 'Space Mono', monospace;
    font-size: 0.69rem;
    color: #8090b8;
    white-space: pre-wrap;
    max-height: 260px;
    overflow-y: auto;
}

/* ── Scoring card ──────────────────────────────────────────────── */
.scoring-card {
    background: #0e1020;
    border: 1px solid #1e2340;
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.7rem;
}
.scoring-card-filename {
    font-family: 'Space Mono', monospace;
    font-size: 0.72rem;
    color: #6c8eff;
    font-weight: 700;
    margin-bottom: 0.55rem;
    word-break: break-all;
}

/* ── Action bar (cancel / re-run) ──────────────────────────────── */
.action-bar {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 0.7rem;
}

/* ── Preview meta ──────────────────────────────────────────────── */
.preview-meta {
    font-family: 'Space Mono', monospace;
    font-size: 0.9rem;
    color: #3d4466;
    margin-bottom: 0.4rem;
}

/* ── Streamlit widget overrides ────────────────────────────────── */
div[data-testid="stButton"] > button {
    font-family: 'Space Mono', monospace !important;
    font-size: 0.85rem !important; /* Slightly larger text for the button */
    letter-spacing: 0.08em !important;
    border-radius: 5px !important;
    transition: all 0.12s ease !important;
}
            
/* ── Streamlit widget overrides ────────────────────────────────── */
div[data-testid="stButton"] > button[kind="primary"] {
    background: #6c8eff !important; /* The specific blue accent color */
    border-color: #6c8eff !important;
    color: #fff !important;
    height: 45px !important; /* Makes the button more prominent */
    font-weight: 700 !important;
}

div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #8aaeff !important; /* Lighter blue on hover */
    border-color: #8aaeff !important;
}
div[data-testid="stButton"] > button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid #2a3060 !important;
    color: #8890b8 !important;
}
div[data-testid="stButton"] > button[kind="secondary"]:hover {
    border-color: #ef4444 !important;
    color: #ef4444 !important;
}
.stSelectbox > div > div {
    background: #111422 !important;
    border-color: #1e2340 !important;
    color: #d4d8e8 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 1.2rem !important;
}
.stCode pre {
    background: #080b14 !important;
    border: 1px solid #1e2340 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.75rem !important; /* Slightly larger for readability */
    border-radius: 8px !important;
    
    /* Remove the 400px limit and allow scrolling for long files */
    max-height: 1200px !important; 
    min-height: 400px !important;
    overflow-y: auto !important;
    white-space: pre !important; /* Ensures formatting is preserved */
}

/* Fix for the Streamlit Code Block container */
[data-testid="stCodeBlock"] {
    margin-bottom: 2rem !important;
}
div[data-testid="stExpander"] {
    background: #0e1020 !important;
    border: 1px solid #1e2340 !important;
    border-radius: 6px !important;
}
hr { border-color: #1e2340 !important; margin: 0.8rem 0 !important; }
.stSuccess, .stInfo, .stError, .stWarning { border-radius: 5px !important; font-size: 0.72rem !important; }

div[data-testid="stDownloadButton"] > button {
    font-family: 'Space Mono', monospace !important;
    font-size: 0.70rem !important;
    background: #111422 !important;
    border: 1px solid #2a3060 !important;
    color: #6c8eff !important;
    border-radius: 5px !important;
    letter-spacing: 0.06em !important;
}
div[data-testid="stDownloadButton"] > button:hover {
    background: #1a1f36 !important;
    border-color: #6c8eff !important;
}
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
def _init():
    defaults = {
        "page":             "upload",
        "status_dict":      {},
        "cancel_event":     None,
        "pipeline_thread":  None,
        "results":          [],
        "coverage_result":  None,
        "benchmark_error":  None,
        "_instr_name":      None,
        "_input_name":      None,
        "_output_names":    [],
        "split_ratio":      75,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()

import base64
def load_logo():
    with open("image (1).png", "rb") as f:
        return base64.b64encode(f.read()).decode()

logo_base64 = load_logo()

def _top_bar():
    st.markdown(f"""
    <div class="top-bar">
        <div class="top-bar-left">
            <img src="data:image/png;base64,{logo_base64}" class="logo">
        </div>
        <div class="top-bar-center">
            <h1 class="top-bar-title">
                Agent<span class="accent">Benchmarking</span>
            </h1>
        </div>
        <div class="top-bar-right"></div>
    </div>
    """, unsafe_allow_html=True)

# ── Split-ratio slider (persisted in session state) ───────────────────────────
def _split_ratio_slider():
    """Thin drag-slider row between upload bar and content panels."""
    st.markdown("""
    <style>
    .resizer-row {
        background: #0b0d14;
        border-bottom: 1px solid #1e2340;
        padding: 0.15rem 1rem 0.2rem;
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }
    .resizer-label {
        font-family: 'Space Mono', monospace;
        font-size: 0.9rem;
        color: #afb2ba;
        letter-spacing: 0.14em;
        white-space: nowrap;
    }
    /* shrink the slider track */
    div[data-testid="stSlider"] {
        padding: 0 !important;
    }
    div[data-testid="stSlider"] > label { display: none !important; }
    div[data-testid="stSlider"] [data-baseweb="slider"] { margin: 0 !important; }
    </style>
    <div class="resizer-row">
        <span class="resizer-label">◀ LEFT / RIGHT ▶</span>
    </div>
    """, unsafe_allow_html=True)

    ratio = st.slider(
        "split", min_value=25, max_value=80, step=5,
        value=st.session_state.get("split_ratio", 75),
        key="split_slider",
        label_visibility="collapsed",
    )
    st.session_state["split_ratio"] = ratio
    return ratio


# ── PAGE: UPLOAD ──────────────────────────────────────────────────────────────
def page_upload():
    _top_bar()

    # ── 3-column upload bar ───────────────────────────────────────
    instr_f, input_f, out_fs, run_clicked = render_top_upload_bar(page="upload")

    ratio = _split_ratio_slider()
    _r = 100 - ratio

    # ── Bottom split (resizable) ─────────────────────────────────
    left, right = st.columns([ratio, _r], gap="small")

    with left:
        render_preview_panel(instr_f, input_f, out_fs)

    with right:
        st.markdown('<div class="section-label">BENCHMARK</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="panel-box panel-box-empty">'
            'Upload files above and click BENCHMARK to start'
            '</div>',
            unsafe_allow_html=True,
        )

    # ── Launch pipeline if ready ──────────────────────────────────
    all_ready = instr_f is not None and input_f is not None and len(out_fs) > 0
    if run_clicked and all_ready:
        st.session_state._instr_name   = instr_f.name
        st.session_state._input_name   = input_f.name
        st.session_state._output_names = [f.name for f in out_fs]
        _start_pipeline(instr_f, input_f, out_fs)


# ── PAGE: RUNNING ─────────────────────────────────────────────────────────────
def page_running():
    _top_bar()

    # ── 3-column upload bar (read-only) ───────────────────────────
    render_top_upload_bar(page="running")

    # --- ADDED: Split ratio slider now visible on execution page ---
    ratio = _split_ratio_slider()
    _r = 100 - ratio

    sd         = st.session_state.status_dict
    cov_result = st.session_state.get("coverage_result")

    # ── Bottom split (resizable) ─────────────────────────────────
    left, right = st.columns([ratio, _r], gap="small")

    with left:
        # Left panel: Coverage & Condition Agent output + Backend Logs
        render_coverage_panel(sd, cov_result)

    with right:
        # Cancel button top-right
        _, btn_col = st.columns([7, 3])
        with btn_col:
            if st.button("⛔  CANCEL", type="secondary", use_container_width=True):
                if st.session_state.cancel_event:
                    st.session_state.cancel_event.set()
                st.session_state.page = "upload"
                st.rerun()

        render_execution_panel(sd, cov_result)

        # State transitions
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
            
            # Use a slightly shorter sleep for a more responsive UI during execution
            time.sleep(1)
            st.rerun()

# ── PAGE: RESULTS ─────────────────────────────────────────────────────────────
def page_results():
    _top_bar()

    # ── 3-column upload bar (read-only) ───────────────────────────
    render_top_upload_bar(page="results")

    ratio = _split_ratio_slider()
    _r = 100 - ratio

    results    = st.session_state.results
    cov_result = st.session_state.get("coverage_result")

    # ── Bottom split (resizable) ─────────────────────────────────
    left, right = st.columns([ratio, _r], gap="small")

    with left:
        # Left panel: DOWNLOAD & VIEW DETAIL FILES
        render_detail_files_panel(results, cov_result)

    with right:
        # Re-run button top-right
        _, btn_col = st.columns([7, 3])
        with btn_col:
            if st.button("🔄  RUN AGAIN", type="primary", use_container_width=True):
                st.session_state.page            = "upload"
                st.session_state.status_dict     = {}
                st.session_state.results         = []
                st.session_state.coverage_result = None
                st.session_state.cancel_event    = None
                st.session_state.pipeline_thread = None
                st.session_state.benchmark_error = None
                st.rerun()

        # Right panel: SCORE SUMMARY only
        render_results_panel(results, cov_result)


# ── Pipeline launcher ─────────────────────────────────────────────────────────
def _start_pipeline(instruction_file, input_file, output_files):
    instruction_bytes = get_file_bytes(instruction_file)
    input_bytes       = get_file_bytes(input_file)
    output_file_data  = [{"name": f.name, "bytes": get_file_bytes(f)} for f in output_files]

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

    st.session_state.cancel_event    = cancel_event
    st.session_state.status_dict     = status_dict
    st.session_state._results_holder = results_holder
    st.session_state.pipeline_thread = thread
    st.session_state.coverage_result = None
    st.session_state.page            = "running"
    thread.start()
    st.rerun()


def _transfer_results_if_ready():
    holder = st.session_state.get("_results_holder", [])
    if holder and st.session_state.status_dict.get("_done"):
        st.session_state.results = list(holder)
    cov = st.session_state.status_dict.get("_coverage_result")
    if cov:
        st.session_state.coverage_result = cov


# ── Router ────────────────────────────────────────────────────────────────────
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