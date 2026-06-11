# Catalog Links — Technical Reference

## Table of Contents
1. [Overview](#overview)
2. [Link Schema & Fields](#link-schema--fields)
3. [Hard Links vs Soft Links](#hard-links-vs-soft-links)
4. [Type Compatibility Rules](#type-compatibility-rules)
5. [Link CRUD Operations](#link-crud-operations)
6. [Automatic Linking on Task Creation](#automatic-linking-on-task-creation)
7. [Task Dependency Links](#task-dependency-links)
8. [Hierarchical Traversal](#hierarchical-traversal)
9. [Links and Deletion](#links-and-deletion)
10. [Frontend Link Management](#frontend-link-management)
11. [API Reference](#api-reference)
12. [Key Files](#key-files)

---

## Overview

**Links** define relationships between items in the catalog. They are stored in MongoDB's `links` collection and serve two purposes:

1. **Containment hierarchy** (hard links): Define which items are inside which folders. These form the tree structure of the catalog.
2. **Associations** (soft links): Create flexible references between items — e.g., a task referencing an operator, or a task depending on another task.

Every item in the catalog (except orphans) has at least one link connecting it to another item. Links are the backbone of catalog navigation, deletion cascading, and access control inheritance.

---

## Link Schema & Fields

Defined in `backend/src/core/catalog/link/schema.py`.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `laui` | `ObjectId` | Auto | MongoDB `_id` — the link's unique identifier |
| `parent_laui` | `ObjectId` | No | LAUI of the parent item. `null` for root-level links |
| `child_laui` | `ObjectId` | Yes | LAUI of the child item |
| `parent_type` | `string` | No | Item type of the parent (e.g., `"folder.workflow"`, `"operator"`) |
| `child_type` | `string` | Yes | Item type of the child (e.g., `"task"`, `"connection"`) |
| `true_parent` | `bool` | Yes | `true` = hard link (containment), `false` = soft link (association) |
| `created_at` | `datetime` | Auto | UTC timestamp when the link was created |

### Pydantic Model Hierarchy

```
_BaseLink (parent_laui, child_laui, parent_type, child_type, true_parent)
  ├── CreateLink
  │     └── CreateLinkInDB (+ created_at)
  └── Link (+ laui)

LinkWithPermission (CreateLink + permission)
```

### Equality & Hashing

Links are considered equal if they have the same `parent_laui` and `child_laui`. This is used for deduplication during deletion:

```python
def __eq__(self, other):
    return self.child_laui == other.child_laui and self.parent_laui == other.parent_laui

def __hash__(self):
    return hash((self.parent_laui, self.child_laui))
```

---

## Hard Links vs Soft Links

The `true_parent` boolean field is the single most important field on a link. It determines the link's behavior across the entire system.

### Comparison

| Aspect | Hard Link (`true_parent=true`) | Soft Link (`true_parent=false`) |
|--------|-------------------------------|--------------------------------|
| **Purpose** | Containment — "this item lives inside this folder" | Association — "this item references that item" |
| **Created when** | Item is created with `parent_laui` (automatic) | Explicit API call or task auto-linking |
| **Cardinality** | One hard parent per item | Multiple soft parents allowed |
| **Deletion cascade** | Deleting parent soft-deletes all hard children | Deleting only removes the soft link |
| **Access inheritance** | Children inherit parent's permission context | No inheritance |
| **Root items** | Have a hard link with `parent_laui=null` | N/A |
| **Examples** | folder.project → folder.workflow, folder.workflow → task | operator → task, connection → task, task → task |

### When Each Type Is Used

**Hard links are created automatically** when:
- A root item is created (`is_root=true`) — link with `parent_laui=null`
- A child item is created under a parent (`parent_laui` provided)

**Soft links are created** when:
- A task is created with `operator_laui`, `connection_laui`, `payload_laui`, or `attached_config_lauis` (auto-linking)
- The `POST /api/v1/catalog/create/link` endpoint is called explicitly
- Task dependencies are established via `LeastActionLinkParents` or `LeastActionCheckIfAreParentsDone`

---

## Type Compatibility Rules

Not all items can be linked to all other items. The allowed relationships are defined in `config/catalog.json` under `item_type_link_mapping`.

### Full Mapping

| Parent Type | Can Contain (Children) |
|-------------|----------------------|
| `folder.account` | `folder.project`, `folder.trash` |
| `folder.project` | `folder.action`, `folder.asset`, `folder.workflow`, `folder.operator`, `folder.payload`, `folder.connection`, `folder.bootstrap`, `folder.config` |
| `folder.workflow` | `folder.workflow`, `task`, `config`, `connection`, `payload`, `operator`, `action` |
| `folder.config` | `folder.config`, `config` |
| `folder.asset` | `folder.asset`, `folder.report`, `folder.table`, `html_report`, `table` |
| `folder.report` | `folder.report`, `html_report`, `config` |
| `folder.table` | `folder.table`, `table`, `config` |
| `folder.operator` | `folder.operator`, `operator` |
| `folder.action` | `folder.action`, `action` |
| `folder.payload` | `folder.payload`, `payload` |
| `folder.connection` | `folder.connection`, `connection` |
| `folder.trash` | `task`, `connection`, `config`, `action`, `operator`, `payload` |
| `connection` | `connection_queue`, `task` |
| `operator` | `task` |
| `task` | `task` |
| `payload` | `task` |
| `config` | `task` |
| `table` | `column` |
| `database` | `schema` |
| `schema` | `table` |

### How Compatibility Is Checked

The `SupportedItemTypesManager` loads the mapping from `config/catalog.json`. When creating a link:

1. Get the parent item's type
2. Look up allowed child types from the mapping
3. Check compatibility using prefix matching:

```python
def _check_item_type_compatible(self, item_type, supported_item_types):
    for supported_item_type in supported_item_types:
        if (
            item_type == supported_item_type
            or item_type.startswith(supported_item_type + ".")
        ):
            return True
    return False
```

This means `operator.python` is compatible with a parent that supports `operator`, because `"operator.python".startswith("operator.")` is true.

### Type Hierarchy Walk

If a direct match isn't found, the system walks up the type hierarchy:

```python
while item_type:
    supported_item_types = manager.get_supported_item_types(item_type)
    if supported_item_types or "." not in item_type:
        break
    item_type = item_type.rsplit(".")[0]  # "operator.python" → "operator"
```

---

## Link CRUD Operations

All link operations go through `LinkRepository` in `backend/src/core/catalog/link/repo.py`.

### Create Link

**Internal (during item creation):**

```python
# Hard link — created automatically in _create_linkable_item()
link = CreateLink(
    child_laui=item_laui,
    parent_laui=item.parent_laui,
    child_type=item.item_type,
    parent_type=parent_item_type,
    true_parent=True,
)
await link_repo.create_link(link)

# Root link — parent_laui is null
link = CreateLink(
    child_laui=item_laui,
    child_type=item.item_type,
    true_parent=True,
)
await link_repo.create_link(link)
```

**External (via API):**

```
POST /api/v1/catalog/create/link
```

Request body:
```json
{
  "parent_laui": "ObjectId",
  "child_laui": "ObjectId"
}
```

**Validation performed:**
1. **Access check**: User must have edit access on parent, view access on child
2. **Trash folder check**: `parent_laui` cannot be the trash folder
3. **Both items must exist**: Parent and child are fetched from the items collection
4. **Type compatibility**: Child's `item_type` must be allowed under parent's type (non-folder types only for explicit links)
5. **Duplicate check**: No existing link (hard or soft) between the same parent-child pair

**Important:** Links created via the API endpoint are always **soft links** (`true_parent=false`). Hard links are only created internally during item creation.

### Read Links

**By primary key:**

```python
await link_repo.get_link_by_pk(child_laui=child, parent_laui=parent)
# Returns single Link or raises NotFoundError
```

**By filter:**

```python
await link_repo.find_links(
    filter={"parent_laui": parent_id, "child_type": {"$regex": "^task"}},
    offset=0,
    limit=10
)
# Returns List[Link]
```

**Parent lookup (GraphLookup):**

```python
await link_repo.parent_links_lookup(child_laui=item_id, depth=5)
```

Uses MongoDB `$graphLookup` to traverse the parent chain upward. Follows only hard links (`true_parent=true`). Returns links sorted by `created_at` (descending). Used for breadcrumb navigation.

**Children lookup (GraphLookup):**

```python
await link_repo.children_links_lookup(link_laui=link_id, true_parent=True)
```

Uses MongoDB `$graphLookup` to find all descendants. Can filter by `true_parent`:
- `true_parent=True` — only hard children (for cascade delete)
- `true_parent=False` — only soft references
- `true_parent=None` — all links

### Delete Links

```python
await link_repo.delete_links(link_lauis=[id1, id2, id3])
# Bulk delete by LAUI list using $in query
```

Links are never deleted individually — they're always deleted in bulk as part of item deletion or relationship cleanup.

### Pagination

```python
has_next = await link_repo.check_next_page_exists(
    filter=link_filters,
    offset=current_offset,
    limit=page_size
)
# Checks if at least one more record exists beyond the current page
```

---

## Automatic Linking on Task Creation

When a task is created, the system automatically creates soft links from referenced items to the task. This happens in `CatalogService._link_task_and_its_paramaters()`.

### Auto-Link Mapping

| Task Field | Link Direction | Link LAUIs Stored On Task |
|------------|---------------|--------------------------|
| `operator_laui` | operator → task | `link_operator_laui` |
| `connection_laui` | connection → task | `link_connection_laui` |
| `payload_laui` | payload → task | `link_payload_laui` |
| `attached_config_lauis` | config → task (per config) | `link_config_lauis[]` |

### Flow

```python
async def _link_task_and_its_paramaters(self, item_laui, item):
    if item.operator_laui:
        link_laui = await self.create_link(
            CreateLinkRequest(parent_laui=item.operator_laui, child_laui=item_laui)
        )
        item.link_operator_laui = link_laui

    if item.connection_laui:
        link_laui = await self.create_link(
            CreateLinkRequest(parent_laui=item.connection_laui, child_laui=item_laui)
        )
        item.link_connection_laui = link_laui

    if item.payload_laui:
        link_laui = await self.create_link(
            CreateLinkRequest(parent_laui=item.payload_laui, child_laui=item_laui)
        )
        item.link_payload_laui = link_laui

    if item.attached_config_lauis:
        item.link_config_lauis = []
        for config_laui in item.attached_config_lauis:
            link_laui = await self.create_link(
                CreateLinkRequest(parent_laui=config_laui, child_laui=item_laui)
            )
            item.link_config_lauis.append(link_laui)
```

The resulting link LAUIs are stored on the task item for quick reference without needing to query the links collection.

---

## Task Dependency Links

Tasks can depend on other tasks. Dependencies are managed through soft links and enforced at runtime.

### Creation-Time Linking

When a task is created with a `LeastActionCheckIfAreParentsDone` pre-action in its `actions.pre_actions`, the orchestrator:

1. Extracts parent task names from `action.action_variables.parents`
2. Searches for each parent task by name (same project, account, partition)
3. Creates a soft link: parent task → child task

```python
# In ItemOrchestrator._link_tasks()
for parent_task in parent_tasks:
    parent_task_laui = await self._get_parent_task_laui(parent_task, task_data)
    await self.catalog_service.link_tasks(parent_task_laui, task_laui)
```

```python
# CatalogService.link_tasks() creates a soft link
await self.link_repo.create_link(
    CreateLink(
        parent_laui=task_laui1,
        child_laui=task_laui2,
        child_type="task",
        parent_type="task",
        true_parent=False  # Soft link
    )
)
```

### Runtime Dependency Linking

The `LeastActionLinkParents` action (`backend/actions/LeastActionLinkParents.py`) manages task dependencies dynamically at runtime:

1. Gets existing parent links for the task
2. Compares with the desired parents from action variables
3. Deletes links for parents that were removed
4. Creates links for newly added parents

This allows task dependencies to be modified without recreating the task.

---

## Hierarchical Traversal

The `ItemDirectory` class (`backend/src/core/catalog/item_directory.py`) builds a tree structure from links for hierarchical display.

### How It Works

The `ItemDirectory` is a levelled tree that starts with root nodes and grows level by level:

```
Initialize → [root_laui_1, root_laui_2]
Add level 1 → children of root_laui_1, children of root_laui_2
Add level 2 → children of level 1 items
...
Flatten → get all LAUIs across all levels
Fill → fetch actual items and populate the tree
```

### Traversal Flow (in CatalogService)

**Child traversal** (`parent_or_child=child`):

```
1. Start with item_laui
2. Query links: { parent_laui: item_laui, child_type: { $regex: "^{type}" } }
3. For each link, get child's permission
4. Add children to ItemDirectory
5. Repeat for `depth` levels
6. Flatten all LAUIs → bulk fetch items → fill tree
```

**Parent traversal** (`parent_or_child=parent`):

```
1. Start with item_laui
2. Query links: { child_laui: item_laui, true_parent: true }
3. For each link, get parent's permission
4. Add parents to ItemDirectory
5. Repeat for `depth` levels
6. Flatten all LAUIs → bulk fetch items → fill tree
```

### Link Filter Construction

The `_get_link_filters()` method builds MongoDB query filters based on the request:

| Direction | Filter |
|-----------|--------|
| Child of item | `{ parent_laui: item_laui, child_type: { $regex: "^{item_type}(\\.|$)" } }` |
| Parent of item | `{ child_laui: item_laui, true_parent: true }` |
| Root items | `{ parent_laui: null }` |

The `$regex` prefix matching ensures that querying for `item_type=folder` returns `folder.workflow`, `folder.config`, etc.

### ItemDirectoryItemNode (Response Structure)

The final response returns a tree of `ItemDirectoryItemNode` objects:

```python
class ItemDirectoryItemNode(BaseModel):
    item: ItemProjection    # The actual item data
    children: List[ItemDirectoryItemNode] = []
    parents: List[ItemDirectoryItemNode] = []
```

---

## Links and Deletion

Links play a critical role in determining what happens when an item is deleted. The deletion mode depends entirely on the link type between the parent and child.

### Deletion Decision Tree

```
delete_item(item_laui, parent_laui)
  │
  ├─ Find link between parent_laui and item_laui
  │
  ├─ Is item_laui the trash folder?
  │     └─ YES → ConflictError (cannot delete trash)
  │
  ├─ Is parent_laui the trash folder? OR hard_delete=true?
  │     └─ YES → HARD DELETE
  │
  ├─ Is link.true_parent == true?
  │     └─ YES → SOFT DELETE (move to trash)
  │
  └─ Is link.true_parent == false?
        └─ YES → UNLINK (remove soft link only)
```

### Hard Delete Process

When an item is permanently deleted (from trash or with `hard_delete=true`):

1. **Get all descendant links** via `children_links_lookup(link_laui)` — returns all links (hard + soft) in the subtree
2. **Separate** into hard and soft link lists
3. **Get hard child item LAUIs** from hard links
4. **Find parent links** where the item itself is a child
5. **Find orphaned soft links** pointing to hard children from outside the tree
6. **Deduplicate** all collected links
7. **Combine** all links to delete: hard + soft + parent + orphaned
8. **Delete all links** in bulk
9. **Hard delete items**: the item + all its hard children (permanently removed from DB)

### Soft Delete Process

When an item with a hard-link parent is deleted:

1. **Get all hard descendants** via `children_links_lookup(link_laui, true_parent=True)`
2. **Collect LAUIs** of all hard children + the item itself
3. **Set `deleted_at`** on all items (soft delete)
4. **Create soft link** from trash folder to the item: `CreateLink(parent_laui=trash_laui, child_laui=item_laui, true_parent=False, child_type=..., parent_type="folder.trash")`
5. **Delete the original hard link** between the item and its parent

### Soft Link Deletion (Unlink)

When a soft link is deleted, only the link record is removed. The item itself is untouched:

```python
await self.link_repo.delete_links(link_lauis=[ObjectId(link.laui)])
```

---

## Frontend Link Management

### LinkModal Component

Located at `frontend/src/components/Browse/LinkModal.tsx`, the `LinkModal` provides a UI for creating soft links between items.

**Props:**
- `parentItem` — the item that will become the child in the link
- `availableItems` — list of candidate parent items

**User flow:**
1. User selects an item and opens the link modal
2. Modal shows a searchable dropdown (MUI Autocomplete) of available parent items
3. User can also manually enter a parent LAUI
4. Client-side validation:
   - Parent LAUI is required
   - Child item is required
   - Parent and child cannot be the same item
5. On submit, calls `POST /api/v1/catalog/create/link`
6. Displays success or error feedback

### Frontend Service

The `catalog.service.ts` file provides the API wrapper:

```typescript
createCatalogLink(parentLaui: string, childLaui: string)
// POST /api/v1/catalog/create/link
// Body: { parent_laui, child_laui }
// Returns: { link_laui: string }
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/catalog/create/link` | Create a soft link between two items |
| `POST` | `/api/v1/catalog/delete` | Delete item — link type determines behavior |

### Create Link

**Request:**
```json
{
  "parent_laui": "ObjectId (required)",
  "child_laui": "ObjectId (required)"
}
```

**Response:**
```json
{
  "link_laui": "string"
}
```

**Access required:** Edit on parent, View on child

**Errors:**
- `400` — Parent is trash folder
- `400` — Child type not compatible with parent
- `400` — Hard link already exists
- `400` — Soft link already exists
- `404` — Parent or child item not found
- `403` — Insufficient permissions

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/src/core/catalog/link/schema.py` | Link Pydantic models (_BaseLink, CreateLink, Link, LinkWithPermission) |
| `backend/src/core/catalog/link/repo.py` | LinkRepository — MongoDB CRUD, GraphLookup queries |
| `backend/src/core/catalog/service.py` | CatalogService — link creation, validation, deletion orchestration |
| `backend/src/core/catalog/orchestrator.py` | ItemOrchestrator — task linking, dependency linking |
| `backend/src/core/catalog/item_directory.py` | ItemDirectory — tree traversal using links |
| `backend/src/core/api/routes/catalog.py` | FastAPI route for link creation |
| `backend/src/core/catalog/api_request.py` | CreateLinkRequest, CreateLinkResponse schemas |
| `config/catalog.json` | Type compatibility rules (item_type_link_mapping) |
| `backend/src/core/catalog/utils/catalog/catalog_manager.py` | SupportedItemTypesManager — type compatibility checks |
| `backend/actions/LeastActionLinkParents.py` | Runtime task dependency link management |
| `frontend/src/components/Browse/LinkModal.tsx` | Frontend UI for creating links |
| `frontend/src/services/catalog.service.ts` | Frontend API service for link operations |
