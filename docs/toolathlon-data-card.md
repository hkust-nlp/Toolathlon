# Toolathlon Data Card

Large-scale mock-environment task data for supervised fine-tuning of tool-using agents, with broad server, tool, domain, and task coverage.

| 30+ | 600+ | 10+ | 5K+ |
|---:|---:|---:|---:|
| MCP SERVERS | TOOL INTERFACES | COVERAGE DOMAINS | MOCK TASKS |

## Overview

Toolathlon task data is a large-scale collection of tool-use tasks built in controlled mock environments. The data is designed for training agents to operate tools over long horizons: reading task instructions, using MCP servers, querying structured data, producing files, updating application state, and verifying final outputs.

The core value is **scalable supervision**: training data is produced and executed in mock environments, giving model teams broad tool-use data without depending on live external services for every training example.

Each task is packaged with the files needed for reproducible training and inspection, including task instructions, MCP server requirements, initialization logic, fixture data, evaluation logic, and optional workspace artifacts.

## SFT Evaluation Result

**Measured SFT lift:** Training on Toolathlon task data improves downstream Toolathlon-Verified evaluation performance. Super LoRA on 3,984 remapped Kimi-K3 trajectories lifts official pass@1 from 27/105 (25.7%) to 38/105 (36.2%).

| Model | Training data | Pass@1 | Pass@4 |
|---|---|---:|---:|
| NVIDIA-Nemotron-3-Super-120B-A12B (base, no SFT) | - | 27/105 (25.7%) | - |
| NVIDIA-Nemotron-3-Super-120B-A12B + SFT LoRA | 4k trajs | 38/105 (36.2%) | 61/105 (58.1%) |

LoRA pass@1 is attempt 1, matching the single base run. Pass@4 counts tasks solved on at least one of four LoRA attempts. Base was run once, so pass@4 is unmeasured.

Three official Verified tasks never entered the agent loop on any LoRA attempt, or on base, and are excluded from these scores: `filter-low-selling-products` (WooCommerce preprocess timeout), `interview-report` and `notion-personal-website` (Fireworks rejected the Word MCP tool schema).

## Training & Inference Configuration

Training (Fireworks LoRA):

```bash
# adaptation
LORA_RANK=128
SHAPE=nemotron-3-super-120b-a12b-bf16-128k-lora

# batch
MBS=2    GBS=2

# sequence / token length
MAX_LENGTH=131072
DROP_OVERSIZED_SEQUENCES=1
TOKENIZE_AND_MASK=cumulative

# lr / schedule
LR=1e-4    MIN_LR=0
WARMUP_STEPS=30
LR_SCHEDULE=linear
EPOCHS=4
```

Inference serving (Fireworks dedicated Super):

```bash
# deployment
SHAPE=rft-nemotron-3-super-120b-a12b-bf16-tp-ep
REPLICAS=4

# eval
WORKERS=8
TIMEOUT_S=5400
MAX_STEPS=100
MAX_OUTPUT_TOKENS=64K
IMAGE=lockon0927/toolathlon-task-image:1016beta
```

## Optional Partial-Credit Mode

For customers who want more diagnostic feedback than pass / fail, task generation can include checkpoint-level accounting. Each rollout can report total checkpoints, passed checkpoints, an overall rate, per-run rates, and named checkpoint IDs:

```json
{
  "status": "pass",
  "run_count": 4,
  "total_passed": 33,
  "total_checkpoints": 40,
  "overall_rate": 0.825,
  "per_run": {
    "run_1": {"passed": 8, "total": 10, "rate": 0.8},
    "run_2": {"passed": 9, "total": 10, "rate": 0.9}
  },
  "checkpoint_ids": ["csv_exists", "row_count", "remote_state_updated"]
}
```

| Option | Customer value |
|---|---|
| Binary scoring | Simple pass / fail result for benchmark-style evaluation |
| Checkpoint scoring | Partial-credit diagnostics showing which requirements were completed and which failed |
| Per-run accounting | Stability view across multiple rollouts, useful for filtering SFT data and comparing models |

