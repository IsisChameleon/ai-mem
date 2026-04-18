# Recent AI chats

## Last 25 chats

```dataview
TABLE platform, model, updated, length(topics) AS "#topics", status
FROM "AI Chats"
WHERE platform
SORT updated DESC
LIMIT 25
```

## Stale (no activity in 30+ days, status = active)

```dataview
TABLE updated, topics
FROM "AI Chats"
WHERE status = "active" AND (date(today) - updated).days > 30
SORT updated ASC
```

## Pending summary (re-run enrich)

```dataview
LIST
FROM "AI Chats"
WHERE !summary OR summary = ""
SORT updated DESC
```

## Topics — frequency

```dataview
TABLE length(rows) AS count
FROM "AI Chats"
FLATTEN topics AS topic
GROUP BY topic
SORT count DESC
```
