# AGENTBENCHMARKING

A production-grade Streamlit application for benchmarking agent outputs against Coverage & Condition and Scoring agents.

---

## Project Structure

```
agentbenchmarking/
├── app.py                  # Main Streamlit entry point + page router
├── requirements.txt
├── ui/
│   └── components.py       # Reusable UI widgets (header, upload, grid, results)
├── backend/
│   ├── api_client.py       # HTTP calls to Coverage & Scoring agents
│   └── workflow.py         # Pipeline orchestration (threading + parallel scoring)
└── utils/
    └── file_helpers.py     # File parsing, summary extraction
    └── config.py           # contains the AAVA environment and workflow ids
```

---

## Setup & Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Features

| Feature | Details |
|---|---|
| File Upload | Instruction file (×1), Input file (×1), Output files (×N) |
| File Preview | Dropdown selector, JSON/CSV/text rendering |
| Benchmarking Pipeline | Coverage Agent → parallel Scoring Agent calls |
| Real-time Status Grid | 6-step operation tracker with live status badges |
| Results Summary | Extracted fields displayed as a table |
| Result File Browser | Dropdown + syntax-highlighted content + download button |
| Re-run | Reset and run again from results page |

---


## Parallel Execution

Multiple output files trigger simultaneous scoring calls via `ThreadPoolExecutor` (up to 8 workers). Each result is independently tracked and collected.