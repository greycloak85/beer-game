---
phase: 04-deploy-streamlit-cloud
verified: 2026-05-18T22:30:00Z
status: human_needed
score: 5/6 must-haves verified (DEPLOY-02 awaits manual share.streamlit.io connect)
human_verification:
  - test: "Connect repo to Streamlit Community Cloud and bring the live URL online"
    expected: "share.streamlit.io shows a deployed app at a public URL (e.g., https://beer-game-greycloak85.streamlit.app); a first-time visitor can play a full 36-week game and reach the debrief; the URL is then backfilled into README.md's 'Live app:' line, replacing the '_(pending Streamlit Community Cloud deploy — Phase 4 Plan 02 will fill in the URL.)_' placeholder, and the README update is committed + pushed."
    why_human: "share.streamlit.io's 'Deploy from GitHub' flow is a browser-only UI with no public API, no CLI, and no automation surface for 'connect a new repo as a new app' — STACK.md and Plan 04-02 both call this out explicitly. Claude has done everything up to this point; the final ~90 seconds is the user clicking through the share.streamlit.io form (set Python version dropdown to 3.12 in Advanced settings, point at greycloak85/beer-game master/app.py, click Deploy)."
  - test: "Sanity-check the deployed app against local behavior"
    expected: "Live app's debrief shows the same bullwhip amplification ratio (variance-based, ~35.38× at the default seed) and 4-panel chart with the week-5 demand-step marker as the local `streamlit run app.py`."
    why_human: "Requires interactive browser session against the share.streamlit.io URL — cannot grep, cannot curl, cannot AppTest a remote container."
  - test: "After URL is in README, re-run this verification to flip DEPLOY-02 / DEPLOY-05 / Phase 4 to passed"
    expected: "grep on README.md for 'pending Streamlit Community Cloud deploy' returns no matches; the 'Live app:' line links to a working share.streamlit.io URL."
    why_human: "The final commit is user-driven (Plan 04-02 Task 3 step 7); re-running gsd verify after that commit will close the loop."
---

# Phase 4: Deploy to Streamlit Community Cloud — Verification Report

**Phase Goal:** The app is live at a public Streamlit Community Cloud URL, deployed from the public GitHub repo with pinned dependencies and Python 3.12, and reachable by anyone with the link.

