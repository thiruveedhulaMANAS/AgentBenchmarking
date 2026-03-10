"""
app.py
------
AGENTBENCHMARKING — production entry point.

Layout:
  ┌──────────────────────────────────────────────────────────────────────┐
  │                AgentBenchmarking  (sticky top bar)                   │
  ├────────────────────┬─────────────────────┬───────────────────────────┤
  │ 📋 Instruction     │ 📥 Input File       │ 📤 Output Files           │
  │    [uploader]      │    [uploader]       │    [uploader]             │
  │                    │                     │    [🚀 BENCHMARK]         │
  ├────────────────────┴─────────────────────┴───────────────────────────┤
  │  LEFT (adjustable)             │  RIGHT                              │
  │  File preview dropdown + code  │  Pipeline ops grid + pills          │
  │                                │  Score summary (results page)       │
  │                                │  Download & detail files            │
  └────────────────────────────────┴─────────────────────────────────────┘
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
    render_top_upload_bar,
)
from utils.file_helpers import get_file_bytes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AgentBenchmarking",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Mulish:wght@300;400;500;600;700;800&family=Space+Mono:wght@400;700&display=swap');

/* ── Base reset ──────────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Mulish', sans-serif;
    background: #0b0d14;
    color: #ffffff;
}

h1, h2, h3 {
    font-family: 'Mulish', sans-serif;
    font-weight: 700;
}
.stApp { background: #0b0d14; }
#MainMenu, footer, header { visibility: hidden; }
.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}
[data-testid="column"] { padding: 0 !important; }

/* ── Scrollbar ───────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0b0d14; }
::-webkit-scrollbar-thumb { background: #2a3060; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #3d4580; }

/* ── Sticky top bar ──────────────────────────────────────────────── */
.top-bar {
    background: linear-gradient(90deg, #0a0c18 0%, #0e1020 60%, #0a0c18 100%);
    border-bottom: 1px solid #1e2340;
    padding: 0.5rem 1.8rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 100;
    height: 80px;
    box-shadow: 0 2px 20px rgba(0,0,0,0.4);
}
.top-bar-left {
    flex: 1;
    display: flex;
    justify-content: flex-start;
    align-items: center;
}
.top-bar-center {
    flex: 2;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 0.6rem;
}
.top-bar-right {
    flex: 1;
    display: flex;
    justify-content: flex-end;
    align-items: center;
}
.logo {
    height: 55px;
    width: auto;
    filter: drop-shadow(0 0 8px rgba(108,142,255,0.3));
}
.top-bar-title {
    font-size: 1.85rem !important;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: #ffffff;
    margin: 0;
}
.top-bar-title .accent { color: #6c8eff; }
.top-bar-badge {
    font-family: 'Space Mono', monospace;
    font-size: 0.60rem;
    background: #111422;
    border: 1px solid #2a3060;
    border-radius: 20px;
    padding: 3px 10px;
    color: #5a6090;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}
.page-indicator {
    font-family: 'Space Mono', monospace;
    font-size: 0.62rem;
    color: #5a6090;
    text-align: right;
    letter-spacing: 0.08em;
}
.page-indicator .pi-active {
    color: #6c8eff;
    font-weight: 700;
}

/* ── Upload bar columns ──────────────────────────────────────────── */
[data-testid="stHorizontalBlock"]:nth-of-type(2) > [data-testid="column"] {
    background: #0e1020 !important;
    border-bottom: 1px solid #1e2340;
    padding: 0.75rem 1rem 0.85rem !important;
}
[data-testid="stHorizontalBlock"]:nth-of-type(2) > [data-testid="column"]:first-child {
    padding-left: 1.5rem !important;
}
[data-testid="stHorizontalBlock"]:nth-of-type(2) > [data-testid="column"]:last-child {
    padding-right: 1.5rem !important;
}
[data-testid="stHorizontalBlock"]:nth-of-type(2) > [data-testid="column"]:not(:last-child) {
    border-right: 1px solid #1e2340;
}

/* ── Split panels ────────────────────────────────────────────────── */
[data-testid="stHorizontalBlock"]:nth-of-type(3) > [data-testid="column"]:first-child {
    border-right: 1px solid #1e2340;
    padding: 1.1rem 1.2rem 1.5rem 1.5rem !important;
    min-height: calc(100vh - 140px);
}
[data-testid="stHorizontalBlock"]:nth-of-type(3) > [data-testid="column"]:last-child {
    padding: 1.1rem 1.5rem 1.5rem 1.2rem !important;
}

/* ── Section labels ──────────────────────────────────────────────── */
.section-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.72rem !important;
    letter-spacing: 0.22em;
    color: #6c8eff;
    border-left: 2px solid #6c8eff;
    padding-left: 0.55rem;
    margin-bottom: 1rem !important;
    text-transform: uppercase;
}

/* ── Panel boxes ─────────────────────────────────────────────────── */
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
    color: #ffffff;
    font-family: 'Space Mono', monospace;
    font-size: 0.78rem;
    letter-spacing: 0.08em;
    min-height: 120px;
    border: 1px dashed #1e2340;
    border-radius: 8px;
}

/* ── Ops grid ────────────────────────────────────────────────────── */
.ops-grid { display: flex; flex-direction: column; gap: 4px; margin-bottom: 0.6rem; }
.op-row {
    display: grid;
    grid-template-columns: 2rem 2fr 6rem 3fr;
    align-items: center;
    gap: 0.7rem;
    padding: 0.5rem 0.85rem;
    border-radius: 5px;
    font-family: 'Space Mono', monospace;
    font-size: 0.70rem;
    transition: background 0.2s;
}
.op-icon  { font-size: 0.9rem; white-space: nowrap; }
.op-label { color: #ffffff; font-weight: 700; }
.op-status { font-size: 0.55rem; letter-spacing: 0.1em; text-align: right; }
.op-message {
    color: #5a6090;
    font-size: 0.65rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* ── Spinner animation ───────────────────────────────────────────── */
@keyframes spin { to { transform: rotate(360deg); } }
.spinner {
    display: inline-block;
    width: 9px; height: 9px;
    border: 2px solid rgba(245,158,11,0.2);
    border-top-color: #f59e0b;
    border-radius: 50%;
    animation: spin 0.75s linear infinite;
    margin-left: 3px;
    vertical-align: middle;
}

/* ── Resizer row ─────────────────────────────────────────────────── */
.resizer-row {
    background: #0b0d14;
    border-bottom: 1px solid #1e2340;
    padding: 0.1rem 1rem 0.15rem;
    display: flex;
    align-items: center;
    gap: 0.6rem;
}
.resizer-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.62rem;
    color: #ffffff;
    letter-spacing: 0.12em;
    white-space: nowrap;
    text-transform: uppercase;
}

/* ── Preview ─────────────────────────────────────────────────────── */
.preview-meta {
    font-family: 'Space Mono', monospace;
    font-size: 0.68rem;
    color: #ffffff;
    margin-bottom: 0.4rem;
}

/* ── Streamlit widget overrides ──────────────────────────────────── */
div[data-testid="stButton"] > button {
    font-family: 'Space Mono', monospace !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.08em !important;
    border-radius: 5px !important;
    transition: all 0.15s ease !important;
}
div[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #5a7aff 0%, #7c9fff 100%) !important;
    border: none !important;
    color: #fff !important;
    height: 44px !important;
    font-weight: 700 !important;
    box-shadow: 0 2px 12px rgba(108,142,255,0.35) !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #6c8eff 0%, #8aaeff 100%) !important;
    box-shadow: 0 4px 18px rgba(108,142,255,0.5) !important;
    transform: translateY(-1px) !important;
}
div[data-testid="stButton"] > button[kind="primary"]:disabled {
    background: #1e2340 !important;
    color: #ffffff !important;
    box-shadow: none !important;
    transform: none !important;
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
    color: #ffffff !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.80rem !important;
}
.stCode pre {
    background: #080b14 !important;
    border: 1px solid #1e2340 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.72rem !important;
    border-radius: 6px !important;
    max-height: 1200px !important;
    min-height: 300px !important;
    overflow-y: auto !important;
    white-space: pre !important;
}
[data-testid="stCodeBlock"] { margin-bottom: 1.2rem !important; }
div[data-testid="stExpander"] {
    background: #0e1020 !important;
    border: 1px solid #1e2340 !important;
    border-radius: 6px !important;
}
hr { border-color: #1e2340 !important; margin: 0.7rem 0 !important; }
.stSuccess, .stInfo, .stError, .stWarning {
    border-radius: 5px !important;
    font-size: 0.72rem !important;
    font-family: 'Space Mono', monospace !important;
}
div[data-testid="stDownloadButton"] > button {
    font-family: 'Space Mono', monospace !important;
    font-size: 0.68rem !important;
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
/* Tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: transparent !important;
    gap: 4px !important;
    border-bottom: 1px solid #1e2340 !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 5px 5px 0 0 !important;
    color: #5a6090 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.72rem !important;
    padding: 0.5rem 1rem !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: #0e1020 !important;
    color: #6c8eff !important;
    border-bottom: 2px solid #6c8eff !important;
}
/* Slider */
div[data-testid="stSlider"] { padding: 0 !important; }
div[data-testid="stSlider"] > label { display: none !important; }
div[data-testid="stSlider"] [data-baseweb="slider"] { margin: 0 !important; }
</style>
""", unsafe_allow_html=True)


