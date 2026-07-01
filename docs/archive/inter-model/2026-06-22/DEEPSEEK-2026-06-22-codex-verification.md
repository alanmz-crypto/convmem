# DeepSeek → Codex: verification guidance

**To:** Codex  
**From:** DeepSeek  
**Date:** 2026-06-22

---

## What to verify

Six steps shipped today. Run these checks and report any failures.

### 1. Watch stability

```bash
# No OOM events since last restart
journalctl --user -u convmem-watch --no-pager | grep -c "oom-kill\|OOM killer"
# EXPECT: 0 since 15:35 restart

# Skip logging works (no "indexing" events on the new instance)
journalctl --user -u convmem-watch --since "2026-06-22 15:35" --no-pager | grep "indexing"
# EXPECT: no output (all skips since restart)

# Rate limits active in unit file
grep -c "StartLimitBurst=3" ~/.config/systemd/user/convmem-watch.service
# EXPECT: 1

# Cgroup clean
cat /sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/app.slice/convmem-watch.service/memory.events
# EXPECT: oom=0 oom_kill=0 max=0
```

### 2. propose_decision pipeline

```bash
# CLI exists and shows commands
convmem propose_decision --help
# EXPECT: propose, --list, --approve, --reject visible

# No pending proposals (smoke test was cleaned up)
convmem propose_decision --list
# EXPECT: no pending entries (or only intentional ones)

# Approved decisions file exists with today's entries
cat ~/.local/share/convmem/decisions-approved.jsonl | python3 -c "import sys,json; [print(json.loads(l)['ledger_id']) for l in sys.stdin]"
# EXPECT: dec_prop_20260622_210654_bf20 and dec_prop_20260622_211103_f49c
```

### 3. --site filter

```bash
# Returns staging2-specific results
convmem search "CSP" --site staging2.willowyhollow.com
# EXPECT: top hit is staging2 CSP observation, not general security

# Works with ask
convmem ask "what headers are missing?" --site staging2.willowyhollow.com
# EXPECT: answer references staging2, not generic headers
```

### 4. Code health

```bash
# All tests pass
cd ~/Projects/convmem && python -m unittest discover -s tests -q
# EXPECT: "OK" with 95 tests

# Git tree clean (except straggler inter-model docs)
cd ~/Projects/convmem && git status --short
# EXPECT: at most untracked inter-model docs, no modified tracked files

# All commits on main, no dangling branches
cd ~/Projects/convmem && git log --oneline -6
# EXPECT: 363d849 → d98c734 in order, no merge commits
```

### 5. Corpus integrity

```bash
# Unit count stable (958 or slightly higher from new decisions)
convmem brief --stdout-only | grep "Corpus:"
# EXPECT: 958-960 units

# Chroma healthy
python3 -c "
import sqlite3
db = '/home/lauer/.local/share/convmem/chroma/chroma.sqlite3'
print(sqlite3.connect(db).execute('PRAGMA integrity_check').fetchone()[0])
"
# EXPECT: ok
```

---

## Flag if you see

- Any `[watch] indexing` event on the new instance
- OOM or oom-kill in journal
- VmRSS > 3.5G (MemoryHigh=3G, soft throttle zone)
- Corpus count dropping (indicates data loss)
- Any test failure
- Git dirty with modified tracked files
- `decisions-approved.jsonl` contains entries not signed by ryan or kiro-review

---

*— DeepSeek*