**Verified:** 2026-05-18T22:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (mapped from Phase 4 success criteria + DEPLOY-01…06)

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Repo `github.com/greycloak85/beer-game` is PUBLIC, non-empty, with default branch `master` (DEPLOY-01) | VERIFIED | `gh repo view greycloak85/beer-game --json url,visibility,isEmpty,defaultBranchRef` returns `{"defaultBranchRef":{"name":"master"},"isEmpty":false,"url":"https://github.com/greycloak85/beer-game","visibility":"PUBLIC"}`. Local `origin` remote = `https://github.com/greycloak85/beer-game.git`. |
| 2 | `requirements.txt` at repo root pins exactly `streamlit==1.57.0` and `plotly==6.7.0` and nothing else (DEPLOY-03) | VERIFIED | File is exactly 2 lines (32 bytes): `streamlit==1.57.0\nplotly==6.7.0\n`. No dev tooling, no comments, no unpinned specifiers. |
| 3 | `.python-version` contains exactly `3.12` (DEPLOY-04, file half) | VERIFIED | File is 5 bytes: `3.12\n` (single line + trailing newline). Note: the Streamlit Cloud Advanced settings dropdown is the authoritative source for the deploy runtime; the `.python-version` file is for local parity and IS in place. |
| 4 | `.gitignore` excludes `.streamlit/secrets.toml`, `__pycache__/`, `.venv/`, `*.pyc`, `uv.lock`, and `*.egg-info/` (DEPLOY-06) | VERIFIED | All 6 required patterns present in `.gitignore` (lines 2, 3, 4, 9, 13, 16). `.streamlit/config.toml` is NOT ignored — correct, Plan 02-02 ships it. |
| 5 | No higher-priority dependency file shadows `requirements.txt` in the working tree or on the remote (DEPLOY-03 second half) | VERIFIED | `git ls-files \| grep -E "uv\.lock\|Pipfile\|environment\.yml"` returns empty (exit=1). `ls uv.lock Pipfile environment.yml` returns "No such file or directory" for all three. `pyproject.toml` IS tracked but sits LAST in Streamlit Cloud's dep-file priority (uv.lock → Pipfile → environment.yml → requirements.txt → pyproject.toml), so it does not shadow requirements.txt — STACK.md-confirmed. |
| 6 | App is live at a public Streamlit Community Cloud URL, reachable from the README link (DEPLOY-02, DEPLOY-05 link half) | FAILED — human_needed | README.md line 7 still reads `**Live app:** _(pending Streamlit Community Cloud deploy — Phase 4 Plan 02 will fill in the URL.)_`. No share.streamlit.io URL has been backfilled. share.streamlit.io has no public API to automate the "connect this repo" flow — Plan 04-02 Task 3 explicitly hands this to the user as a 7-step manual checklist. The repo and artifacts are 100% ready; the user has not yet clicked through the share.streamlit.io form. |
| 7 | README explains how to play, notes ~30s cold-start, credits Sterman 1989 (DEPLOY-05 content half) | VERIFIED | README.md contains: `# Beer Game` (line 1), `## Play it` (line 5), `## How to play` (line 11) with 4-station + 36-week + step-demand + info-opacity bullets, `## What is the bullwhip effect?` (line 20), `## Running locally` (line 26) with python3.12+venv+pip+pytest+streamlit-run flow, `## Tech stack` (line 54) matching requirements.txt pins exactly (Python 3.12, Streamlit 1.57.0, Plotly 6.7.0), `## Cold-start note` (line 61) explicitly describing the 30-second wake-up, `## Credits` (line 65) citing Sterman 1989 + MIT Sloan with the canonical parameters. |
| 8 | First-time visitor can play full game and reach debrief without errors (verifiable locally) | VERIFIED | `.venv/bin/python -m pytest -q` reports **82 passed in 3.48s** — all 82 tests including AppTest smoke + bullwhip calibration + equilibrium regression pass. Engine remains streamlit-free: only `beergame/views/{play,setup,debrief,rules}.py` import streamlit; `beergame/engine/`, `beergame/ai/`, `beergame/charts/`, `beergame/config/`, `beergame/narrative/` all pass the no-streamlit-import structural guard. |

**Score:** 7/8 truths verified; 1 (live URL) deferred to user manual step.

