"""
backend/workflow.py
-------------------
Pipeline orchestration layer.

Improvements over v5:
- Stores coverage result in status_dict["_coverage_result"] immediately.
- Parallel scoring via ThreadPoolExecutor (up to 8 workers).
- Structured log entries with level tags.
- Graceful cancel propagation at every step.
- Cleaner model-name extraction helper.
"""

import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from backend.api_client import call_coverage_agent, call_scoring_agent, call_summary_agent, AgentAPIError

logger = logging.getLogger(__name__)

STATUS_PENDING   = "pending"
STATUS_RUNNING   = "running"
STATUS_DONE      = "done"
STATUS_ERROR     = "error"
STATUS_CANCELLED = "cancelled"


def _make_op(label: str) -> dict:
    return {"label": label, "status": STATUS_PENDING, "message": ""}


def run_benchmark_pipeline(
    instruction_bytes: bytes,
    instruction_filename: str,
    input_bytes: bytes,
    input_filename: str,
    output_files: list,
    status_dict: dict,
    cancel_event: threading.Event,
    result_callback: Callable,
) -> None:

    ops_order = [
        "upload",
        "coverage_call",
        "coverage_wait",
        "scoring_call",
        "scoring_jobs",
        "summary_call",
        "collect",
    ]

    status_dict.update({
        "upload":           _make_op("Uploading files"),
        "coverage_call":    _make_op("Calling Coverage & Condition Agent"),
        "coverage_wait":    _make_op("Waiting for Coverage Response"),
        "scoring_call":     _make_op("Calling Scoring Agent"),
        "scoring_jobs":     _make_op("Running scoring jobs"),
        "summary_call":     _make_op("Calling Summary Agent"),
        "collect":          _make_op("Collecting results"),
        "_ops_order":       ops_order,
        "_error":           None,
        "_done":            False,
        "_coverage_result": None,
        "_summary_result":  None,
        "_logs":            [],
    })

    def _log(message: str, level: str = "INFO"):
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        status_dict["_logs"].append(f"[{ts}] [{level}] {message}")
        if level == "ERROR":
            logger.error(message)
        else:
            logger.info(message)

    def update(op_key: str, status: str, message: str = ""):
        status_dict[op_key]["status"]  = status
        status_dict[op_key]["message"] = message
        level = "ERROR" if status == STATUS_ERROR else "INFO"
        _log(f"[{op_key.upper()}] {status.upper()} — {message}", level)

    def abort_remaining(from_op: str = None):
        """Mark all pending/running ops as cancelled from from_op onward."""
        marking = from_op is None
        for key in ops_order:
            if from_op and key == from_op:
                marking = True
            if marking and status_dict[key]["status"] in (STATUS_PENDING, STATUS_RUNNING):
                status_dict[key]["status"]  = STATUS_CANCELLED
                status_dict[key]["message"] = "Cancelled"
        status_dict["_done"] = False

    try:
        # ── STEP 1: Upload ─────────────────────────────────────────────────
        if cancel_event.is_set():
            abort_remaining()
            return

        update("upload", STATUS_RUNNING, "Preparing files…")
        n_output = len(output_files)

        # ── Rename instruction and input files, preserving their extension ──
        import os as _os
        _, _instr_ext = _os.path.splitext(instruction_filename)
        _, _input_ext  = _os.path.splitext(input_filename)
        renamed_instruction_filename = f"instruction{_instr_ext}"
        renamed_input_filename       = f"input{_input_ext}"

        time.sleep(0.3)
        update(
            "upload", STATUS_DONE,
            f"{input_filename} (→ {renamed_input_filename}) + {instruction_filename} (→ {renamed_instruction_filename}) + {n_output} output file(s) ready",
        )

        # ── STEP 2: Coverage Agent call ────────────────────────────────────
        if cancel_event.is_set():
            abort_remaining("coverage_call")
            return

        from utils.config import COVERAGE_PIPELINE_ID
        update(
            "coverage_call", STATUS_RUNNING,
            f"Submitting pipeline {COVERAGE_PIPELINE_ID} → {renamed_input_filename}…",
        )

        coverage_result = call_coverage_agent(
            agent_input_bytes=input_bytes,
            agent_input_filename=renamed_input_filename,
            cancel_event=cancel_event,
            log_sink=_log,
        )

        update(
            "coverage_call", STATUS_DONE,
            f"Execution {coverage_result['execution_id']} → SUCCESS",
        )

        # ── STEP 3: Coverage response received ─────────────────────────────
        update("coverage_wait", STATUS_RUNNING, "Extracting coverage output…")

        coverage_text  = coverage_result["coverage_text"]
        coverage_bytes = coverage_text.encode("utf-8")
        coverage_fname = _derive_coverage_filename(input_filename)
        n_agents = len(coverage_result["agent_outputs"])

        # Store immediately so the UI can show it while scoring runs
        status_dict["_coverage_result"] = coverage_result

        update(
            "coverage_wait", STATUS_DONE,
            f"Coverage received — {n_agents} agent output(s)",
        )

        # ── STEP 4: Scoring Agent (parallel) ──────────────────────────────
        if cancel_event.is_set():
            abort_remaining("scoring_call")
            return

        total = n_output
        from utils.config import SCORING_PIPELINE_ID
        update(
            "scoring_call", STATUS_RUNNING,
            f"Dispatching {total} scoring job(s) — pipeline {SCORING_PIPELINE_ID}…",
        )
        update("scoring_jobs", STATUS_RUNNING, f"0 / {total} complete")

        results:   list = []
        errors:    list = []
        completed: int  = 0
        lock = threading.Lock()

        def score_one(of: dict) -> dict:
            return call_scoring_agent(
                agent_output_bytes=of["bytes"],
                agent_output_filename=of["name"],
                instruction_bytes=instruction_bytes,
                instruction_filename=renamed_instruction_filename,
                input_bytes=input_bytes,
                input_filename=renamed_input_filename,
                coverage_bytes=coverage_bytes,
                coverage_filename=coverage_fname,
                cancel_event=cancel_event,
                log_sink=_log,
            )

        with ThreadPoolExecutor(max_workers=min(total, 8)) as executor:
            future_map = {executor.submit(score_one, of): of for of in output_files}

            for future in as_completed(future_map):
                of = future_map[future]

                if cancel_event.is_set():
                    for f in future_map:
                        f.cancel()
                    abort_remaining("scoring_jobs")
                    return

                try:
                    scoring_result = future.result()

                    content_parts = [
                        f"=== Scoring Result: {of['name']} ===",
                        f"Execution ID : {scoring_result['execution_id']}",
                        "",
                    ]
                    for ao in scoring_result["agent_outputs"]:
                        content_parts.append(f"--- {ao['agent_name']} ---")
                        content_parts.append(ao["content"])
                        content_parts.append("")

                    base, ext = os.path.splitext(of["name"])
                    result_filename = f"scoring-agent-{base}{ext or '.txt'}"
                    model_name = _extract_model_name(of["name"])

                    with lock:
                        results.append({
                            "filename":      result_filename,
                            "source_file":   of["name"],
                            "model_name":    model_name,
                            "content":       "\n".join(content_parts),
                            "data":          scoring_result,
                            "agent_outputs": scoring_result["agent_outputs"],
                        })

                except AgentAPIError as exc:
                    err_msg = str(exc)
                    _log(f"[SCORING] Error for {of['name']}: {err_msg}", "ERROR")
                    base, ext = os.path.splitext(of["name"])
                    with lock:
                        errors.append(f"{of['name']}: {err_msg}")
                        results.append({
                            "filename":      f"scoring-agent-{base}{ext or '.txt'}",
                            "source_file":   of["name"],
                            "model_name":    _extract_model_name(of["name"]),
                            "content":       f"[ERROR] {err_msg}",
                            "data":          {"error": err_msg},
                            "agent_outputs": [],
                        })

                with lock:
                    completed += 1
                update("scoring_jobs", STATUS_RUNNING, f"{completed} / {total} complete")

        update("scoring_call", STATUS_DONE,  f"{total} job(s) dispatched")
        update("scoring_jobs", STATUS_DONE,  f"All {total} complete — {len(errors)} error(s)")

        # ── STEP 5: Summary Agent ──────────────────────────────────────────
        if cancel_event.is_set():
            abort_remaining("summary_call")
            return

        from utils.config import SUMMARY_PIPELINE_ID
        update(
            "summary_call", STATUS_RUNNING,
            f"Submitting {len(results)} scoring result(s) to Summary Agent…",
        )

        summary_result = None
        try:
            # Build scoring result files from the results collected above
            scoring_result_files = [
                {"name": r["filename"], "bytes": r["content"].encode("utf-8")}
                for r in results
            ]
            summary_result = call_summary_agent(
                scoring_result_files=scoring_result_files,
                cancel_event=cancel_event,
                log_sink=_log,
            )
            status_dict["_summary_result"] = summary_result
            n_summary_agents = len(summary_result["agent_outputs"])
            update(
                "summary_call", STATUS_DONE,
                f"Execution {summary_result['execution_id']} → SUCCESS ({n_summary_agents} agent output(s))",
            )
        except AgentAPIError as exc:
            _log(f"[SUMMARY] Error: {exc}", "ERROR")
            update("summary_call", STATUS_ERROR, str(exc))
            # Non-fatal — continue to collect even if summary fails

        # ── STEP 6: Collect ────────────────────────────────────────────────
        update("collect", STATUS_RUNNING, "Aggregating results…")
        time.sleep(0.2)

        err_suffix = f", {len(errors)} error(s)" if errors else " ✓"
        update("collect", STATUS_DONE, f"Done — {len(results)} result(s){err_suffix}")

        status_dict["_logs"].clear()   # logs no longer needed once done
        status_dict["_done"] = True
        result_callback(results)

    except AgentAPIError as exc:
        _log(f"Pipeline AgentAPIError: {exc}", "ERROR")
        status_dict["_error"] = str(exc)
        for key in ops_order:
            if status_dict[key]["status"] in (STATUS_PENDING, STATUS_RUNNING):
                status_dict[key]["status"]  = STATUS_ERROR
                status_dict[key]["message"] = str(exc)

    except Exception as exc:
        _log(f"Unexpected pipeline error: {exc}", "ERROR")
        logger.exception(f"Unexpected pipeline error: {exc}")
        status_dict["_error"] = f"Unexpected error: {exc}"
        for key in ops_order:
            if status_dict[key]["status"] in (STATUS_PENDING, STATUS_RUNNING):
                status_dict[key]["status"]  = STATUS_ERROR
                status_dict[key]["message"] = str(exc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _derive_coverage_filename(input_filename: str) -> str:
    base, ext = os.path.splitext(input_filename)
    return f"coverage_{base}{ext or '.txt'}"


def _extract_model_name(filename: str) -> str:
    """
    Best-effort extraction of a model name from an output filename.

    Examples:
      "DI Teradata Document - gpt 4 response.txt"  -> "gpt 4"
      "DI Teradata Document - gemini response.txt" -> "gemini"
      "DI Teradata Document - claude response.txt" -> "claude"
      "claude_output.txt"                          -> "claude"
      "my_file.txt"                                -> ""
    """
    import re as _re
    name = os.path.splitext(filename)[0]

    if " - " in name:
        name = name.rsplit(" - ", 1)[-1]
    elif "_" in name:
        name = name.split("_")[0]

    name = _re.sub(
        r"\b(response|output|result|answer|file|doc|document)\b",
        "",
        name,
        flags=_re.IGNORECASE,
    )
    return name.strip(" -_")