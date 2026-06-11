# Marketplace — Guide

The Marketplace lets you discover, import, and publish LeastAction items. It is accessible from the main navigation and works against the LeastAction marketplace catalog.

---

## Browsing and Searching

The search panel on the left lists all available items. As you type, results update in real time.

### Plain text search
Type any keyword — name, description, category — to filter results.

### Field filters
Narrow results using structured filters in the search box:

```
publisher:"LeastAction"
publisher:"LeastAction" tag:"aws"
type:"operator" tag:"postgresql"
```

Active filters appear as chips below the search box. Click the **×** on any chip to remove it.

You can also add filters by clicking the **type**, **publisher**, **category**, or **tag** chips on any item's detail panel — they are added to the active filter set automatically.

### Item list
Each result shows:
- Name and item type
- Category (if set)
- Publisher — green badge for Official (LeastAction), blue dot for Verified community items
- Warning icon for incompatible or deprecated items
- Import button (disabled with reason if the item cannot be imported)

Results load incrementally — scroll to the bottom to load more.

---

## Item Detail

Click any item to open its detail panel on the right. The panel shows:

- **Name**, item type, version, core compatibility status
- **Official** or **Verified** badge
- **Publisher** and **category** — clickable to add as filters
- **Tags** — each tag is clickable to filter
- **Tabs** — content fields (codeblock, bashblock, description, connection sample, payload sample, etc.) rendered according to the item's schema
- **Import button** — in the top-right corner of the tab area

---

## Compatibility

Every item has a `version_compatibility` field that specifies which core versions it supports. The marketplace checks this against your installed `CORE_VERSION`:

| Status | Meaning |
|---|---|
| `core X.Y ✓` | Compatible with your version |
| `Incompatible` | Requires a different core version — cannot import |
| `Deprecated` | Item is no longer maintained — cannot import |

Hover over the **Incompatible** chip to see which core version is required.

---

## Importing

Click the import button (↓) on any compatible item. An import modal opens where you can confirm the destination folder and any required fields before the item is added to your catalog.

Importing is free — no account required to import.

Once imported, the item lives in your catalog and can be used in tasks, configs, and AI generation immediately.

---

## Publishing

Publishing requires a LeastAction account. Log in from the account menu.

To publish a locally created item:

1. Open the item in your catalog (operator, action, payload, skill, or workflow)
2. Click **Publish**
3. Fill in publishing details: version, category, tags, description, image (optional)
4. Submit — the item appears in the marketplace for others to discover and import

**What can be published:** operators, actions, payloads, skills, workflows.

**Versioning:** Each published item has a `version` and a `version_compatibility` range specifying which core versions it supports. Set these accurately so users know if the item works with their installation.

**Deprecating:** If you publish a new version of an item and want to retire an old one, mark it as deprecated. Deprecated items remain visible but cannot be imported.

---

## Official and Verified Items

| Badge | Meaning |
|---|---|
| **Official** | Published by LeastAction. Reviewed, maintained, and guaranteed to work with the current core. |
| **Verified** | Published by a community member and reviewed by LeastAction for quality and safety. |
| *(none)* | Community-published, unreviewed. Use with the same care as any open-source code. |