Mapped to success criteria: **5/6 verified, 1 human_needed**:
1. Repo public with required files — PASSED
2. No shadower files committed — PASSED
3. Streamlit Cloud deployment reachable — **HUMAN_NEEDED** (placeholder still in README)
4. Local playthrough works (tests pass) — PASSED
5. README explains play, cold-start — PASSED (link half blocked by criterion 3)
6. (DEPLOY-04 dropdown) — HUMAN_NEEDED (part of share.streamlit.io connect flow)

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `requirements.txt` | exactly `streamlit==1.57.0` + `plotly==6.7.0` | VERIFIED | 2 lines, 32 bytes, no extras. Matches plan verbatim. |
| `.python-version` | exactly `3.12\n` | VERIFIED | 5 bytes, single line + trailing newline. |
| `.gitignore` | covers `.streamlit/secrets.toml`, `__pycache__/`, `.venv/`, `*.pyc`, `uv.lock`, `*.egg-info/` | VERIFIED | All 6 entries present + defensives (`venv/`, `*.pyc`, OS cruft). |
| `README.md` | ≥50 lines with all 8 required sections | VERIFIED (content) / PARTIAL (link) | 69 lines, 4258 bytes; all sections present (Beer Game H1, Play it, How to play, What is the bullwhip effect?, Running locally, Tech stack, Cold-start note, Credits). Live-app link is still the placeholder string — by design, awaiting user backfill. |
| `pyproject.toml` (tracked) | acceptable per Streamlit Cloud priority order | VERIFIED OK | Tracked but sits LAST in CC priority; does not shadow requirements.txt. |
| `uv.lock`, `Pipfile`, `environment.yml` | MUST NOT exist | VERIFIED ABSENT | None exist in working tree; `git ls-files` returns no matches. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `requirements.txt` | Streamlit Cloud dependency resolver | uv-backed pip install at deploy time | VERIFIED (deploy-ready) | File contains `streamlit==1\.57\.0` pattern. No higher-priority shadower exists, so CC will land on this file. Deploy itself awaits human connect step. |
| `.gitignore` | git ls-files (post-commit verification) | untracked-files filter | VERIFIED | `git ls-files \| grep "uv\.lock"` returns empty — defensive ignore is effective. |
| `README.md` | Plan 02 post-deploy URL backfill target | `pending Streamlit Community Cloud deploy` unique placeholder substring | VERIFIED (target present, not yet replaced) | `grep -n "Live app:" README.md` → line 7 has the placeholder; ready for the user to run grep+replace per Plan 04-02 Task 3 step 7a. |
| local `master` branch | `github.com/greycloak85/beer-game` | `gh repo create … --source . --remote origin --push` (HTTPS retry after SSH failure) | VERIFIED | `git remote -v` shows `origin https://github.com/greycloak85/beer-game.git` (fetch + push). `gh repo view` confirms `isEmpty=false`, default branch `master`. |
| `github.com/greycloak85/beer-game` | Streamlit Community Cloud deploy | user-driven connection at share.streamlit.io | NOT_WIRED (by design, awaiting user) | No share.streamlit.io API exists for this step; Plan 04-02 hands the user a verbatim 7-step checklist embedded in `04-02-SUMMARY.md`. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| DEPLOY-01 | 04-02-PLAN | Public GitHub repo at `github.com/greycloak85/beer-game` | SATISFIED | `gh repo view` reports `visibility=PUBLIC`, `isEmpty=false`, URL matches exactly. |
| DEPLOY-02 | 04-02-PLAN | App deployed to Streamlit Community Cloud, reachable at public URL | NEEDS HUMAN | README still shows the `_(pending …)_` placeholder; the share.streamlit.io connect step is browser-only with no public API. Plan 04-02 explicitly hands this off in its 7-step checklist. |
| DEPLOY-03 | 04-01-PLAN | `requirements.txt` with pinned versions only; `uv.lock`/`Pipfile`/`pyproject.toml` NOT used to declare deploy deps | SATISFIED | `requirements.txt` has exactly the two pins; no `uv.lock`/`Pipfile`/`environment.yml` exist; `pyproject.toml` is tracked but per Streamlit Cloud's documented priority order sits LAST, so it does NOT declare deploy deps. |
| DEPLOY-04 | 04-01-PLAN | Python version pinned via `.python-version` AND set in CC's Advanced settings dropdown to 3.12 | SATISFIED (file) / NEEDS HUMAN (dropdown) | `.python-version` is `3.12`. The CC Advanced settings dropdown is part of the Streamlit Cloud connect flow (Step 4 in Plan 04-02's checklist) and is set by the user during the share.streamlit.io connect step. |
| DEPLOY-05 | 04-01-PLAN | README explains how to play, links to live app, notes ~30s cold-start | SATISFIED (play+cold-start) / NEEDS HUMAN (live link) | README has all required content (How to play section, Cold-start note section, Sterman 1989 credit). The live-app link is still a placeholder — same blocker as DEPLOY-02. |
| DEPLOY-06 | 04-01-PLAN | `.gitignore` excludes `.streamlit/secrets.toml`, `__pycache__/`, `.venv/`, `*.pyc`, `uv.lock` | SATISFIED | All 5 required entries grep-verified present in `.gitignore`; `*.egg-info/` also present per plan's defensive set. |

No orphaned requirements: every DEPLOY-* ID maps to a plan that claimed it.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `README.md` | 7 | `_(pending Streamlit Community Cloud deploy — Phase 4 Plan 02 will fill in the URL.)_` | Info (intentional handoff marker) | DESIGNED: Plan 04-01 deliberately uses this unique substring so Plan 04-02's user-driven step has an unambiguous grep+replace target. NOT a stub bug — it IS the wiring mechanism for the manual handoff. Will be replaced by the user after share.streamlit.io connect. |

No blocker anti-patterns. No TODO/FIXME/HACK/XXX in any of the four phase artifacts. No stubs in `app.py` or `beergame/` (tests cover full play-to-debrief flow at 82/82).