## Approach

The dataset is built around mock-environment tool use:

- **Mock-first task construction** - Tasks are created against local / mock MCP services, deterministic fixtures, local files, and controlled web assets, so data generation never depends on unstable live APIs.
- **Broad tool coverage** - The task pool spans 30+ MCP servers and 600+ agent-visible tool interfaces, covering office files, spreadsheets, browser / fetch, email, LMS, commerce, finance, media, databases, and filesystem workflows.
- **Final-state supervision** - Tasks produce concrete outputs such as spreadsheets, reports, messages, database records, presentations, CSV files, or workspace artifacts, and are scored by reading back the final artifact or service state.

### Quality Signals

| Dimension | Dataset signal |
|---|---|
| Reproducibility | Mock environments avoid dependence on unstable live APIs during data generation and SFT preparation |
| Tool realism | Tasks require real tool-use sequences rather than isolated text-only answers |
| Artifact grounding | Outputs are concrete files or application states that can be checked by evaluators |
| Transfer evidence | Fine-tuning on Toolathlon task data shows measured lift on downstream tool-use evaluation |
| Optional partial credit | Tasks can expose checkpoint-level scoring, allowing customers to inspect partial progress instead of only binary pass / fail outcomes |

> ***Design principle:*** *Keep training scalable and reproducible in mock environments while preserving enough tool semantics and task realism to improve real-environment agent performance. Every task must run against mock services, deterministic fixtures, local files, or controlled local web assets - never live external APIs - and is judged only on final artifacts and mock service state, not intermediate steps.*

<!-- separate-callouts -->

> ***Hard Rejection Criteria:*** *Tasks are rejected if they reach live external services, leave task state outside the fixture / local-mirror / workspace / per-task mock service layers, or leak the expected answer into the workspace so the agent can copy rather than perform the tool-use workflow. Static offline-isolation scans confirm mock paths avoid live endpoints before a task enters the pool.*

## What You Get

### Directory Structure

