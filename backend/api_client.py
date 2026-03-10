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


def _fetch_result(execution_id):
    """
    Fetch and parse the result of a completed workflow.

    Returns
    -------
    dict  parsed result with pipeLineAgents and tasksOutputs
    """
    url = f"{API_BASE}{WORKFLOW_EXECUTIONS_ENDPOINT}/{execution_id}/result"

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

    try:
        raw_response = resp.json()["data"]["result"]["response"]
        result = json.loads(raw_response)
    except (KeyError, TypeError) as e:
        raise AgentAPIError(f"Unexpected result shape for {execution_id}: {e}")
    except json.JSONDecodeError as e:
        raise AgentAPIError(
            f"Result response is not valid JSON for {execution_id}: {e}"
        )

    return result


def _extract_agent_outputs(result):
    """
    Zip pipeLineAgents with tasksOutputs into a clean list.

    Returns
    -------
    list[dict]  [{"agent_name": str, "content": str}, ...]
    """
    agents = result.get("pipeLineAgents", [])
    tasks  = result.get("tasksOutputs", [])
    outputs = []
    for agent, task in zip(agents, tasks):
        name    = agent.get("agent", {}).get("name", "Unknown Agent")
        content = task.get("raw") or task.get("description") or ""
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

    raw_result     = _fetch_result(execution_id)
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
                   "output_file":      agent_output_filename,
                 }
    ZIP        : all three files packed together

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
        f"coverage_file={coverage_filename}, instruction_file={instruction_filename}"
    )

    execution_id = _submit_workflow(
        pipeline_id=SCORING_PIPELINE_ID,
        user=SCORING_USER,
        user_inputs={
            "coverage_file":    coverage_filename,
            "instruction_file": instruction_filename,
            "output_file":      agent_output_filename,
        },
        zip_files={
            coverage_filename:     coverage_bytes,
            instruction_filename:  instruction_bytes,
            agent_output_filename: agent_output_bytes,
        },
        log_sink=log_sink,
    )

    _poll_until_complete(execution_id, cancel_event=cancel_event, log_sink=log_sink)

    raw_result    = _fetch_result(execution_id)
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
