"""
utils/config.py
---------------
Centralised configuration for the AGENTBENCHMARKING application.

Edit the values below to match your AAVA environment before running.
"""

import os

# ================= AAVA CONFIG =================
API_BASE = os.getenv("AAVA_API_BASE", "https://int-ai.aava.ai")
REALM_ID = os.getenv("AAVA_REALM_ID", "79")
AAVA_BEARER_TOKEN = os.getenv(
    "AAVA_BEARER_TOKEN",
    "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJNYW5hcyBUaGlydXZlZWRodWxhIiwiaWF0IjoxNzgwMjk2ODU5LCJleHAiOjE3ODU1NDIzOTksImFwcGlkIjoiNWY2ZDAxY2ItNDkyNC00ZWNlLWFhYmItZDcxZmEyZjZmMzY4IiwidW5pcXVlX25hbWUiOiJtYW5hcy50aGlydXZlZWRodWxhQGFzY2VuZGlvbi5jb20iLCJkb21haW4iOiJpbnQtYWkuYWF2YS5haSIsInVzZXJEZXRhaWxzIjoiemcyZzlHSmdRQTFCVWR1UVdFQU10dVlMbXNTOWg4YlJwQitMYTk5amhwc3JPTXMzODl4ZUs3bjBOcWNJV3pxN21CS2dYcHd6bW1KMWcrcWxUSUhCOVRPTENxVi9yeXE3eEZoVHlsWXp0bThGTGNJOS9tNUlNbEtqRS9hQzZIZk1hVld1L1Q0SHVHQld6UVFaKzZ6WGhIalB6dUxMYlRaQ3N6MFE0d25oMkFoRU1EY3l3VDNXNyt6SElBUWt6K1RTN3VFTlptS1JOdFdaSEhXRWFzNDlycUR0cnFja1k3VnVyekJyQVBEMWlXeE5QRW1QVGE4eEVlZmJpbVV4bmVFSHQ4NENWeS82NUpxLzQrcmNaT3krdEE9PSJ9.fbEqFyBOCiPZjVWuIvwZO9uTgPKxIGqjVYtCk5elejO0-_fmas4Ln7nMRXAZ3OQlO8vfROtEvfEKv-57dlp5PdMVNSaIl7F6VGP36GeZ3xTLZilRpE7H2VMmBjtW1bhp4ca75YmXLnfvlaX9iK55qXiQTgF0UVAwbcrgSFXRyTDo9mh0zTAMTyZPjPouGvzHYFtwio-bgQHo3jQtzB-WNAjlgj9b6IXPg8tQTXQHopTU1SL1nGGZBQYiT_DAdvBKurZOiZyemyigaPxWAt5G0saeeo0CJHCl-LhAG6-jsmKOfIAX8UsujaArNHKP8HIjKi8vDKtzjB5W0Ar4qzhzTg")
AAVA_HEADERS = {
    "Authorization": f"Bearer {AAVA_BEARER_TOKEN}",
    "x-realm-id": REALM_ID,
    "platform": "plugin",
    "Accept": "application/json",
    "Connection": "close",
}

# ---------------------------------------------------------------------------
# Coverage & Condition Agent workflow
# ---------------------------------------------------------------------------
COVERAGE_PIPELINE_ID = os.getenv("COVERAGE_PIPELINE_ID", "11508")
COVERAGE_WORKFLOW_NAME = "DI Comprehensive Coverage Item And Condition Extraction workflow"
COVERAGE_USER = os.getenv("AAVA_USER", "manas.thiruveedhula@ascendion.com")

# ---------------------------------------------------------------------------
# Scoring Agent workflow
# ---------------------------------------------------------------------------
# SCORING_PIPELINE_ID = os.getenv("SCORING_PIPELINE_ID", "11542")
# SCORING_WORKFLOW_NAME = "DI Output Evaluation And Scoring Agent For LLM Responses workflow"
# SCORING_USER = os.getenv("AAVA_USER", "manas.thiruveedhula@ascendion.com")

SCORING_PIPELINE_ID = os.getenv("SCORING_PIPELINE_ID", "12452")
SCORING_WORKFLOW_NAME = "DI LLM Response Evaluation And Scoring workflow"
SCORING_USER = os.getenv("AAVA_USER", "manas.thiruveedhula@ascendion.com")

# ---------------------------------------------------------------------------
# Summary Agent workflow
# ---------------------------------------------------------------------------
SUMMARY_PIPELINE_ID = os.getenv("SUMMARY_PIPELINE_ID", "12467")
SUMMARY_WORKFLOW_NAME = "DI Scoring Summary workflow"
SUMMARY_USER = os.getenv("AAVA_USER", "manas.thiruveedhula@ascendion.com")

# ---------------------------------------------------------------------------
# API endpoints (relative to API_BASE)
# ---------------------------------------------------------------------------
WORKFLOW_EXECUTIONS_ENDPOINT = "/workflows/workflow-executions"

# ---------------------------------------------------------------------------
# Polling & timeout settings
# ---------------------------------------------------------------------------
POLL_INTERVAL_SECONDS = 2
WORKFLOW_TIMEOUT_SECONDS = 600
REQUEST_TIMEOUT_SECONDS = 60

# ---------------------------------------------------------------------------
# SSL verification (set False only for dev/internal environments)
# ---------------------------------------------------------------------------
VERIFY_SSL = False
