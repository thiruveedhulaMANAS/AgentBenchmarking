"""
backend/api_client.py
---------------------
AAVA Workflow API communication layer.

Real API contract (from workflow runner reference code):

  Submit:  POST /workflows/workflow-executions
           multipart fields: pipelineId, user, userInputs (JSON), files (ZIP)

  Poll:    GET  /workflows/workflow-executions?execution-id=<id>
           response: data.workflowExecutionResponseList[0].status
           values:   "SUCCESS" | "FAILED" | (anything else = still running)

  Result:  GET  /workflows/workflow-executions/<execution_id>/result
           response: data.result.response (JSON string)
                     └─ pipeLineAgents[].agent.name
                     └─ tasksOutputs[].raw | .description

Coverage Agent userInputs:
  { "input_file": "<agent_input_filename>" }

Scoring Agent userInputs:
  { "coverage_file":    "<coverage_filename>",
    "instruction_file": "<instruction_filename>",
    "output_file":      "<output_filename>" }
"""

import io
import json
import logging
import time
import zipfile
from typing import Any

import requests
import urllib3

from utils.config import (
    API_BASE,
    AAVA_HEADERS,
    COVERAGE_PIPELINE_ID,
    COVERAGE_USER,
    SCORING_PIPELINE_ID,
    SCORING_USER,
    SUMMARY_PIPELINE_ID,
    SUMMARY_USER,
    VERIFY_SSL,
    WORKFLOW_EXECUTIONS_ENDPOINT,
    POLL_INTERVAL_SECONDS,
    WORKFLOW_TIMEOUT_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class AgentAPIError(Exception):
    """Raised on any workflow API failure."""
    pass


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_zip(files: dict) -> bytes:
    """
    Pack multiple in-memory files into a ZIP archive.

    Parameters
    ----------
    files : dict[str, bytes]
        Mapping of {filename: file_bytes} to include in the ZIP.

    Returns
    -------
    bytes
        Raw ZIP archive bytes.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for filename, data in files.items():
            zf.writestr(filename, data)
    return buf.getvalue()


def _submit_workflow(pipeline_id, user, user_inputs, zip_files, log_sink=None):
    """
    Submit a workflow execution to the AAVA API.

    Parameters
    ----------
    pipeline_id : str
    user : str
    user_inputs : dict[str, str]   placeholder -> filename
    zip_files : dict[str, bytes]   filename -> bytes
    log_sink : callable | None     if provided, called with each INFO message

    Returns
    -------
    str  execution_id
    """
    def _emit(msg):
        logger.info(msg)
        if log_sink:
            log_sink(msg)

    url = f"{API_BASE}{WORKFLOW_EXECUTIONS_ENDPOINT}"
    zip_bytes = _build_zip(zip_files)

    multipart = {
        "pipelineId": (None, pipeline_id),
        "user":       (None, user),
        "userInputs": (None, json.dumps(user_inputs)),
        "files":      ("payload.zip", zip_bytes, "application/zip"),
    }

    _emit(
        f"[SUBMIT] pipeline={pipeline_id} user={user} "
        f"userInputs={user_inputs} files={list(zip_files.keys())}"
    )

    try:
        resp = requests.post(
            url,
            headers=AAVA_HEADERS,
            files=multipart,
            timeout=REQUEST_TIMEOUT_SECONDS,
            verify=VERIFY_SSL,
        )
        resp.raise_for_status()
    except requests.Timeout:
        raise AgentAPIError(
            f"Submit timed out after {REQUEST_TIMEOUT_SECONDS}s (pipeline={pipeline_id})"
        )
    except requests.HTTPError as e:
        raise AgentAPIError(
            f"Submit HTTP {e.response.status_code} (pipeline={pipeline_id}): {e.response.text}"
        )
    except requests.RequestException as e:
        raise AgentAPIError(f"Submit request failed (pipeline={pipeline_id}): {e}")

    try:
        execution_id = resp.json()["data"]["workflowExecutionId"]
    except (KeyError, TypeError, ValueError):
        raise AgentAPIError(f"Unexpected submit response: {resp.text[:500]}")

    _emit(f"[SUBMIT] Execution started: {execution_id}")
    return execution_id


def _poll_until_complete(execution_id, cancel_event=None, log_sink=None):
    """
    Poll workflow status until SUCCESS or FAILED.

    Raises AgentAPIError on failure, timeout, or cancellation.
    """
    def _emit(msg):
        logger.info(msg)
        if log_sink:
            log_sink(msg)

    url = f"{API_BASE}{WORKFLOW_EXECUTIONS_ENDPOINT}"
    elapsed = 0

    while True:
        if cancel_event and cancel_event.is_set():
            raise AgentAPIError(f"Cancelled while polling {execution_id}")

        if elapsed >= WORKFLOW_TIMEOUT_SECONDS:
            raise AgentAPIError(
                f"Workflow {execution_id} timed out after {WORKFLOW_TIMEOUT_SECONDS}s"
            )

        try:
            resp = requests.get(
                url,
                headers=AAVA_HEADERS,
                params={"execution-id": execution_id},
                timeout=REQUEST_TIMEOUT_SECONDS,
                verify=VERIFY_SSL,
            )
            resp.raise_for_status()
            status = (
                resp.json()["data"]["workflowExecutionResponseList"][0]["status"]
            )
        except (KeyError, IndexError, TypeError, ValueError) as e:
            raise AgentAPIError(f"Unexpected poll response for {execution_id}: {e}")
        except requests.RequestException as e:
            raise AgentAPIError(f"Poll request failed for {execution_id}: {e}")

        _emit(f"[POLL] {execution_id} -> {status}")

        if status == "SUCCESS":
            return
        if status == "FAILED":
            raise AgentAPIError(f"Workflow {execution_id} reported FAILED status")

        time.sleep(POLL_INTERVAL_SECONDS)
        elapsed += POLL_INTERVAL_SECONDS


def _fetch_result(execution_id, log_sink=None):
    """
    Fetch and parse the result of a completed workflow.

    The AAVA API sometimes returns an empty/incomplete result immediately
    after reporting SUCCESS status — the result data is written asynchronously.
    This function retries up to RESULT_FETCH_MAX_RETRIES times with
    RESULT_FETCH_RETRY_INTERVAL_SECONDS between attempts until a valid
    non-null result with at least one of the expected keys is returned.

    Returns
    -------
    dict  parsed result with pipeLineAgents and tasksOutputs
    """
    RESULT_FETCH_MAX_RETRIES = 10
    RESULT_FETCH_RETRY_INTERVAL_SECONDS = 3

    def _emit(msg):
        logger.info(msg)
        if log_sink:
            log_sink(msg)

    url = f"{API_BASE}{WORKFLOW_EXECUTIONS_ENDPOINT}/{execution_id}/result"

    for attempt in range(1, RESULT_FETCH_MAX_RETRIES + 1):
        try:
            resp = requests.get(
                url,
                headers=AAVA_HEADERS,
                timeout=REQUEST_TIMEOUT_SECONDS,
                verify=VERIFY_SSL,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise AgentAPIError(f"Result fetch failed for {execution_id}: {e}")

        # The API may return the result payload as a nested JSON string,
        # or the result/data keys may simply be absent on the first few calls.
        try:
            body         = resp.json()
            data_block   = body.get("data") or {}
            result_block = data_block.get("result") or {}
            raw_response = result_block.get("response")
        except (AttributeError, ValueError):
            body         = {}
            result_block = {}
            raw_response = None


        # No response field yet — result not populated on the server side
        if not raw_response:
            _emit(
                f"[RESULT] {execution_id} — attempt {attempt}/{RESULT_FETCH_MAX_RETRIES}: "
                f"response field empty, retrying in {RESULT_FETCH_RETRY_INTERVAL_SECONDS}s…"
            )
            time.sleep(RESULT_FETCH_RETRY_INTERVAL_SECONDS)
            continue

        # Parse the nested JSON string
        try:
            result = json.loads(raw_response)
        except json.JSONDecodeError as e:
            raise AgentAPIError(
                f"Result response is not valid JSON for {execution_id}: {e}"
            )

        # Null payload — treat same as empty
        if result is None:
            _emit(
                f"[RESULT] {execution_id} — attempt {attempt}/{RESULT_FETCH_MAX_RETRIES}: "
                f"payload is null, retrying in {RESULT_FETCH_RETRY_INTERVAL_SECONDS}s…"
            )
            time.sleep(RESULT_FETCH_RETRY_INTERVAL_SECONDS)
            continue

        # Check that at least one of the expected keys is present and non-empty
        has_agents = bool(result.get("pipeLineAgents") or result.get("tasksOutputs"))
        if not has_agents:
            _emit(
                f"[RESULT] {execution_id} — attempt {attempt}/{RESULT_FETCH_MAX_RETRIES}: "
                f"pipeLineAgents/tasksOutputs missing or empty, retrying in {RESULT_FETCH_RETRY_INTERVAL_SECONDS}s…"
            )
            time.sleep(RESULT_FETCH_RETRY_INTERVAL_SECONDS)
            continue

        _emit(f"[RESULT] {execution_id} — result received on attempt {attempt}")

        return result

    raise AgentAPIError(
        f"Result for {execution_id} was not populated after "
        f"{RESULT_FETCH_MAX_RETRIES} attempts — the workflow may have completed "
        "without producing output."
    )


def _extract_agent_outputs(result):
    """
    Zip pipeLineAgents with tasksOutputs into a clean list.

    AAVA API behaviour observed:
      - pipeLineAgents is often [] (empty) even when tasksOutputs has content.
      - When pipeLineAgents is empty we fall back to tasksOutputs alone, using
        the workflow-level "name" field (or agents[].agent.name from the nested
        workflow definition) as the agent name.

    Returns
    -------
    list[dict]  [{"agent_name": str, "content": str}, ...]
    """
    if not result or not isinstance(result, dict):
        return []

    agents = result.get("pipeLineAgents") or []
    tasks  = result.get("tasksOutputs")   or []

    if not tasks:
        return []

    outputs = []

    if agents:
        # Normal path: pipeLineAgents and tasksOutputs are both populated
        for agent, task in zip(agents, tasks):
            if not isinstance(agent, dict):
                continue
            name = (
                agent.get("agent", {}).get("name", "Unknown Agent")
                if isinstance(agent.get("agent"), dict)
                else "Unknown Agent"
            )
            content = (task.get("raw") or task.get("description") or "") if isinstance(task, dict) else ""
            outputs.append({"agent_name": name, "content": content})
    else:
        # Fallback path: pipeLineAgents is empty — use tasksOutputs directly.
        # Derive a name from the top-level workflow name in the result payload,
        # or from the nested agents list inside result["workflow"]["agents"].
        workflow_name = result.get("name", "Agent")

        # Try to pull agent names from the nested workflow definition if present
        agent_names = []
        try:
            import json as _json
            wf_raw = result.get("workflow")
            if isinstance(wf_raw, str):
                wf_obj = _json.loads(wf_raw)
            elif isinstance(wf_raw, dict):
                wf_obj = wf_raw
            else:
                wf_obj = {}
            for ag_entry in (wf_obj.get("workflow", {}).get("agents") or []):
                n = ag_entry.get("agent", {}).get("name")
                if n:
                    agent_names.append(n)
        except Exception:
            pass

        for idx, task in enumerate(tasks):
            if not isinstance(task, dict):
                continue
            content = task.get("raw") or task.get("description") or ""
            name = agent_names[idx] if idx < len(agent_names) else workflow_name
            outputs.append({"agent_name": name, "content": content})

    return outputs


# ---------------------------------------------------------------------------
# Public API — called by workflow.py
# ---------------------------------------------------------------------------

def call_coverage_agent(agent_input_bytes, agent_input_filename, cancel_event=None, log_sink=None):
    """
    Run the Coverage & Condition Agent workflow.

    Workflow contract
    -----------------
    pipelineId : COVERAGE_PIPELINE_ID
    userInputs : { "input_file": agent_input_filename }
    ZIP        : { agent_input_filename: agent_input_bytes }

    Returns
    -------
    dict
        execution_id   : str
        agent_outputs  : [{"agent_name": str, "content": str}, ...]
        raw_result     : full parsed result payload (dict)
        coverage_text  : concatenated raw content from all agents (str)
                         — used as the coverage_file for the Scoring Agent
    """
    if cancel_event and cancel_event.is_set():
        raise AgentAPIError("Cancelled before Coverage Agent submission.")

    def _emit(msg):
        logger.info(msg)
        if log_sink:
            log_sink(msg)

    _emit(f"[COVERAGE] Submitting: input_file={agent_input_filename}")

    execution_id = _submit_workflow(
        pipeline_id=COVERAGE_PIPELINE_ID,
        user=COVERAGE_USER,
        user_inputs={"input_file": agent_input_filename},
        zip_files={agent_input_filename: agent_input_bytes},
        log_sink=log_sink,
    )

    _poll_until_complete(execution_id, cancel_event=cancel_event, log_sink=log_sink)

    raw_result     = _fetch_result(execution_id, log_sink=log_sink)
    agent_outputs  = _extract_agent_outputs(raw_result)

    # Flatten all agent output content into a single text blob
    # This becomes the "coverage_file" passed to the Scoring Agent
    coverage_text = "\n\n".join(
        f"=== {o['agent_name']} ===\n{o['content']}" for o in agent_outputs
    )

    _emit(
        f"[COVERAGE] Done. execution_id={execution_id}, "
        f"agents={[o['agent_name'] for o in agent_outputs]}"
    )

    return {
        "execution_id":  execution_id,
        "agent_outputs": agent_outputs,
        "raw_result":    raw_result,
        "coverage_text": coverage_text,
    }


def call_scoring_agent(
    agent_output_bytes,
    agent_output_filename,
    instruction_bytes,
    instruction_filename,
    input_bytes,
    input_filename,
    coverage_bytes,
    coverage_filename,
    cancel_event=None,
    log_sink=None,
):
    """
    Run the Scoring Agent workflow for one agent output file.

    Workflow contract
    -----------------
    pipelineId : SCORING_PIPELINE_ID
    userInputs : {
                   "coverage_file":    coverage_filename,
                   "instruction_file": instruction_filename,
                   "input_file":       input_filename,
                   "output_file":      agent_output_filename,
                 }
    ZIP        : all four files packed together

    Returns
    -------
    dict
        execution_id   : str
        output_filename: str   (which output file was scored)
        agent_outputs  : [{"agent_name": str, "content": str}, ...]
        raw_result     : full parsed result payload (dict)
    """
    if cancel_event and cancel_event.is_set():
        raise AgentAPIError(f"Cancelled before scoring {agent_output_filename}.")

    def _emit(msg):
        logger.info(msg)
        if log_sink:
            log_sink(msg)

    _emit(
        f"[SCORING] Submitting: output_file={agent_output_filename}, "
        f"coverage_file={coverage_filename}, instruction_file={instruction_filename}, "
        f"input_file={input_filename}"
    )

    execution_id = _submit_workflow(
        pipeline_id=SCORING_PIPELINE_ID,
        user=SCORING_USER,
        user_inputs={
            "coverage_file":    coverage_filename,
            "instruction_file": instruction_filename,
            "input_file":       input_filename,
            "output_file":      agent_output_filename,
        },
        zip_files={
            coverage_filename:     coverage_bytes,
            instruction_filename:  instruction_bytes,
            input_filename:        input_bytes,
            agent_output_filename: agent_output_bytes,
        },
        log_sink=log_sink,
    )

    _poll_until_complete(execution_id, cancel_event=cancel_event, log_sink=log_sink)

    raw_result    = _fetch_result(execution_id, log_sink=log_sink)
    agent_outputs = _extract_agent_outputs(raw_result)


    _emit(
        f"[SCORING] Done. execution_id={execution_id}, "
        f"output={agent_output_filename}"
    )

    return {
        "execution_id":   execution_id,
        "output_filename": agent_output_filename,
        "agent_outputs":  agent_outputs,
        "raw_result":     raw_result,
    }


def call_summary_agent(
    scoring_result_files: list,
    cancel_event=None,
    log_sink=None,
):
    """
    Run the Summary Agent workflow after all scoring jobs are complete.

    Workflow contract
    -----------------
    pipelineId : SUMMARY_PIPELINE_ID
    userInputs : { "scoring_files": "<comma-separated scoring filenames>" }
    ZIP        : all scoring result files packed together

    Parameters
    ----------
    scoring_result_files : list[dict]
        Each dict: { "name": str, "bytes": bytes }
        These are the text outputs produced by the scoring agent for each model.

    Returns
    -------
    dict
        execution_id   : str
        agent_outputs  : [{"agent_name": str, "content": str}, ...]
        raw_result     : full parsed result payload (dict)
        summary_text   : concatenated content from all agent outputs (str)
    """
    if cancel_event and cancel_event.is_set():
        raise AgentAPIError("Cancelled before Summary Agent submission.")

    def _emit(msg):
        logger.info(msg)
        if log_sink:
            log_sink(msg)

    filenames = [f["name"] for f in scoring_result_files]
    _emit(f"[SUMMARY] Submitting: scoring_files={filenames}")

    zip_files   = {f["name"]: f["bytes"] for f in scoring_result_files}
    scoring_csv = ",".join(filenames)

    execution_id = _submit_workflow(
        pipeline_id=SUMMARY_PIPELINE_ID,
        user=SUMMARY_USER,
        user_inputs={"scoring_files": scoring_csv},
        zip_files=zip_files,
        log_sink=log_sink,
    )

    _poll_until_complete(execution_id, cancel_event=cancel_event, log_sink=log_sink)

    raw_result    = _fetch_result(execution_id, log_sink=log_sink)
    agent_outputs = _extract_agent_outputs(raw_result)

    summary_text = "\n\n".join(
        f"=== {o['agent_name']} ===\n{o['content']}" for o in agent_outputs
    )

    _emit(
        f"[SUMMARY] Done. execution_id={execution_id}, "
        f"agents={[o['agent_name'] for o in agent_outputs]}"
    )

    return {
        "execution_id":  execution_id,
        "agent_outputs": agent_outputs,
        "raw_result":    raw_result,
        "summary_text":  summary_text,
    }
