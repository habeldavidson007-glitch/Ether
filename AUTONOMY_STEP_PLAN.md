# Ether Autonomy Step Plan (No Overengineering)

This plan is intentionally incremental. Each step is small, measurable, and compared against Ether's current state before adding complexity.

## Current State Snapshot (April 22, 2026)

| Capability | Current Ether | Gap to Autonomous Mode |
|---|---|---|
| Request/response loop | ✅ `process_query()` user-driven loop | Needs background loop for self-initiated work |
| Context retrieval | ✅ Librarian KB retrieval | Needs retrieval for autonomous tasks, not just user prompts |
| Output formatting | ✅ Writer templates | Needs machine-readable task/status reports |
| Memory | ⚠️ Mixed (history + memory_core for fixes) | Needs explicit long-term success metrics for goals |
| Safety controls | ⚠️ Code safety checks exist for generated edits | Needs global tool budget + permission policy per task |
| Planning cycle | ⚠️ Intent routing + task decomposition for coding | Needs planner → executor → critic with retries/rollback |

## Phase 1 — Baseline Control Plane (Do This First)

**Goal:** Add observability and structure before autonomy.

1. Add a priority task queue (manual enqueue only).
2. Add safety budget accounting (tool cost + cap per run).
3. Add autonomy status report API to compare *current vs target* in runtime.

**Exit criteria:**
- You can enqueue/dequeue tasks.
- Every task run records budget usage.
- A status report shows enabled/disabled autonomy features.

## Phase 2 — Background Scheduler (Still Conservative)

**Goal:** Execute queued tasks on a timer, but only from approved task types.

1. Add background tick loop (disabled by default).
2. Execute one task per tick under budget constraints.
3. Persist queue snapshots to disk for crash recovery.

**Exit criteria:**
- Scheduler can be toggled on/off.
- Failed tick does not crash core query path.
- Restart resumes pending tasks from disk.

## Phase 3 — Planner/Executor/Critic with Retry + Rollback

**Goal:** Improve reliability without open-ended autonomy.

1. Planner creates bounded step list from a task.
2. Executor runs one step and emits structured output.
3. Critic validates result and either approves, retries, or rolls back.

**Exit criteria:**
- At least one retry path is tested.
- Rollback path is tested for file-change tasks.
- Critic decisions are logged with explicit reasons.

## Phase 4 — Long-Term Metrics + Self-Initiated Actions

**Goal:** Allow narrow self-initiation based on evidence.

1. Record success/failure metrics per task type.
2. Enable self-initiated tasks only when confidence + budget thresholds pass.
3. Keep hard caps (max tasks per hour/day).

**Exit criteria:**
- Self-initiated actions are auditable.
- Tasks pause automatically when failure rate rises.
- No uncapped loops.

## Anti-Hallucination Guardrails (Required Every Phase)

- Evidence-first: each planner step must reference concrete local state (files, diagnostics, metrics).
- Schema outputs: planner/executor/critic exchange structured objects, not free-form prose.
- Hard stop conditions: max retries, max runtime, max budget.
- Post-run diff checks: verify claimed changes match filesystem/git state.

## Suggested Build Order (Minimal)

1. `core/autonomy.py` control primitives (queue, budget, simple cycle helper).
2. `core/builder.py` status-report method + non-invasive initialization.
3. Optional scheduler only after step 1–2 are stable.
