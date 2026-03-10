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
    "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJNYW5hcyBUaGlydXZlZWRodWxhIiwiaWF0IjoxNzczMTEzMjQyLCJleHAiOjE3NzUwMDE1OTksImFwcGlkIjoiZDQ2YzMwZGItMzA4My00OGJmLTkwZmMtY2Q5MjY0NmZhYjEzIiwidW5pcXVlX25hbWUiOiJtYW5hcy50aGlydXZlZWRodWxhQGFzY2VuZGlvbi5jb20iLCJkb21haW4iOiJpbnQtYWkuYWF2YS5haSIsInVzZXJEZXRhaWxzIjoiemcyZzlHSmdRQTFCVWR1UVdFQU10dVlMbXNTOWg4YlJwQitMYTk5amhwc3JPTXMzODl4ZUs3bjBOcWNJV3pxN21CS2dYcHd6bW1KMWcrcWxUSUhCOVRPTENxVi9yeXE3eEZoVHlsWXp0bThGTGNJOS9tNUlNbEtqRS9hQzZIZk1hVld1L1Q0SHVHQld6UVFaKzZ6WGhIalB6dUxMYlRaQ3N6MFE0d25oMkFoRU1EY3l3VDNXNyt6SElBUWt6K1RTN3VFTlptS1JOdFdaSEhXRWFzNDlycUR0cnFja1k3VnVyekJyQVBEMWlXeE5QRW1QVGE4eEVlZmJpbVV4bmVFSHQ4NENWeS82NUpxLzQrcmNaT3krdEE9PSJ9.MrDw_vUsxP39ZUzFXPyXvpZkOahWUWggxNtAhWMcZZFmq3jeDHepWzTjZl3V3F0aKZS-VA3S1ubNXpGMfYNt87QRrzkKDyz2w5QOkX_AEKwNfuID0gtuPmjfvGC8Zi5rWwHpsCBNMcoD76mKdAodXGvQAWpKgYCFVyOAEwQ-QrYiAJkUbkf1ZPhAFrxOUyBSbvCWdoUGJf2QZx5IlysK6NMF9xB28QjcbOJn9Z8YUec6Zc1ZVbi992r3PmQmNoMpCQ5pm5NGHY9275R7qve9In9nuNMK3gNvAOODSWSTWCUuogyrrneHlZQX0zJxbSaa8RO0RJrF3lEDRuz4Obkw-Q")


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
SCORING_PIPELINE_ID = os.getenv("SCORING_PIPELINE_ID", "11542")
SCORING_WORKFLOW_NAME = "DI Output Evaluation And Scoring Agent For LLM Responses workflow"
SCORING_USER = os.getenv("AAVA_USER", "manas.thiruveedhula@ascendion.com")

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
