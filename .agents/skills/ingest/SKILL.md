---
name: ingest
description: Ingest a Claude.ai export ZIP into the Obsidian vault at ~/Documents/ai-mem.
---

Import a Claude.ai export ZIP into the Obsidian vault using the ai-mem pipeline.

## Instructions

1. **Find the ZIP.** If the user didn't specify a path, list recent ZIPs:
   ```bash
   ls -lt ~/ai-archive/raw/*.zip 2>/dev/null | head -5
   ```
   Use the most recent one, or ask if it's ambiguous.

2. **Run the ingest.**
   ```bash
   cd /Users/isabelleredactive/src/ai-mem
   .venv/bin/ai-mem --ingest <zip_path>
   ```
   Add `--account <email>` if the user specifies an account.
   Add `--no-since` if they want a full rescan regardless of the last run.

3. **Report the result.** Parse the log line:
   ```
   ingest: seen=N written=N skipped=N filtered=N failed=N stubs=N
   ```
   Tell the user: how many notes were written, how many were skipped as unchanged,
   and whether any failed. If `failed > 0`, check `~/ai-archive/failed/` for dumps.

4. **If `written > 0`**, remind the user to reload the vault in Obsidian
   (Cmd+R or close/reopen the vault).

## Flags

| Flag | When to use |
|---|---|
| `--account <email>` | User has multiple accounts and wants to label this batch |
| `--no-since` | Force full rescan (ignores last ingest date) |
| `--dry-run` | Preview what would change without writing anything |
| `--only <chat-id>` | Re-process a single chat |
| `--since <YYYY-MM-DD>` | Manual date filter (overrides auto-since) |

## Guardrails

- Run from the project dir so `config.yaml` is found at the default path.
- Do not modify `config.yaml` unless the user explicitly asks.
- If the ingest fails entirely (not just individual chats), check that the ZIP is a valid Claude export (should contain `conversations.json` inside).
