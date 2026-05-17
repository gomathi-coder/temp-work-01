# LinkWiki — Archive Command Design

## Purpose

The `archive` command moves the `linkwiki-html` export folder into an `archive/`
directory and renames it with a timestamp suffix, keeping a timestamped history of
past HTML exports without cluttering the project root.

---

## Command

### `archive` — Archive the HTML export folder

```
linkwiki archive [options]

Options:
  --source TEXT   Folder to archive  [default: linkwiki-html]
  --dest TEXT     Destination archive directory  [default: archive]

Examples:
  linkwiki archive
  linkwiki archive --source my-export
  linkwiki archive --dest backups
```

---

## Behaviour

1. Resolve the `--source` path and verify it exists as a directory.
2. Create the `--dest` directory if it does not already exist.
3. Generate a timestamped name: `archive-DD-MM-YYYY-HH-MM-SS`.
4. Move (rename) the source folder into `<dest>/<timestamp-name>/`.
5. Print a confirmation line.

The source folder is **moved**, not copied — the original path is gone after the
command completes. Run `linkwiki export --format html` again to regenerate it.

---

## Output

```
✔ Archived → archive/archive-16-05-2026-14-32-07/
```

On error (source not found):

```
✖ Source folder not found: linkwiki-html
```

---

## Folder Layout (after archiving)

```
project-root/
├── archive/
│   ├── archive-16-05-2026-14-32-07/   ← moved here
│   │   ├── index.html
│   │   ├── entries/
│   │   └── groups/
│   └── archive-15-05-2026-09-10-44/   ← earlier run
└── (linkwiki-html/ no longer present)
```

---

## Timestamp Format

| Component | Format | Example |
|-----------|--------|---------|
| Day       | `DD`   | `16`    |
| Month     | `MM`   | `05`    |
| Year      | `YYYY` | `2026`  |
| Hour      | `HH`   | `14`    |
| Minute    | `MM`   | `32`    |
| Second    | `SS`   | `07`    |

Full pattern: `archive-%d-%m-%Y-%H-%M-%S` (Python `strftime`).

---

## Implementation

| Item | Detail |
|------|--------|
| File | `linkwiki/cli.py` |
| Stdlib used | `shutil.move`, `datetime.now().strftime`, `pathlib.Path` |
| New files | None |
| Config changes | None |

---

## Error Handling

| Situation | Behaviour |
|-----------|-----------|
| `--source` folder does not exist | Print error, exit with code 1 |
| `--dest` directory does not exist | Auto-created (`mkdir -p`) |
| Timestamp collision (same second) | Not possible in normal usage |
| Insufficient permissions | OS error propagates naturally |
