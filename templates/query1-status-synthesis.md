<%*
// Query 1 — "Where was I at with topic X?"
// Usage: Templater → open this template in a scratch note, pick a topic when prompted.
// Output is intended to be copied into a fresh ChatGPT/Claude conversation as the first message.

const topic = await tp.system.prompt("Topic (canonical slug or free text)", "");
if (!topic) { return; }
tR += `# Status synthesis: ${topic}\n\n`;
tR += `_Generated ${tp.date.now("YYYY-MM-DD HH:mm")}_\n\n`;
tR += "---\n\n";
tR += "You are helping me recall where I left off on a topic across past AI chats.\n\n";
tR += `Topic: **${topic}**\n\n`;
tR += "Given the chat notes below (each has frontmatter + a Summary section), produce:\n\n";
tR += "1. **Current state** — one paragraph. What's the latest thinking.\n";
tR += "2. **Decisions already made** — bullet list, each with the note it came from.\n";
tR += "3. **Open questions** — what's still unresolved.\n";
tR += "4. **Artifacts that exist** — filenames only, grouped by which chat produced them.\n";
tR += "5. **Natural next step** — what I should do first when I resume.\n\n";
tR += "Keep it tight. Do not invent details that aren't in the notes.\n\n";
tR += "## Chat notes\n\n";
-%>
```dataview
LIST summary
FROM "AI Chats"
WHERE contains(topics, "<% topic %>")
SORT updated DESC
LIMIT 25
```
