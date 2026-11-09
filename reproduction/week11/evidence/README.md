# Raw evidence archives

These ZIPs contain every regular file from the completed run directories, copied
byte-for-byte. Packaging did not rerun, filter, repair, or change any mission.

| Archive | Scope | Files | ZIP bytes | Raw bytes |
|---|---|---:|---:|---:|
| `week11-formal-20261108-raw.zip` | All 400 formal attempts | 30,122 | 19,040,102 | 32,842,202 |
| `week11-preflight-20261108-raw.zip` | 8 engineering-preflight attempts; **excluded from the formal 400** | 608 | 393,799 | 688,128 |

`archive-manifest.json` and `preflight-archive-manifest.json` record SHA256 hashes,
inventory counts, and scope. Each ZIP has one corresponding run-directory root.
They contain only generated experiment evidence and copied public-source inputs:
JSON configurations/receipts, CSV state/results, and text process logs. Packaging
checks found no symlinks, binaries, unexpected file extensions, or credential
pattern matches. No build output or unrelated workspace content is included.

From the repository root, independently verify the formal archive without
rerunning an experiment:

```bash
python3 reproduction/week11/verify_archive.py
```

Both extracted archives passed the independent scientific audit. Receipts are
in `../results/archive-validation.json`, `../results/archive-verification.log`,
and `../results/preflight-archive-verification.json`.

**Scope:** archive verification checks ZIP integrity, safe extraction, the
69-file pinned upstream source snapshot, all raw scientific records, and their
reported statistics. It does **not** verify identity of locally built binaries.
The original local-run audit checked those binaries separately; its receipt is
`../results/independent-verification.json`.
