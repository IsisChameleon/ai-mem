# ai-mem

Sync Claude.ai and ChatGPT conversation exports into an Obsidian vault.

**Status:** v0.1 scaffold. Schema, config, filename, and frontmatter modules are implemented. Parsers, fetch, enrich, and sync stages are stubbed with `NotImplementedError` and will be filled in against a real Claude export.

## What it does (once built)

1. Watches Gmail for export-ready emails from Claude.ai and ChatGPT (read-only scope).
2. Downloads the ZIPs, archives them at `~/ai-archive/raw/<platform>/`.
3. Parses both platforms into a unified schema.
4. Generates a summary and topic list per chat via Claude Haiku 4.5.
5. Renders one Markdown note per chat into your Obsidian vault, with attachments copied under `AI Chats/attachments/<chat-id>/`.
6. Tracks everything in `.sync-state.json` so re-running only touches changed chats.

## Layout

```
src/ai_mem/
  cli.py          argparse entrypoint
  config.py       loads config.yaml
  schema.py       NormalizedChat, NormalizedMessage, Attachment, Artifact, WebCitation
  fetch/          Gmail OAuth + ZIP archival
  parse/          Claude + ChatGPT parsers
  enrich/         per-chat summary + topic normalization
  render/         markdown rendering (filenames, frontmatter, transcript, note)
  sync/           state, attachment copy, atomic writes
  util/           hashing, logging
templates/        Templater meta-prompts for Query 1 and Query 2
dashboards/       Dataview dashboard
tests/            unit + golden-file tests; fixtures/ committed once exports are redacted
```

## Setup (planned — not wired yet)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp config.example.yaml config.yaml
cp topics.example.yaml topics.yaml
# edit config.yaml with your paths + API keys
```

Then, once implemented:

```bash
ai-mem --fetch              # pull new exports from Gmail
ai-mem --ingest <zip>       # process a specific ZIP
ai-mem --dry-run            # print what would change, write nothing
ai-mem --only <chat-id>     # re-process one chat
```

## Next milestones

1. Drop a real Claude export ZIP at `~/ai-archive/raw/claude/` and share redacted fixtures.
2. Implement `parse/claude.py` against real data.
3. Implement `render/transcript.py` + `render/note.py` with golden-file tests.
4. Implement `sync/state.py` + `sync/writer.py` with idempotency tests.
5. Implement `fetch/gmail_client.py` (OAuth flow + download).
6. Implement `enrich/summarize.py` (Claude Haiku 4.5).
7. Implement `parse/chatgpt.py` (best-effort until a real ChatGPT export is available).
8. Templates, dashboard, full README.
