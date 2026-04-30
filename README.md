# ai-mem

Sync Claude.ai and ChatGPT conversation exports into an Obsidian vault.

## What it does

1. Parses Claude.ai export ZIPs into a unified schema.
2. Renders one Markdown note per chat into your Obsidian vault under `AI Chats/<platform>/<YYYY-MM>/`.
3. Stubs text-based attachments as separate notes under `AI Chats/attachments/<chat-id>/`.
4. Tracks everything in `.sync-state.json` so re-running only touches changed chats.
5. *(planned)* Watches Gmail for export-ready emails and downloads ZIPs automatically.
6. *(planned)* ChatGPT export support.

## Install

```bash
uv sync
```

## Configuration

```bash
cp config.example.yaml config.yaml
# edit config.yaml — set vault path and account email at minimum
```

Key fields in `config.yaml`:

```yaml
account: "you@example.com"   # stamped on every note so you know which login opens the URL

paths:
  vault: "~/Documents/ai-mem"
  notes_subdir: "AI Chats"
  raw_archive: "~/ai-archive/raw"
  failed: "~/ai-archive/failed"
  sync_state: "~/Documents/ai-mem/.sync-state.json"
```

## Usage

### Ingest a Claude export ZIP

Download your export from claude.ai → Account → Export Data, then:

```bash
ai-mem --ingest ~/Downloads/claude-export.zip
```

Override the account email for this run (useful if you have multiple accounts):

```bash
ai-mem --ingest ~/Downloads/claude-export.zip --account personal@example.com
```

### Other flags

```bash
ai-mem --ingest <zip> --dry-run          # render but write nothing
ai-mem --ingest <zip> --only <chat-id>   # re-process one specific chat
ai-mem --ingest <zip> --since 2025-01-01 # skip chats not updated since this date
ai-mem --fetch                           # (planned) pull new exports from Gmail
```

### Opening in Obsidian

Point Obsidian at the vault directory:

- **⌘⇧G** in the vault picker → paste `~/Documents/ai-mem` → Open
- The `.sync-state.json` file is a dotfile and stays hidden in Obsidian by default

Re-running `ai-mem --ingest <same-zip>` is a no-op — only chats whose content changed will be rewritten.

## Note structure

Each chat note contains:

```
---                          # frontmatter: id, title, platform, account, url, dates, message_count
# Chat title
> [!info] callout            # platform · model · date range · message count · import date

## Sources & artifacts
### Uploaded by me           # wikilinks to attachment stubs
### Generated during the conversation
### Web sources referenced   # URLs cited by the assistant

## Conversation              # full transcript with role headers, timestamps, tool calls
```

Attachment stubs (text files only — images are skipped) live at:

```
AI Chats/attachments/<chat-id>/<sha-prefix>-<original-filename>.md
```

## Project layout

```
src/ai_mem/
  cli.py          argparse entrypoint (--ingest, --fetch, --dry-run, --only, --since, --account)
  config.py       config.yaml loader
  schema.py       NormalizedChat, NormalizedMessage, Attachment, WebCitation
  fetch/          Gmail OAuth + ZIP archival (planned)
  parse/          Claude parser (ChatGPT planned)
  render/         filenames, frontmatter, transcript, note assembly
  sync/           sync state, atomic writes
  util/           hashing, logging
tests/
  fixtures/       redacted export fixtures
  snapshots/      golden-file render outputs
```

## Dev

```bash
uv run pytest           # run all tests
uv run pytest -q        # quiet output
```
