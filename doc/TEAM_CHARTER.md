# PrivacyLens — Team Charter (doc/team_charter.md)

## Roster (4 roles)

| Member | Role | Working dir | Primary artifact |
|---|---|---|---|
| A | Detection | `src/detection/` | Pattern + DOM layer, `detect()` service |
| B | Local classifier | `src/model/` | PII classifier train + search |
| C | Pipeline | `src/pipeline/` | Sanitization + reasoning + UI |
| D | Security + docs | `src/eval/` + `doc/` | Canary + eval + video + README |

## Communication cadence (12.5h sprint)
- **Hourly triage** (10:00, 11:00, …, 9:00): 5 min each — what was built, what blocks you,
  what D needs for eval numbers. Stop and report when blocked.
- **Shared state**: one source of truth for `config.yaml`, a shared `canary/` corpus,
  and a shared `doc/PLATFORM_PLAN.md`.
- **Semaphores**: reports to `/video/steering.md` written by the hour. The senior head reviews
  before committing to more time on a failed path.

## Definition of Done (each member, per artifact)
Each artifact is Done when:
1. Runs end-to-end on the provided Windows box with the 12GB 5070 Ti / 32GB RAM.
2. Produces a **measured** output (numbers, not asserts) — recall/precision/leakage/latency.
3. Includes a **canary** check that `leakage_count == 0`.
4. README(s) updated in `doc/` with the method + how to re-run.

## Code & security standards
- **No cloud handoff**: never log raw PII. Redact before any LLM call, any network call.
- **Fail-closed**: on detection/sanitization failure, block, do not pass.
- **Reproducible**: config + corpus frozen for the demo; record versions in a `doc/versions.md`.
- **Clean-room demo**: a 2–3 min video showing detect → redact → reason, with a canary leak of 0.

## Review gates (lead only)
- Gate 1: Detection API + eval corpus ready → 12:00
- Gate 2: Local model fine-tuned + quantized → 16:00
- Gate 3: Sanitization + reasoning pipeline working → 21:00
- Gate 4: Canary = 0 leakage, demo video + README done → 01:00

## Tools & environment
- OS: Windows 11, 12GB RTX 5070 Ti (12GB VRAM), 32GB RAM
- Env: Hermes venv python (see `.venv` note in README)
- Storage: `F:\Hackthon`
- Model scale: keep to ≤ 600M params (fits VRAM) unless quantized
