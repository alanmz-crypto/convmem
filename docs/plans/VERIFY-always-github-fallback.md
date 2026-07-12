# Verify Plan — Always-Available GitHub Fallback

```
Planning Status

Phase:        Verify
Authority:    Post-Execute
```

**Subject:** `feat/2026-07-12-always-github-fallback`  
**Gates:** defaults accepted 2026-07-12 (see EXECUTION)

## Mechanical checks

```bash
cd ~/Projects/convmem
git switch feat/2026-07-12-always-github-fallback
bash scripts/install-repo-config.sh
python -m pytest tests/test_git_hooks.py tests/test_doctor.py::BranchingDoctorTests -q

# Pre-commit rejects main
git switch main
# expect reject (do not leave dirty commit):
# CONVMEM_SKIP_MAIN_HOOK=1 not set
# echo test >> /tmp/x; do not actually commit on main in prod verify —
# use fixture in pytest instead (already covered).

# Pre-push rejects main (fixture)
# work helper taxonomy
python -c "from work_git import build_branch_name; print(build_branch_name('feat','x'))"

# Doctor
convmem doctor 2>&1 | rg 'hooks_path|dirty_main|unpushed_commits|wip_on_main'

# Protocol negatives
rg -n 'Single-file doc typos may stay' config/agent-protocol.md && echo FAIL || echo 'no typo exception OK'
rg -nF 'convmem work start' config/agent-protocol.md
rg -n 'work start' config/agent-protocol.md && echo 'FAIL work start phrase' || echo 'OK'  # careful: "work start" as command is OK
# Prefer:
rg -nF 'Always-Available GitHub Fallback' config/agent-protocol.md

# Explicit refspec documented
rg -nF 'refs/heads/' config/agent-protocol.md docs/plans/branching-strategy.md

# GitHub protection (expect 403 on free private until Pro)
gh api repos/alanmz-crypto/convmem/branches/main/protection 2>&1 | head -5
# PASS for this arc: document 403 + Ryan Pro checklist; FAIL only if we falsely claim protected
```

## Verdict

| Result | When |
|--------|------|
| Mechanical PASS | pytest green; hooks installed; typo exception gone; work CLI importable |
| GitHub GATE | Ryan enables Pro (or public) and configures PR-only protection — **not claimable** until `gh api …/protection` succeeds |
| Sign-off | Kiro / Ryan after Mechanical PASS |

## Ryan GitHub Pro checklist (Phase 2a)

When Pro is available:

1. Protect `main`: require PR, no force-push, no deletion
2. No bypass for agents; Ryan-only if any bypass actor
3. Verify: `gh api repos/alanmz-crypto/convmem/branches/main/protection`
4. Then claim “main protected” in handoff
