# Codex note — GitHub hygiene gaps (read-only state)

**Who:** Codex read-only review for Ryan.
**What:** Freeze-safe state snapshot of four GitHub hygiene gaps.
**When:** 2026-08-03.
**Why:** Keep gap status explicit without mutating GitHub settings or CI policy during freeze.
**How:** Source-only review of repo docs and workflow files.

## Scope

This note is read-only. No branch/ruleset changes, no workflow execution-policy changes, and no security-setting writes were performed.

## Gap status

| Gap | Current state | Evidence |
|---|---|---|
| Branch protection on `main` | **Classic branch-protection endpoint returns `HTTP 404`, but active repository ruleset enforcement exists** (`Protect Main` on `refs/heads/main`). Residual policy gap: PR approvals currently set to `0`, with repository-role bypass configured. | [docs/inter-model/LATEST.md](LATEST.md), [docs/plans/branching-strategy.md](../plans/branching-strategy.md), [docs/plans/VERIFY-always-github-fallback.md](../plans/VERIFY-always-github-fallback.md) |
| Code scanning enabled | **Disabled** as of 2026-08-03 API probe (`HTTP 403` code scanning not enabled) | [docs/inter-model/LATEST.md](LATEST.md) (no explicit code-scanning enablement entry) |
| `pylint.yml` hardening | **Open hardening candidates confirmed repo-wide**: only one workflow exists, actions are tag-pinned (not full-SHA pinned), and explicit workflow/job `permissions:` is not declared | [.github/workflows/pylint.yml](../../.github/workflows/pylint.yml) |
| Dependabot 0 alerts scope check | **API reachable; current Dependabot alerts probe returned empty array (`[]`)**. `vulnerability-alerts` endpoint returns `HTTP 204` (enabled). Repo manifest inventory currently shows only `requirements.txt`; ecosystem coverage still needs GitHub-side confirmation. | [docs/inter-model/LATEST.md](LATEST.md), [docs/plans/VERIFY-always-github-fallback.md](../plans/VERIFY-always-github-fallback.md) |

## Observed probe results (2026-08-03)

```bash
gh api repos/alanmz-crypto/convmem/branches/main/protection
# -> HTTP 404: "Branch not protected"

gh api repos/alanmz-crypto/convmem/rulesets
# -> active ruleset "Protect Main" (id 19156572)

gh api repos/alanmz-crypto/convmem/rules/branches/main
# -> effective rules include pull_request, required_status_checks, deletion, non_fast_forward

gh api repos/alanmz-crypto/convmem/rulesets/19156572
# -> target refs/heads/main; required_approving_review_count: 0; bypass_actors includes RepositoryRole id 5 (always)

gh api repos/alanmz-crypto/convmem/code-scanning/alerts --paginate -q '.[0:3]'
# -> HTTP 403: "Code scanning is not enabled for this repository"

gh api repos/alanmz-crypto/convmem/dependabot/alerts --paginate -q '.[0:3]'
# -> []

gh api repos/alanmz-crypto/convmem/vulnerability-alerts -H 'Accept: application/vnd.github+json' -i
# -> HTTP 204 No Content (endpoint enabled)

ls -1 .github/workflows
# -> pylint.yml

rg -n "uses:\\s*[^\\n]+@|^permissions:" .github/workflows/*.yml
# -> uses: actions/checkout@v4
# -> uses: actions/setup-python@v5
# -> uses: actions/upload-artifact@v4
# -> no permissions: lines found

rg --files -g 'requirements*.txt' -g 'pyproject.toml' -g 'poetry.lock' -g 'Pipfile*' -g 'package.json' -g 'pnpm-lock.yaml' -g 'yarn.lock' -g 'go.mod' -g 'Cargo.toml' -g 'Gemfile*'
# -> requirements.txt
```

## Acceptance checklist (closure criteria)

- [x] | `branch-protection/exists` | PASS | Ruleset `Protect Main` active on `refs/heads/main`; classic endpoint 404 is expected and irrelevant.
- [ ] | `branch-protection/reviews` | FAIL | `required_approving_review_count >= 1` and no unenforced pull-request-reviews required.
- [ ] | `branch-protection/no-bypass` | FAIL | No `bypass_actors` entries with `bypass_mode: always` in `Protect Main` ruleset.
- [ ] | `code-scanning/enabled` | FAIL | `/code-scanning/analyses` returns HTTP 200 with non-empty array, or default setup API returns `status: enabled`.
- [ ] | `actions/sha-pinned` | FAIL | Every `uses:` in `.github/workflows/*.yml` references a full 40-char hex SHA, no mutable tags.
- [ ] | `actions/permissions` | FAIL | Every workflow file defines a top-level `permissions:` least-privilege block.
- [x] | `dependabot/alerts-enabled` | PASS | `/dependabot/alerts` returns HTTP 200 (empty array is acceptable; feature is enabled).
- [ ] | `dependabot/ecosystem-coverage` | FAIL | `.github/dependabot.yml` present with `pip` + `github-actions` ecosystems; alerts API confirms coverage.