# ── Session state ──────────────────────────────────────────────────────────────
def _init_session():
    defaults = {
        "page":                   "upload",
        "status_dict":            {},
        "cancel_event":           None,
        "pipeline_thread":        None,
        "results":                [],
        "coverage_result":        None,
        "benchmark_error":        None,
        "_instr_name":            None,
        "_input_name":            None,
        "_output_names":          [],
        "split_ratio":            60,
        "_files_locked":          False,
        "_draft_instr_bytes":     None,
        "_draft_instr_name":      None,
        "_draft_input_bytes":     None,
        "_draft_input_name":      None,
        "_draft_output_files":    None,
        "_pipeline_start_time":   None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_session()


# ── Logo loader ────────────────────────────────────────────────────────────────
@st.cache_data
def _load_logo() -> str:
    logo_path = "logo.png"
    fallback  = "image (1).png"
    for path in (logo_path, fallback):
        if os.path.exists(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
    return ""


_logo_b64 = _load_logo()


def _top_bar(page_label: str = "UPLOAD"):
    page_steps = ["UPLOAD", "RUNNING", "RESULTS"]
    crumbs = " → ".join(
        f'<span class="pi-active">{s}</span>' if s == page_label else s
        for s in page_steps
    )
    logo_img = (
        f'<img src="data:image/png;base64,{_logo_b64}" class="logo">'
        if _logo_b64 else ""
    )
    st.markdown(
        f"""
        <div class="top-bar">
            <div class="top-bar-left">{logo_img}</div>
            <div class="top-bar-center">
                <h1 class="top-bar-title">Agent<span class="accent">Benchmarking</span></h1>
            </div>
            <div class="top-bar-right">
                <div class="page-indicator">{crumbs}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Split-ratio slider ─────────────────────────────────────────────────────────
def _split_ratio_slider():
    st.markdown("""
    <div class="resizer-row">
        <span class="resizer-label">◀ Panel Width ▶</span>
    </div>
    """, unsafe_allow_html=True)

    ratio = st.slider(
        "split", min_value=25, max_value=75, step=5,
        value=st.session_state.get("split_ratio", 60),
        key="split_slider",
        label_visibility="collapsed",
    )
    st.session_state["split_ratio"] = ratio
    return ratio


# ── PAGE: UPLOAD ───────────────────────────────────────────────────────────────
def page_upload():
    _top_bar("UPLOAD")

    instr_f, input_f, out_fs, run_clicked = render_top_upload_bar(page="upload")

    ratio = _split_ratio_slider()
    _r = 100 - ratio

    left, right = st.columns([ratio, _r], gap="small")

    with left:
        render_preview_panel(instr_f, input_f, out_fs)

    with right:
        st.markdown('<div class="section-label" style="font-size:1.05rem !important;">BENCHMARK</div>', unsafe_allow_html=True)

        # Dynamic readiness checklist
        checks = [
            ("📋 Instruction file", instr_f is not None),
            ("📥 Input file",        input_f is not None),
            ("📤 Output file(s)",    len(out_fs) > 0),
        ]
        check_html = '<div style="margin-bottom:0.8rem;">'
        for label, ok in checks:
            icon  = "✅" if ok else "⬜"
            color = "#10b981" if ok else "#ffffff"
            check_html += (
                f'<div style="font-family:Space Mono,monospace;font-size:0.72rem;'
                f'color:{color};padding:0.2rem 0;">{icon} {label}</div>'
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
                '<div class="panel-box" style="display:flex;align-items:center;justify-content:center;'
                'color:#10b981;font-family:Space Mono,monospace;font-size:0.80rem;">'
                '✅ All files ready — click BENCHMARK to start'
                '</div>',
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
    _top_bar("RUNNING")
    render_top_upload_bar(page="running")

    ratio = _split_ratio_slider()
    _r = 100 - ratio

    sd         = st.session_state.status_dict
    cov_result = st.session_state.get("coverage_result")

    # Elapsed timer
    start_t = st.session_state.get("_pipeline_start_time")
    if start_t:
        elapsed = int(time.time() - start_t)
        mins, secs = divmod(elapsed, 60)
        st.markdown(
            f'<div style="font-family:Space Mono,monospace;font-size:0.65rem;'
            f'color:#ffffff;text-align:right;padding:0.2rem 1.5rem 0;">'
            f'⏱ Elapsed: {mins:02d}:{secs:02d}</div>',
            unsafe_allow_html=True,
        )

    left, right = st.columns([ratio, _r], gap="small")

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
    _top_bar("RESULTS")
    render_top_upload_bar(page="results")

    results    = st.session_state.results
    cov_result = st.session_state.get("coverage_result")

    # RUN AGAIN button
    _, btn_col = st.columns([7, 3])
    with btn_col:
        if st.button("🔄  RUN AGAIN", type="primary", use_container_width=True):
            st.session_state.status_dict     = {}
            st.session_state.results         = []
            st.session_state.coverage_result = None
            st.session_state.cancel_event    = None
            st.session_state.pipeline_thread = None
            st.session_state.benchmark_error = None
            st.session_state._files_locked   = False
            st.session_state._pipeline_start_time = None
            st.session_state.page = "upload"
            st.rerun()

    st.markdown(
        "<div style='padding: 0.8rem 1.5rem 1.5rem;'>",
        unsafe_allow_html=True,
    )
    render_full_results_page(results, cov_result)
    st.markdown("</div>", unsafe_allow_html=True)


# ── Pipeline launcher ──────────────────────────────────────────────────────────
def _start_pipeline(instruction_file, input_file, output_files):
    instruction_bytes = get_file_bytes(instruction_file)
    input_bytes       = get_file_bytes(input_file)
    output_file_data  = [{"name": f.name, "bytes": get_file_bytes(f)} for f in output_files]

    # Persist for RUN AGAIN
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
    thread.start()
    st.rerun()


def _transfer_results_if_ready():
    holder = st.session_state.get("_results_holder", [])
    if holder and st.session_state.status_dict.get("_done"):
        st.session_state.results = list(holder)
    cov = st.session_state.status_dict.get("_coverage_result")
    if cov:
        st.session_state.coverage_result = cov


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
