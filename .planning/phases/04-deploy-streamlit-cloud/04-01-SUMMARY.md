---
phase: 04-deploy-streamlit-cloud
plan: 01
subsystem: infra
tags: [streamlit-cloud, deploy, requirements, gitignore, readme]

# Dependency graph
requires:
  - phase: 01-simulation-engine-ai
    provides: pure-Python engine pinned at streamlit==1.57.0 + plotly==6.7.0 (currently in requirements-dev.txt only)
  - phase: 02-ui-shell-per-turn-play
    provides: app.py at repo root (Streamlit Cloud's auto-discovered entrypoint) + locked streamlit+plotly versions
  - phase: 03-debrief-charts-narrative
    provides: 82-test suite that this plan must keep green
provides:
  - requirements.txt with exact streamlit+plotly pins (deploy-only, no dev tooling)
  - .gitignore extended with .streamlit/secrets.toml + uv.lock + venv/ + OS cruft
  - README.md: public-facing entry point with how-to-play, cold-start note, live-app placeholder, Sterman 1989 credit
  - .python-version verified as `3.12` (single line, single trailing newline)
affects: [04-deploy-streamlit-cloud Plan 02 (gh repo create + Streamlit Cloud connect + live-URL README backfill)]

# Tech tracking
tech-stack:
  added: []  # no new runtime deps — these artifacts pin the existing ones
  patterns:
    - "Deploy-only requirements.txt is the only file CC's resolver sees: requirements-dev.txt stays for local dev"
    - "Defensive gitignore: .streamlit/secrets.toml + uv.lock blocked from ever entering the repo"
    - "Live-app URL is a placeholder Plan 02's manual step backfills — clear delimiters keep the swap unambiguous"

key-files:
  created:
    - requirements.txt
    - README.md
    - .planning/phases/04-deploy-streamlit-cloud/04-01-SUMMARY.md
  modified:
    - .gitignore

key-decisions:
  - "requirements.txt holds EXACTLY two lines (streamlit==1.57.0, plotly==6.7.0) — no dev tooling, no transitive pins; CC's uv-backed resolver reads only this file"
  - ".python-version was already correct (3.12) from Plan 01-01 — verified, not rewritten; CC's Advanced settings dropdown is still the authoritative source"
  - "pyproject.toml is tracked but sits LAST in CC's dep-file priority (uv.lock → Pipfile → environment.yml → requirements.txt → pyproject.toml) — letting it stay tracked is fine, no action needed"
  - "README uses python3.12 -m venv + .venv/bin/pip install pattern (matches env-notes objective), not uv venv — uv is optional, stdlib venv is universal"
  - "Live-app section uses the literal placeholder '(pending Streamlit Community Cloud deploy — Phase 4 Plan 02 will fill in the URL.)' — Plan 02 has a unique substring to grep+replace"

patterns-established:
  - "Deploy artifacts are metadata-only: they add files, never modify the app — pytest count is the regression gate (82 before, 82 after)"
  - "Conventional commits per task: chore() for infra/config, docs() for README; scope is {phase}-{plan} (04-01)"

requirements-completed:
  - DEPLOY-03
  - DEPLOY-04
  - DEPLOY-05
  - DEPLOY-06

# Metrics
duration: 5min
completed: 2026-05-18
---

# Phase 04 Plan 01: Ship-Ready Deploy Artifacts Summary

**Deploy metadata committed: requirements.txt pins streamlit 1.57.0 + plotly 6.7.0, .gitignore blocks secrets/lockfiles, README.md ships a public-facing how-to-play with cold-start note and Sterman 1989 credit — pytest still 82/82.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-18T22:00:00Z (approx, from plan start)
- **Completed:** 2026-05-18T22:05:22Z
- **Tasks:** 3
- **Files modified:** 4 (requirements.txt, README.md created; .gitignore extended; .python-version verified unchanged)

## Accomplishments

- **requirements.txt** committed at repo root with exactly two lines (`streamlit==1.57.0`, `plotly==6.7.0`) — Streamlit Cloud's uv-backed pip resolver now has a single, lean, pinned dependency file to read at deploy time
- **.gitignore** extended from 6 to 14 entries: added `.streamlit/secrets.toml`, `uv.lock`, `venv/`, and editor/OS cruft; preserved all 6 existing exclusions; `.streamlit/config.toml` deliberately NOT ignored
- **README.md** created (68 lines) with 8 required sections: H1+tagline, "Play it" (live-URL placeholder), "How to play" (4-station/36-week/info-opacity/step-demand bullets), "What is the bullwhip effect?", "Running locally" (stdlib venv flow), "Tech stack" (matches requirements.txt pins exactly), "Cold-start note", "Credits" (Sterman 1989 + MIT Sloan link)
- **`.python-version`** verified as exactly `3.12` (single line + trailing newline) — no rewrite required, Plan 01-01's file was already correct
- **Test suite still green:** 82/82 pytest pass, both before and after the four-file deploy artifact set
- **No higher-priority dep file introduced:** no `uv.lock`, no `Pipfile`, no `environment.yml` exist in the working tree, so Streamlit Cloud's priority order will land on `requirements.txt`

## Task Commits

Each task was committed atomically:

1. **Task 1: Write requirements.txt and verify .python-version** — `e5bc3dc` (chore)
2. **Task 2: Audit .gitignore for secrets, lockfiles, and caches** — `e3047fa` (chore)
3. **Task 3: Write a public-facing README.md** — `2ed6538` (docs)

**Plan metadata:** _(see final commit at bottom — `docs(04-01): complete plan` with this SUMMARY + STATE.md update)_

## Files Created/Modified

- `requirements.txt` (CREATED) — Streamlit Cloud deploy dependency pins. Exact contents:
  ```
  streamlit==1.57.0
  plotly==6.7.0
  ```
- `.gitignore` (MODIFIED) — Reordered and extended from 6 to 14 lines.
  - **Preserved (already present in Plan 01-01's version):** `__pycache__/`, `*.pyc`, `*.egg-info/`, `.pytest_cache/`, `.ruff_cache/`, `.venv/`
  - **Added (this plan):** `venv/`, `.streamlit/secrets.toml`, `uv.lock`, `.DS_Store`, `.idea/`, `.vscode/`, `*.swp`
  - **Deliberately NOT added:** `.streamlit/config.toml` (Plan 02-02 ships it), `pyproject.toml` (already committed, fine because it sits LAST in CC's dep-file priority), `requirements-dev.txt` (it belongs in the repo for local-dev contributors).
- `README.md` (CREATED, 68 lines) — Public-facing project description. Final section order: `# Beer Game` (H1) → tagline → `## Play it` (with placeholder) → `## How to play` → `## What is the bullwhip effect?` → `## Running locally` → `## Tech stack` → `## Cold-start note` → `## Credits` (Sterman 1989 + MIT Sloan link to https://web.mit.edu/jsterman/www/SDG/beergame.html). Plan 02 will replace the placeholder string `_(pending Streamlit Community Cloud deploy — Phase 4 Plan 02 will fill in the URL.)_` with the deployed share.streamlit.io URL.
- `.python-version` (VERIFIED, unchanged) — Single line `3.12` with trailing newline.

## Final Contents (for Plan 02 sanity-check)

### requirements.txt (verbatim)
```
streamlit==1.57.0
plotly==6.7.0
```

### .python-version (verbatim)
```
3.12
```

### .gitignore (verbatim)
```
# Python build / cache
__pycache__/
*.pyc
*.egg-info/
.pytest_cache/
.ruff_cache/

# Virtual environments
.venv/
venv/

# Streamlit secrets — NEVER commit
.streamlit/secrets.toml

# Lockfiles — must NOT shadow requirements.txt on Streamlit Cloud
uv.lock

# OS / editor cruft
.DS_Store
.idea/
.vscode/
*.swp
```

## Decisions Made

1. **README uses stdlib venv setup, not uv.** The plan's authored README template uses `uv venv` / `uv pip install`. The environment-notes objective specified `python3.12 -m venv .venv` + `.venv/bin/pip install -r requirements.txt -r requirements-dev.txt` + `.venv/bin/streamlit run app.py`. Env-notes win — stdlib `venv` is universal and matches what a first-time visitor without `uv` installed can run immediately. (No behavioural impact: deploy resolution still goes through CC's uv pipeline regardless of what README documents for local dev.)
2. **README structure reordered slightly from plan template.** Plan template put "What is the bullwhip effect?" BEFORE "How to play". The env-notes README structure put "How to play" first, then "What is the bullwhip effect?" Both orderings satisfy the verify block's `grep -qF '## How to play'` and `grep -qF '## What is the bullwhip'`; env-notes ordering wins.
3. **`pyproject.toml` left tracked, no action needed.** STACK.md's CC dep-file priority order is `uv.lock → Pipfile → environment.yml → requirements.txt → pyproject.toml`. `pyproject.toml` is LAST, so it doesn't shadow `requirements.txt`. The plan's mid-task self-correction confirmed this; left it tracked.
4. **Live-URL placeholder uses unambiguous parenthesized prose, not a markdown badge or commented HTML.** Specifically `_(pending Streamlit Community Cloud deploy — Phase 4 Plan 02 will fill in the URL.)_`. Plan 02 can grep for `pending Streamlit Community Cloud deploy` (a unique substring) to find the exact replacement target.
5. **Test count preserved at 82/82.** Deploy artifacts are metadata; no app code changed. Both pre-task and post-Task-3 `pytest -q` runs report `82 passed`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking, very minor] Plan verify block grep regex for `## How to play` vs. README section ordering**

- **Found during:** Task 3 verification
- **Issue:** Plan template had "What is the bullwhip effect?" appear before "How to play" in the README skeleton; env-notes objective specified the opposite ordering. Plan's verify block uses `grep -qF` (literal substring), so ordering doesn't matter — both pass.
- **Fix:** Honored env-notes ordering (How to play → What is the bullwhip effect → ...). No regex/verify changes needed.
- **Files modified:** README.md
- **Verification:** Both `grep -qF '## How to play'` and `grep -qF '## What is the bullwhip'` pass.
- **Committed in:** `2ed6538` (Task 3 commit)

---

**Total deviations:** 1 minor (ordering preference, no behavioural change)
**Impact on plan:** None. All success criteria met; all `verify` blocks pass; pytest 82/82.

## Issues Encountered

None. All three tasks executed cleanly; no unplanned blockers.

One transient verification-block oddity: the plan's combined verification (step 3, `.gitignore` entries) piped a `for` loop through `tee` and then counted lines from the captured file; under bash pipeline subshell semantics the counter variable in the subshell didn't propagate, so the count read `0` even though all 6 echo lines printed correctly. Re-ran the check with a non-pipeline counter and confirmed `count: 6`. This is a quirk of the verification command, not an artifact issue.

## User Setup Required

None. Plan 01 is artifact-only — Plan 02 owns the manual steps:
- `gh repo create greycloak85/beer-game --public --source . --push`
- Streamlit Community Cloud → "New app" → connect repo → set Advanced settings → Python version = 3.12 → Deploy
- Backfill the live URL into README.md's `## Play it` section
- Run a full 36-week canonical playthrough on the deployed URL

## Next Phase Readiness

- All four artifacts (`requirements.txt`, `.python-version`, `.gitignore`, `README.md`) are committed at repo root, ready for `gh repo create` + Streamlit Cloud connect.
- DEPLOY-03 (requirements pin), DEPLOY-04 (Python version pin), DEPLOY-05 (README with live-app placeholder + cold-start note), DEPLOY-06 (gitignore secrets+lockfiles) are all satisfied on disk.
- DEPLOY-01 (public GitHub repo under `greycloak85`) and DEPLOY-02 (working deploy on share.streamlit.io) are Plan 02's responsibility.
- Pytest 82/82 still green — no app-behaviour regression from deploy metadata.
- AST guard 4/4 still clean (Plan 01's structural invariant intact).

---
*Phase: 04-deploy-streamlit-cloud*
*Completed: 2026-05-18*

## Self-Check: PASSED

Verified at completion:
- All 5 expected files exist on disk (`requirements.txt`, `.python-version`, `.gitignore`, `README.md`, `04-01-SUMMARY.md`).
- All 3 task commits exist in git history (`e5bc3dc`, `e3047fa`, `2ed6538`).
- All 6 DEPLOY-06 gitignore entries grep-verified present.
- `requirements.txt` sorts-equal to `{plotly==6.7.0, streamlit==1.57.0}` (exact pin match, no extras).
- `.python-version` content equals `3.12\n`.
- README.md contains all 8 required section headers + Sterman+1989 credit + cold-start note + live-app placeholder + all three stack pins.
- `pytest -q` reports 82 passed (no regression).
- `import app` succeeds.
- No higher-priority dependency file (`uv.lock`, `Pipfile`, `environment.yml`) exists in the working tree.