### Human Verification Required

#### 1. Connect repo to Streamlit Community Cloud and bring the live URL online

**Test:** Follow the 7-step checklist in `.planning/phases/04-deploy-streamlit-cloud/04-02-SUMMARY.md`:

1. Open https://share.streamlit.io and sign in as **greycloak85**. Authorize the Streamlit GitHub app to read `greycloak85/beer-game` if prompted.
2. Click "Create app" → "Deploy a public app from GitHub".
3. Fill the form: Repository=`greycloak85/beer-game`, Branch=`master`, Main file=`app.py`, App URL=auto or `beer-game-greycloak85`.
4. **CRITICAL** — Click "Advanced settings" and set **Python version: 3.12** (dropdown is the authoritative source for the runtime, per Streamlit docs; this satisfies the DEPLOY-04 dropdown half).
5. Click "Deploy". First build takes ~60–120s as uv pip-installs streamlit + plotly into a fresh container.
6. Once it loads, play one full game (pick any station, submit 36 orders, reach debrief, see the 4-panel chart with the week-5 demand-step marker and bullwhip amplification ratio ≈ 35.38× at default seed).
7. Copy the live URL (e.g., `https://beer-game-greycloak85.streamlit.app`), edit `README.md` to replace the `_(pending Streamlit Community Cloud deploy — Phase 4 Plan 02 will fill in the URL.)_` placeholder with a markdown link to the live URL, then:

```bash
git add README.md
git commit -m "docs(04-02): link README to live app URL"
git push
```

**Expected:** A working public Streamlit Community Cloud URL is reachable by anyone with the link; README's "Live app:" line links to that URL; the placeholder string is gone from README. DEPLOY-02 + DEPLOY-04 (dropdown) + DEPLOY-05 (link half) all become satisfied.

**Why human:** share.streamlit.io's "Deploy from GitHub" flow is a browser-only UI. There is no public API, no CLI, no programmatic surface for "connect this repo as a new Streamlit app" — STACK.md and Plan 04-02 both call this out explicitly as the one boundary Claude cannot cross. The repo, artifacts, and instruction checklist are all 100% ready; what's left is ~90 seconds of clicks the user runs once.

#### 2. Sanity-check the deployed app against local behavior

**Test:** With the live URL open, play one full canonical game and confirm the debrief's amplification ratio and 4-panel chart match what `streamlit run app.py` shows locally at the same seed.

**Expected:** Variance-based bullwhip amplification ratio ≈ 35.38× at seed=42; 4-panel chart with week-5 demand-step marker; cost breakdown per station; narrative paragraph identifies where amplification emerged. Cold start of ~30s on first request after sleep is expected (not a bug).

**Why human:** Requires interactive browser session against a remote container — cannot grep, curl, AppTest, or pytest a deployed share.streamlit.io URL from this environment.

#### 3. Re-run verification after the URL backfill commit

**Test:** Once README has the live URL committed and pushed, re-run `gsd verify-phase 4` (or this verification script).

**Expected:** Truth 6 flips from FAILED to VERIFIED; status flips from `human_needed` to `passed`; score becomes 8/8 truths and 6/6 requirements satisfied; Phase 4 closes.

**Why human:** The commit that closes the loop is user-driven (Plan 04-02 Task 3 step 7); only the user knows when share.streamlit.io has produced the URL.

### Gaps Summary

There are **no implementation gaps** — every artifact required by Plans 04-01 and 04-02 exists on disk with the exact content specified, every test still passes, the repo is live on GitHub at the right URL with the right visibility, and no shadower files exist anywhere. The single open item (DEPLOY-02 live URL) is **a known, deliberate handoff to a manual share.streamlit.io browser flow** that has no public API — Plan 04-02 anticipates this and embeds a verbatim 7-step checklist as the deliverable. The README's `_(pending …)_` placeholder is not a stub bug; it's the designated grep+replace target the user fills in after clicking Deploy.

**Bottom line:** Phase 4 is automation-complete and awaits ~90 seconds of user clicks at share.streamlit.io to flip from `human_needed` to `passed`.

---

*Verified: 2026-05-18T22:30:00Z*
*Verifier: Claude (gsd-verifier)*