```text
{task_id}/
|-- task_config.json             # required MCP servers and local tools
|-- docs/task.md                 # user-facing task instruction
|-- docs/agent_system_prompt.md  # agent runtime prompt
|-- preprocess/main.py           # mock environment setup
|-- evaluation/main.py           # final-state validation
|-- fixtures/mock_data.json      # mock backend data, when needed
|-- initial_workspace/           # optional starting files
`-- groundtruth_workspace/       # optional reference artifacts
```

### Key File Example

`task_config.json`:

```json
{
  "needed_mcp_servers": ["emails", "excel", "playwright_with_chunk", "filesystem"],
  "needed_local_tools": ["python_execute", "claim_done",
    "handle_overlong_tool_outputs", "manage_context", "history"]
}
```

### Field Reference

| Field | Type | Description |
|---|---|---|
| `task_config.json` | JSON | Lists the MCP servers and local tools needed by the task |
| `docs/task.md` | Markdown | Natural-language task instruction for the agent |
| `preprocess/main.py` | Python | Builds the mock environment and initial workspace state |
| `evaluation/main.py` | Python | Checks the final output or application state |
| `fixtures/mock_data.json` | JSON | Structured mock records for MCP-backed services |
| `trajectories/*.jsonl` | JSONL | Agent interaction records used for SFT and inspection |

## Coverage & Statistics

The dataset emphasizes breadth: many task forms, many tool families, many output artifacts, and reproducible mock-service states.

<div class="coverage-marker"></div>

### Dataset Scale

| Metric | Value | Meaning |
|---|---:|---|
| MCP server coverage | 30+ | Mock MCP servers represented in the task pool |
| Tool interface coverage | 600+ | Agent-visible tool interfaces across the covered mock MCP environment |
| Coverage domains | 10+ | Capability areas spanning productivity, code, cloud, data, research, media, and more |
| Mock task pool | 5K+ | Scalable mock-environment tasks for SFT and data inspection |

### Server Family Coverage

| Family | Covered capabilities |
|---|---|
| Code, Cloud, and Development | GitHub, Git, Google Cloud, filesystem, terminal, memory, repo state, cloud tables, storage objects, logs, and local artifact handoff |
| Office and Documents | Word, PowerPoint, Excel, PDF tools, spreadsheets, workbooks, decks, reports, file conversion, and document validation |
| Productivity and Learning | Email, Sheets, Notion, Calendar, Forms, Canvas, inbox readback, scheduling, submissions, grading, and announcements |
| Browser and Web | Playwright, fetch, local portals, linked policy pages, form pages, table extraction, webpage evidence collection, and local mirrors |
| ML and Research | HuggingFace, W&B, arXiv, scholarly search, paper retrieval, model / dataset repositories, experiment runs, and citation workflows |
| Commerce, Data, and Finance | WooCommerce, Snowflake, yfinance-style market data, inventory updates, customer / order analysis, SQL, and tabular aggregation |
| Geo, Travel, Media, and Lifestyle | Google Maps, rail / travel, YouTube, transcripts, place / route data, media eligibility, and lifestyle content workflows |

### Workflow Coverage

| Workflow type | Representative supervision signal |
|---|---|
| Read - reason - write | Read data from mock services and produce a final spreadsheet, report, CSV, slide deck, message, or database update |
| Multi-source reconciliation | Combine fixture data, web rules, local files, and tool responses into one final decision or artifact |
| Long-output aggregation | Enumerate large tables, many records, multiple pages, or many transcript / paper sections without dropping rows |
| Post-action verification | Read back sent messages, saved files, updated records, or generated artifacts before claiming completion |
| Exact-format delivery | Follow required filenames, CSV headers, spreadsheet sheets, PDF / report sections, email subjects, and presentation contents |
| Date, timezone, and numeric precision | Handle temporal alignment, financial calculations, ranking formulas, tie-breaks, rounding, and policy cutoffs |

### Artifact Coverage

| Artifact / state type | Examples of evaluated outputs |
|---|---|
| Office artifacts | Excel workbooks, Word documents, PowerPoint decks, and PDF reports |
| Structured files | CSV, JSON, TXT, Markdown, logs, and workspace handoff files |
| Service state | Email sends, calendar events, Canvas submissions, WooCommerce records, cloud tables, storage objects, GitHub repo state, and W&B runs |
| Analysis outputs | Ranked shortlists, eligibility audits, financial summaries, research selections, grading reports, route / place decisions, and model / data repository updates |

### Mock Environment Coverage

| Mock data layer | Coverage role |
|---|---|
| PostgreSQL-backed fixtures | Stable backend state for services such as email, Sheets, Forms, Canvas, WooCommerce, Snowflake, yfinance-style finance, YouTube, arXiv, scholarly search, GitHub, HuggingFace, Google Cloud, Google Maps, W&B, and memory-related task state |
| Local web assets | Policy pages, dashboards, linked amendments, reference documents, and task-specific portals hosted locally for deterministic browser / fetch tasks |
| Initial workspace files | Spreadsheets, documents, CSVs, archives, PDFs, repo workspaces, memory files, and task-specific input files available before the agent starts |
| Offline and isolation checks | Static scans confirm mock paths avoid live external services and keep task state in fixture, local mirror, workspace, or per-task mock service state |
| Evaluation checkpoints | Final-state checks over produced artifacts and mock service records, supporting SFT data filtering, strict review, and optional partial-credit accounting |

> ***Scope note:*** *This DataCard describes the Toolathlon task data asset for training and transfer. Compact HTML / zip samples are provided only for inspection and do not represent the full pool size.*

<style>
.coverage-marker ~ table {
  margin-bottom: 12px;
  font-size: 12px;
  line-height: 1.42;
}
.coverage-marker ~ table th,
.coverage-marker ~ table td {
  padding-top: 6px;
  padding-bottom: 6px;
}
.coverage-marker ~ h3 {
  margin-top: 16px;
  margin-bottom: 6px;
}
</style>
