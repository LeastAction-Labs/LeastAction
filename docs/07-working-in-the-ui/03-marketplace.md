# LeastAction Marketplace

The Marketplace is where you discover, import, and publish LeastAction items — operators, payloads, actions, workflows, and skills — built by LeastAction and the community.

---

## What's in the Marketplace

**Operators** — Ready-to-use execution logic for AWS services, Airflow, PostgreSQL, and more. LeastAction publishes official operators; community members contribute their own.

**Payloads** — Reusable payload templates compatible with common operators.

**Actions** — Lifecycle hooks for dependencies, notifications, CI/CD, and custom behavior.

**Usecases** — Bundled pipelines: payloads + skills + scheduling metadata, ready to deploy.

**Skills** — AI capabilities you can import and use directly in the Service AI or any MCP-connected AI client.

---

## Importing

Importing is free in LeastAction core. Browse the marketplace, select an item, and click the **import** button. The item is copied into your catalog and ready to use immediately.

Items show compatibility status before you import:

- **Core version** — whether the item is compatible with your installed version
- **Deprecated** — items flagged as no longer maintained
- **Official** — published by LeastAction
- **Verified** — community-published items that have been reviewed

Incompatible or deprecated items cannot be imported.

---

## Publishing

To publish an item, you need a LeastAction account. Once logged in, open any locally created item — operator, action, payload, skill, or workflow — and hit **Publish**. The item becomes available in the marketplace for others to discover and import.

---

## Using the Marketplace UI

The Marketplace is accessible from the main navigation. The search panel on the left lists items; results update as you type.

**Search & filters.** Type any keyword (name, description, category), or use structured filters in the search box:

```
publisher:"LeastAction"
type:"operator" tag:"postgresql"
```

Active filters show as chips (click **×** to remove). Clicking the **type / publisher / category / tag** chips on an item's detail panel adds them as filters. Results load incrementally — scroll to load more.

**Item detail.** Click an item to open its panel: name, type, version, core-compatibility status, Official/Verified badge, publisher & category (clickable), tags (clickable), content tabs (codeblock, bashblock, samples, …), and the **Import** button.

## Compatibility

Every item declares a `version_compatibility` range checked against your installed `CORE_VERSION`:

| Status | Meaning |
|---|---|
| `core X.Y ✓` | Compatible with your version |
| `Incompatible` | Requires a different core version — cannot import (hover to see which) |
| `Deprecated` | No longer maintained — cannot import |

## Versioning & deprecating (when publishing)

Each published item carries a `version` and a `version_compatibility` range — set them accurately so users know if it works with their install. To retire an old version, mark it **deprecated**: it stays visible but can't be imported.

## Official & Verified

| Badge | Meaning |
|---|---|
| **Official** | Published by LeastAction — reviewed, maintained, guaranteed for the current core. |
| **Verified** | Community-published and reviewed by LeastAction for quality and safety. |
| *(none)* | Community-published, unreviewed — use with the same care as any open-source code. |