**Closure summary:** 2 PASS / 6 FAIL. All six FAILs require Ryan-authorized writes outside the freeze window.

## Notes

1. This is a status clarification only; it does not assert that a missing local file proves a missing GitHub-level setting.
2. Branch enforcement uses GitHub Rulesets in this repo. Classic `branches/main/protection` `404` alone is not sufficient to conclude `main` is unprotected.
3. Current ruleset posture still leaves a governance gap versus strict PR-review intent: required PR approvals are `0` and a repository-role bypass is configured as `always`.

## Policy delta (current vs intended)

| Control | Current evidence | Intended strict posture | Gap status |
|---|---|---|---|
| Main branch enforcement mechanism | Ruleset `Protect Main` active on `refs/heads/main` | Ruleset or equivalent server-side enforcement active | Met (mechanism present) |
| Required PR approvals | `required_approving_review_count: 0` | `>= 1` required approval | Open |
| Bypass behavior | `bypass_actors` includes repository role with `bypass_mode: always` | No broad always-bypass for routine actors | Open |
| Required status checks | `pylint (3.12)` required, strict policy true | Required checks aligned with release policy | Partially met (single check present) |
| Code scanning | API says not enabled (`HTTP 403`) | Enabled and reporting | Open |
| Workflow hardening | Tag-pinned actions, no explicit `permissions:` block | Full-SHA pinning + least-privilege permissions | Open |
| Dependabot alert visibility | Dependabot alerts API returns `[]`; manifest inventory currently only `requirements.txt` | Explicit ecosystem coverage confirmed against GitHub settings | Open |
3. For code scanning and Dependabot alerts, authoritative truth is in GitHub repository settings/security views, not only in local files.

## Suggested read-only next checks (Ryan-owned surfaces)

1. Confirm `main` protection state in GitHub UI/API and record a dated result in an inter-model handoff.
2. Confirm whether GitHub code scanning is enabled and whether default code scanning setup or custom workflow coverage exists.
3. Decide whether to harden `.github/workflows/pylint.yml` with full-SHA action pinning and explicit least-privilege `permissions:`.
4. Confirm Dependabot alerts scope and whether alert count `0` includes all ecosystems in use.

## Read-only verification commands

Use these to gather evidence only. They do not mutate repo settings.

### 1) Branch protection on `main`

```bash
gh api repos/alanmz-crypto/convmem/branches/main/protection 2>&1 | head -40
```

Expected interpretation:
- `200`/JSON object with required settings: protection present.
- `403` with plan/permission wording: protection not verifiable from current plan/token context.
- `404`: protection not configured on `main`.

### 2) Code scanning enabled state

```bash
gh api repos/alanmz-crypto/convmem/code-scanning/alerts --paginate -q '.[0:5]'
```

Expected interpretation:
- returns alerts/empty array with no feature error: code scanning API is active.
- feature/permission error: code scanning not enabled or token lacks scope.

### 3) `pylint.yml` hardening review

```bash
sed -n '1,220p' .github/workflows/pylint.yml
```

Checklist:
- actions pinned to full commit SHA (currently tag-pinned).
- explicit workflow/job `permissions:` least-privilege block.

### 4) Dependabot alert scope check

```bash
gh api repos/alanmz-crypto/convmem/dependabot/alerts --paginate -q '.[0:20]'
```

Expected interpretation:
- array (possibly empty): Dependabot alert API reachable; evaluate scope by ecosystems/manifests.
- feature/permission error: need GitHub-side enablement or token scope.

## Recording pattern (recommended)

When checks are run, append a dated mini-summary in an inter-model note:

1. Command run
2. Exit/result class (`200`/`403`/`404`/feature-error)
3. What is now proven vs still unknown

## Decision memo — gap prioritization for Ryan

| Rank | Control | Current state | Risk | Unblock impact | Priority | Closing action |
|---|---|---|---|---|---|---|
| 1 | required-approvals | `required_approving_review_count: 0` | H | H | H | Ryan approves required-approvals ≥ 1 on default branch. |
| 2 | always-bypass-actor | bypass actor present with `bypass_mode: always` | H | H | H | Ryan approves removing always-bypass-actor from ruleset. |
| 3 | code-scanning | disabled (`HTTP 403`) | H | M | M | Ryan approves enabling default code scanning on repo. |

**Recommended sequencing:** Ryan approves required approvals, then bypass removal, then code scanning.

Workflow hardening (SHA pinning, permissions block) and Dependabot ecosystem coverage are lower priority — important but do not block governance gates 1 and 2.

**TL;DR:** The four hygiene gaps remain open. Branch enforcement mechanism is PASS (ruleset active); governance posture is not — required approvals are 0 and bypass is always. `pylint.yml` has hardening candidates. Code-scanning and Dependabot ecosystem coverage need GitHub-surface confirmation.