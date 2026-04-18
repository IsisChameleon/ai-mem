<%*
// Query 2 — "Generate a self-contained prompt to continue doing X"
// Produces a portable prompt in my voice that I can paste into a fresh conversation,
// with attachments referenced by exact filename so I know what to attach.

const topic = await tp.system.prompt("Topic (canonical slug or free text)", "");
const intent = await tp.system.prompt("What do I want to do next?", "continue");
if (!topic) { return; }

tR += `# Continuation prompt: ${topic}\n\n`;
tR += `_Generated ${tp.date.now("YYYY-MM-DD HH:mm")}_\n\n`;
tR += "---\n\n";
tR += "You are writing a prompt **in my voice** that I will paste into a fresh AI conversation.\n";
tR += "Rules:\n";
tR += "- Self-contained. Assume the reader has no prior context.\n";
tR += "- Only include context that's directly relevant to what I want to do next.\n";
tR += "- Reference attachments by their exact filename so I know what to attach.\n";
tR += "- Use first person. Match my tone from the notes (not yours).\n";
tR += "- End with a concrete ask.\n\n";
tR += `Topic: **${topic}**\n`;
tR += `Intent: **${intent}**\n\n`;
tR += "## Chat notes\n\n";
-%>
```dataview
TABLE summary, file.link AS note
FROM "AI Chats"
WHERE contains(topics, "<% topic %>")
SORT updated DESC
LIMIT 25
```
